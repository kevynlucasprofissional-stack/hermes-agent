# MISSÃO — Sincronizar o Hermes Workstation do Linux Mint com o GitHub

## 1. Objetivo

Execute a sincronização do repositório local do Hermes Workstation no Linux Mint com a versão mais recente da branch `main` do repositório remoto no GitHub.

Esta é uma **missão exclusivamente de sincronização, não de desenvolvimento**.

O Windows é minha máquina principal de desenvolvimento. Todas as modificações de código são feitas nele, commitadas e enviadas ao GitHub. O Linux Mint é minha máquina de execução e deve apenas receber essas modificações.

**Resultado esperado:** ao finalizar, a branch `main` local do Linux deve apontar exatamente para o mesmo commit que a branch `main` remota do GitHub, sem perder arquivos locais, criar conflitos ou introduzir alterações próprias.

Não me apresente apenas instruções: execute a sincronização diretamente no ambiente Linux, usando o terminal e as ferramentas disponíveis.

## 2. Ambiente e repositório

- Sistema operacional: Linux Mint.
    
- Repositório local: `/home/kevyn/hermes-agent`.
    
- Repositório remoto: `https://github.com/kevynlucasprofissional-stack/hermes-agent.git`.
    
- Remote Git: `origin`.
    
- Branch obrigatória: `main`.
    
- Fluxo autorizado: **GitHub → Linux**.
    
- Fluxo proibido nesta missão: **Linux → GitHub**.
    

O Git já está instalado no Linux. Não é necessário instalar o GitHub Desktop.

Os caminhos acima identificam o repositório esperado. Não trabalhe em outro repositório caso algum caminho esteja ausente ou incorreto.

## 3. Regras de segurança inegociáveis

1. Não executar `git push`, `git commit`, `git reset --hard`, `git clean`, `git stash`, `git rebase`, `git cherry-pick` ou `git merge` sem `--ff-only`.
    
2. Não criar branches, worktrees, commits ou arquivos temporários dentro do repositório.
    
3. Não apagar, sobrescrever, mover ou modificar arquivos locais não rastreados pelo Git.
    
4. Não descartar alterações locais rastreadas, sejam staged ou unstaged.
    
5. Não usar `--force` nem resolver divergências reescrevendo o histórico.
    
6. Não alterar credenciais, configurações globais do Git, permissões, `.env`, bancos de dados, perfis Electron, sessões ou arquivos operacionais.
    
7. Não alterar o código-fonte para fazer a sincronização funcionar.
    
8. Não atualizar automaticamente Node.js, Python ou dependências.
    
9. Não executar `npm ci`, `npm install`, scripts de bootstrap ou reinstalações como parte desta missão.
    
10. Não iniciar, reiniciar ou encerrar o Hermes Workstation ou processos do usuário sem necessidade e autorização.
    
11. Não solicitar credenciais nem imprimi-las em logs. O repositório remoto é público; a sincronização de leitura deve funcionar sem autenticação.
    
12. Se identificar um conflito, divergência, operação Git pendente ou situação que ameace os arquivos locais, **interrompa a etapa de atualização, preserve o estado existente e explique o bloqueio**.
    

Não tente contornar bloqueios de segurança para cumprir o objetivo.

## 4. Execução obrigatória — ordem exata

### Etapa 1 — Identificar e validar o repositório

No terminal Linux:

```
cd /home/kevyn/hermes-agent || exit 1

git rev-parse --is-inside-work-tree
git rev-parse --show-toplevel
git branch --show-current
git remote get-url origin
git rev-parse HEAD
git status --short --branch
```

Confirme obrigatoriamente que:

- O diretório existe e é um repositório Git válido.
    
- A raiz canônica do repositório é `/home/kevyn/hermes-agent`.
    
- A branch ativa é `main`.
    
- O remote `origin` aponta para o repositório `kevynlucasprofissional-stack/hermes-agent`, e não para um fork diferente ou outro projeto.
    
- O Git consegue identificar o commit local atual.
    

Se qualquer condição falhar, interrompa. Não faça checkout automático de outra branch nem altere o remote.

### Etapa 2 — Auditar alterações locais

Verifique o estado da árvore de trabalho e do índice:

