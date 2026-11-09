# Compilador MiniPar 2026.2

Projeto da disciplina de Compiladores (UFAL / IC). Implementação em Python 3,
arquitetura por componentes, gerando C++ compilado com GCC.

## Requisitos

- Python 3
- GCC / G++ (para gerar executáveis e rodar os programas)
- Make (opcional; os comandos também podem ser executados diretamente)

Windows: instale Python 3 e MSYS2; no terminal MSYS2 UCRT64 instale
`mingw-w64-ucrt-x86_64-gcc` e adicione `C:\msys64\ucrt64\bin` ao PATH.
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
- `docs/`: gramática, regras, [arquitetura](docs/ARQUITETURA.md), [diagramas UML em PlantUML](docs/uml/) e documentação
- `evidencias/`: capturas reais de execução para o relatório

## Uso da CLI

```bash
make test
make tokens F=exemplos/teste02_par_fatorial_fibonacci.mp
make ast F=exemplos/teste03_neuronio.mp
make check F=exemplos/teste03_neuronio.mp
make tac F=exemplos/teste07_quicksort_iterativo.mp
make cpp F=exemplos/teste03_neuronio.mp
make run F=exemplos/teste03_neuronio.mp
```

## Segunda interface Web

Execute `make web` e abra http://127.0.0.1:8765. A interface permite editar MiniPar,
carregar exemplos e inspecionar tokens, AST, análise semântica, TAC e C++.
Também permite compilar e executar localmente (requer GCC). O servidor escuta
somente em loopback por padrão. Consulte `docs/INTERFACE_WEB.md`.

## Estado

- [x] Gramática 2026.2, tratamento de erros e análise léxica
- [x] Parser, AST, tabela de símbolos e análise semântica
- [x] TAC, gerador C++ e integração GCC
- [x] Programas de teste e exemplos
- [x] Canais e fork/join
- [x] Interface Web didática adicional (em validação)
- [x] Capturas reais da interface registradas em `evidencias/interface-web/` (7 arquivos; uma captura reúne duas etapas)
