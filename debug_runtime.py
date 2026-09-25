"""Pontos de pausa no interpretador AdvPL, sem dependência do VS Code."""

from pathlib import Path
from threading import Condition

from fixture_runtime import FixtureInterpreter


def source_key(path):
    return str(Path(path).resolve()).casefold()


def statement_line(stmt):
    if isinstance(stmt, list):
        return None
    line = getattr(stmt, "line", None)
    if line is not None:
        return line
    for name in ("expr", "target", "cond", "start"):
        line = getattr(getattr(stmt, name, None), "line", None)
        if line is not None:
            return line
    expressions = getattr(stmt, "exprs", None)
    if expressions:
        return getattr(expressions[0], "line", None)
    branches = getattr(stmt, "branches", None)
    if branches:
        return getattr(branches[0][0], "line", None)
    return None


class DebugStopped(Exception):
    """A sessão foi encerrada durante uma pausa."""


class DebugController:
    def __init__(self, on_stopped=None, stop_on_entry=False):
        self.condition = Condition()
        self.on_stopped = on_stopped or (lambda reason: None)
        self.breakpoints = {}
        self.stop_on_entry = stop_on_entry
        self.mode = "continue"
        self.target_frame_depth = 0
        self.target_statement_depth = 0
        self.paused = False
        self.terminated = False
        self.pause_requested = False

    def set_breakpoints(self, path, lines):
        with self.condition:
            self.breakpoints[source_key(path)] = set(lines)

    def before_statement(self, path, line, frame_depth, statement_depth):
        if line is None:
            return
        with self.condition:
            if self.terminated:
                raise DebugStopped()
            breakpoint = line in self.breakpoints.get(source_key(path), ())
            step = (
                self.mode == "stepIn"
                or (self.mode == "next" and frame_depth <= self.target_frame_depth
                    and statement_depth <= self.target_statement_depth)
                or (self.mode == "stepOut" and frame_depth < self.target_frame_depth)
            )
            if not (self.stop_on_entry or breakpoint or step or self.pause_requested):
                return
            reason = ("entry" if self.stop_on_entry else "breakpoint" if breakpoint
                      else "pause" if self.pause_requested else "step")
            self.stop_on_entry = False
            self.pause_requested = False
            self.mode = "continue"
            self.paused = True
        self.on_stopped(reason)
        with self.condition:
            while self.paused and not self.terminated:
                self.condition.wait()
            if self.terminated:
                raise DebugStopped()

    def resume(self, mode, frame_depth, statement_depth):
        with self.condition:
            if not self.paused:
                return False
            self.mode = mode
            self.target_frame_depth = frame_depth
            self.target_statement_depth = statement_depth
            self.paused = False
            self.condition.notify_all()
            return True

    def pause(self):
        with self.condition:
            self.pause_requested = True

    def terminate(self):
        with self.condition:
            self.terminated = True
            self.paused = False
            self.condition.notify_all()


class DebugFixtureInterpreter(FixtureInterpreter):
    def __init__(self, program, controller, **kwargs):
        self.debug_controller = controller
        self._statement_depth = 0
        self._frame_locations = {}
        super().__init__(program, **kwargs)
        self._source_by_function = {
            self.name_policy.key(decl.name): str(decl.source_path)
            for decl in program.functions
        }
        self._source_by_function.update({
            f"{self.name_policy.key(decl.class_name)}."
            f"{self.name_policy.key(decl.method_name)}": str(decl.source_path)
            for decl in program.methods
        })

    def _source_for_frame(self, frame_index):
        for frame in reversed(self.call_stack[:frame_index + 1]):
            path = self._source_by_function.get(frame.func_name)
            if path is not None:
                return path
        return str(self.source_name)

    def exec_stmt(self, stmt):
        if not isinstance(stmt, list) and self.call_stack:
            line = statement_line(stmt)
            if line is not None:
                frame = self.call_stack[-1]
                path = self._source_for_frame(len(self.call_stack) - 1)
                self._frame_locations[id(frame)] = (path, line)
                self.debug_controller.before_statement(
                    path, line, len(self.call_stack), self._statement_depth
                )
        self._statement_depth += 1
        try:
            return super().exec_stmt(stmt)
        finally:
            self._statement_depth -= 1

    def stack_frames(self):
        result = []
        for index in range(len(self.call_stack) - 1, -1, -1):
            frame = self.call_stack[index]
            path, line = self._frame_locations.get(
                id(frame), (self._source_for_frame(index), 1)
            )
            result.append({
                "id": index + 1,
                "name": frame.func_name,
                "source": {"name": Path(path).name, "path": path},
                "line": line,
                "column": 1,
            })
        return result

    def frame_values(self, frame_id):
        index = frame_id - 1
        if not 0 <= index < len(self.call_stack):
            raise ValueError(f"Frame {frame_id} nao existe")
        frame = self.call_stack[index]
        return frame.locals, frame.privates
