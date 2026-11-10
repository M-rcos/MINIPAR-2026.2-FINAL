# Segunda interface Web — MiniPar 2026.2

## Objetivo
A interface Web didática é uma terceira forma de interação com o compilador, sem substituir a CLI nem a interface Web já existente no escopo do projeto. Apresenta visualmente as fases do pipeline.

## Tecnologias
- Python 3 e biblioteca padrão (`http.server`) no servidor local.
- HTML5, CSS e JavaScript sem dependências externas no navegador.
- Componentes existentes: Lexer, Parser/AST, SemanticAnalyzer, TACGenerator e gerador C++.
- GCC para compilação e execução.

## Como executar
Na raiz do repositório, execute `make web` e acesse http://127.0.0.1:8765.
Alternativa: `PYTHONPATH=src python -m minipar.webapp --host 127.0.0.1 --port 8765`.

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

## Evidências registradas
As capturas foram coletadas durante a execução real da interface e estão em `evidencias/interface-web/`. São 7 arquivos para documentar 8 etapas, pois duas etapas foram reunidas em uma única captura. Não são utilizados mockups ou imagens ilustrativas como evidência.

| Arquivo | Conteúdo |
|---|---|
| `interface-tokens.png` | Interface inicial e análise de tokens (captura combinada) |
| `ast.png` | AST expandida e legível |
| `semantica.png` | Resultado semântico e tabela de símbolos |
| `tac.png` | Código intermediário de três endereços |
| `c++.png` | Código C++ gerado |
| `saida.png` | Saída de execução de um programa de exemplo |
| `erro_semantico.png` | Mensagem de erro semântico |

## Validação automatizada
Execute `PYTHONPATH=src python -m unittest tests.test_webapp -v` e `make test`.
Os testes verificam a integração das etapas e o bloqueio das fases posteriores quando há erros. As capturas são evidências manuais complementares da interface em execução.
