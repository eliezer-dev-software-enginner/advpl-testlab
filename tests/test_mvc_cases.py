import unittest

from fixture_runtime import Fixture, FixtureError, compile_source, run_source, run_sources
from interpreter import AdvPLRuntimeError
from semantic import SemanticError


SOURCE = """User Function DemoMvc()
Local oBrowse := FWMBrowse():New()
Private cCadastro := 'Livros'
oBrowse:SetAlias('ZA1')
oBrowse:SetDescription(cCadastro)
oBrowse:Activate()
Return NIL

Static Function ModelDef()
Local oStruct := FWFormStruct(1, 'ZA1')
Local oModel := MPFormModel():New('ZA1', , { |oModel| VldSalvar(oModel) })
oModel:AddFields('ZA1MASTER', , oStruct)
oModel:SetPrimaryKey({'ZA1_COD'})
oModel:SetDescription(cCadastro)
Return oModel

Static Function VldSalvar(oModel)
Local nPreco := oModel:GetValue('ZA1MASTER', 'ZA1_PRECO')
If nPreco < 0
    MsgAlert('Preco negativo')
    Return .F.
EndIf
Return .T.
"""


def make_fixture():
    return Fixture.from_dict({
        "tabelas": [{"ZA1": {
            "campos": [
                {"nome": "ZA1_COD", "tipo": "C"},
                {"nome": "ZA1_PRECO", "tipo": "N"},
            ],
            "registros": [{"ZA1_COD": "001", "ZA1_PRECO": 10}],
        }}],
        "cenariosMvc": [
            {"nome": "bloqueado", "operacao": "incluir",
             "dados": {"ZA1MASTER": {"ZA1_COD": "002", "ZA1_PRECO": -1}},
             "esperado": {"salvou": False, "totalRegistros": 1}},
            {"nome": "valido", "operacao": "incluir",
             "dados": {"ZA1MASTER": {"ZA1_COD": "002", "ZA1_PRECO": 20}},
             "esperado": {"salvou": True, "totalRegistros": 2}},
        ],
    })


class MvcCaseTests(unittest.TestCase):
    def run_case(self, fixture, name):
        return run_sources([("demo.prw", SOURCE)], fixture=fixture,
                           entry="DemoMvc", mvc_case=name)

    def test_rejected_inclusion_keeps_original_record(self):
        fixture = make_fixture()
        result = self.run_case(fixture, "bloqueado")
        self.assertFalse(result["salvou"])
        self.assertEqual([{"ZA1_COD": "001", "ZA1_PRECO": 10}], result["registros"])
        self.assertEqual(1, len(fixture.tabelas["ZA1"]["registros"]))

    def test_valid_inclusion_exists_only_in_runtime(self):
        fixture = make_fixture()
        result = self.run_case(fixture, "valido")
        self.assertTrue(result["salvou"])
        self.assertEqual("002", result["registros"][-1]["ZA1_COD"])
        self.assertEqual(1, len(fixture.tabelas["ZA1"]["registros"]))

    def test_expected_result_mismatch_fails(self):
        fixture = make_fixture()
        fixture.cenarios_mvc["valido"]["esperado"]["salvou"] = False
        with self.assertRaisesRegex(FixtureError, "esperado salvou=False"):
            self.run_case(fixture, "valido")

    def test_expected_record_mismatch_fails(self):
        fixture = make_fixture()
        fixture.cenarios_mvc["valido"]["esperado"]["registro"] = {
            "ZA1_COD": "wrong", "ZA1_PRECO": 20,
        }
        with self.assertRaisesRegex(FixtureError, "ultimo registro difere"):
            self.run_case(fixture, "valido")

    def test_unknown_case_fails(self):
        with self.assertRaisesRegex(FixtureError, "nao encontrado"):
            self.run_case(make_fixture(), "ausente")

    def test_unknown_field_fails(self):
        fixture = make_fixture()
        fixture.cenarios_mvc["valido"]["dados"]["ZA1MASTER"]["ZA1_X"] = "x"
        with self.assertRaisesRegex(FixtureError, "ZA1_X"):
            self.run_case(fixture, "valido")

    def test_missing_value_read_by_post_block_fails_explicitly(self):
        fixture = make_fixture()
        del fixture.cenarios_mvc["valido"]["dados"]["ZA1MASTER"]["ZA1_PRECO"]
        with self.assertRaisesRegex(AdvPLRuntimeError, "ZA1_PRECO.*ausente"):
            self.run_case(fixture, "valido")

    def test_case_schema_requires_boolean_expectation(self):
        with self.assertRaisesRegex(FixtureError, "esperado.salvou"):
            Fixture.from_dict({"cenariosMvc": [{"nome": "x", "operacao": "incluir",
                                                  "dados": {"M": {}},
                                                  "esperado": {"salvou": 1}}]})

    def test_literal_unknown_submodel_fails_without_mvc_case(self):
        source = SOURCE.replace("GetValue('ZA1MASTER'", "GetValue('ZA1MASTE'")
        with self.assertRaisesRegex(SemanticError, "ZA1MASTE") as error:
            compile_source(source, fixture=make_fixture())
        self.assertEqual(18, error.exception.line)
        with self.assertRaisesRegex(SemanticError, "ZA1MASTE"):
            run_source(source, fixture=make_fixture(), entry="DemoMvc")

    def test_literal_known_submodel_is_case_insensitive(self):
        source = SOURCE.replace("GetValue('ZA1MASTER'", "GetValue('za1master'")
        compile_source(source, fixture=make_fixture())

    def test_dynamic_submodel_id_is_checked_at_runtime(self):
        source = SOURCE.replace(
            "Local nPreco := oModel:GetValue('ZA1MASTER', 'ZA1_PRECO')",
            "Local cId := 'ZA1MASTE'\nLocal nPreco := oModel:GetValue(cId, 'ZA1_PRECO')",
        )
        compile_source(source, fixture=make_fixture())
        with self.assertRaisesRegex(AdvPLRuntimeError, "ZA1MASTE"):
            run_sources([("demo.prw", source)], fixture=make_fixture(),
                        entry="DemoMvc", mvc_case="valido")

    def test_dynamic_addfields_id_does_not_cause_static_false_positive(self):
        source = SOURCE.replace(
            "oModel:AddFields('ZA1MASTER', , oStruct)",
            "Local cSub := 'ZA1MASTER'\noModel:AddFields(cSub, , oStruct)",
        ).replace("GetValue('ZA1MASTER'", "GetValue('ZA1MASTE'")
        compile_source(source, fixture=make_fixture())
        with self.assertRaisesRegex(AdvPLRuntimeError, "ZA1MASTE"):
            run_sources([("demo.prw", source)], fixture=make_fixture(),
                        entry="DemoMvc", mvc_case="valido")


if __name__ == "__main__":
    unittest.main()
