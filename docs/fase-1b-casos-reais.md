# Fase 1b — Primeiros casos reais do desafio1

## Origem

Os casos desta entrega foram extraidos de:

```text
DGB/desafios-pedro-torres/desafio1-solicitacao-compra/NOTIFSOL.prw
```

O fonte e funcional no Protheus e passa a servir como referencia concreta para a evolucao do TestLab.

## Escopo

Foram isoladas duas funcoes sem dependencia de banco, interface ou SMTP:

- `U_SolMailCfg()`: monta a configuracao SMTP usando `GetMV` com valor default.
- `TextoHtml()`: escapa texto para HTML e converte quebras de linha em `<br>`.

## Extensoes implementadas

### GetMV compativel com defaults reais

O builtin agora aceita:

```advpl
GetMV(cParam)
GetMV(cParam, lHelp)
GetMV(cParam, lHelp, uDefault)
```

Quando o parametro existe no fixture, o valor configurado vence. Quando nao existe e o terceiro argumento foi informado, o default e devolvido. Sem default, permanece o erro claro definido na Fase 1.

Codigo relevante:

```python
def b_getmv(args):
    if not 1 <= len(args) <= 3:
        raise AdvPLRuntimeError("GetMV espera de 1 a 3 argumentos")
    if not isinstance(args[0], str):
        raise AdvPLRuntimeError("GetMV espera o nome do parametro como texto")
    default = args[2] if len(args) == 3 else _MISSING
    return self.fixture.get_parameter(args[0], default=default)
```

O segundo argumento, `lHelp`, e aceito para compatibilidade de chamada, mas nao produz interface no ambiente headless.

### StrTran e Chr

Os dois builtins foram adicionados apenas porque `TextoHtml()` os usa diretamente:

```python
def b_strtran(args):
    if len(args) != 3 or not all(isinstance(value, str) for value in args):
        raise AdvPLRuntimeError("StrTran espera 3 argumentos de texto")
    return args[0].replace(args[1], args[2])

def b_chr(args):
    if len(args) != 1 or not isinstance(args[0], (int, float)):
        raise AdvPLRuntimeError("Chr espera 1 argumento numerico")
    try:
        return chr(int(args[0]))
    except ValueError as exc:
        raise AdvPLRuntimeError("Chr recebeu um codigo invalido") from exc
```

## Caso real U_SolMailCfg

Fonte isolado, preservando a logica original:

```advpl
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
```

O fixture omite `MV_RELFROM`, `MV_RELSSL` e `MV_RELTLS` de proposito. O resultado real verificado foi:

```text
{
  "smtp.exemplo.local:587",
  "conta.smtp",
  "senha-teste",
  "conta.smtp",
  587,
  .T.,
  .F.,
  .F.
}
```

## Caso real TextoHtml

Entrada usada no teste:

```text
  A&B<>"'
Linha 2
```

O valor possui espacos tambem no final da segunda linha para validar `AllTrim`.

Resultado real verificado:

```text
A&amp;B&lt;&gt;&quot;&#39;<br>Linha 2
```

## Ciclo TDD verificado

1. Os testes de `U_SolMailCfg` falharam com `GetMV espera exatamente 1 argumento`.
2. A extensao de `GetMV` foi implementada e os testes passaram.
3. O teste de `TextoHtml` falhou com `Funcao 'StrTran' nao encontrada`.
4. `StrTran` e `Chr` foram implementados e o teste passou.
5. A suite completa terminou com 9 testes aprovados.

## Fora do escopo

- Conexao ou envio SMTP.
- Classes `TMailManager` e `TMailMessage`.
- Leitura das tabelas Z02/Z03.
- Execucao integral de `NOTIFSOL.prw`.
- Interfaces produzidas pelo argumento `lHelp` de `GetMV`.
