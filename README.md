# Compilador MiniPar 2026.2

Projeto da disciplina de Compiladores (UFAL / IC). Implementação em Python 3,
arquitetura por componentes, gerando C++ compilado com GCC.

> **Pronto para demonstração:** consulte primeiro o [Guia rápido de apresentação](docs/GUIA_APRESENTACAO.md). Ele contém os comandos para iniciar a interface, o roteiro sugerido e um plano alternativo pela CLI.

## Requisitos

- Python 3
- GCC / G++ (para gerar executáveis e rodar os programas)
- Make (opcional; os comandos também podem ser executados diretamente)

Windows: instale Python 3 e MSYS2; no terminal MSYS2 UCRT64 instale
`mingw-w64-ucrt-x86_64-gcc` e adicione `C:\\msys64\\ucrt64\\bin` ao PATH.
Use `python run_tests.py` no lugar de `make test`.

## Estrutura

- `src/minipar/common/`: erros compartilhados
- `src/minipar/lexer/`: analisador léxico
- `src/minipar/parser/`: parser, AST, visitor e printer
- `src/minipar/symtable/`: tabela de símbolos e escopos
- `src/minipar/semantic/`: analisador semântico
- `src/minipar/tac/`: gerador de código de três endereços
- `src/minipar/codegen/`: gerador C++, runtime e integração GCC
- `src/minipar/webapp.py` e `web/`: segunda interface Web didática
- `tests/`: testes automatizados
- `exemplos/`: programas MiniPar e saídas de referência
- `docs/`: gramática, regras, [arquitetura](docs/ARQUITETURA.md), [guia de apresentação](docs/GUIA_APRESENTACAO.md), [diagramas UML em PlantUML](docs/uml/) e documentação
- `evidencias/`: capturas reais de execução para consulta

## Uso rápido

### Interface Web

```bash
make web
```

Acesse http://127.0.0.1:8765. A interface permite editar MiniPar,
carregar exemplos e inspecionar tokens, AST, análise semântica, TAC e C++.
Também permite compilar e executar localmente (requer GCC). O servidor escuta
somente em loopback por padrão. Consulte [docs/INTERFACE_WEB.md](docs/INTERFACE_WEB.md).

### CLI

```bash
make tokens F=exemplos/teste02_par_fatorial_fibonacci.mp
make ast F=exemplos/teste03_neuronio.mp
make check F=exemplos/teste03_neuronio.mp
make tac F=exemplos/teste07_quicksort_iterativo.mp
make cpp F=exemplos/teste03_neuronio.mp
make run F=exemplos/teste03_neuronio.mp
```

### Testes

```bash
make test
```

No Windows, use `python run_tests.py`.

## Documentação principal

- [Guia rápido de apresentação](docs/GUIA_APRESENTACAO.md)
- [Arquitetura e fluxo de compilação](docs/ARQUITETURA.md)
- [Interface Web e evidências](docs/INTERFACE_WEB.md)
- [Gramática BNF 2026.2](docs/GRAMATICA_BNF_2026_2.md)
- [Regras semânticas](docs/REGRAS_SEMANTICAS.md)
- [Programas de teste](docs/PROGRAMAS_DE_TESTE.md)
- [Diagramas UML](docs/uml/)
- [Evidências](evidencias/)

## Estado do projeto

- [x] Análise léxica e tratamento de erros
- [x] Parser e AST
- [x] Tabela de símbolos e análise semântica
- [x] TAC e geração de código C++
- [x] Integração com GCC/G++
- [x] Construções paralelas e canais
- [x] Interface Web didática adicional
- [x] Documentação técnica e diagramas UML

A suíte automatizada é executada pelo GitHub Actions. Consulte a aba **Actions**
para verificar o resultado associado ao commit mais recente. Antes da apresentação,
execute também a verificação manual descrita em
[docs/GUIA_APRESENTACAO.md](docs/GUIA_APRESENTACAO.md).

## Repositório e branch de apresentação

Este trabalho está sendo preparado na branch `feature/web-educacional` do
repositório [MINIPAR-2026.2-testes](https://github.com/M-rcos/MINIPAR-2026.2-testes).
A branch `main` e o repositório original não são alterados por este guia.
