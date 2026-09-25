"""Adaptador Debug Adapter Protocol (DAP) para o AdvPL TestLab."""

import contextlib
import copy
import json
import sys
import threading
import traceback
from pathlib import Path

from debug_runtime import (
    DebugController, DebugFixtureInterpreter, DebugStopped, source_key,
    statement_line,
)
from executor import discover_entry, discover_fixture, discover_source_units
from fixture_runtime import Fixture, FixtureError, compile_sources
from state_store import load_state, save_state


def executable_lines(program):
    result = {}

    def visit(stmt, lines):
        if isinstance(stmt, list):
            for item in stmt:
                visit(item, lines)
            return
        line = statement_line(stmt)
        if line is not None:
            lines.add(line)
        for name in ("body", "else_body", "otherwise_body", "recover_body"):
            child = getattr(stmt, name, None)
            if isinstance(child, list):
                visit(child, lines)
        for branch in getattr(stmt, "branches", ()):
            if isinstance(branch, tuple) and len(branch) == 2:
                visit(branch[1], lines)

    for decl in (*program.functions, *program.methods):
        key = source_key(decl.source_path)
        lines = result.setdefault(key, set())
        visit(decl.body, lines)
    return result


class _Output:
    def __init__(self, adapter, category):
        self.adapter = adapter
        self.category = category

    def write(self, value):
        if value:
            self.adapter.event("output", {"category": self.category, "output": value})
        return len(value)

    def flush(self):
        pass


