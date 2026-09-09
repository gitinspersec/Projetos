# Port Scanner

![Mode](https://img.shields.io/badge/Mode-Individual-402)
![Difficulty](https://img.shields.io/badge/Difficulty-N3_Intermedi%C3%A1rio-yellow)
![Stack](https://img.shields.io/badge/Stack-C%2B%2B-00599C)

> Scanner de portas TCP assíncrono construído com C++ e Boost.Asio para reconhecimento de rede de alta concorrência.

_Esta é uma visão geral rápida — teoria de segurança, arquitetura e orientações completas estão nos [/learn](./learn/00-Introdução.md)._

## 🎯 Objective

Construir um scanner de portas TCP assíncrono que mapeia portas abertas em um alvo autorizado, usando C++ e Boost.Asio para alta concorrência e controle preciso de timeouts e estados de conexão.

## 🧠 Learning Outcomes

- O que é reconhecimento de rede e por que mapear portas importa
- Fundamentos de TCP: estados de conexão, handshake, timeouts
- Programação de sockets com Boost.Asio (assíncrono)
- Concorrência e controle de carga em escaneamento
- Diferenças entre portas abertas, fechadas e filtradas

## � Caso tenha dificuldades com a base do projeto

> [!NOTE]
> Este projeto ensina conceitos de redes e C++ nos módulos `learn/`. Se você tiver dificuldade com sockets ou C++, estes recursos ajudam a avançar.

- [C++ Socket Programming Tutorial](https://www.youtube.com/watch?v=LtXEMwSG5-8) — introdução prática a sockets em C++
- [Beej's Guide to Network Programming](https://beej.us/guide/bgnet/) — referência consolidada para socket APIs
- [YouTube: What is TCP/IP? - Techquickie](https://youtu.be/PpsEaqJV_A0?si=c4rZo9wSYmt6hNQa) — visualize os principais conceitos de rede

## 🛠️ Scope

### MVP

- Concluir os **Desafios 1–3 (fáceis)** em `learn/04-Desafios.md`: saída CSV, indicador de progresso e escaneamento de múltiplos hosts.
- Manter o scanner TCP assíncrono, os intervalos de portas, o controle de concorrência/timeout e a classificação de estados definidos na base do projeto.
- Demonstrar cada desafio com uma execução em alvo autorizado e testes/validações reproduzíveis.

### Stretch

- **Desafios 4–5 (intermediários):** saída JSON e detecção de versão de serviço.

### Conquer

- **Desafios 6–7 (avançados):** SYN scan e fingerprinting de sistema operacional.
- **Desafios 8–9 (especialistas):** engine de escaneamento completa estilo Nmap e técnicas de evasão de IDS.
- **Integração no mundo real:** integração com Metasploit e implantação em AWS Lambda.
- **Desempenho:** suporte a 100.000 conexões concorrentes e redução do uso de largura de banda.
- **Segurança:** detecção de sequência de port knock e marca d'água de atribuição de scan.

## ✅ Definition of Done

- [ ] Compila com CMake sem erros
- [ ] `./simplePortScanner --target <ip> --ports <range>` funciona
- [ ] Identifica portas abertas, fechadas e filtradas corretamente
- [ ] Controla concorrência e timeout conforme configuração

## 🧪 Validation

```
bash
mkdir build && cd build
cmake ..
make
./simplePortScanner --target 10.0.0.1 --ports 22,80,443 --concurrency 200
./simplePortScanner --target 172.16.0.5 --ports 1-65535 --timeout 500
```

> [!IMPORTANT]
> Use **apenas alvos autorizados** (seu próprio ambiente, CTF, lab local). Nunca escaneie sistemas sem permissão explícita.

## 🎬 Demo

Execute o scanner em um alvo local autorizado e explique:

- Como o scanner determina cada estado de porta (aberta, fechada, filtrada)
- Como a concorrência afeta a velocidade e a carga na rede
- Como o timeout lida com portas filtradas

## 🚀 Getting Started

```
bash
mkdir build && cd build
cmake ..
make
./simplePortScanner --target 192.168.1.1 --ports 1-1024
```

> [!TIP]
> Este projeto usa [`just`](https://github.com/casey/just) como executor de comandos. Digite `just` para ver todos os comandos disponíveis.
>
> Instalação: `curl -sSf https://just.systems/install.sh | bash -s -- --to ~/.local/bin`

## Requisitos

- Compilador C++20
- Biblioteca Boost
- CMake >= 3.31

## 📚 Learning Resources

| Módulo                                          | Tópico                             |
| ----------------------------------------------- | ---------------------------------- |
| [00 - Introdução](learn/00-Introdução.md)       | Pré-requisitos e início rápido     |
| [01 - Conceitos](learn/01-Conceitos.md)         | Teoria de segurança, TCP, sockets  |
| [02 - Arquitetura](learn/02-Arquitetura.md)     | Design do sistema e fluxo de dados |
| [03 - Implementação](learn/03-Implementação.md) | Passo a passo do código            |
| [04 - Desafios](learn/04-Desafios.md)           | Ideias de extensão e exercícios    |

## 🔗 Referências externas

- learncpp.com — https://www.learncpp.com/
- Beej's Guide to Network Programming — https://beej.us/guide/bgnet/
- Kurose & Ross (Computer Networking) — https://gaia.cs.umass.edu/kurose_ross/index.php

## 🧭 Next Step

Após concluir `Port_Scanner`, avance para o projeto em equipe do mesmo ramo: [`Net_Analyzer`](../../Team/Net_Analyzer/README.md) — análise de tráfego de rede e interpretação de protocolos.

> [!NOTE]
> **Não é obrigatório** avançar imediatamente para o próximo projeto. Você pode trabalhar em múltiplos projetos primários em paralelo, respeitando as janelas de entrega do calendário.

---

@CarterPerez-dev | Copyright (C) 2026 Murilo Miacci
