# UI headless e confirmacoes deterministicas

## Objetivo

Permitir que fontes AdvPL emitam mensagens e declarem dialogos sem SmartClient, mantendo decisoes de `MsgYesNo` explicitas no fixture.

## Desenho

- `Define MSDialog ... TITLE ... FROM ...` e adaptado antes do parser para `TestLabMSDialog(titulo)`.
- Linhas iniciadas por `@` e `Activate Dialog` viram operacoes sem efeito visual.
- `MsgAlert` imprime `[ALERTA] Titulo: Mensagem` e retorna `NIL`.
- `MsgInfo` imprime `[INFO] Titulo: Mensagem` e retorna `NIL`.
- `MsgYesNo` nao imprime texto e busca um retorno logico no fixture.

## Fixture

```json
{
  "especificidadesPrw": [
    {
      "fonte": "TRNSOL02.prw",
      "funcoes": [
        {
          "nome": "MSGYESNO",
          "conteudo": "'Gerar arquivo Excel com o resultado da consulta?', 'Consulta'",
          "retorno": false
        }
      ]
    }
  ]
}
```

A chave de busca e formada pelo nome do arquivo, nome da funcao e argumentos avaliados no formato AdvPL. Chamadas diferentes no mesmo fonte recebem itens separados. Para chamadas com conteudo identico e respostas distintas, `ocorrencia` identifica a ordem de execucao a partir de 1. Sem `ocorrencia`, a regra funciona como padrao para aquele conteudo. A grafia canonica da colecao e `especificidadesPrw`; a grafia conceitual anterior `especificicidadesPrw` e aceita apenas como alias de leitura.

## Saida verificada

```text
[MSDIALOG] Cadastro sem UI
[ALERTA] Atencao: Falha simulada
[INFO] Resultado: Operacao concluida
```

`MsgYesNo` nao acrescenta nenhuma linha a saida.

## Erros intencionais

- retorno de `MsgYesNo` que nao seja `true` ou `false` e rejeitado ao carregar o fixture;
- regra duplicada para a mesma fonte, funcao e conteudo e rejeitada;
- chamada sem regra especifica ou fallback global gera erro com a fonte e o conteudo procurados.

## Fora do escopo desta entrega

- abrir janelas reais;
- preencher variaveis por `GET`;
- executar `ACTION` de botoes;
- interpretar coordenadas, tamanho, picture ou alinhamento;
- executar o ramo de exportacao do `TRNSOL02` quando sua confirmacao retorna `true`.

## Verificacao

```powershell
python -m unittest discover -s tests -v
advpl-testlab -run TRNSOL02.prw
```

Resultado da entrega: vinte e sete testes aprovados, exemplo `ui-headless.prw` executado ponta a ponta e `TRNSOL02.prw` executado com retorno `false` configurado especificamente para sua chamada de `MsgYesNo`.
