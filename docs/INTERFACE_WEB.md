# Segunda interface Web — MiniPar 2026.2

## Objetivo
A interface Web didática é uma terceira forma de interação com o compilador, sem substituir a CLI nem a interface Web já existente no escopo do projeto. Apresenta visualmente as fases do pipeline.

## Tecnologias
- Python 3 e biblioteca padrão (\`http.server\`) no servidor local.
- HTML5, CSS e JavaScript sem dependências externas no navegador.
- Componentes existentes: Lexer, Parser/AST, SemanticAnalyzer, TACGenerator e gerador C++.
- GCC para compilação e execução.

## Como executar
Na raiz do repositório, execute \`make web\` e acesse http://127.0.0.1:8765.
Alternativa: \`PYTHONPATH=src python -m minipar.webapp --host 127.0.0.1 --port 8765\`.

Requisitos para executar programas: Python 3 e GCC. O servidor escuta em loopback por padrão e não deve ser exposto diretamente à internet.

## Recursos
1. Editor MiniPar com carregamento de exemplos.
2. Tabela de tokens com categoria, lexema e posição.
3. AST hierárquica expansível.
4. Análise semântica e tabela de símbolos.
5. Código intermediário TAC.
6. Código C++ gerado.
7. Execução local com stdout, stderr, código de saída e limite de tempo.
8. Erros com fase e localização.

## Evidências a capturar
As imagens devem ser capturadas durante a execução real. Não usar imagens ilustrativas como se fossem resultados de teste.

| Arquivo | Conteúdo |
|---|---|
| 01-editor.png | Interface aberta, editor e seleção de exemplo |
| 02-tokens.png | Tabela de tokens após análise |
| 03-ast.png | AST expandida e legível |
| 04-semantica.png | Resultado semântico e tabela de símbolos |
| 05-tac.png | Código de três endereços |
| 06-cpp.png | Código C++ gerado |
| 07-execucao.png | Saída de um programa de exemplo |
| 08-erros.png | Mensagem de erro léxico, sintático ou semântico |

Guardar capturas em \`evidencias/interface-web/\`. Para cada captura, registrar o programa utilizado, comando de inicialização, resultado observado e data.

## Validação automatizada
Execute \`PYTHONPATH=src python -m unittest tests.test_webapp -v\` e \`make test\`.
Os testes verificam a integração das etapas e o bloqueio das fases posteriores quando há erros. As capturas continuam sendo evidências manuais da interface em execução.
