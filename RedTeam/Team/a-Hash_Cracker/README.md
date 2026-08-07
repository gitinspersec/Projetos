```ruby
██╗  ██╗ █████╗ ███████╗██╗  ██╗ ██████╗██████╗  █████╗  ██████╗██╗  ██╗███████╗██████╗
██║  ██║██╔══██╗██╔════╝██║  ██║██╔════╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗
███████║███████║███████╗███████║██║     ██████╔╝███████║██║     █████╔╝ █████╗  ██████╔╝
██╔══██║██╔══██║╚════██║██╔══██║██║     ██╔══██╗██╔══██║██║     ██╔═██╗ ██╔══╝  ██╔══██╗
██║  ██║██║  ██║███████║██║  ██║╚██████╗██║  ██║██║  ██║╚██████╗██║  ██╗███████╗██║  ██║
╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
```

[![C++](https://img.shields.io/badge/C%2B%2B23-00599C?style=flat&logo=cplusplus&logoColor=white)](https://isocpp.org)

> Ferramenta multi-threaded de quebra de hash com ataques de dicionário, força bruta e mutação baseada em regras.

_Esta é uma visão geral rápida — teoria de segurança, arquitetura e orientações completas estão nos [módulos de aprendizado](#learn)._

## O Que Ele Faz

- Quebra hashes MD5, SHA1, SHA256 e SHA512 com detecção automática a partir do comprimento do hash
- Ataques de dicionário usando wordlists mapeadas em memória para manipulação de arquivos grandes com zero-copy
- Ataques de força bruta com conjuntos de caracteres configuráveis e particionamento de keyspace
- Mutações baseadas em regras (capitalização, leet speak, anexação de dígitos, inversão, alternância de caixa)
- Multi-threaded com particionamento de trabalho sem contenção em todos os núcleos da CPU
- Suporte a salt com posicionamento de prefixo/sufixo
- Exibição de progresso rica no terminal com velocidade, ETA e barra de progresso

## Início Rápido

```bash
./install.sh
hashcracker --hash 5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8 \
  --wordlist wordlists/10k-most-common.txt
# ✔ QUEBRADO: password
```

> [!TIP]
> Este projeto usa o [`just`](https://github.com/casey/just) como um executor de comandos. Digite `just` para ver todos os comandos disponíveis.
>
> Instalação: `curl -sSf https://just.systems/install.sh | bash -s -- --to ~/.local/bin`

## Hashes de Demonstração

Tente estes — todos são quebrados instantaneamente contra a wordlist incluída:

| Hash                                                               | Tipo   | Texto simples |
| ------------------------------------------------------------------ | ------ | ------------- |
| `5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8` | SHA256 | password      |
| `8621ffdbc5698829397d97767ac13db3`                                 | MD5    | dragon        |
| `ed9d3d832af899035363a69fd53cd3be8f71501c`                         | SHA1   | shadow        |

```bash
hashcracker --hash 8621ffdbc5698829397d97767ac13db3 --wordlist wordlists/10k-most-common.txt
hashcracker --hash ed9d3d832af899035363a69fd53cd3be8f71501c --wordlist wordlists/10k-most-common.txt --rules
hashcracker --hash 5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8 --bruteforce --charset lower --max-length 8
```

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
