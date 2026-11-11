# Compilador MiniPar 2026.2

Implementação de um compilador para a linguagem MiniPar, desenvolvida como projeto da disciplina de Compiladores do Instituto de Computação da Universidade Federal de Alagoas (UFAL).

O projeto é implementado em Python 3 e possui arquitetura modular. Seu fluxo de compilação contempla análise léxica e sintática, análise semântica, geração de código intermediário (TAC) e geração de código C++, com integração ao GCC/G++.

## Funcionalidades

- Análise léxica e tratamento de erros.
- Análise sintática e construção da AST.
- Tabela de símbolos e análise semântica.
- Geração de código intermediário de três endereços (TAC).
- Geração de código C++ e integração com GCC/G++.
- Suporte às construções paralelas e aos canais da linguagem MiniPar.
- Interface de terminal (CLI).
- Interfaces Web, incluindo uma interface didática para acompanhar as etapas da compilação.
- Testes automatizados e documentação técnica.

## Requisitos

- Python 3.
- GCC e G++ (para gerar executáveis e executar os programas).
- GNU Make (opcional; os comandos também podem ser executados diretamente).

### Windows

Instale Python 3 e MSYS2. No terminal MSYS2 UCRT64, instale `mingw-w64-ucrt-x86_64-gcc` e adicione `C:\\msys64\\ucrt64\\bin` ao PATH. Para executar os testes, use `python run_tests.py` no lugar de `make test`.

## Como obter o projeto

Clone o repositório oficial:

```bash
git clone https://github.com/M-rcos/MINIPAR-2026.2-FINAL.git
cd MINIPAR-2026.2-FINAL
```

## Como executar

### Interface Web didática

Na raiz do projeto, execute:

```bash
make web
```

Depois, acesse http://127.0.0.1:8765 no navegador.

A interface permite editar programas MiniPar, carregar exemplos e visualizar tokens, AST, análise semântica, TAC e código C++ gerado. Também permite compilar e executar os programas localmente (requer GCC/G++). Por padrão, o servidor fica acessível somente pela própria máquina.

Consulte a [documentação da interface Web](docs/INTERFACE_WEB.md) e o [guia de apresentação](docs/GUIA_APRESENTACAO.md).

### Interface de terminal (CLI)

Os comandos abaixo devem ser executados na raiz do repositório:

```bash
make tokens F=exemplos/teste02_par_fatorial_fibonacci.mp
make ast F=exemplos/teste03_neuronio.mp
make check F=exemplos/teste03_neuronio.mp
make tac F=exemplos/teste07_quicksort_iterativo.mp
make cpp F=exemplos/teste03_neuronio.mp
make run F=exemplos/teste03_neuronio.mp
```

### Testes automatizados

Execute a suíte de testes com:

```bash
make test
```

No Windows, use:

```bash
python run_tests.py
```

## Estrutura do projeto

- `src/minipar/common/`: erros e recursos compartilhados.
- `src/minipar/lexer/`: analisador léxico.
- `src/minipar/parser/`: parser, AST, visitor e printer.
- `src/minipar/symtable/`: tabela de símbolos e escopos.
- `src/minipar/semantic/`: analisador semântico.
- `src/minipar/tac/`: gerador de código de três endereços.
- `src/minipar/codegen/`: geração de C++, runtime e integração com GCC.
- `src/minipar/webapp.py` e `web/`: implementação da interface Web didática.
- `tests/`: testes automatizados.
- `exemplos/`: programas MiniPar e saídas de referência.
- `docs/`: gramática, regras semânticas, arquitetura, guias e documentação.
- `docs/uml/`: fontes dos diagramas UML em PlantUML.
- `evidencias/`: registros de execução e capturas da interface.

## Documentação

- [Guia de apresentação](docs/GUIA_APRESENTACAO.md).
- [Arquitetura e fluxo de compilação](docs/ARQUITETURA.md).
- [Interface Web e evidências](docs/INTERFACE_WEB.md).
- [Gramática BNF 2026.2](docs/GRAMATICA_BNF_2026_2.md).
- [Regras semânticas](docs/REGRAS_SEMANTICAS.md).
- [Programas de teste](docs/PROGRAMAS_DE_TESTE.md).
- [Diagramas UML](docs/uml/).
- [Evidências](evidencias/).

## Estado do projeto

O repositório reúne a implementação do compilador MiniPar 2026.2, suas interfaces, testes automatizados e documentação técnica. A suíte automatizada pode ser executada localmente com `make test`; os resultados das execuções de integração contínua podem ser consultados na aba **Actions** do GitHub.

---

**Projeto da disciplina de Compiladores — UFAL, Instituto de Computação.**
