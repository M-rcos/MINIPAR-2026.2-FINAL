# Arquitetura do Compilador MiniPar 2026.2

Este documento descreve a organização implementada no repositório. Os diagramas editáveis estão em [docs/uml/](uml/).

## 1. Visão geral

O MiniPar é implementado principalmente em Python. O compilador recebe código MiniPar, realiza as análises léxica, sintática e semântica, gera uma representação intermediária de três endereços (TAC), traduz o TAC para C++ e pode chamar o GCC/G++ para produzir um executável.

O projeto disponibiliza três formas de interação:

- **Terminal (CLI):** comandos executados no terminal.
- **Primeira interface Web:** interface Web já existente no projeto.
- **Segunda interface Web didática:** aplicação local com editor e visualização das etapas do compilador, acrescentada para facilitar a compreensão do pipeline durante o uso e a apresentação acadêmica.

As três formas de interação acessam o compilador. A CLI oferece comandos independentes para as etapas; as interfaces Web apresentam recursos de interação pelo navegador. A segunda interface Web destaca a visualização dos tokens, da AST, da análise semântica, da tabela de símbolos, do TAC e do C++ gerado, além da possibilidade de executar programas.

## 2. Fluxo de compilação

1. **Entrada:** o usuário fornece um arquivo ou texto-fonte MiniPar.
2. **Análise léxica:** Lexer reconhece lexemas e produz uma lista de Token, incluindo o marcador final EOF. Erros léxicos são registrados.
3. **Análise sintática:** Parser recebe os tokens e constrói a AST (Program e seus nós). Erros sintáticos são registrados.
4. **Análise semântica:** se não houver erros léxicos ou sintáticos, SemanticAnalyzer percorre a AST e constrói a tabela de símbolos.
5. **Código intermediário:** TACGenerator recebe a AST e o analisador semântico e produz um TACProgram.
6. **Geração C++:** CppGenerator traduz o TACProgram em código-fonte C++.
7. **Compilação nativa:** build_executable, no módulo de driver, grava o C++, copia minipar_runtime.hpp para a pasta de saída e invoca GCC/G++ com C++17 e suporte a threads (-pthread). Em caso de sucesso, retorna um BuildResult; falhas de compilação são reportadas por BuildError.
8. **Execução:** o executável gerado utiliza o runtime MiniPar. Na segunda interface Web, compilação e execução ocorrem em diretório temporário e com limites de tempo e de saída.

O fluxo de compilação pelo pipeline pode ser resumido assim:

~~~text
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
~~~

A análise semântica não é executada quando o lexer ou o parser reporta erros. Da mesma forma, a geração TAC depende de uma análise semântica sem erros.

## 3. Componentes e responsabilidades

| Componente | Implementação | Responsabilidade |
|---|---|---|
| Analisador léxico | Lexer / ILexer | Reconhecer tokens e reportar erros léxicos. |
| Analisador sintático | Parser / IParser | Aplicar a gramática e construir a AST. |
| AST | Program, Stmt, Expr e demais nós | Representar a estrutura do programa, incluindo declarações, comandos, tarefas paralelas e canais. |
| Analisador semântico | SemanticAnalyzer / ISemanticAnalyzer | Verificar regras semânticas e produzir informações para as etapas seguintes. |
| Tabela de símbolos | SymbolTable / ISymbolTable | Manter símbolos e escopos hierárquicos. |
| Gerador TAC | TACGenerator / ITACGenerator | Traduzir a AST validada em uma estrutura TAC. |
| Gerador C++ | CppGenerator / ICodeGenerator | Traduzir o programa TAC em C++. |
| Driver de compilação | build_executable | Gravar C++, preparar o runtime e invocar GCC/G++. |
| Runtime | minipar_runtime.hpp | Oferecer operações utilizadas pelo código gerado, incluindo recursos paralelos e canais. |
| CLI | cli.py | Disponibilizar comandos de análise, geração, compilação e execução no terminal. |
| Segunda interface Web | webapp.py e diretório web/ | Disponibilizar análise e execução local por navegador, com visualização didática do pipeline. |

## 4. Interfaces de acesso

### 4.1 Terminal (CLI)

