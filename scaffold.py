import json
import re
from pathlib import Path

from fixture_runtime import FixtureError


MVC1_SOURCE = '''#Include "TOTVS.CH"
#Include "FWMVCDef.ch"

User Function @TABLE@MVC()
    Local oBrowse := FWMBrowse():New()
    oBrowse:SetAlias('@TABLE@')
    oBrowse:SetDescription('Cadastro @TABLE@')
    oBrowse:Activate()
Return NIL

Static Function MenuDef()
    Local aRotina := {}
    ADD OPTION aRotina TITLE 'Visualizar' ACTION 'VIEWDEF.@TABLE@MVC' OPERATION 2 ACCESS 0
    ADD OPTION aRotina TITLE 'Incluir' ACTION 'VIEWDEF.@TABLE@MVC' OPERATION 3 ACCESS 0
    ADD OPTION aRotina TITLE 'Alterar' ACTION 'VIEWDEF.@TABLE@MVC' OPERATION 4 ACCESS 0
    ADD OPTION aRotina TITLE 'Excluir' ACTION 'VIEWDEF.@TABLE@MVC' OPERATION 5 ACCESS 0
Return aRotina

Static Function ModelDef()
    Local oStruct := FWFormStruct(1, '@TABLE@')
    Local oModel := MPFormModel():New('MODEL_@TABLE@', , {|oModel| .T.})
    oModel:AddFields('@TABLE@MASTER', , oStruct)
    oModel:SetPrimaryKey({'@TABLE@_FILIAL', '@TABLE@_COD'})
    oModel:SetDescription('Cadastro @TABLE@')
Return oModel

Static Function ViewDef()
    Local oModel := FWLoadModel('@TABLE@MVC')
    Local oStruct := FWFormStruct(2, '@TABLE@')
    Local oView := FWFormView():New()
    oView:SetModel(oModel)
    oView:AddField('VIEW_@TABLE@', oStruct, '@TABLE@MASTER')
    oView:CreateHorizontalBox('BOX_@TABLE@', 100)
    oView:SetOwnerView('VIEW_@TABLE@', 'BOX_@TABLE@')
Return oView
'''


def create_mvc1(table='ZA1'):
    table = table.upper()
    if not re.fullmatch(r'[A-Z][A-Z0-9]{2}', table, flags=re.ASCII):
        raise FixtureError('--table deve ser um alias de tres caracteres, como ZA4')
    source_directory = Path.cwd() / 'Fontes'
    source_path = source_directory / f'{table}MVC.prw'
    fixture_path = Path.cwd() / 'mock.jsonc'
    for path in (source_path, fixture_path):
        if path.exists() or path.is_symlink():
            raise FixtureError(f'Arquivo ja existe: {path}; nenhum arquivo foi criado')
    record = {f'{table}_FILIAL': '01', f'{table}_COD': '000001',
              f'{table}_DESC': 'Exemplo de cadastro'}
    fixture = {
        'parametros': [],
        'tabelas': [{table: {
            'campos': [{'nome': field, 'tipo': 'C'} for field in record],
            'registros': [],
        }}],
        'funcoes': [], 'ambiente': [], 'dialogos': [],
        'especificidadesPrw': [], 'consultas': [],
        'cenariosMvc': [{
            'nome': 'incluir-registro', 'operacao': 'incluir',
            'dados': {f'{table}MASTER': record},
            'esperado': {'salvou': True, 'totalRegistros': 1, 'registro': record},
        }],
    }
    comments = {
        'parametros': 'Valores consultados por GetMV().',
        'tabelas': 'Campos de exemplo: ajuste ao SX3 da tabela real.',
        'funcoes': 'Retornos simulados de funcoes.',
        'ambiente': 'Variaveis do ambiente, como DDATABASE e TIME.',
        'dialogos': 'Respostas de dialogos simulados.',
        'especificidadesPrw': 'Configuracoes especificas por fonte PRW.',
        'consultas': 'Resultados simulados de consultas.',
        'cenariosMvc': 'Inclusao simulada; nao cria tabela no Protheus.',
    }
    fixture_text = json.dumps(fixture, indent=2, ensure_ascii=False) + '\n'
    for key, comment in comments.items():
        fixture_text = fixture_text.replace(f'  "{key}":', f'  // {comment}\n  "{key}":', 1)
    created = []
    created_directory = False
    try:
        if not source_directory.exists():
            source_directory.mkdir()
            created_directory = True
        for path, content in (
            (source_path, MVC1_SOURCE.replace('@TABLE@', table)),
            (fixture_path, fixture_text),
        ):
            with path.open('x', encoding='utf-8') as output:
                created.append(path)
                output.write(content)
    except OSError:
        for path in created:
            path.unlink()
        if created_directory:
            source_directory.rmdir()
        raise
    return source_path, fixture_path