```
git status --porcelain=v1 --untracked-files=normal
git diff --name-only
git diff --cached --name-only
git ls-files -u
```

Verifique também se há merge, rebase, cherry-pick ou outra operação Git inacabada.

Aplique esta política:

**Arquivos rastreados modificados:** não execute a atualização. Informe quais arquivos impedem a sincronização e preserve-os integralmente.

**Arquivos não rastreados:** podem permanecer no diretório. Não os exclua, não os adicione ao Git e não os modifique. A atualização só poderá prosseguir se nenhum deles for sobrescrito ou entrar em colisão com arquivos recebidos do remoto.

**Operação Git incompleta ou conflitos existentes:** não prossiga.

Um arquivo local conhecido é `PLANO_DEFINITIVO.md`, que pode existir como arquivo não rastreado. Sua presença, isoladamente, não exige bloqueio, desde que esteja protegido contra sobrescrita.

Não conclua que um diretório está seguro apenas porque `git diff` está vazio: verifique também o índice e os arquivos não rastreados.

### Etapa 3 — Consultar a versão atual do GitHub

Consulte a referência remota:

```
GIT_TERMINAL_PROMPT=0 git ls-remote origin refs/heads/main
```

Exija um resultado válido contendo o hash da branch remota `main`.

Depois execute:

```
GIT_TERMINAL_PROMPT=0 git fetch origin main
```

Aguarde a conclusão efetiva do processo e confirme o código de saída.

Não interprete o início do processo como sucesso.

Verifique:

```
git rev-parse HEAD
git rev-parse origin/main
git merge-base HEAD origin/main
```

Compare o commit local com o commit remoto.

Se a referência remota mudar durante a operação, não declare sincronização concluída com um hash desatualizado.

### Etapa 4 — Determinar o cenário de sincronização

Classifique o estado em um dos cenários seguintes.

**Cenário A — Linux já atualizado**

Se `HEAD` local e `origin/main` forem iguais, não execute merge nem crie commit.

Confirme a igualdade com a versão mais recente consultada no GitHub e passe diretamente à auditoria final.

**Cenário B — Linux está atrás do GitHub**

Se `HEAD` local for ancestral de `origin/main`, a atualização por fast-forward é permitida.

Confirme com:

```
git merge-base --is-ancestor HEAD origin/main
```

Se o resultado for bem-sucedido, verifique novamente a segurança dos arquivos locais e prossiga.

**Cenário C — Linux tem commits próprios ou histórico divergente**

Se o commit local não for ancestral do remoto, interrompa.

Não faça rebase, merge convencional, reset ou force.

Informe os hashes divergentes e o motivo do bloqueio. Não tente resolver por conta própria.

**Cenário D — Arquivos locais seriam sobrescritos**

Interrompa sem excluir nem mover os arquivos. Informe precisamente quais caminhos apresentam colisões.

### Etapa 5 — Executar a sincronização

Somente se todas as verificações anteriores forem aprovadas, execute:

```
git merge --ff-only origin/main
```

Esse comando deve apenas avançar o ponteiro da branch `main` local até o commit já existente no remoto.

A execução não pode produzir um novo commit de merge.

Não use `git pull` sem `--ff-only` e não use `git pull --rebase`.

Se o comando falhar, registre o erro real, preserve o estado e interrompa a operação.

### Etapa 6 — Validar o resultado

Execute:

```
git rev-parse HEAD
git rev-parse origin/main
git status --short --branch
git diff --exit-code
git diff --cached --exit-code
```

Confirme que:

1. `HEAD` local é idêntico a `origin/main`.
    
2. A branch ativa continua sendo `main`.
    
3. Não foi criado nenhum commit local adicional.
    
4. Não surgiram alterações rastreadas na árvore de trabalho.
    
5. Nenhum arquivo local preexistente foi apagado ou sobrescrito.
    
6. O repositório não ficou em estado de conflito.
    
7. Não foi executado nenhum push.
    

Consulte novamente o hash do `main` remoto usando `git ls-remote`.

Se o GitHub tiver recebido novos commits durante a sincronização, informe que houve atualização concorrente. Poderá repetir uma única vez o ciclo de fetch, verificação e fast-forward, desde que todas as condições de segurança permaneçam satisfeitas. Não entre em um ciclo ilimitado.

Compare também o hash da árvore Git:

