# Hash Cracker

![Team](https://img.shields.io/badge/Team-Red_Team-c62828)
![Mode](https://img.shields.io/badge/Mode-Team-555)
![Difficulty](https://img.shields.io/badge/Difficulty-N4_Avan%C3%A7ado-orange)
![Stack](https://img.shields.io/badge/Stack-C%2B%2B-00599C)

> Ferramenta multi-threaded de quebra de hash com ataques de dicionário, força bruta e mutação baseada em regras.

> [!NOTE]
> **Sucessor de:** [`Hash_ID`](../../Individual/a-Hash_ID/README.md) — identifique hashes primeiro, depois quebre-os.

_Esta é uma visão geral rápida — teoria de segurança, arquitetura e orientações completas estão nos [módulos de aprendizado](#learn)._

## 🎯 Objective

Construir uma ferramenta multi-threaded de quebra de hashes que suporta ataques de dicionário, força bruta e mutação baseada em regras, com detecção automática do algoritmo e exibição de progresso em tempo real.

## 🧠 Learning Outcomes

- Como funciona a quebra de hashes (dicionário, brute force, regras)
- C++ moderno (C++23): concorrência, threads, particionamento de trabalho
- CMake e build systems
- Wordlists mapeadas em memória (zero-copy para arquivos grandes)
- Otimização de busca e particionamento de keyspace
- Medição do custo real de quebrar um hash

## 📋 Prerequisites

- **C++ moderno** (C++20/C++23) — variáveis, funções, classes, templates
- **Concorrência** — threads, mutexes (ou disposição para aprender durante)
- **CMake** — build system
- **Conceitos de hashing** — recomendado concluir `Hash_ID` antes
- Terminal Linux/Unix

### 📖 O que estudar antes

> [!NOTE]
> Este projeto requer conforto com C++ moderno e concorrência. Os módulos `learn/` cobrem muitos conceitos, mas recomenda-se revisão prévia.

- [learncpp.com](https://www.learncpp.com/) — C++ moderno, templates e práticas
- [C++ Concurrency in Action (Chap. sobre threading)](https://www.amazon.com/C-Concurrency-Action-Anthony-Williams/dp/1933988770) — threading patterns
- [Introdução aux hashes e segurança (Crypto 101)](https://www.crypto101.io/)

## 🛠️ Scope

### Obrigatório

- Quebrar hashes MD5, SHA1, SHA256 e SHA512 com detecção automática
- Ataques de dicionário usando wordlists mapeadas em memória
- Ataques de força bruta com conjuntos de caracteres configuráveis
- Mutações baseadas em regras (capitalização, leet speak, anexação de dígitos)
- Multi-threading com particionamento de trabalho
- Suporte a salt com posicionamento prefixo/sufixo
- Exibição de progresso com velocidade, ETA e barra de progresso

### Mínimo viável (MVP)

- Quebrar MD5 e SHA256 com ataque de dicionário
- Exibir resultado em texto simples

### Stretch

- Força bruta com particionamento de keyspace
- Mutações baseadas em regras completas
- Suporte a salt
- Interface de terminal rica (velocidade, ETA, barra de progresso)

## ✅ Definition of Done

- [ ] Compila com CMake e CCache sem erros
- [ ] `hashcracker --hash <hash> --wordlist <file>` quebra hashes de demonstração
- [ ] Ataques de dicionário, brute force e regras funcionam
- [ ] Multi-threading com particionamento de trabalho sem contenção
- [ ] Testes automatizados passam
- [ ] Completar pelo menos os Desafios Nível 1–3 listados em `learn/04-CHALLENGES.md` (ver `learn/04-CHALLENGES.md`)

## 🧪 Validation

```bash
hashcracker --hash 5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8 \
  --wordlist wordlists/10k-most-common.txt
# ✔ QUEBRADO: password
```

Teste com os [hashes de demonstração](#hashes-de-demonstração) abaixo.

## 🎬 Demo

Execute a ferramenta com os hashes de demonstração e explique:

- Como o ataque de dicionário funciona e por que wordlists importam
- Como o brute force particiona o keyspace entre threads
- Como as regras geram mutações de candidatos
- Como o particionamento de trabalho evita contenção entre threads

## 👥 Suggested Team Breakdown

| Workstream    | Responsabilidade                                                        |
| ------------- | ----------------------------------------------------------------------- |
| **Hash**      | Detecção de algoritmo, interface de hashing (MD5, SHA1, SHA256, SHA512) |
| **Attack**    | Dicionário, brute force, particionamento de keyspace                    |
| **Rules**     | Sistema de mutação baseada em regras                                    |
| **IO**        | Carregamento de wordlists, mapeamento em memória, entrada/saída         |
| **Threading** | Particionamento de trabalho, sincronização, progresso                   |
| **Display**   | Interface de terminal, barra de progresso, ETA                          |

> **Dica:** cada workstream pode ser desenvolvido em paralelo se as interfaces forem definidas primeiro. Combine os módulos na fase de integração.

## Milestones

| Milestone            | Prazo estimado | Entregável (referência `learn/`)                                            |
| -------------------- | -------------- | -------------------------------------------------------------------------- |
| M1 — Fundação        | Semana 1       | CMake setup, detecção de hash, interface de hashing (ver `learn/00-OVERVIEW.md`, `learn/01-CONCEPTS.md`)   |
| M2 — Ataques básicos | Semana 2       | Dicionário + brute force em single-thread (ver `learn/03-IMPLEMENTATION.md`) |
| M3 — Regras          | Semana 3       | Sistema de mutação baseada em regras (ver `learn/03-IMPLEMENTATION.md`, `learn/04-CHALLENGES.md`)                  |
| M4 — Concorrência    | Semana 4       | Multi-threading com particionamento de trabalho (ver `learn/03-IMPLEMENTATION.md`)       |
| M5 — Integração      | Semana 5       | Integração de todos os módulos, testes, demo (ver `learn/04-CHALLENGES.md`)          |

## 🚀 Getting Started

```
bash
./install.sh
hashcracker --hash 5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8 \
  --wordlist wordlists/10k-most-common.txt
# ✔ QUEBRADO: password
```

> [!TIP]
> Este projeto usa o [`just`](https://github.com/casey/just) como executor de comandos. Digite `just` para ver todos os comandos disponíveis.
>
> Instalação: `curl -sSf https://just.systems/install.sh | bash -s -- --to ~/.local/bin`

## Hashes de Demonstração

| Hash                                                               | Tipo   | Texto simples |
| ------------------------------------------------------------------ | ------ | ------------- |
| `5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8` | SHA256 | password      |
| `8621ffdbc5698829397d97767ac13db3`                                 | MD5    | dragon        |
| `ed9d3d832af899035363a69fd53cd3be8f71501c`                         | SHA1   | shadow        |

## 📚 Learning Resources

| Módulo                                           | Tópico                                        |
| ------------------------------------------------ | --------------------------------------------- |
| [00 - Visão Geral](learn/00-OVERVIEW.md)         | Pré-requisitos e início rápido                |
| [01 - Conceitos](learn/01-CONCEPTS.md)           | Teoria de segurança e violações do mundo real |
| [02 - Arquitetura](learn/02-ARCHITECTURE.md)     | Design do sistema e fluxo de dados            |
| [03 - Implementação](learn/03-IMPLEMENTATION.md) | Passo a passo do código                       |
| [04 - Desafios](learn/04-CHALLENGES.md)          | Ideias de extensão e exercícios               |

## 🔗 Referências externas

- learncpp.com — https://www.learncpp.com/
- Crypto 101 — https://www.crypto101.io/
- C++ Concurrency patterns — artigos e capítulos relevantes (ver links indicados nos módulos `learn/`)

## 🧭 Next Step

Após concluir `Hash_Cracker`, você terá completado o **Ramo A** (Cryptography & Hashing). Avance para o [Purple Capstone](../../../PurpleTeam/README.md) ou explore outro ramo Red/Blue.

> [!NOTE]
> **Não é obrigatório** avançar imediatamente para o próximo projeto. Você pode trabalhar em múltiplos projetos primários em paralelo, respeitando as janelas de entrega do calendário.

---

@CarterPerez-dev | Copyright (C) 2026 Murilo Miacci
