User Function UiHeadless()
    Local oDlg := Nil

    Define MSDialog oDlg TITLE 'Cadastro sem UI' FROM 0,0 TO 100,200
    @ 010, 010 SAY oSay PROMPT 'Nome:' SIZE 040, 010 OF oDlg
    ACTIVATE DIALOG oDlg CENTER

    MsgAlert('Falha simulada', 'Atencao')
    MsgInfo('Operacao concluida', 'Resultado')

    If MsgYesNo('Continuar?', 'Teste')
        MsgInfo('Resposta configurada: sim', 'MsgYesNo')
    Else
        MsgInfo('Resposta configurada: nao', 'MsgYesNo')
    EndIf

Return Nil
