# Arquitetura do Compilador MiniPar 2026.2

Este documento descreve a organização implementada no repositório. Os diagramas
editáveis estão em [`docs/uml/`](uml/).

## 1. Visão geral

O MiniPar é implementado principalmente em Python. O compilador recebe código
MiniPar, realiza as análises léxica, sintática e semântica, gera uma
representação intermediária de três endereços (TAC), traduz o TAC para C++ e
pode chamar o GCC/G++ para produzir um executável.

Há duas interfaces de acesso ao compilador:

- **CLI:** comandos executados no terminal.
- **Interface Web:** aplicação local com editor e visualização das etapas.

As duas interfaces utilizam os componentes do compilador. A interface Web
também apresenta os resultados das etapas de análise e oferece compilação e
execução local.

## 2. Fluxo de compilação

1. **Entrada:** o usuário fornece um arquivo ou texto-fonte MiniPar.
2. **Análise léxica:** `Lexer` reconhece lexemas e produz uma lista de
   `Token`, incluindo o marcador final EOF. Erros léxicos são registrados.
3. **Análise sintática:** `Parser` recebe os tokens e constrói a AST
   (`Program` e seus nós). Erros sintáticos são registrados.
4. **Análise semântica:** se não houver erros léxicos ou sintáticos,
   `SemanticAnalyzer` percorre a AST, verifica regras semânticas e constrói
   a tabela de símbolos.
5. **Código intermediário:** `TACGenerator` utiliza a AST validada e os
   resultados do analisador semântico para produzir um `TACProgram`.
6. **Geração C++:** `CppGenerator` traduz o `TACProgram` em código-fonte C++.
7. **Compilação nativa:** `build_executable` grava o C++, copia
   `minipar_runtime.hpp` para a pasta de saída e invoca GCC/G++ com C++17 e
   suporte a threads (`-pthread`).
8. **Execução:** o executável gerado utiliza o runtime MiniPar. Na interface
   Web, compilação e execução são realizadas em diretório temporário e com
   limites de tempo e de saída.

O fluxo principal pode ser resumido assim:

```text
Código MiniPar
     |
     v
  Lexer ------> Tokens
     |
     v
  Parser -----> AST (Program)
     |
     v
SemanticAnalyzer <----> SymbolTable / Scope / Symbol
     |
     v
 TACGenerator -----> TACProgram
     |
     v
 CppGenerator -----> Código C++
     |
     v
 build_executable + GCC/G++
     |
     v
 Executável -----> Runtime MiniPar
```

A análise semântica não é executada quando o lexer ou o parser reporta erros.
Da mesma forma, a geração TAC depende de uma análise semântica sem erros.

## 3. Componentes e responsabilidades

| Componente | Implementação | Responsabilidade |
|---|---|---|
| Analisador léxico | `Lexer` / `ILexer` | Reconhecer tokens e reportar erros léxicos. |
| Analisador sintático | `Parser` / `IParser` | Aplicar a gramática e construir a AST. |
| AST | `Program`, `Stmt`, `Expr` e demais nós | Representar a estrutura do programa. |
| Analisador semântico | `SemanticAnalyzer` / `ISemanticAnalyzer` | Verificar declarações, tipos, escopos, funções, classes, canais e tarefas. |
| Tabela de símbolos | `SymbolTable` / `ISymbolTable` | Manter símbolos e escopos hierárquicos. |
| Gerador TAC | `TACGenerator` / `ITACGenerator` | Traduzir a AST validada em instruções de três endereços. |
| Gerador C++ | `CppGenerator` / `ICodeGenerator` | Traduzir o programa TAC em C++. |
| Driver de compilação | `build_executable` | Gravar C++, preparar runtime e invocar GCC/G++. |
| Runtime | `minipar_runtime.hpp` | Oferecer as operações de execução utilizadas pelo código gerado, incluindo recursos paralelos e canais. |
| CLI | `cli.py` | Disponibilizar comandos de análise, geração, compilação e execução no terminal. |
| Interface Web | `webapp.py` e diretório `web/` | Disponibilizar análise e execução local por navegador. |

## 4. Interfaces de acesso

### 4.1 CLI

A CLI oferece comandos independentes para consultar tokens, AST e análise
semântica, além de gerar TAC, gerar C++, compilar e executar. Ela lê o arquivo
MiniPar indicado pelo usuário e chama os componentes correspondentes.

Exemplos:

```bash
minipar tokens exemplos/programa.mp
minipar check exemplos/programa.mp --symbols
minipar tac exemplos/programa.mp
minipar cpp exemplos/programa.mp
minipar build exemplos/programa.mp
minipar run exemplos/programa.mp
```

### 4.2 Interface Web

A interface Web é servida localmente por `minipar.webapp`. O frontend em
HTML/CSS/JavaScript comunica-se com o servidor Python por HTTP. O serviço
disponibiliza arquivos estáticos e exemplos, recebe o código para análise e
pode compilar/executar o programa.

Rotas principais:

| Método | Rota | Finalidade |
|---|---|---|
| GET | `/`, `/app.js`, `/style.css` | Servir a interface. |
| GET | `/api/examples` | Listar exemplos MiniPar. |
| GET | `/api/examples/{name}` | Carregar um exemplo. |
| POST | `/api/analyze` | Executar as etapas de análise e devolver os resultados. |
| POST | `/api/run` | Compilar e executar o programa. |

Por padrão, o servidor escuta em `127.0.0.1:8765`. As requisições POST
verificam origem local. O serviço limita o tamanho da fonte, a quantidade de
execuções simultâneas, o tempo de compilação e execução e o volume de saída.
É uma interface didática local, não um serviço configurado para exposição
pública.

## 5. Estruturas de dados relevantes

- **AST:** os nós derivam de `Node`; comandos derivam de `Stmt` e expressões
  derivam de `Expr`. `Program` agrega os nós do programa.
- **Tabela de símbolos:** `SymbolTable` mantém o escopo global e o escopo
  corrente. Cada `Scope` pode possuir escopo pai e escopos filhos. Os
  `Symbol` representam variáveis, parâmetros, funções, métodos, classes,
  atributos, canais e subtarefas.
- **TAC:** `TACProgram` agrega funções, classes, canais, globais e
  instruções representadas por `TACInstr`.
- **Compilação:** `BuildResult` informa os caminhos do fonte C++ e do
  executável, o comando usado e a saída do compilador.

## 6. Execução paralela e canais

A linguagem inclui construções como `par`, `fork`, `join`, `send` e
`receive`. O analisador semântico verifica regras de uso e isolamento de
tarefas. O gerador TAC representa essas operações em instruções próprias; o
gerador C++ as traduz para chamadas do runtime MiniPar. A compilação utiliza
`-pthread` para habilitar suporte a threads. A comunicação e a execução são
responsabilidade do runtime, não do analisador sintático nem do gerador TAC
isoladamente.

## 7. Diagramas UML

Os arquivos PlantUML correspondem às três modelagens solicitadas:

1. [Diagrama de casos de uso](uml/casos-de-uso.puml).
2. [Diagrama de componentes](uml/componentes.puml).
3. [Diagrama de classes](uml/classes.puml).

Os arquivos `.puml` são a fonte editável dos diagramas. Para gerar imagens,
é necessário renderizá-los com uma instalação do PlantUML. Ao alterar a
arquitetura ou as classes, atualize os diagramas correspondentes.