A CLI oferece comandos independentes para consultar tokens, AST e análise semântica, além de gerar TAC, gerar C++, compilar e executar. Ela lê o arquivo MiniPar indicado pelo usuário e chama os componentes correspondentes.

Exemplos:

~~~bash
make tokens F=exemplos/teste02_par_fatorial_fibonacci.mp
make check F=exemplos/teste03_neuronio.mp
make tac F=exemplos/teste07_quicksort_iterativo.mp
make cpp F=exemplos/teste03_neuronio.mp
make build F=exemplos/teste03_neuronio.mp
make run F=exemplos/teste03_neuronio.mp
~~~

### 4.2 Segunda interface Web didática

A segunda interface Web é servida localmente por minipar.webapp. O frontend em HTML/CSS/JavaScript comunica-se com o servidor Python por HTTP. O serviço disponibiliza arquivos estáticos e exemplos, recebe o código para análise e pode compilar/executar o programa.

Para iniciar, execute make web e acesse http://127.0.0.1:8765.

Rotas principais:

| Método | Rota | Finalidade |
|---|---|---|
| GET | /, /app.js, /style.css | Servir a interface. |
| GET | /api/examples | Listar exemplos MiniPar. |
| GET | /api/examples/{name} | Carregar um exemplo. |
| POST | /api/analyze | Executar as etapas de análise e devolver os resultados. |
| POST | /api/run | Compilar e executar o programa. |

Por padrão, o servidor escuta em 127.0.0.1:8765. As requisições POST verificam origem local. O serviço limita o tamanho da fonte, a quantidade de execuções simultâneas, o tempo de compilação e execução e o volume de saída. É uma interface didática local, não um serviço configurado para exposição pública.

A primeira interface Web permanece como parte do projeto; esta documentação e o guia de apresentação descrevem especificamente a segunda interface Web didática.

## 5. Estruturas de dados relevantes

- **AST:** os nós derivam de Node; comandos derivam de Stmt e expressões derivam de Expr. Program agrega os nós do programa. Entre as construções representadas estão declarações de canais, blocos paralelos, operações fork e join, além de comandos e expressões convencionais.
- **Tabela de símbolos:** SymbolTable mantém o escopo global e o escopo corrente. Cada Scope registra símbolos, escopos filhos e uma referência ao escopo pai. Um Symbol registra nome, categoria, tipo e posição no código; conforme a categoria, também pode conter parâmetros, retorno, informações de classe, proprietário ou extremos de canal.
- **TAC:** TACProgram agrega globals, channels, classes e functions. As instruções TACInstr ficam dentro de cada TACFunction, na coleção instrs.
- **Compilação:** BuildResult informa os caminhos do fonte C++ e do executável, o comando usado e a saída do compilador.

## 6. Execução paralela e canais

A linguagem inclui construções como par, fork, join, send e receive. O analisador semântico verifica regras de uso e isolamento de tarefas. O gerador TAC representa essas operações em instruções próprias; o gerador C++ as traduz para chamadas do runtime MiniPar. A compilação utiliza -pthread para habilitar suporte a threads. A comunicação e a execução são responsabilidade do runtime, não do analisador sintático nem do gerador TAC isoladamente.

## 7. Diagramas UML

Os arquivos PlantUML correspondem às três modelagens:

1. [Diagrama de casos de uso](uml/casos-de-uso.puml).
2. [Diagrama de componentes](uml/componentes.puml).
3. [Diagrama de classes](uml/classes.puml).

Os arquivos .puml são a fonte editável dos diagramas. Para gerar imagens, é necessário renderizá-los com uma instalação do PlantUML. Ao alterar a arquitetura ou as classes, atualize os diagramas correspondentes.

## 8. Documentos relacionados

- [Guia rápido de apresentação](GUIA_APRESENTACAO.md).
- [Documentação da segunda interface Web](INTERFACE_WEB.md).
- [Gramática BNF](GRAMATICA_BNF_2026_2.md).
- [Regras semânticas](REGRAS_SEMANTICAS.md).
- [Código intermediário TAC](CODIGO_INTERMEDIARIO.md).
- [Fork e join](FORK_JOIN.md).
- [Canais](CANAIS.md).
- [Programas de teste](PROGRAMAS_DE_TESTE.md).
