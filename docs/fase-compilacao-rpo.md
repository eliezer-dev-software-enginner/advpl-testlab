# Compilacao recursiva no RPO

## Uso

Conecte e autentique o servidor Protheus no VS Code. Na pasta do projeto:

```bash
advplab -compile Fontes/ZA4MVC.prw --dry-run
advplab -compile Fontes/ZA4MVC.prw
```

--dry-run somente lista o grafo usePrw na ordem dependencias-primeiro; nao le tokens, inicia o Language Server ou acessa o RPO. --compile-order define outra ordem completa. --include pode repetir para substituir os includes salvos. --tds-cli define o binario oficial manualmente.

## Sessao do VS Code (padrao)

O caminho e Path.home() / .totvsls / servers.json, sem usuario fixo. read_connected_server em tds_session.py exige connectedServer do tipo Protheus, ambiente e token. Prefere o savedTokens correspondente exatamente a id:ambiente, com fallback no token do servidor conectado. Nao escolhe automaticamente outro servidor nem lastConnectedServer.

Os includes do servidor prevalecem sobre os globais. Paths relativos e ${workspaceFolder} usam a pasta atual do terminal; ~ e variaveis de ambiente sao expandidos. Os diretorios devem existir. Ajuste --include quando o workspace do VS Code for diferente da pasta atual.

A autorizacao de compilacao e separada do token de sessao: builds posteriores a 7.00.191205P usam rpoToken.token quando habilitado; legados usam permissions.authorizationToken (ou authorizationtoken). Essa selecao segue o codigo da extensao TOTVS instalada.

LanguageServer inicia advpls language-server em diretorio temporario privado (inclusive logs nativos), com pipes locais e quadros JSON-RPC Content-Length em UTF-8. Responde a solicitacoes de configuracao/workspace, ignora notificacoes e limita esperas. A sequencia e initialize, initialized, $totvsserver/reconnect (connType 3) e $totvsserver/compilation com o token devolvido. O ambiente retornado precisa coincidir com o conectado. Erros FATAL/ERROR ou returnCode diferente de zero nao sao sucesso. O cliente local e encerrado em finally; nao envia disconnect para a sessao salva nem reescreve servers.json.

Referencias primarias: codigo protocolMessages.js, serversView.js, utils.js e TotvsLanguageClient.js da extensao TOTVS 2.1.6 instalada. Protocolo publico em [tds-vscode](https://github.com/totvs/tds-vscode/blob/master/src/protocolMessages.ts) e modo [language-server](https://github.com/totvs/tds-ls/blob/master/TDS-CLi.md).

## Alternativa com INI

--tds-config continua aceitando um INI CP1252 privado com [authentication] e, se necessario, [authorization]/[user]. O fluxo antigo cria programs.txt e compile.ini temporarios e executa advpls cli. Exige --include explicito e nao consulta a sessao do VS Code. Nao altere ou versione seu arquivo privado.

## Validacao e limites

Testes locais cobrem leitura do servidor, tokens por ambiente, autorizacao separada, includes, descoberta Linux, sequencia LSP, token renovado, rejeicao/ambiente divergente e erros de compilacao. Um subprocesso Python simulado valida o enquadramento JSON-RPC, Unicode, notificacoes, solicitacoes do servidor e timeout/limpeza.

Nao houve reconexao ao AppServer nem envio de fontes/RPO real nesta implementacao. A inicializacao local do advpls instalado respondeu em 30,3 segundos, dentro da espera padrao de 60 segundos; testes iniciais com 10/15 segundos expiravam cedo demais, inclusive pelo transporte vscode-jsonrpc. O handshake LSP local foi validado sem reconectar ao AppServer. Falhas de inicializacao sao propagadas sem falso sucesso. A reconexao via token e a compilacao real continuam pendentes de validacao.