```
git rev-parse HEAD^{tree}
git rev-parse origin/main^{tree}
```

Os hashes das árvores devem coincidir.

### Etapa 7 — Verificar alterações de dependências

Compare os arquivos modificados entre o commit Linux original e o commit final.

Preste atenção a mudanças em:

- `package.json` e arquivos de manifests dos workspaces;
    
- `package-lock.json`;
    
- `pyproject.toml`;
    
- `uv.lock`;
    
- scripts de bootstrap;
    
- configurações de compilação e execução do Desktop.
    

Se houver mudanças nessas áreas, informe que pode ser necessária uma preparação do ambiente antes de executar o Hermes.

**Não execute automaticamente a reinstalação.** O objetivo é sincronizar o código, não modificar o ambiente de execução.

Caso não haja mudanças relevantes nessas áreas, não recomende reinstalação sem motivo demonstrável.

Também identifique mudanças em submódulos, quando existirem. Não execute `git submodule update` automaticamente.

## 5. Comportamento esperado em situações especiais

**Se a internet estiver indisponível:** interrompa após tentativas razoáveis de consulta. Não use referências locais antigas como se fossem a versão atual do GitHub.

**Se houver uma falha de autenticação:** não solicite nem armazene tokens no repositório; reporte o problema.

**Se o diretório estiver ausente:** não clone automaticamente outro repositório.

**Se houver alterações locais não commitadas:** não faça stash automático nem commits de preservação. Informe o bloqueio.

**Se houver arquivos não rastreados:** preserve-os e diferencie claramente esses arquivos de mudanças versionadas.

**Se o repositório já estiver atualizado:** conclua sem modificações desnecessárias.

**Se houver uma atualização remota durante o procedimento:** revalide a referência antes de declarar sucesso.

**Se o Hermes estiver aberto:** não encerre o aplicativo à força. Se a atualização modificar arquivos utilizados por um processo ativo, informe que poderá ser necessário reiniciá-lo posteriormente para carregar a nova versão. Não realize esse reinício nesta missão.

## 6. Relatório final obrigatório

Ao finalizar, apresente um relatório curto, factual e auditável contendo:

**Identificação**

- Computador: Linux Mint.
    
- Repositório: `/home/kevyn/hermes-agent`.
    
- Branch: `main`.
    

**Sincronização**

- Hash local antes da execução.
    
- Hash remoto identificado.
    
- Hash local após a execução.
    
- Hash remoto após a execução.
    
- Quantidade de commits recebidos.
    
- Quantidade de arquivos alterados, se aplicável.
    
- Confirmação da igualdade entre os commits e as árvores Git.
    

**Segurança**

- Alterações locais rastreadas identificadas.
    
- Arquivos não rastreados preservados.
    
- Conflitos ou impedimentos detectados.
    
- Confirmação de que nenhum commit, push, reset, stash ou limpeza foi realizado.
    

**Ambiente**

- Informar se foram detectadas mudanças de dependências.
    
- Informar se será necessário algum procedimento de preparação antes de executar o Hermes.
    

**Resultado**

Use uma das seguintes classificações:

- **SINCRONIZADO:** Linux e GitHub estão no mesmo commit, com validações concluídas.
    
- **JÁ ATUALIZADO:** nenhuma atualização era necessária, e a igualdade foi confirmada.
    
- **BLOQUEADO COM SEGURANÇA:** havia uma condição que impediria a atualização segura.
    
- **PARCIAL / NÃO VERIFICADO:** houve falha de conexão, limitação da ferramenta ou outra impossibilidade de concluir todas as verificações.
    

Nunca declare sucesso apenas porque o comando Git retornou sem apresentar erros. Confirme efetivamente os hashes finais.

## 7. Critério definitivo de conclusão

Esta missão estará concluída somente quando for possível demonstrar:

`**Linux main HEAD = GitHub origin/main HEAD = GitHub remoto main HEAD**`

Com os arquivos locais preexistentes preservados, a árvore rastreada limpa e nenhuma alteração enviada do Linux para o GitHub.

A regra de arquitetura é permanente:

**Windows desenvolve → GitHub recebe → Linux sincroniza e executa.**

Execute a missão agora, de forma autônoma, segura, idempotente e sem expandir o escopo.