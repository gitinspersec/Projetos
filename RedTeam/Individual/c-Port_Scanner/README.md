```ruby
██████╗  ██████╗ ██████╗ ████████╗    ███████╗ ██████╗ █████╗ ███╗   ██╗███╗   ██╗███████╗██████╗
██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝    ██╔════╝██╔════╝██╔══██╗████╗  ██║████╗  ██║██╔════╝██╔══██╗
██████╔╝██║   ██║██████╔╝   ██║       ███████╗██║     ███████║██╔██╗ ██║██╔██╗ ██║█████╗  ██████╔╝
██╔═══╝ ██║   ██║██╔══██╗   ██║       ╚════██║██║     ██╔══██║██║╚██╗██║██║╚██╗██║██╔══╝  ██╔══██╗
██║     ╚██████╔╝██║  ██║   ██║       ███████║╚██████╗██║  ██║██║ ╚████║██║ ╚████║███████╗██║  ██║
╚═╝      ╚═════╝ ╚═╝  ╚═╝   ╚═╝       ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝
```

[![C++20](https://img.shields.io/badge/C++-20-00599C?style=flat&logo=cplusplus)](https://isocpp.org)
[![CMake](https://img.shields.io/badge/CMake-3.31+-064F8C?style=flat&logo=cmake)](https://cmake.org)

> Scanner de portas TCP assíncrono construído com C++ e Boost.Asio para reconhecimento de rede de alta concorrência.

_Esta é uma visão geral rápida — teoria de segurança, arquitetura e orientações completas estão nos [módulos de aprendizado](#learn)._

> _Desenvolvido por [@deniskhud](https://github.com/deniskhud)_

## O que ele faz

- Escaneamento de portas TCP assíncrono usando Boost.Asio para alta concorrência
- Intervalos de portas configuráveis, desde portas únicas até escaneamentos completos de 65535
- Nível de concorrência ajustável para controlar a velocidade do escaneamento e a carga na rede
- Configuração de timeout de conexão para lidar com portas filtradas de forma adequada
- Saída de terminal limpa mostrando estados de portas abertas, fechadas e filtradas

## Início Rápido

```bash
mkdir build && cd build
cmake ..
make
./simplePortScanner --target 192.168.1.1 --ports 1-1024
```

> [!TIP]
> Este projeto usa [`just`](https://github.com/casey/just) como um executor de comandos. Digite `just` para ver todos os comandos disponíveis.
>
> Instalação: `curl -sSf https://just.systems/install.sh | bash -s -- --to ~/.local/bin`

## Compilação

**Requisitos:** Compilador C++20, biblioteca Boost, CMake >= 3.31

```bash
./simplePortScanner --target 10.0.0.1 --ports 22,80,443 --concurrency 200
./simplePortScanner --target 172.16.0.5 --ports 1-65535 --timeout 500
```

## Aprenda

Este projeto inclui materiais de aprendizado passo a passo cobrindo teoria de segurança, arquitetura e implementação.

| Módulo                                        | Tópico                                        |
| --------------------------------------------- | --------------------------------------------- |
| [00-Introdução](learn/00-Introdução.md)       | Pré-requisitos e início rápido                |
| [01-Conceitos](learn/01-Conceitos.md)         | Teoria de segurança e violações do mundo real |
| [02-Arquitetura](learn/02-Arquitetura.md)     | Design do sistema e fluxo de dados            |
| [03-Implementação](learn/03-Implementação.md) | Passo a passo do código                       |
| [04-Desafios](learn/04-Desafios.md)           | Ideias de extensão e exercícios               |

---

@CarterPerez-dev | Copyright (C) 2026 Murilo Miacci
