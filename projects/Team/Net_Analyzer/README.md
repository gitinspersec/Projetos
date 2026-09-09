# Net Analyzer

![Mode](https://img.shields.io/badge/Mode-Team-402)
![Difficulty](https://img.shields.io/badge/Difficulty-N5_Especialista-red)
![Stack](https://img.shields.io/badge/Stack-Python%20%2F%20C%2B%2B-3776AB)

> Analisador de tráfego de rede com duas implementações — Python (baseline) e C++ (variante avançada). Ambas capturam pacotes no nível do kernel, analisam cabeçalhos de protocolo e exibem estatísticas em tempo real.

> [!NOTE]
> **Sucessor de:** [`Port_Scanner`](../../Individual/Port_Scanner/README.md) — da descoberta de portas para a observação e interpretação de tráfego.

_Esta é uma visão geral rápida — teoria de segurança, arquitetura e orientações completas estão nos [/learn](.)._

## 🎯 Objective

Construir um analisador de tráfego de rede que captura pacotes, analisa cabeçalhos de protocolo e exibe estatísticas em tempo real. O projeto possui **duas implementações**: Python (baseline principal) e C++ (variante avançada).

## 🧠 Learning Outcomes

- Como capturar e analisar tráfego de rede (libpcap, Scapy)
- Parsing de cabeçalhos de protocolo (IP, TCP, UDP, ICMP)
- Filtros BPF e captura seletiva
- Estatísticas em tempo real: distribuição de protocolos, top talkers, largura de banda
- Concorrência: threading produtor-consumidor (Python), mutex (C++)
- Diferenças entre implementações de alto e baixo nível

## � Caso tenha dificuldades com a base do projeto

> [!NOTE]
> Este projeto combina captura de pacotes e análise de redes. Se você travar na base, estes recursos rápidos ajudam a avançar.

- [Wireshark Tutorial for Beginners — NetworkChuck](https://www.youtube.com/watch?v=TkCSr30UojM) — captura e análise de pacotes prática
- [C++ Packet Sniffing Tutorial](https://youtu.be/5PPfy-nUWIM?si=dOLh2h3DyWHoPKfP) — exemplo prático de leitura de pacotes em C++
- [Scapy - Null Byte](https://youtu.be/yD8qrP8sCDs?si=tndom-P9g1s9n6Oa) — análise de rede com Python

## 🛠️ Scope

### MVP

- Escolher uma implementação (Python ou C++) e concluir os **Desafios 1–3** da trilha correspondente:
  - Python: suporte a IPv6, consulta OUI de MAC e alerta de limite de largura de banda em `python/learn/04-CHALLENGES.md`.
  - C++: detalhamento de tipos ICMP, protocolos por cores na TUI e contador de taxa de pacotes em `cpp/learn/04-CHALLENGES.md`.
- Manter a captura de pacotes, a análise de protocolos e as estatísticas em tempo real da implementação escolhida.
- Demonstrar cada desafio com testes automatizados e uma captura reproduzível em interface autorizada.

### Stretch

- **Python, Desafios 4–6 (intermediários):** rastreamento TCP, correlação DNS e histograma de distribuição de tamanho de pacote.
- **C++, Desafios 4–6 (intermediários):** remontagem de fluxo TCP, log de consultas DNS e engine de regras de alerta.

### Conquer

- **Python, Desafios 7–9 (avançados):** geolocalização de IP, extração de certificado SSL/TLS e detecção de anomalias em tempo real.
- **C++, Desafios 7–10 (avançados):** hex dump, baseline de anomalias, exportação PCAP e detecção de port scanning.
- **Desempenho:** lidar com tráfego de 10 Gbps na trilha Python.
- **Segurança:** criptografia PCAP e atendimento ao checklist de benchmark do CIS na trilha Python.
- **Integração no mundo real (Python):** enviar estatísticas para SIEM e implantar como DaemonSet no Kubernetes.
- Implementar ambas as trilhas, filtros BPF, exportação de gráficos e análise offline de `.pcap` quando fizer sentido para a equipe.

> [!IMPORTANT]
> **Python é o baseline obrigatório.** A implementação C++ é uma **variante avançada opcional** para membros veteranos. A equipe deve escolher **uma** implementação como entregável principal, ou ambas se houver capacidade.

## ✅ Definition of Done

- [ ] Captura de pacotes em tempo real funciona em interface de rede
- [ ] Análise de protocolos (IP, TCP, UDP, ICMP) correta
- [ ] Estatísticas em tempo real exibidas (distribuição, top talkers, largura de banda)
- [ ] Implementação Python (baseline) completa
- [ ] Testes automatizados passam
- [ ] Completar os desafios definidos no MVP da trilha escolhida (Desafios 1–3)

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

| Milestone       | Prazo estimado | Entregável (referência `learn/`)                                                                                        |
| --------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------- |
| M1 — Fundação   | Semana 1       | Captura de pacotes básica, estrutura de dados (ver `python/learn/00-OVERVIEW.md` or `cpp/learn/00-OVERVIEW.md`)         |
| M2 — Parsing    | Semana 2       | Análise de cabeçalhos de protocolo (ver `python/learn/01-CONCEPTS.md` or `cpp/learn/01-CONCEPTS.md`)                    |
| M3 — Stats      | Semana 3       | Engine de estatísticas em tempo real (ver `python/learn/03-IMPLEMENTATION.md`)                                          |
| M4 — UI         | Semana 4       | Interface de terminal, tabelas, progresso (ver `python/learn/03-IMPLEMENTATION.md` or `cpp/learn/03-IMPLEMENTATION.md`) |
| M5 — Integração | Semana 5       | Integração, testes, demo (ver `python/learn/04-CHALLENGES.md` or `cpp/learn/04-CHALLENGES.md`)                          |

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

---

@CarterPerez-dev | Copyright (C) 2026 Murilo Miacci
