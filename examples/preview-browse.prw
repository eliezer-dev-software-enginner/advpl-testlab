User Function Preview()
    Local oBrowse := FWMBrowse():New()
    oBrowse:SetAlias('T01')
    oBrowse:SetDescription('Cadastro de patrimonio - exemplo')
    oBrowse:Activate()
Return NIL

Static Function MenuDef()
    Local aRotina := {}
    ADD OPTION aRotina TITLE 'Incluir' ACTION 'VIEWDEF.Preview' OPERATION 3 ACCESS 0
    ADD OPTION aRotina TITLE 'Alterar' ACTION 'VIEWDEF.Preview' OPERATION 4 ACCESS 0
    ADD OPTION aRotina TITLE 'Visualizar' ACTION 'VIEWDEF.Preview' OPERATION 2 ACCESS 0
    ADD OPTION aRotina TITLE 'Excluir' ACTION 'VIEWDEF.Preview' OPERATION 5 ACCESS 0
Return aRotina

Static Function ViewDef()
Return NIL
