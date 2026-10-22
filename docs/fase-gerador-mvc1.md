# Gerador MVC tipo 1

`advplab --mvc1 --table ZA4` cria Fontes/ZA4MVC.prw e mock.jsonc na pasta atual. Sem --table, usa ZA1. A geracao fica em scaffold.py; main.py valida as opcoes e apresenta os comandos seguintes.

O fonte usa FWMBrowse, MenuDef, MPFormModel/AddFields e FWFormView. O mock.jsonc aceita sintaxe JSONC e inclui comentarios explicativos por secao. O fixture fornece campos C de exemplo (FILIAL, COD e DESC), tabela vazia e um cenario de inclusao. A pos-validacao inicial aceita o registro; acrescente as regras de negocio do projeto. --mvc-case incluir-registro verifica salvou=true e um registro. --persist permite salvar esse registro em state.json.

Validacao local: 118 testes aprovados. O fonte gerado valida quatro funcoes; o cenario retorna salvou=true, totalRegistros=1. Testes verificam preservacao de arquivos e limpeza em falha de escrita.

Fora do escopo: descoberta de SX3, criacao de tabelas no Protheus, interface grafica MVC e validacao contra AppServer/RPO real. Ajustar campos e chave primaria ao dicionario do ambiente antes da compilacao real.
