# Compilacao recursiva no RPO

## Objetivo

Recompilar, por comando explicito, o fonte principal e seus `//usePrw` sem executar manualmente Ctrl+F9 em cada arquivo. A compilacao real pertence ao TDS-CLI da TOTVS; o TestLab apenas descobre, ordena e envia os caminhos.

## Desenho

- `executor.discover_source_units(..., dependencies_first=True)` percorre o mesmo grafo usado em `-run`/`-validate`, sem repetir arquivos.
- `executor.ordered_sources` produz a ordem padrao ou valida `--compile-order` completo para casos de RPO com simbolos antigos.
- `-compile --dry-run` imprime o plano sem exigir credenciais ou tocar no RPO.
- A compilacao real requer arquivo de autenticacao CP1252 privado, diretorios de include e `advpls.exe` oficial. O TestLab cria temporariamente `programs.txt` e `compile.ini` em CP1252, usa `advpls.exe cli compile.ini` e propaga falha pelo codigo de saida.
- O arquivo privado aceita somente secoes de usuario, autenticacao e autorizacao. Nenhuma acao de remocao do RPO e gerada ou aceita.

## Evidencia local

- `python main.py -compile ../desafios-aprendizado/desafio1-solicitacao-compra/TRNSOL01.prw --dry-run` descobriu `ENVEMAIL`, `NOTIFSOL`, `UTILS`, `OUACOES` e `TRNSOL01` nessa ordem.
- `python -m unittest discover -s tests -q` passou com testes de ordem, validacao da ordem explicita, script TDS temporario e rejeicao de acoes perigosas.
- Nao houve conexao nem compilacao no AppServer real; o usuario deve testar com seu arquivo privado e ambiente de desenvolvimento.

## Limites

O TestLab nao reaproveita automaticamente a conexao do TDS-VSCode nem garante que a ordem padrao resolva funcoes antigas no RPO. Para migracao de simbolos entre fontes, use `--compile-order`; se o RPO continuar inconsistente, examine os objetos com as ferramentas TOTVS. A compilacao requer acesso exclusivo ao RPO e permissoes adequadas.