class DebugAdapter:
    def __init__(self, input_stream=None, output_stream=None):
        self.input = input_stream or sys.stdin.buffer
        self.output = output_stream or sys.stdout.buffer
        self.output_lock = threading.Lock()
        self.sequence = 1
        self.controller = None
        self.runtime = None
        self.program = None
        self.entry = None
        self.entry_args = []
        self.mvc_case = None
        self.state_path = None
        self.initial_records = None
        self.worker = None
        self._variables = {}
        self._next_reference = 1

    def send(self, message):
        with self.output_lock:
            message["seq"] = self.sequence
            self.sequence += 1
            payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
            self.output.write(f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii"))
            self.output.write(payload)
            self.output.flush()

    def response(self, request, body=None, error=None):
        result = {
            "type": "response", "request_seq": request["seq"],
            "command": request["command"], "success": error is None,
        }
        if body is not None:
            result["body"] = body
        if error is not None:
            result["message"] = str(error)
        self.send(result)

    def event(self, name, body=None):
        result = {"type": "event", "event": name}
        if body is not None:
            result["body"] = body
        self.send(result)

    def read(self):
        headers = {}
        while True:
            line = self.input.readline()
            if not line:
                return None
            if line in (b"\r\n", b"\n"):
                break
            name, separator, value = line.decode("ascii").partition(":")
            if separator:
                headers[name.lower()] = value.strip()
        length = int(headers["content-length"])
        payload = self.input.read(length)
        if len(payload) != length:
            return None
        return json.loads(payload)

    def launch(self, arguments):
        program_path = Path(arguments["program"]).resolve()
        if not program_path.is_file():
            raise ValueError(f"Fonte PRW nao encontrado: '{program_path}'")
        fixture_path = (Path(arguments["fixture"]).resolve()
                        if arguments.get("fixture") else discover_fixture(program_path))
        units = discover_source_units(program_path)
        fixture = Fixture.from_file(fixture_path)
        self.program = compile_sources(
            units, fixture=fixture,
            name_profile=arguments.get("nameProfile", "modern"),
        )
        self.controller = DebugController(
            on_stopped=lambda reason: self.event(
                "stopped", {"reason": reason, "threadId": 1, "allThreadsStopped": True}
            ),
            stop_on_entry=bool(arguments.get("stopOnEntry", False)),
        )
        self.runtime = DebugFixtureInterpreter(
            self.program, self.controller, fixture=fixture,
            source_name=program_path,
            entry_name=arguments.get("entry") or discover_entry(units[0][1]),
            name_profile=arguments.get("nameProfile", "modern"),
        )
        self.entry = arguments.get("entry") or discover_entry(units[0][1])
        self.entry_args = arguments.get("args", [])
        if not isinstance(self.entry_args, list):
            raise ValueError("args deve ser um array JSON")
        self.mvc_case = arguments.get("mvcCase")
        if self.mvc_case is not None:
            case = fixture.cenarios_mvc.get(self.mvc_case)
            if case is None:
                raise ValueError(f"Cenario MVC '{self.mvc_case}' nao encontrado")
            self.runtime.mvc_case = case
        if arguments.get("persist", False):
            self.state_path = fixture_path.parent / "state.json"
            for alias, records in load_state(self.state_path, fixture.tabelas).items():
                self.runtime._aliases[alias].records = copy.deepcopy(records)
                self.runtime._aliases[alias].position = 0
            self.initial_records = {
                alias: copy.deepcopy(self.runtime._aliases[alias].records)
                for alias in fixture.tabelas
            }

    def _run(self):
        try:
            with contextlib.redirect_stdout(_Output(self, "stdout")):
                self.runtime.run(self.entry, self.entry_args)
            if self.mvc_case is not None and self.runtime.mvc_result is None:
                raise FixtureError(
                    f"Cenario MVC '{self.mvc_case}' nao foi executado: entrada nao ativou browse"
                )
            if self.state_path is not None:
                final = {
                    alias: self.runtime._aliases[alias].records
                    for alias in self.runtime.fixture.tabelas
                }
                if final != self.initial_records:
                    save_state(self.state_path, final)
            self.event("exited", {"exitCode": 0})
        except DebugStopped:
            self.event("exited", {"exitCode": 0})
        except Exception as exc:
            self.event("output", {
                "category": "stderr", "output": f"{type(exc).__name__}: {exc}\n",
            })
            self.event("exited", {"exitCode": 1})
        finally:
            self.event("terminated")

    def _reference(self, value):
        number = self._next_reference
        self._next_reference += 1
        self._variables[number] = value
        return number

    def _variable(self, name, value):
        if isinstance(value, (list, dict)):
            reference = self._reference(value)
            display = f"{type(value).__name__} ({len(value)})"
        else:
            reference = 0
            display = "NIL" if value is None else str(value)
        return {"name": str(name), "value": display, "variablesReference": reference}

    def _handle(self, request):
        command = request["command"]
        args = request.get("arguments") or {}
        if command == "initialize":
            self.response(request, {
                "supportsConfigurationDoneRequest": True,
                "supportsTerminateRequest": True,
            })
        elif command == "launch":
            self.launch(args)
            self.response(request)
            self.event("initialized")
        elif command == "setBreakpoints":
            path = args["source"]["path"]
            valid_lines = executable_lines(self.program).get(source_key(path), set())
            requested = [item["line"] for item in args.get("breakpoints", [])]
            verified = [line for line in requested if line in valid_lines]
            self.controller.set_breakpoints(path, verified)
            self.response(request, {"breakpoints": [
                {"verified": line in valid_lines, "line": line}
                for line in requested
            ]})
        elif command == "configurationDone":
            self.response(request)
            self.worker = threading.Thread(target=self._run, daemon=True)
            self.worker.start()
        elif command == "threads":
            self.response(request, {"threads": [{"id": 1, "name": "AdvPL TestLab"}]})
        elif command == "stackTrace":
            frames = self.runtime.stack_frames() if self.controller.paused else []
            self.response(request, {"stackFrames": frames, "totalFrames": len(frames)})
        elif command == "scopes":
            if not self.controller.paused:
                raise ValueError("A execucao precisa estar pausada")
            locals_, privates = self.runtime.frame_values(args["frameId"])
            self.response(request, {"scopes": [
                {"name": "Locais", "variablesReference": self._reference(locals_), "expensive": False},
                {"name": "Privadas", "variablesReference": self._reference(privates), "expensive": False},
                {"name": "Globais", "variablesReference": self._reference(self.runtime.globals), "expensive": False},
            ]})
        elif command == "variables":
            value = self._variables.get(args["variablesReference"])
            if value is None:
                raise ValueError("Referencia de variaveis desconhecida")
            pairs = enumerate(value, start=1) if isinstance(value, list) else value.items()
            self.response(request, {"variables": [
                self._variable(name, item) for name, item in pairs
            ]})
        elif command in ("continue", "next", "stepIn", "stepOut"):
            mode = "continue" if command == "continue" else command
            resumed = self.controller.resume(
                mode, len(self.runtime.call_stack), self.runtime._statement_depth
            )
            if not resumed:
                raise ValueError("A execucao nao esta pausada")
            self._variables.clear()
            self.response(request, {"allThreadsContinued": True} if command == "continue" else None)
        elif command == "pause":
            self.controller.pause()
            self.response(request)
        elif command in ("disconnect", "terminate"):
            if self.controller is not None:
                self.controller.terminate()
            self.response(request)
        else:
            raise ValueError(f"Comando DAP '{command}' nao suportado")

    def serve(self):
        while True:
            request = self.read()
            if request is None:
                if self.controller is not None:
                    self.controller.terminate()
                return
            if request.get("type") != "request":
                continue
            try:
                self._handle(request)
            except Exception as exc:
                self.response(request, error=exc)
                if request.get("command") == "launch":
                    self.event("output", {
                        "category": "stderr", "output": traceback.format_exc(),
                    })


def main():
    DebugAdapter().serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
