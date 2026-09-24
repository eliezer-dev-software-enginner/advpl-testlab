import unittest
from pathlib import Path

from executor import discover_fixture
from fixture_runtime import Fixture, FixtureError


class JsoncFixtureTests(unittest.TestCase):
    FIXTURES = Path(__file__).parent / "fixtures" / "jsonc"

    def test_loads_comments_trailing_commas_and_preserves_string_content(self):
        fixture = Fixture.from_file(self.FIXTURES / "comentarios.jsonc")
        self.assertEqual("https://exemplo.com/a//b/*c*/,}", fixture.parametros["URL"])
        self.assertEqual([], Fixture.read_data(self.FIXTURES / "comentarios.jsonc")["dialogos"])

    def test_json_files_remain_strict(self):
        with self.assertRaisesRegex(FixtureError, "JSON invalido"):
            Fixture.from_file(self.FIXTURES / "comentarios-invalidos.json")

    def test_discovers_jsonc_before_json_in_same_directory(self):
        source = self.FIXTURES / "rotina.prw"
        jsonc = self.FIXTURES / "testlab.jsonc"
        self.assertEqual(jsonc, discover_fixture(source))

    def test_legacy_name_remains_discoverable(self):
        source = self.FIXTURES / "legacy" / "rotina.prw"
        self.assertEqual(source.parent / "advpl-testlab.jsonc", discover_fixture(source))

    def test_unterminated_block_comment_is_reported(self):
        with self.assertRaisesRegex(FixtureError, "Comentario de bloco nao terminado"):
            Fixture.from_file(self.FIXTURES / "bloco-incompleto.jsonc")
