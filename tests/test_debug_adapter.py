import io
import json
import subprocess
import sys
import time
import unittest
from pathlib import Path

from debug_adapter import DebugAdapter


ROOT = Path(__file__).parent / "fixtures" / "debug"
DEMO = ROOT / "demo.prw"
HELPER = ROOT / "helper.prw"


def messages(buffer):
    data = buffer.getvalue()
    result = []
    while data:
        header, data = data.split(b"\r\n\r\n", 1)
        length = int(header.split(b":", 1)[1].strip())
        result.append(json.loads(data[:length]))
        data = data[length:]
    return result


class DebugAdapterTests(unittest.TestCase):
    def setUp(self):
        self.output = io.BytesIO()
        self.adapter = DebugAdapter(output_stream=self.output)
        self.seq = 0

    def request(self, command, arguments=None):
        self.seq += 1
        self.adapter._handle({
            "type": "request", "seq": self.seq,
            "command": command, "arguments": arguments or {},
        })
        response = next(item for item in reversed(messages(self.output))
                        if item["type"] == "response" and item["request_seq"] == self.seq)
        self.assertTrue(response["success"], response.get("message"))
        return response.get("body", {})

    def wait_for_pause(self):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if self.adapter.controller.paused:
                return
            time.sleep(0.01)
        self.fail("O depurador nao pausou")

    def test_breakpoint_in_useprw_step_out_and_locals(self):
        self.request("initialize")
        self.request("launch", {"program": str(DEMO), "entry": "Demo"})
        body = self.request("setBreakpoints", {
            "source": {"path": str(HELPER)},
            "breakpoints": [{"line": 2}, {"line": 99}],
        })
        self.assertEqual([True, False],
                         [item["verified"] for item in body["breakpoints"]])
        self.request("configurationDone")
        self.wait_for_pause()
        frames = self.request("stackTrace")["stackFrames"]
        self.assertEqual("helper.prw", frames[0]["source"]["name"])
        self.assertEqual(2, frames[0]["line"])
        self.assertEqual("demo.prw", frames[1]["source"]["name"])
        scopes = self.request("scopes", {"frameId": frames[0]["id"]})["scopes"]
        variables = self.request("variables", {
            "variablesReference": scopes[0]["variablesReference"]
        })["variables"]
        self.assertIn({"name": "N", "value": "1", "variablesReference": 0}, variables)
        self.request("stepOut")
        self.wait_for_pause()
        frames = self.request("stackTrace")["stackFrames"]
        self.assertEqual(5, frames[0]["line"])
        self.request("continue")
        self.adapter.worker.join(timeout=3)
        self.assertFalse(self.adapter.worker.is_alive())
        self.assertIn("terminated", [item.get("event") for item in messages(self.output)])

    def test_stop_on_entry_and_next(self):
        self.request("initialize")
        self.request("launch", {"program": str(DEMO), "stopOnEntry": True})
        self.request("configurationDone")
        self.wait_for_pause()
        self.assertEqual(3, self.request("stackTrace")["stackFrames"][0]["line"])
        self.request("next")
        self.wait_for_pause()
        self.assertEqual(4, self.request("stackTrace")["stackFrames"][0]["line"])
        self.request("next")
        self.wait_for_pause()
        self.assertEqual(5, self.request("stackTrace")["stackFrames"][0]["line"])
        self.request("continue")
        self.adapter.worker.join(timeout=3)
        self.assertFalse(self.adapter.worker.is_alive())

    def test_step_in_enters_dependency(self):
        self.request("initialize")
        self.request("launch", {"program": str(DEMO), "stopOnEntry": True})
        self.request("configurationDone")
        self.wait_for_pause()
        self.request("next")
        self.wait_for_pause()
        self.request("stepIn")
        self.wait_for_pause()
        frame = self.request("stackTrace")["stackFrames"][0]
        self.assertEqual("helper.prw", frame["source"]["name"])
        self.assertEqual(2, frame["line"])
        self.request("continue")
        self.adapter.worker.join(timeout=3)
        self.assertFalse(self.adapter.worker.is_alive())

    def test_adapter_process_speaks_dap_over_stdio(self):
        def packet(seq, command, arguments=None):
            body = json.dumps({
                "seq": seq, "type": "request", "command": command,
                "arguments": arguments or {},
            }).encode("utf-8")
            return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body

        result = subprocess.run(
            [sys.executable, "-u", "-m", "debug_adapter"],
            input=packet(1, "initialize") + packet(2, "launch", {"program": str(DEMO)}),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=Path(__file__).parent.parent, timeout=5, check=True,
        )
        self.assertEqual(b"", result.stderr)
        received = messages(io.BytesIO(result.stdout))
        self.assertEqual(["initialize", "launch"], [
            item["command"] for item in received if item["type"] == "response"
        ])
        self.assertIn("initialized", [item.get("event") for item in received])


if __name__ == "__main__":
    unittest.main()
