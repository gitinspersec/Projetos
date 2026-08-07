# Net Analyzer

![Team](https://img.shields.io/badge/Team-Red_Team-c62828)
![Mode](https://img.shields.io/badge/Mode-Team-555)
![Difficulty](https://img.shields.io/badge/Difficulty-N5_Especialista-red)
![Stack](https://img.shields.io/badge/Stack-Python%20%2F%20C%2B%2B-3776AB)

> Analisador de tráfego de rede com duas implementações — Python (baseline) e C++ (variante avançada). Ambas capturam pacotes no nível do kernel, analisam cabeçalhos de protocolo e exibem estatísticas em tempo real.

> [!NOTE]
> **Sucessor de:** [`Port_Scanner`](../../Individual/c-Port_Scanner/README.md) — da descoberta de portas para a observação e interpretação de tráfego.

_Esta é uma visão geral rápida — teoria de segurança, arquitetura e orientações completas estão nos [módulos de aprendizado](#learn)._

## 🎯 Objective

Construir um analisador de tráfego de rede que captura pacotes, analisa cabeçalhos de protocolo e exibe estatísticas em tempo real. O projeto possui **duas implementações**: Python (baseline principal) e C++ (variante avançada).

## 🧠 Learning Outcomes

- Como capturar e analisar tráfego de rede (libpcap, Scapy)
- Parsing de cabeçalhos de protocolo (IP, TCP, UDP, ICMP)
- Filtros BPF e captura seletiva
- Estatísticas em tempo real: distribuição de protocolos, top talkers, largura de banda
- Concorrência: threading produtor-consumidor (Python), mutex (C++)
- Diferenças entre implementações de alto e baixo nível

## 📋 Prerequisites

- **Python 3.14+** (baseline) — conhecimento básico de Python
- **C++20** (variante avançada) — conhecimento de C++, CMake, Boost
- **Conceitos de redes** — TCP, IP, protocolos (recomendado concluir `Port_Scanner`)
- **Permissões de root** ou `CAP_NET_RAW` para captura de pacotes

### 📖 O que estudar antes

> [!NOTE]
> Este projeto combina redes e captura de pacotes com níveis diferentes por implementação. Um estudo prévio de redes e ferramentas de captura é recomendado.

- [Kurose & Ross — Computer Networking](https://gaia.cs.umass.edu/kurose_ross/index.php) — fundamentos de TCP/IP
- [libpcap/pcap docs and tutorials](https://www.tcpdump.org/pcap.html) — captura de pacotes
- [Scapy documentation](https://scapy.readthedocs.io/en/latest/) — análise e manipulação de pacotes em Python

## 🛠️ Scope

### Obrigatório

- Capturar pacotes de uma interface de rede
- Analisar cabeçalhos de protocolo (IP, TCP, UDP, ICMP)
- Exibir estatísticas em tempo real (total de pacotes, volume, distribuição de protocolos)
- Identificar top talkers (IPs mais ativos)
- Calcular largura de banda

### Mínimo viável (MVP)

- **Python:** capturar pacotes e exibir distribuição de protocolos em texto simples

### Stretch

- **C++:** TUI interativa com FTXUI, parser polimórfico, engine de estatísticas com mutex
- Filtros BPF
- Exportação de gráficos (Matplotlib)
- Análise offline de arquivos `.pcap`

> [!IMPORTANT]
> **Python é o baseline obrigatório.** A implementação C++ é uma **variante avançada opcional** para membros veteranos. A equipe deve escolher **uma** implementação como entregável principal, ou ambas se houver capacidade.

## ✅ Definition of Done

- [ ] Captura de pacotes em tempo real funciona em interface de rede
- [ ] Análise de protocolos (IP, TCP, UDP, ICMP) correta
- [ ] Estatísticas em tempo real exibidas (distribuição, top talkers, largura de banda)
- [ ] Implementação Python (baseline) completa
- [ ] Testes automatizados passam
- [ ] Completar pelo menos os Desafios Nível 1–3 listados em `python/learn/04-CHALLENGES.md` ou `cpp/learn/04-CHALLENGES.md` conforme implementação escolhida

## 🧪 Validation

**Python (baseline):**

```bash
cd python
uv sync
sudo netanal capture -i eth0
```

**C++ (variante avançada):**

```bash
cd cpp
./install.sh
just run -i eth0
```

> [!IMPORTANT]
> Use **apenas ambientes autorizados**. A captura de pacotes requer privilégios elevados.

## 🎬 Demo

Execute o analisador em uma interface de rede e explique:

- Como os pacotes são capturados e analisados
- Como a distribuição de protocolos é calculada
- Como os top talkers são identificados
- Como a largura de banda é medida

## 👥 Suggested Team Breakdown

| Workstream  | Responsabilidade                                                                   |
| ----------- | ---------------------------------------------------------------------------------- |
| **Capture** | Captura de pacotes (Scapy / libpcap), filtros BPF                                  |
| **Parsing** | Análise de cabeçalhos de protocolo (IP, TCP, UDP, ICMP)                            |
| **Stats**   | Engine de estatísticas em tempo real (distribuição, top talkers, largura de banda) |
| **UI**      | Interface de terminal (Rich / FTXUI), tabelas, progresso                           |
| **Export**  | Exportação de resultados (JSON, CSV, gráficos)                                     |

> **Dica:** se a equipe optar pela variante C++, divida o trabalho entre parsing (C++) e UI (C++/FTXUI). Se optar por Python, use threading produtor-consumidor.

## Milestones

| Milestone       | Prazo estimado | Entregável (referência `learn/`)                                    |
| --------------- | -------------- | -------------------------------------------------------------------- |
| M1 — Fundação   | Semana 1       | Captura de pacotes básica, estrutura de dados (ver `python/learn/00-OVERVIEW.md` or `cpp/learn/00-OVERVIEW.md`) |
| M2 — Parsing    | Semana 2       | Análise de cabeçalhos de protocolo (ver `python/learn/01-CONCEPTS.md` or `cpp/learn/01-CONCEPTS.md`)            |
| M3 — Stats      | Semana 3       | Engine de estatísticas em tempo real (ver `python/learn/03-IMPLEMENTATION.md`)          |
| M4 — UI         | Semana 4       | Interface de terminal, tabelas, progresso (ver `python/learn/03-IMPLEMENTATION.md` or `cpp/learn/03-IMPLEMENTATION.md`)     |
| M5 — Integração | Semana 5       | Integração, testes, demo (ver `python/learn/04-CHALLENGES.md` or `cpp/learn/04-CHALLENGES.md`)                      |

## 🚀 Getting Started

**Python (baseline):**

```bash
cd python
uv sync
sudo netanal capture -i eth0
```

**C++ (variante avançada):**

```bash
cd cpp
./install.sh
just run -i eth0
```

> [!TIP]
> Este projeto usa o [`just`](https://github.com/casey/just) como executor de comandos. Digite `just` para ver todos os comandos disponíveis.
>
> Instalação: `curl -sSf https://just.systems/install.sh | bash -s -- --to ~/.local/bin`

## Implementações

| Implementação                    | Stack                      | Destaques                                                                                  |
| -------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------ |
| [**Python**](./python/README.md) | Python 3.14 • Scapy • Rich | Threading produtor-consumidor, construtor de filtro BPF, exportação de gráficos Matplotlib |
| [**C++**](./cpp/README.md)       | C++20 • libpcap • FTXUI    | TUI interativa, parser de IP polimórfico, engine de estatísticas protegida por mutex       |

## 📚 Learning Resources

Os módulos de aprendizado estão nas subpastas de cada implementação:

| Implementação | Módulos de aprendizado                                                            |
| ------------- | --------------------------------------------------------------------------------- |
| **Python**    | [`python/learn/`](./python/learn/) — teoria, arquitetura, implementação, desafios |
| **C++**       | [`cpp/learn/`](./cpp/learn/) — teoria, arquitetura, implementação, desafios       |

Cada subpasta contém os módulos `00-OVERVIEW.md`, `01-CONCEPTS.md`, `02-ARCHITECTURE.md`, `03-IMPLEMENTATION.md` e `04-CHALLENGES.md`.

## 🔗 Referências externas

- Kurose & Ross — https://gaia.cs.umass.edu/kurose_ross/index.php
- libpcap / pcap docs — https://www.tcpdump.org/pcap.html
- Scapy docs — https://scapy.readthedocs.io/en/latest/

## 🧭 Next Step

Após concluir `Net_Analyzer`, você terá completado o **Ramo C** (Network Security). Avance para the [Purple Capstone](../../../PurpleTeam/README.md) ou explore outro ramo Red/Blue.

> [!NOTE]
> **Não é obrigatório** avançar imediatamente para o próximo projeto. Você pode trabalhar em múltiplos projetos primários em paralelo, respeitando as janelas de entrega do calendário.

---

@CarterPerez-dev | Copyright (C) 2026 Murilo Miacci
