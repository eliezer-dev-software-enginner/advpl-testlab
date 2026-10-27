import contextlib
import io
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import main
from executor import (
    CompileError, _read_authentication, compile_source_tree, ordered_sources,
)


USE_PRW_ROOT = PROJECT_ROOT / "tests" / "fixtures" / "use_prw" / "entrada_escopo.prw"
AUTH_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "tds-auth.ini"


class RpoCompilerTests(unittest.TestCase):
    def test_recursive_plan_compiles_dependencies_before_callers(self):
        names = [path.name for path in ordered_sources(USE_PRW_ROOT)]
        self.assertEqual(
            ["util_escopo.prw", "modulo_escopo.prw", "entrada_escopo.prw"],
            names,
        )

    def test_explicit_order_can_handle_stale_rpo_during_refactor(self):
        names = [path.name for path in ordered_sources(
            USE_PRW_ROOT,
            "util_escopo.prw,entrada_escopo.prw,modulo_escopo.prw",
        )]
        self.assertEqual(
            ["util_escopo.prw", "entrada_escopo.prw", "modulo_escopo.prw"], names
        )
        with self.assertRaisesRegex(CompileError, "exatamente uma vez"):
            ordered_sources(USE_PRW_ROOT, "entrada_escopo.prw,modulo_escopo.prw")

    def test_dry_run_prints_plan_without_tds_credentials(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(0, main(["-compile", str(USE_PRW_ROOT), "--dry-run"]))
        self.assertLess(output.getvalue().index("util_escopo.prw"),
                        output.getvalue().index("entrada_escopo.prw"))

    def test_tds_script_uses_private_config_and_ordered_program_list(self):
        observed = {}

        def fake_write(path, data):
            observed[path.name] = data.decode("cp1252")
            return len(data)

        def fake_run(command, check):
            observed["command"] = command
            return SimpleNamespace(returncode=0)

        with patch("executor.tempfile.TemporaryDirectory",
                   return_value=contextlib.nullcontext(str(PROJECT_ROOT))), \
                patch.object(Path, "write_bytes", fake_write), \
                patch("executor.subprocess.run", side_effect=fake_run):
            paths = compile_source_tree(
                USE_PRW_ROOT,
                config_path=AUTH_FIXTURE,
                includes=[PROJECT_ROOT / "tests" / "fixtures"],
                cli_path=sys.executable,
            )
        self.assertEqual(3, len(paths))
        self.assertEqual([str(Path(sys.executable).resolve()), "cli"],
                         observed["command"][:2])
        self.assertNotIn("EXAMPLE_ONLY", " ".join(observed["command"]))
        self.assertIn("action=authentication", observed["compile.ini"])
        self.assertIn("action=compile", observed["compile.ini"])
        self.assertIn("recompile=T", observed["compile.ini"])
        self.assertEqual(
            ["util_escopo.prw", "modulo_escopo.prw", "entrada_escopo.prw"],
            [Path(line).name for line in observed["programs.txt"].splitlines()],
        )

    def test_missing_connected_session_returns_error_without_compiling(self):
        output = io.StringIO()
        from tds_session import TdsSessionError
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output), \
                patch('tds_session.read_connected_server', side_effect=TdsSessionError('Conecte pelo VS Code')):
            self.assertEqual(1, main(["-compile", str(USE_PRW_ROOT)]))

    def test_rejects_unrelated_rpo_actions_in_private_config(self):
        with patch.object(Path, "read_text", return_value=(
            "[authentication]\naction=authentication\n"
            "[deleteProg]\naction=deleteProg\nprogram=TRNSOL01.prw\n"
        )):
            with self.assertRaisesRegex(CompileError, "aceita somente"):
                _read_authentication(AUTH_FIXTURE)


if __name__ == "__main__":
    unittest.main()
