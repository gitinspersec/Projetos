# Password Vault

## O que é isso

Um pequeno gerenciador de senhas de linha de comando escrito em Python. Você digita uma senha mestra uma vez, e a ferramenta armazena todas as outras senhas que você fornecer dentro de um único arquivo criptografado. Mais tarde, você solicita à ferramenta "github" ou "email" ou "bank" e ela devolve a senha.

O projeto todo tem aproximadamente 1.400 linhas de código espalhadas por cinco arquivos. Sem servidor web, sem extensão de navegador, sem conta na nuvem. Um arquivo no disco, uma senha mestra na sua cabeça.

```
$ pv init
Nova senha mestra: ************
Confirme a senha mestra: ************
Vault criado em /home/voce/.password-vault/vault.json

$ pv add github
Usuário para github: alice
Senha para github (oculta): ************
URL (opcional, pressione Enter para pular): https://github.com
Notas (opcional, pressione Enter para pular):
Entrada adicionada: github

$ pv get github
╭────────────────── github ──────────────────╮
│ username   alice                           │
│ password   hunter2-but-better              │
│ url        https://github.com              │
│ created    2026-05-13T14:22:10+00:00       │
│ updated    2026-05-13T14:22:10+00:00       │
╰────────────────────────────────────────────╯
```

Essa é a ferramenta completa. Ela também possui `list`, `delete`, `gen` (gerar uma senha aleatória forte) e `change-password` (rotacionar a senha mestra).

## Por que alguém precisa disso

A resposta honesta é "você precisa". Cada site precisa de uma senha. Cada senha deve ser diferente. Ninguém consegue lembrar de 200 senhas diferentes, então as pessoas reutilizam uma — e no momento em que qualquer site sofre uma violação, o atacante tenta essa mesma senha em todos os outros lugares. Isso é chamado de **credential stuffing** e é como a maioria das invasões de conta realmente acontece em 2025.

Um gerenciador de senhas resolve isso fornecendo exatamente uma senha para você lembrar (a mestra) enquanto ele lembra de todo o resto. O objetivo de "cada site com uma senha diferente" torna-se alcançável porque você não precisa mais guardá-las na cabeça.

**Momentos do mundo real onde as escolhas de segurança deste projeto importam:**

