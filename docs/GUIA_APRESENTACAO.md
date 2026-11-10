# Guia rápido de apresentação — MiniPar 2026.2

Este roteiro foi preparado para iniciar e demonstrar o projeto em uma apresentação acadêmica. Ele prioriza o caminho mais curto e confiável: abrir a interface Web didática, analisar um programa, mostrar as etapas do compilador e executar um exemplo.

## 1. Antes da apresentação

Confira os requisitos na máquina que será utilizada:

- Python 3.11 ou compatível.
- GCC/G++ com suporte a C++17 e pthread.
- GNU Make.
- Navegador atualizado.

No Linux, confira as ferramentas:

```bash
python3 --version
g++ --version
make --version
```

Se o GCC/G++ não estiver instalado, instale-o antes da apresentação. Em distribuições Debian/Ubuntu, por exemplo:

```bash
sudo apt update
sudo apt install python3 make g++
```

## 2. Abrir o projeto

Na pasta do repositório, atualize a branch de apresentação:

```bash
git switch feature/web-educacional
git pull
```

Se o repositório ainda não estiver na máquina, clone-o usando a conta que tem acesso ao projeto e entre na pasta:

```bash
git clone https://github.com/M-rcos/MINIPAR-2026.2-testes.git
cd MINIPAR-2026.2-testes
git switch feature/web-educacional
```

> O repositório é privado. A pessoa que for clonar precisa ter permissão no GitHub.

## 3. Iniciar a interface Web

Na raiz do projeto:

```bash
make web
```

Abra no navegador:

```text
http://127.0.0.1:8765
```

Mantenha o terminal aberto durante a demonstração. Para encerrar o servidor, volte ao terminal e pressione `Ctrl+C`.

A interface é local e escuta em loopback por padrão. Não a exponha diretamente à internet.

## 4. Roteiro sugerido (5 a 8 minutos)

### Etapa A — Apresentar a interface

1. Mostre o editor e a lista de exemplos.
2. Explique que o usuário pode carregar um exemplo ou escrever seu próprio programa.
3. Destaque que esta interface foi acrescentada para tornar as etapas do compilador mais visuais e didáticas.

### Etapa B — Mostrar o pipeline

Carregue um exemplo simples disponível na lista e solicite a análise. Apresente os resultados nesta ordem:

1. **Tokens:** saída do analisador léxico.
2. **AST:** estrutura sintática em árvore. Dê atenção especial a esta visualização.
3. **Análise semântica e tabela de símbolos:** como o compilador verifica declarações, tipos e escopos.
4. **TAC:** representação intermediária de três endereços.
5. **C++:** código gerado a partir da representação intermediária.

Explique que essas etapas são encadeadas: uma etapa posterior depende do sucesso das anteriores.

### Etapa C — Executar o programa

Use a ação de executar na interface. Mostre a saída produzida pelo programa e explique que o código MiniPar é traduzido para C++, compilado com GCC/G++ e executado localmente.

### Etapa D — Demonstrar tratamento de erros

Carregue ou escreva um exemplo inválido e execute a análise. Uma opção é usar o arquivo `exemplos/erros_semanticos.mp`. Mostre que o compilador identifica o erro e não deve avançar normalmente para as etapas que dependem de uma análise válida.

### Etapa E — Relacionar com concorrência

Se houver tempo, mostre o exemplo `exemplos/fork_join.mp` ou `exemplos/fork_remoto.mp`. Explique brevemente os conceitos de tarefas paralelas, `fork`, `join` e canais. Não dependa de uma demonstração entre computadores diferentes se a rede/local não tiver sido preparada e testada antes.

## 5. Demonstração pelo terminal (plano alternativo)

Se o navegador ou o servidor Web apresentar algum problema, a CLI permite demonstrar as etapas sem a interface gráfica. Na raiz do repositório, execute:

```bash
make tokens F=exemplos/teste03_neuronio.mp
make ast F=exemplos/teste03_neuronio.mp
make check F=exemplos/teste03_neuronio.mp
make tac F=exemplos/teste03_neuronio.mp
make cpp F=exemplos/teste03_neuronio.mp
make run F=exemplos/teste03_neuronio.mp
```

Os comandos mostram, respectivamente, tokens, AST, análise semântica/tabela de símbolos, TAC, C++ e execução.

## 6. Verificação antes de apresentar

Faça esta verificação com antecedência, não nos minutos iniciais da apresentação:

```bash
make test
make web
```

- [ ] O ambiente Python inicia sem erro.
- [ ] `g++` está disponível.
- [ ] A suíte automatizada termina com sucesso.
- [ ] O servidor Web abre em `127.0.0.1:8765`.
- [ ] Um exemplo válido é analisado.
- [ ] Um exemplo válido é executado e apresenta a saída esperada.
- [ ] Um exemplo inválido apresenta mensagem de erro.
- [ ] O terminal e o navegador estão com tamanho de fonte legível.
- [ ] Notificações, atualizações e programas desnecessários estão fechados.

## 7. Problemas comuns

| Problema | O que fazer |
|---|---|
| `make: command not found` | Instalar GNU Make ou executar os comandos Python equivalentes descritos no README. |
| `g++: command not found` | Instalar GCC/G++ antes de tentar compilar ou executar programas. |
| Porta 8765 ocupada | Encerrar o processo que está usando a porta ou iniciar o servidor com outra porta, se a opção estiver disponível na versão instalada. |
| Página não abre | Confirmar que `make web` continua em execução e acessar exatamente `http://127.0.0.1:8765`. |
| Programa não compila | Conferir a mensagem exibida pela interface e validar primeiro o exemplo pela CLI. |
| Rede instável | A interface é local; não precisa de conexão com a internet depois que o repositório e os requisitos estiverem na máquina. |

## 8. Documentação para consulta durante perguntas

- [Arquitetura e fluxo do compilador](ARQUITETURA.md)
- [Segunda interface Web e evidências](INTERFACE_WEB.md)
- [Gramática BNF 2026.2](GRAMATICA_BNF_2026_2.md)
- [Regras semânticas](REGRAS_SEMANTICAS.md)
- [Código intermediário TAC](CODIGO_INTERMEDIARIO.md)
- [Fork e join](FORK_JOIN.md)
- [Canais](CANAIS.md)
- [Programas de teste](PROGRAMAS_DE_TESTE.md)
- [Diagramas UML editáveis](uml/)
- [Evidências reais](../evidencias/)

## 9. Observação sobre a validação

O workflow de integração contínua do GitHub Actions executa `python run_tests.py`, incluindo a suíte automatizada e a integração com C++. Consulte a aba **Actions** e confirme que o workflow do commit mais recente está com resultado **Success** antes da apresentação.

A validação manual da interface deve ser feita também na máquina e no navegador que serão usados na aula. O sucesso dos testes automatizados, isoladamente, não substitui essa conferência.
