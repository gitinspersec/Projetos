# Hash Identifier

## O que é isto

Um pequeno programa em Python que analisa uma sequência de caracteres aparentemente aleatórios e informa qual tipo de hash criptográfico ela provavelmente representa. Você fornece algo como isto:

```
5f4dcc3b5aa765d61d8327deb882cf99
```

e ele responde "isso é um hash MD5", juntamente com o motivo pelo qual chegou a essa conclusão.

Esse é todo o trabalho da ferramenta. Ela não quebra o hash. Ela não converte o hash de volta para uma senha. Ela apenas responde à pergunta "que tipo de hash é este?" — que é justamente a pergunta que você precisa responder _primeiro_ antes que qualquer outra ferramenta possa ajudar.

## Por que alguém precisa disso

A primeira coisa que acontece quando um ataque real é bem-sucedido é que o atacante obtém um dump de banco de dados cheio de hashes de senha. Esses hashes parecem um monte de caracteres sem sentido, mas não são aleatórios — cada hash carrega pistas sobre como foi gerado. Assim que você identifica o algoritmo (MD5, SHA-256, bcrypt, Argon2, etc.), pode fornecer o hash a uma ferramenta de quebra de senhas como o [hashcat](https://hashcat.net) ou o [John the Ripper](https://www.openwall.com/john/) e começar a tentar recuperar a senha original.

Mas existe um detalhe: o hashcat precisa que você informe qual algoritmo está sendo usado. Ele possui [mais de 400 modos de hash](https://hashcat.net/wiki/doku.php?id=example_hashes), cada um identificado por um número diferente. O modo 0 é MD5. O modo 100 é SHA-1. O modo 3200 é bcrypt. Se você escolher o modo errado, o hashcat ficará executando indefinidamente sem encontrar nada. Portanto, antes de quebrar um hash, você precisa identificá-lo. É exatamente isso que esta ferramenta faz.

**Situações reais em que você usaria esta ferramenta:**

- Um pentester encontra um arquivo de dump em um servidor comprometido cheio de strings como `$2b$12$EixZaYVK1...` e precisa descobrir o que fornecer ao hashcat.
- Um desafio de CTF entrega um hash sem absolutamente nenhuma dica sobre qual algoritmo o gerou.
- Você está lendo uma análise de um vazamento de dados e quer entender se as senhas vazadas estavam armazenadas como MD5 sem salt (um desastre) ou bcrypt com salt (muito melhor).
- O [vazamento do LinkedIn em 2012](https://en.wikipedia.org/wiki/2012_LinkedIn_hack) expôs 6,5 milhões de hashes SHA-1 sem salt. A primeira coisa que qualquer pesquisador precisou fazer antes de _qualquer outra etapa_ foi confirmar: "sim, estes são hashes SHA-1". Quarenta caracteres hexadecimais. Simples. A ferramenta que você está prestes a estudar teria informado isso em milissegundos.

## O que você aprenderá

**Conceitos de segurança:**

- O que realmente é um hash criptográfico (uma função que transforma qualquer entrada em uma sequência de tamanho fixo que não pode ser revertida).
- Os três sinais que todo hash revela sobre si mesmo: seu **prefixo**, seu **comprimento** e seu **conjunto de caracteres**.
- Por que hashes modernos para senhas (`$2b$...`, `$argon2id$...`) _se identificam deliberadamente_, enquanto hashes rápidos antigos (MD5, SHA-1) não fazem isso.
- A diferença entre um hash rápido (feito para desempenho, péssimo para senhas) e um hash lento (projetado especificamente para resistir à quebra de senhas).
- Por que nunca é possível recuperar a senha a partir de um hash; você só pode _adivinhar_ a senha e verificar se o hash gerado corresponde.

**Conceitos de Python (assumindo que seja seu primeiro contato):**

- Como ler um arquivo Python do início ao fim e entender o que ele faz.
- O que `import` faz e onde termina a biblioteca padrão e começam os pacotes de terceiros.
- Funções, type hints (`str`, `int`, `list[str]`) e o significado de `-> bool` após a assinatura de uma função.
- `@dataclass` — um atalho para criar pequenos objetos semelhantes a registros.
- `frozenset`, `dict`, `list`, `tuple` — as principais estruturas de dados do Python e quando usar cada uma.
- Como um programa de linha de comando realmente começa a ser executado (a linha `if __name__ == "__main__"` no final do arquivo).
- Como funciona um arquivo de testes e por que cada função do código principal possui testes correspondentes.

**Ferramentas que você utilizará:**

- [`uv`](https://github.com/astral-sh/uv) — o gerenciador moderno de pacotes para Python. É como o `pip`, mas aproximadamente 100 vezes mais rápido.
- [`just`](https://github.com/casey/just) — um executor de comandos. Em vez de decorar comandos longos, você digita `just test` ou `just run`.
- [`rich`](https://github.com/Textualize/rich) — a biblioteca responsável por imprimir a tabela colorida exibida ao final.
- [`pytest`](https://pytest.org) — o executor de testes do Python.
- [`ruff`](https://github.com/astral-sh/ruff) + [`mypy`](https://mypy-lang.org) + [`pylint`](https://pylint.org) — os linters que avisam quando seu código está incorreto, lento ou mal escrito.

## O que você precisa antes de começar

**Conhecimentos que você deve ter:**

- Já utilizou um terminal pelo menos uma vez (você sabe o que `cd` e `ls` fazem).
- Tem uma noção básica de que "um hash" é uma função de mão única. Caso contrário, o arquivo [01-Conceitos.md](./01-Conceitos.md) ensinará isso em cerca de 10 minutos.
- Consegue ler código, ou pelo menos está disposto a aprender. Explicaremos cada recurso do Python conforme ele aparecer.

**Conhecimentos que você NÃO precisa ter:**

- Qualquer experiência anterior com Python.
- Qualquer experiência anterior com cibersegurança.
- Qualquer conhecimento de matemática além de saber contar. Não há matemática. A criptografia utiliza matemática internamente, mas identificar um hash pelo seu formato não exige isso.

**Softwares que você precisa ter instalados:**

- Python 3.14 ou superior.
- A ferramenta `uv` (o script de instalação cuidará disso caso ela ainda não esteja instalada).
- A ferramenta `just` (também instalada automaticamente pelo script).
- Um terminal. Qualquer terminal. No Mac, Terminal.app ou iTerm2; no Linux, qualquer terminal fornecido pela sua distribuição; no Windows, WSL2 + Ubuntu (recomendamos fortemente o WSL2 em vez do Windows nativo).

Você _não_ precisa de uma IDE — um editor de texto é suficiente. Recomendo o [VS Code](https://code.visualstudio.com) com a extensão para Python, ou se não o [Zed](https://zed.dev/download), mas `nano`, `vim`, `helix` ou qualquer editor que você já utilize funcionarão perfeitamente.

## Início rápido

Dentro de `projects/Individual/Hash_ID/`:

```bash
sudo apt update
wget -qO- https://astral.sh/uv/install.sh | sh
uv venv --python 3.14
source .venv/bin/activate
./install.sh
```

Esse script instalará `uv` e `just`, caso estejam ausentes, criará um ambiente virtual (um ambiente Python isolado apenas para o Hash_ID), instalará todas as dependências e verificará se todos os testes passam. Ele informa cada etapa durante a execução — leia a saída em vez de simplesmente fechar o terminal.

Depois, experimente a ferramenta:

```bash
just run -- 5f4dcc3b5aa765d61d8327deb882cf99
```

Você deverá ver uma tabela colorida identificando essa sequência como MD5 (com NTLM, MD4 e RIPEMD-128 aparecendo como alternativas menos prováveis — todos os quatro produzem 32 caracteres hexadecimais, portanto apenas o comprimento não é suficiente para distingui-los).

Experimente mais alguns exemplos:

```bash
# bcrypt — hash moderno para senhas, identifica-se pelo prefixo $2b$
just run -- '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQNQy.uK4Of2T7G'

# SHA-256 — 64 caracteres hexadecimais
just run -- e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

# Um JWT (isto NÃO é um hash, mas a ferramenta informará isso educadamente)
just run -- eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U

# Texto completamente aleatório — a ferramenta responderá "não faço ideia" em vez de chutar
just run -- helloworld
```

**Observação sobre aspas:** quando um hash começa com `$`, você deve colocá-lo entre aspas simples (`'$2b$...'`). Sem as aspas, seu shell tentará expandir `$2` como uma variável de shell e acabará truncando o hash. Isso é uma característica do shell, não do Python — todos os shells Unix se comportam dessa forma.

## Estrutura

```
Hash_ID/
├── hash_identifier.py        toda a ferramenta — um único arquivo, ~680 linhas
├── test_hash_identifier.py   testes para todos os comportamentos prometidos pela ferramenta
├── install.sh                script de configuração em uma única execução
├── justfile                  atalhos para run / test / lint / format
├── pyproject.toml            configuração: dependências, regras dos linters etc.
├── README.md                 breve introdução apontando para esta pasta learn/
├── assets/                   gif, imagens e capturas de tela
└── learn/                    você está aqui
    ├── 00-Introdução.md      início rápido (este arquivo)
    ├── 01-Conceitos.md       o que são hashes e como a identificação funciona
    ├── 02-Arquitetura.md     como o código está estruturado, com diagramas
    ├── 03-Implementação.md   explicação linha por linha do código
    └── 04-Desafios.md        ideias de extensões caso queira ir além
```

O fato de existir apenas um arquivo de código é intencional. A estrutura foi projetada para que todo o código possa ser lido em uma única sessão.

## Para onde ir em seguida

1. **[01-Conceitos.md](./01-Conceitos.md)** — entenda _o que_ é um hash, _por que_ identificá-lo é o primeiro passo e _como_ as pistas de prefixo, comprimento e conjunto de caracteres realmente funcionam. Leia este material mesmo que ache que já conhece o assunto; a forma como ele é apresentado faz diferença.
2. **[02-Arquitetura.md](./02-Arquitetura.md)** — conheça o pipeline de seis etapas que a ferramenta utiliza para tomar uma decisão, ilustrado por meio de um fluxograma.
3. **[03-Implementação.md](./03-Implementação.md)** — leia `hash_identifier.py` conosco, linha por linha. Cada recurso do Python é explicado quando aparece pela primeira vez.
4. **[04-Desafios.md](./04-Desafios.md)** — desafios e extensões que você pode implementar depois de dominar o restante.

## Problemas comuns

**"command not found: just"**

O script de instalação deveria configurar isso automaticamente, mas, caso não tenha acontecido, execute: `curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash`. Em seguida, feche e abra novamente o terminal para que ele reconheça a nova ferramenta.

**"command not found: uv"**

A mesma ideia: execute `curl -LsSf https://astral.sh/uv/install.sh | sh` e depois reabra o terminal.

**`just run -- $2b$12$...` corta o hash**

Você esqueceu de colocar o hash entre aspas simples. Execute novamente usando `just run -- '$2b$12$...'`.

**"ModuleNotFoundError: No module named 'rich'"**

Você executou `python hash_identifier.py` diretamente em vez de usar `just run`. A receita `just run` utiliza o ambiente virtual que já possui `rich` instalado. Use `just run` ou ative primeiro o ambiente virtual com `source .venv/bin/activate` e _depois_ execute `python hash_identifier.py <hash>`.

**Os testes falham logo após a instalação**

Os testes devem passar após uma execução limpa de `./install.sh`. Caso contrário, provavelmente você está utilizando uma versão mais antiga do Python (execute `python --version`; você precisa da versão 3.14 ou superior). No Ubuntu, instale-a através do [`deadsnakes`](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa); no Mac, utilize o [Homebrew](https://brew.sh).