- A [violação da Adobe em 2013](https://en.wikipedia.org/wiki/2013_Adobe_breach) vazou 153 milhões de senhas. A Adobe as havia criptografado com uma única chave no modo ECB — sem salt, sem aleatoriedade por registro — então senhas idênticas produziam ciphertexts idênticos. Pesquisadores puderam ver grupos de usuários que escolheram `password123` apenas olhando para o arquivo criptografado. O uso de um nonce aleatório novo por salvamento e Argon2id com um salt por vault neste projeto é a correção direta para esse tipo de erro.
- A [violação da LastPass em 2022](https://blog.lastpass.com/posts/notice-of-recent-security-incident) vazou backups de vaults criptografados. Vaults com senhas mestras fracas foram quebrados offline em escala porque o atacante tinha tempo ilimitado. A defesa — tornar cada tentativa cara — é exatamente o que o Argon2id nos oferece. Nossos padrões elevam o custo de cada tentativa para aproximadamente meio segundo em um laptop moderno, o que faz com que um ataque de um bilhão de tentativas leve cerca de 15 anos na máquina do atacante.
- Cada desafio de CTF ou engajamento de pentest onde alguém lhe entrega "um arquivo criptografado" e pergunta "isso está seguro em repouso?" — ao final deste projeto você saberá quais perguntas fazer (qual KDF? qual modo de cifra? qual a situação do salt? a tag de autenticação é verificada?).

## O que você aprenderá

**Ideias de segurança:**

- O que é **criptografia simétrica** — uma chave criptografa e descriptografa. Usamos [AES-256-GCM](https://en.wikipedia.org/wiki/Galois/Counter_Mode), o mesmo algoritmo que protege a conexão HTTPS do seu banco.
- O que uma **key derivation function (KDF)** faz — ela transforma uma senha humana (curta, fraca, previsível) em uma chave criptográfica real (32 bytes de pura imprevisibilidade). Usamos o [Argon2id](https://en.wikipedia.org/wiki/Argon2), o vencedor da Password Hashing Competition de 2015 e o algoritmo que a OWASP recomenda atualmente para armazenamento de senhas.
- Por que **salts** e **nonces** são coisas diferentes, embora ambos sejam "bytes aleatórios que você armazena ao lado do ciphertext".
- O que significa **criptografia autenticada** e por que "apenas criptografado" não é suficiente — sem autenticação, um atacante pode alterar bits no seu arquivo de maneiras previsíveis sem conhecer a chave.
- A diferença entre `random` (bom para um lançamento de dados) e `secrets` (a única coisa que você deve usar quando um atacante quer prever a saída).
- Por que **armazenamos os parâmetros KDF no arquivo** em vez de apenas deixá-los fixos no código, e como essa decisão permite que o `change-password` atualize vaults antigos para novos padrões anos depois.
- Por que escrever um arquivo "atomicamente" (escrever em um `.tmp`, fsync, renomear) importa quando uma queda de energia poderia, de outra forma, deixá-lo com zero senhas.

**Ideias de Python (assumindo que esta é sua primeira vez):**

- O que é um **pacote** e o que o `__init__.py` faz por ele.
- **Módulos** e como o `import` realmente encontra os arquivos.
- **Type hints** — `str`, `int`, `bytes`, `list[str]`, `dict[str, Entry]`, `Path | None`. Eles não são impostos em tempo de execução, mas são a documentação mais útil da linguagem.
- **`@dataclass`** — o atalho para criar classes do tipo registro sem escrever o `__init__` manualmente.
- Tipo **`Final`** — dizendo ao Python "este valor é uma constante, nunca o reatribua".
- **Context managers** (`with vault.unlock(...) as v:`) — a maneira mais limpa de dizer "configure algo, use-o, desmonte-o mesmo em caso de erros".
- **Exceções e classes de exceção personalizadas** — definindo seus próprios tipos de erro e capturando-os por categoria.
- **Geradores**, **dict comprehensions**, **f-strings** — idiomas modernos do Python que você verá em todos os lugares.
- Como o `pytest` funciona e por que o `conftest.py` é especial.
- Como funciona uma CLI construída com [Typer](https://typer.tiangolo.com) — transformando uma função em um comando apenas escrevendo seus type hints.

**Ferramentas que você tocará:**

- [`uv`](https://github.com/astral-sh/uv) — o gerenciador de pacotes Python moderno. Como o `pip`, mas cerca de 100x mais rápido.
- [`just`](https://github.com/casey/just) — um executor de comandos. Em vez de memorizar comandos longos, você digita `just test` ou `just run`.
- [`typer`](https://typer.tiangolo.com) — o framework de CLI.
- [`rich`](https://github.com/Textualize/rich) — a biblioteca que imprime os painéis e tabelas coloridos.
- [`argon2-cffi`](https://github.com/hynek/argon2-cffi) — o binding Python para a implementação de referência do Argon2.
- [`cryptography`](https://cryptography.io) — a biblioteca da Python Cryptographic Authority. O padrão ouro.
- [`pytest`](https://pytest.org) + [`ruff`](https://github.com/astral-sh/ruff) + [`mypy`](https://mypy-lang.org) + [`pylint`](https://pylint.org) — testes e linting.

## O que você precisa antes de começar

**Conhecimento que você deve ter:**

- Você já usou um terminal pelo menos uma vez (sabe o que `cd` e `ls` fazem).
- Você já viu pelo menos as palavras "hash" e "criptografia" antes. Se elas não significam nada para você, o [01-Conceitos.md](./01-Conceitos.md) foi feito para começar do zero — leia-o antes do código.
- Você consegue ler código ou está disposto a tentar. Cada recurso do Python é explicado quando aparece pela primeira vez.

**Conhecimento que você NÃO precisa:**

- Experiência prévia com Python.
- Qualquer conhecimento prévio de criptografia. Você aprenderá o que é um KDF, um nonce e uma tag de autenticação no [01-Conceitos.md](./01-Conceitos.md). Nenhuma matemática além de contagem é necessária — a matemática vive dentro das bibliotecas que chamamos.
- Qualquer histórico prévio em segurança cibernética.

**Software que você precisa instalado:**

- Python 3.13 ou mais recente (3.14 recomendado).
- A ferramenta `uv` (o script de instalação obterá isso para você se não tiver).
- A ferramenta `just` (também tratada pelo script de instalação).
- Um terminal. Mac: Terminal.app ou iTerm2. Linux: o que sua distro fornecer. Windows: WSL2 + Ubuntu (fortemente recomendado em vez do Windows nativo — os caminhos de código de bloqueio de arquivo e fsync são de estilo POSIX).

Você _não_ precisa de uma IDE — qualquer editor de texto funciona. [VS Code](https://code.visualstudio.com) com a extensão Python é um bom padrão.

## Início rápido

De dentro de `projects/Individual/Pass_Vault`:

```bash
sudo apt update
wget -qO- https://astral.sh/uv/install.sh | sh
uv venv --python 3.14
source .venv/bin/activate
./install.sh
```

Esse script instala `uv` e `just` se estiverem faltando, cria um ambiente virtual (um sandbox Python isolado apenas para este projeto), instala todas as dependências e executa a suíte de testes para confirmar que tudo funciona. Leia a saída conforme ela avança — não apenas feche o terminal.

Então crie seu primeiro vault:

```bash
just run -- init
```

Ele solicitará uma senha mestra, pedirá que você a digite novamente para confirmar e criará um vault vazio em `~/.password-vault/vault.json`. O primeiro `init` é lento de propósito — é o Argon2id fazendo seu trabalho, levando deliberadamente cerca de meio segundo para derivar a chave. Um atacante que rouba seu arquivo de vault tem que pagar esse mesmo custo de meio segundo para cada senha que quiser adivinhar.

Adicione uma entrada:

```bash
just run -- add github
```

Ele solicitará o usuário, a senha (entrada oculta) e URL e notas opcionais.

Veja a entrada:

```bash
just run -- get github
```

Você verá um painel colorido com todos os campos. A senha é mostrada em texto simples — esta é uma ferramenta de CLI local, o usuário já confia em sua própria tela.

Gere uma senha aleatória forte sem tocar no vault:

```bash
just run -- gen 32
```

Isso imprime uma senha de 32 caracteres no stdout (nada mais). Você pode enviá-la diretamente para sua área de transferência:

```bash
just run -- gen 32 | pbcopy        # macOS
just run -- gen 32 | xclip -sel c  # Linux
```

Liste o nome de cada entrada:

```bash
just run -- list
```

Altere sua senha mestra (o vault é re-criptografado sob uma nova chave):

```bash
just run -- change-password
```

Exclua uma entrada:

```bash
just run -- delete github
```

## Layout do projeto

```
password-manager/
├── src/password_manager/
│   ├── __init__.py           metadados do pacote + re-exports
│   ├── __main__.py           permite que `python -m password_manager` funcione
│   ├── constants.py          cada número mágico e string fixa
│   ├── crypto.py             primitivas Argon2id + AES-256-GCM
│   ├── generator.py          senhas aleatórias criptograficamente seguras
│   ├── vault.py              formato de arquivo, escritas atômicas, bloqueio
│   └── main.py               os comandos de CLI (init, add, get, …)
├── tests/
│   ├── conftest.py           fixtures compartilhadas do pytest
│   ├── test_crypto.py        testes de ida e volta (round-trip) + adulteração
│   ├── test_generator.py     testes de pool/comprimento/aleatoriedade
│   └── test_vault.py         testes de ponta a ponta do vault
├── install.sh                configuração de um passo
├── justfile                  atalhos para run / test / lint / format
├── pyproject.toml            config do projeto + dependências + regras de linter
├── README.md                 ponteiro curto para esta pasta
├── learn/                    você está aqui
│   ├── 00-Introdução.md      início rápido (este arquivo)
│   ├── 01-Conceitos.md       KDFs, AES-GCM, salts, nonces, violações reais
│   ├── 02-Arquitetura.md     layout de módulos, fluxos de dados, formato de arquivo
│   ├── 03-Implementação.md   passo a passo linha por linha
│   └── 04-Desafios.md        extensões se você quiser continuar
└── assets/                   imagens, capturas de tela
```

A divisão em cinco arquivos fonte é o único lugar onde este projeto abandona a simplicidade de "arquivo único" do `hash-identifier`. A criptografia exige limites estritos: o arquivo que fala com `secrets.token_bytes` é um arquivo diferente do arquivo que fala com seu sistema de arquivos, e _ambos_ são diferentes do arquivo que imprime painéis coloridos. Se um bug aparecer, o arquivo pequeno onde ele vive é o primeiro lugar a procurar.

## Para onde ir em seguida

1. **[01-Conceitos.md](./01-Conceitos.md)** — as ideias de segurança. O que é uma KDF, por que usamos Argon2id, o que o AES-GCM realmente faz por nós, por que nonces importam, o que significa criptografia autenticada. Leia isso antes do código, mesmo que ache que já sabe. O enquadramento importa mais do que as palavras.
2. **[02-Arquitetura.md](./02-Arquitetura.md)** — como o código está organizado em módulos, como o arquivo do vault se parece no disco e o fluxo passo a passo de `init` / `add` / `get` / `change-password`. Diagramas para cada um.
3. **[03-Implementação.md](./03-Implementação.md)** — leia cada arquivo fonte conosco, em ordem, com cada recurso do Python explicado conforme aparece pela primeira vez.
4. **[04-Desafios.md](./04-Desafios.md)** — ideias de extensão (busca, exportação, TOTP, caminho de atualização de key-stretching) depois de absorver o resto.

## Problemas comuns

**"command not found: just"**
O script de instalação deve configurar isso, mas se não configurou: `curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash`. Em seguida, feche e reabra seu terminal.

**"command not found: uv"**
Mesma ideia: `curl -LsSf https://astral.sh/uv/install.sh | sh`, depois reabra seu terminal.

**"`pv` é lento no `init`"**
Esse é o ponto. O Argon2id leva deliberadamente cerca de meio segundo por chamada com os padrões. O usuário paga isso uma vez por sessão; um atacante paga isso em cada tentativa. Se estiver dolorosamente lento (vários segundos), sua CPU é mais antiga — `constants.py` tem os três botões de ajuste do Argon2 que você pode diminuir.

**"Senha mestra incorreta (ou arquivo de vault está corrompido)"**
A ferramenta não consegue distinguir esses dois casos — isso é proposital, veja [01-Conceitos.md](./01-Conceitos.md). Se tiver certeza de que digitou a senha corretamente, tente `ls -la ~/.password-vault/` e verifique se o tamanho do arquivo `vault.json` é diferente de zero.

**"ModuleNotFoundError: No module named 'argon2'"**
Você executou `python src/password_manager/main.py` diretamente em vez de usar o `just run`. A receita `just run` usa o ambiente virtual que tem todas as dependências instaladas. Use o `just run` ou ative o venv primeiro: `source .venv/bin/activate`, depois execute `pv` ou `python -m password_manager`.

**Testes falham logo após a instalação**
Os testes devem passar em um `./install.sh` limpo. Se não passarem, verifique `python --version` — você precisa do 3.13+. No Ubuntu, instale um Python mais novo via [`deadsnakes`](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa); no Mac use [Homebrew](https://brew.sh).

**"Esqueci minha senha mestra"**
Não há recuperação. Isso é por design — se houvesse uma maneira de recuperar a senha, qualquer pessoa que roubasse o arquivo também a teria. Esse é o mesmo compromisso que todo gerenciador de senhas real faz. Escolha algo memorável, anote uma dica (NÃO a senha) em um local físico seguro e use o `change-password` para rotacioná-la ocasionalmente.
