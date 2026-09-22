User Function SolMailCfg()
    Local cConta := AllTrim(GetMV("MV_RELACNT", .F., ""))
    Local aSMTP := { ;
        AllTrim(GetMV("MV_RELSERV", .F., "")), ;
        cConta, ;
        GetMV("MV_RELPSW", .F., ""), ;
        AllTrim(GetMV("MV_RELFROM", .F., cConta)), ;
        GetMV("MV_PORSMTP", .F., 0), ;
        GetMV("MV_RELAUTH", .F., .T.), ;
        GetMV("MV_RELSSL", .F., .F.), ;
        GetMV("MV_RELTLS", .F., .F.) }
Return(aSMTP)

Static Function TextoHtml(cTexto)
    cTexto := StrTran(AllTrim(cTexto), "&", "&amp;")
    cTexto := StrTran(cTexto, "<", "&lt;")
    cTexto := StrTran(cTexto, ">", "&gt;")
    cTexto := StrTran(cTexto, '"', "&quot;")
    cTexto := StrTran(cTexto, "'", "&#39;")
    cTexto := StrTran(cTexto, CRLF, Chr(10))
    cTexto := StrTran(cTexto, Chr(13), Chr(10))
Return(StrTran(cTexto, Chr(10), "<br>"))
