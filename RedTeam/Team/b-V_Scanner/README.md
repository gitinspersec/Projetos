```regex
 █████╗ ███╗   ██╗ ██████╗ ███████╗██╗      █████╗
██╔══██╗████╗  ██║██╔════╝ ██╔════╝██║     ██╔══██╗
███████║██╔██╗ ██║██║  ███╗█████╗  ██║     ███████║
██╔══██║██║╚██╗██║██║   ██║██╔══╝  ██║     ██╔══██║
██║  ██║██║ ╚████║╚██████╔╝███████╗███████╗██║  ██║
╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝
```

[![Go](https://img.shields.io/badge/Go-1.24+-00ADD8?style=flat&logo=go&logoColor=white)](https://go.dev)
[![Go Report Card](https://goreportcard.com/badge/github.com/CarterPerez-dev/angela)](https://goreportcard.com/report/github.com/CarterPerez-dev/angela)
[![OSV.dev](https://img.shields.io/badge/OSV.dev-integrated-4285F4?style=flat)](https://osv.dev)

> Atualizador de dependências Python e scanner de vulnerabilidades rápido escrito em Go.

_Esta é uma visão geral rápida — teoria de segurança, arquitetura e orientações completas estão nos [módulos de aprendizado](#learn)._

## O Que Ele Faz

- Escaneia pyproject.toml e requirements.txt em busca de CVEs conhecidas via OSV.dev
- Atualiza todas as dependências Python para as versões estáveis mais recentes em um único comando
- Consultas paralelas ao PyPI com cache local de ETag para maior velocidade
- Parsing completo de versões PEP 440 com filtragem automática de pre-releases
- Atualizações de arquivos que preservam comentários e mantêm sua formatação intacta
- Configurável via .angela.toml ou [tool.angela] no pyproject.toml

## Início Rápido

```bash
go install github.com/CarterPerez-dev/angela/cmd/angela@latest
angela scan
```

> [!TIP]
> Este projeto usa o [`just`](https://github.com/casey/just) como um executor de comandos. Digite `just` para ver todos os comandos disponíveis.
>
> Instalação: `curl -sSf https://just.systems/install.sh | bash -s -- --to ~/.local/bin`

## Comandos

| Comando              | Descrição                                                                    |
| -------------------- | ---------------------------------------------------------------------------- |
| `angela init`        | Inicializa um novo arquivo de configuração .angela.toml                      |
| `angela update`      | Atualiza todas as dependências Python para as versões estáveis mais recentes |
| `angela check`       | Visualiza atualizações disponíveis sem modificar os arquivos                 |
| `angela scan`        | Escaneia dependências em busca de CVEs conhecidas via OSV.dev                |
| `angela cache clear` | Limpa o cache local de ETag e de versões                                     |

## Aprenda

Este projeto inclui materiais de aprendizado passo a passo cobrindo teoria de segurança, arquitetura e implementação.

| Módulo                                           | Tópico                                        |
| ------------------------------------------------ | --------------------------------------------- |
| [00 - Visão Geral](learn/00-OVERVIEW.md)         | Pré-requisitos e início rápido                |
| [01 - Conceitos](learn/01-CONCEPTS.md)           | Teoria de segurança e violações do mundo real |
| [02 - Arquitetura](learn/02-ARCHITECTURE.md)     | Design do sistema e fluxo de dados            |
| [03 - Implementação](learn/03-IMPLEMENTATION.md) | Passo a passo do código                       |
| [04 - Desafios](learn/04-CHALLENGES.md)          | Ideias de extensão e exercícios               |

---

@CarterPerez-dev | Copyright (C) 2026 Murilo Miacci
