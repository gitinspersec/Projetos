```ruby
██████╗  █████╗ ███████╗███████╗    ██╗   ██╗ █████╗ ██╗   ██╗██╗     ████████╗
██╔══██╗██╔══██╗██╔════╝██╔════╝    ██║   ██║██╔══██╗██║   ██║██║     ╚══██╔══╝
██████╔╝███████║███████╗███████╗    ██║   ██║███████║██║   ██║██║        ██║
██╔═══╝ ██╔══██║╚════██║╚════██║    ╚██╗ ██╔╝██╔══██║██║   ██║██║        ██║
██║     ██║  ██║███████║███████║     ╚████╔╝ ██║  ██║╚██████╔╝███████╗   ██║
╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝      ╚═══╝  ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝
```

[![Python 3.13](https://img.shields.io/badge/Python-3.13%2B-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![Argon2id](https://img.shields.io/badge/KDF-Argon2id-8E44AD?style=flat&logo=keepassxc&logoColor=white)](https://en.wikipedia.org/wiki/Argon2)
[![AES-256-GCM](https://img.shields.io/badge/Cipher-AES--256--GCM-2E86C1?style=flat&logo=letsencrypt&logoColor=white)](https://en.wikipedia.org/wiki/Galois/Counter_Mode)

> Gerenciador de senhas de linha de comando criptografado — derivação de chave Argon2id, criptografia autenticada AES-256-GCM, escritas atômicas e duráveis, bloqueio de arquivo consultivo (advisory file locking). Uma senha mestra protege cada credencial que você confia a ele.

_Esta é uma visão geral rápida — teoria de segurança, arquitetura e orientações completas estão nos [módulos de aprendizado](#learn)._

> [!NOTE]
> O projeto assume que não há experiência prévia com Python, mas avança mais rápido. O código-fonte é fortemente comentado como auxílio didático, a pasta `learn/` explica cada ideia criptográfica do zero, e cada recurso do Python é introduzido quando aparece pela primeira vez.

## O Que Ele Faz

- Armazena credenciais em um único arquivo JSON criptografado em `~/.password-vault/vault.json` (modo `0600`)
- Deriva uma chave AES de 32 bytes da sua senha mestra via **Argon2id** (parâmetros recomendados pela OWASP, ~0.5s por derivação)
- Criptografa o conteúdo do vault com **AES-256-GCM** — confidencialidade + detecção de adulteração em uma única primitiva
- **Escritas atômicas, duráveis e seguras para concorrência**: arquivo temporário → fsync → renomeação atômica → fsync do diretório, com bloqueio `fcntl` consultivo para serializar invocações concorrentes do `pv`
- Rotação de senha mestra que re-criptografa todo o vault sob um novo salt e chave
- Gerador de senhas criptograficamente seguro usando `secrets` (nunca `random`) com um embaralhamento Fisher-Yates sobre o `secrets.randbelow`
- Armazena parâmetros KDF _no arquivo_ — vaults antigos permanecem legíveis quando os padrões mudam, e a rotação pode atualizá-los de forma transparente
- Hierarquia de exceções tipadas (`WrongPasswordError`, `VaultFormatError`, `EntryNotFoundError`, …) para tratamento preciso de erros
- Painéis e tabelas coloridos renderizados com Rich; separação de stdout/stderr amigável para pipes
- Recusa-se a distinguir "senha incorreta" de "arquivo adulterado" — ambos parecem iguais criptograficamente; expor a diferença ajuda atacantes

## Início Rápido

```bash
./install.sh
just run -- init
just run -- add github
just run -- get github
```

```text
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

> [!TIP]
> Este projeto usa o [`just`](https://github.com/casey/just) como executor de comandos. Digite `just` para ver todas as receitas disponíveis.
>
> Instalação: `curl -sSf https://just.systems/install.sh | bash -s -- --to ~/.local/bin`

## Comandos

| Comando              | O que faz                                                                                                               |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `pv init`            | Cria um novo vault vazio. Solicita a senha mestra duas vezes.                                                           |
| `pv add <name>`      | Adiciona uma entrada. Solicita usuário, senha, URL opcional e notas. `--generate` / `-g` para usar uma senha aleatória. |
| `pv get <name>`      | Mostra todos os campos de uma entrada em um painel colorido.                                                            |
| `pv list`            | Imprime o nome de cada entrada como uma tabela (senhas não são mostradas).                                              |
| `pv delete <name>`   | Remove uma entrada pelo nome.                                                                                           |
| `pv gen [length]`    | Gera uma senha aleatória forte e a imprime no stdout. Não requer vault.                                                 |
| `pv change-password` | Rotaciona a senha mestra — re-criptografa todo o vault sob um novo salt e chave.                                        |

Cada comando aceita `--vault PATH` (ou `$PV_VAULT`) para apontar para um arquivo de vault alternativo.

## Demo: geração amigável para pipes

```bash
# Gera e copia para a área de transferência (macOS)
just run -- gen 32 | pbcopy

# Gera e copia para a área de transferência (Linux)
just run -- gen 32 | xclip -selection clipboard

# Gera para uma variável de shell
PASSWORD=$(just run -- gen 32)

# Apenas letras + dígitos, sem símbolos
just run -- gen 24 --no-symbols
```

> [!IMPORTANT]
> O `pv` _nunca_ aceita a senha mestra como uma flag de CLI. Senhas passadas como flags vazam para o histórico do shell (comando `history`) e listagens de processos (`ps aux`). Cada prompt usa `getpass.getpass()` — a mesma primitiva que o `sudo` usa — para que a senha nunca seja ecoada e nunca registrada.

## Garantias criptográficas

| Preocupação                                   | Mitigação                                                                                                              |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Arquivo do vault roubado                      | Argon2id com 64 MiB / 3 passagens / 4 threads faz com que cada tentativa leve ~0.5s; um bilhão de tentativas ≈ 15 anos |
| Arquivo do vault adulterado                   | A tag de autenticação AES-GCM recusa a descriptografia; mesmo erro de "senha incorreta" por design                     |
| Queda de energia durante o salvamento         | Escrita atômica: tmp → fsync → `os.replace` → fsync do diretório pai. Sempre o antigo ou o novo, nunca metade          |
| Dois processos `pv` em disputa                | `fcntl.LOCK_EX` consultivo em arquivo `.lock` lateral (POSIX; renomeação atômica NTFS no Windows)                      |
| Arquivo temporário do vault legível por todos | `os.open` com modo `0o600` na primeiríssima chamada de sistema — sem janela de tempo para disputa de chmod             |
| Saída aleatória previsível                    | Módulo `secrets` em todos os lugares — para salts, nonces, senhas e o embaralhamento Fisher-Yates                      |
| Parâmetros KDF obsoletos                      | Parâmetros armazenados no arquivo do vault; `change-password` pode atualizá-los de forma transparente                  |
| Corrupção de parâmetros KDF                   | Validados contra os limites algorítmicos do Argon2 ao carregar; `VaultFormatError` limpo em vez de crash da biblioteca |
| Formato incompatível com versões futuras      | Campo `version` de nível superior; versões futuras podem recusar ou migrar                                             |

O que este projeto _não_ defende — e o porquê — está documentado honestamente em [`learn/01-Conceitos.md §12`](learn/01-Conceitos.md#12-putting-it-all-together-the-threat-model).

## Ferramental

```bash
just            # lista as receitas disponíveis
just test       # executa o pytest (mais de 60 testes cobrindo criptografia, vault e gerador)
just test-cov   # testes + relatório de cobertura
just lint       # ruff + mypy + pylint
just format     # yapf
just run -- <cmd> [args]
```

## Requisitos

- **Python 3.13+** — o script de instalação irá verificar.
- [`uv`](https://github.com/astral-sh/uv) — gerenciador de pacotes Python moderno (instalado automaticamente pelo `./install.sh`).
- [`just`](https://github.com/casey/just) — executor de comandos (instalado automaticamente pelo `./install.sh`).
- Linux, macOS ou WSL2 são fortemente recomendados em vez do Windows nativo — o bloqueio de arquivos e os caminhos de `fsync` de diretório são de estilo POSIX. O NTFS oferece `os.replace` atômico de qualquer forma, então o Windows nativo funciona com garantias de concorrência reduzidas.

Sem compiladores ou bibliotecas de sistema além do que `argon2-cffi` e `cryptography` instalam através do `uv`. Não é necessário acesso à rede em tempo de execução.

## Aprenda

Este projeto inclui materiais de aprendizado passo a passo cobrindo a teoria de segurança, arquitetura e implementação — escritos para alguém que nunca tocou em Python _ou_ criptografia antes. Leia-os em ordem.

| Módulo                                        | Tópico                                                                                                                             |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| [00-Introdução](learn/00-Introdução.md)       | Início rápido, pré-requisitos, layout do projeto, problemas comuns                                                                 |
| [01-Conceitos](learn/01-Conceitos.md)         | O que _é_ criptografia, KDFs, Argon2id, salts, AES-GCM, nonces, o modelo de ameaça, violações reais                                |
| [02-Arquitetura](learn/02-Arquitetura.md)     | Layout de cinco arquivos, formato em disco, diagramas de fluxo por comando, o pipeline de escrita atômica                          |
| [03-Implementação](learn/03-Implementação.md) | Passo a passo linha por linha de cada arquivo fonte — cada recurso do Python explicado quando encontrado pela primeira vez         |
| [04-Desafios](learn/04-Desafios.md)           | Quinze ideias de extensão em quatro níveis, desde um comando `search` até a portabilidade do formato do vault para outra linguagem |

---

@CarterPerez-dev | Copyright (C) 2026 Murilo Miacci
