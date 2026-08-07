```regex
██████╗  ██████╗ ██████╗ ████████╗██╗ █████╗
██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝██║██╔══██╗
██████╔╝██║   ██║██████╔╝   ██║   ██║███████║
██╔═══╝ ██║   ██║██╔══██╗   ██║   ██║██╔══██║
██║     ╚██████╔╝██║  ██║   ██║   ██║██║  ██║
╚═╝      ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝╚═╝  ╚═╝
```

[![Go](https://img.shields.io/badge/Go-1.24+-00ADD8?style=flat&logo=go&logoColor=white)](https://go.dev)
[![HIBP](https://img.shields.io/badge/HIBP-integrated-2A6DB2?style=flat)](https://haveibeenpwned.com/API/v3)

> Scanner de segredos para bases de código e repositórios git, escrito em Go.

_Esta é uma visão geral rápida. Teoria de segurança, arquitetura e orientações completas estão nos [módulos de aprendizado](#learn)._

## O Que Ele Faz

- 150 regras de detecção cobrindo AWS, GitHub, GitLab, GCP, Azure, Slack, Stripe, Twilio, SendGrid, chaves SSH/PGP, senhas, strings de conexão, JWTs e mais de 100 outros
- Análise de entropia de Shannon para detectar strings de alta aleatoriedade
- Verificação de vazamento HIBP via protocolo de k-anonimato (seus segredos nunca saem da sua máquina)
- Varredura de diretórios e varredura completa do histórico do git (branches, profundidade, intervalos de datas)
- Saída em tabelas coloridas no terminal, JSON ou SARIF v2.1.0
- Defesa contra falsos positivos em 5 camadas: pré-filtro de palavras-chave, validação estrutural, stopwords, allowlists, entropia
- Pipeline concorrente com pools de workers limitados
- Configuração TOML via `.portia.toml` ou `pyproject.toml`

## Instalação

```bash
curl -fsSL https://raw.githubusercontent.com/CarterPerez-dev/portia/main/install.sh | bash
```

Ou com Go:

```bash
go install github.com/CarterPerez-dev/portia/cmd/portia@latest
```

## Início Rápido

```bash
portia scan .
```

> [!TIP]
> Este projeto usa [`just`](https://github.com/casey/just) como um executor de comandos. Digite `just` para ver todos os comandos disponíveis.
>
> Instalação: `curl -sSf https://just.systems/install.sh | bash -s -- --to ~/.local/bin`

## Comandos

| Comando                 | Descrição                                                |
| ----------------------- | -------------------------------------------------------- |
| `portia scan [caminho]` | Escaneia um diretório em busca de segredos               |
| `portia git [repo]`     | Escaneia o histórico do git em busca de segredos         |
| `portia init`           | Inicializa a configuração `.portia.toml`                 |
| `portia pyproject`      | Cria `pyproject.toml` com a configuração `[tool.portia]` |
| `portia config rules`   | Lista todas as 150 regras de detecção                    |
| `portia config show`    | Mostra a configuração ativa                              |

**Flags:** `--format` (terminal/json/sarif), `--verbose`, `--no-color`, `--exclude`, `--max-size`, `--hibp`, `--config`

**Flags do Git:** `--branch`, `--since`, `--depth`, `--staged`

## Aprenda

Este projeto inclui materiais de aprendizado passo a passo cobrindo teoria de segurança, arquitetura e implementação.

| Módulo                                           | Tópico                                                  |
| ------------------------------------------------ | ------------------------------------------------------- |
| [00 - Visão Geral](learn/00-OVERVIEW.md)         | Pré-requisitos e início rápido                          |
| [01 - Conceitos](learn/01-CONCEPTS.md)           | Secret sprawl, entropia e bancos de dados de vazamentos |
| [02 - Arquitetura](learn/02-ARCHITECTURE.md)     | Design do sistema e fluxo de dados                      |
| [03 - Implementação](learn/03-IMPLEMENTATION.md) | Passo a passo do código                                 |
| [04 - Desafios](learn/04-CHALLENGES.md)          | Ideias de extensão e exercícios                         |

---

@CarterPerez-dev | Copyright (C) 2026 Murilo Miacci
