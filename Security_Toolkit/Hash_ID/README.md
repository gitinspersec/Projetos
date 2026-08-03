```ruby
██╗  ██╗ █████╗ ███████╗██╗  ██╗    ██╗██████╗
██║  ██║██╔══██╗██╔════╝██║  ██║    ██║██╔══██╗
███████║███████║███████╗███████║    ██║██║  ██║
██╔══██║██╔══██║╚════██║██╔══██║    ██║██║  ██║
██║  ██║██║  ██║███████║██║  ██║    ██║██████╔╝
╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝    ╚═╝╚═════╝
```

> Identifique o algoritmo por trás de uma string de hash por seu prefixo, comprimento e conjunto de caracteres — o primeiro passo em qualquer fluxo de trabalho de quebra de senhas.

_Esta é uma visão geral rápida — teoria de segurança, arquitetura e tutoriais completos estão nos [módulos de aprendizado](#learn)._

> [!NOTE]
> Esta ferramenta foi desenvolvida para alguém que nunca escreveu Python antes. O código-fonte é amplamente comentado como material de apoio ao aprendizado, a pasta `materiais/` explica cada conceito do zero, e toda a ferramenta consiste em um único arquivo legível.

## O Que Ela Faz

- Identifica aproximadamente 30 formatos de hash por prefixo (`$2b$`, `$argon2id$`, `$apr1$`, `pbkdf2_sha256$`, `{SSHA}` e outros)
- Identifica hashes hexadecimais comuns pelo comprimento (MD5, SHA-1, SHA-256, SHA-512, NTLM, MD4, RIPEMD, BLAKE2, SHA-3)
- Reconhece MySQL5, NetNTLMv1/v2 e o tradicional DES crypt de 13 caracteres pelo formato
- Detecta entradas que não são hashes (JWTs, blobs em base64) e informa ao usuário o que ele realmente colou
- Retorna candidatos classificados com níveis de confiança `high` / `medium` / `low` e uma _justificativa_ de uma linha para cada hipótese
- Núcleo baseado em funções puras — sem rede, sem sistema de arquivos, sem estado global, execução instantânea
- Tabela colorida com renderização avançada; códigos de saída limpos para scripts de shell

## Início Rápido

Dentro de `Security_Toolkit/Hash_ID/`:

```bash
sudo apt update
wget -qO- https://astral.sh/uv/install.sh | sh
uv venv --python 3.14
source .venv/bin/activate
./install.sh
just run -- 5f4dcc3b5aa765d61d8327deb882cf99
# ✔ MD5 (medium) — 32 caracteres hexadecimais, candidato mais provável para este comprimento
```

> [!TIP]
> Este projeto utiliza o [`just`](https://github.com/casey/just) como executor de comandos. Digite `just` para ver todos os comandos disponíveis.
>
> Instalação: `curl -sSf https://just.systems/install.sh | bash -s -- --to ~/.local/bin`

## Hashes de Demonstração

Experimente estes exemplos — cada um demonstra um caminho diferente de identificação:

| Hash                                                                          | Detectado como      | Motivo                                                                     |
| ----------------------------------------------------------------------------- | ------------------- | -------------------------------------------------------------------------- |
| `5f4dcc3b5aa765d61d8327deb882cf99`                                            | MD5                 | 32 caracteres hexadecimais — candidato mais provável para este comprimento |
| `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`            | SHA-256             | 64 caracteres hexadecimais — candidato mais provável para este comprimento |
| `$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQNQy.uK4Of2T7G.VHvgvWK`              | bcrypt              | prefixo `$2b$` — string PHC do bcrypt, variante 2b (atual)                 |
| `$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$RdescudvJCsgt3ub+b+dWRWJTmaaJObG` | Argon2id            | prefixo `$argon2id$` — string PHC moderna, padrão atual                    |
| `$apr1$JlOdSlVe$ipa1mTAv3LFRBHHzqaIaH/`                                       | Apache MD5-crypt    | prefixo `$apr1$` — variante MD5 do Apache htpasswd (`htpasswd -m`)         |
| `*A4B6157319038724E3560894F7F932C8886EBFCF`                                   | MySQL5              | começa com `*` seguido de 40 caracteres hexadecimais em maiúsculas         |
| `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgN...`  | JWT (não é um hash) | o prefixo `eyJ` é a codificação em base64 de `{"` — JWT, não um hash       |

```bash
just run -- 5f4dcc3b5aa765d61d8327deb882cf99
just run -- '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQNQy.uK4Of2T7G.VHvgvWK'
just run -- '*A4B6157319038724E3560894F7F932C8886EBFCF'
just run -- e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

> [!IMPORTANT]
> Sempre envolva hashes que começam com `$` em **aspas simples**. Sem as aspas, seu shell tentará expandir `$2`, `$P$`, `$1$` etc. como variáveis de shell e alterará silenciosamente a entrada.

## Ferramentas

```bash
just            # lista os comandos disponíveis
just test       # executa o pytest (mais de 30 testes, executados em menos de um segundo)
just lint       # ruff + mypy --strict + pylint
just format     # yapf
just run -- <h> # identifica um hash
```

## Requisitos

- **Python 3.14+** — o script de instalação fará a verificação.
- [`uv`](https://github.com/astral-sh/uv) — gerenciador moderno de pacotes para Python (instalado automaticamente por `./install.sh`).
- [`just`](https://github.com/casey/just) — executor de comandos (instalado automaticamente por `./install.sh`).

Nenhum compilador, biblioteca de sistema ou acesso à rede é necessário. O projeto consiste em um único arquivo Python mais os testes.

## Learn

Este projeto inclui materiais de aprendizado passo a passo cobrindo teoria de segurança, arquitetura e implementação — escritos para alguém que nunca teve contato com Python.

| Módulo                                          | Tópico                                                                                                           |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| [00 - Introdução](learn/00-Introdução.md)       | Início rápido, pré-requisitos, problemas comuns                                                                  |
| [01 - Conceitos](learn/01-Conceitos.md)         | O que são hashes, violações de segurança no mundo real e os três sinais de identificação                         |
| [02 - Arquitetura](learn/02-Arquitetura.md)     | Arquitetura em três camadas, pipeline de decisão em seis etapas e design orientado a dados                       |
| [03 - Implementação](learn/03-Implementação.md) | Explicação linha por linha — cada recurso do Python é explicado quando aparece pela primeira vez                 |
| [04 - Desafios](learn/04-Desafios.md)           | Cinco níveis de ideias para extensão, desde adicionar uma regra de prefixo até construir um classificador com ML |

---

@CarterPerez-dev | Copyright (C) 2026 Murilo Miacci
