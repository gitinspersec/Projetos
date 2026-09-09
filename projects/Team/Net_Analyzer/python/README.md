```ruby
███╗   ██╗███████╗████████╗     █████╗ ███╗   ██╗ █████╗ ██╗  ██╗   ██╗███████╗███████╗██████╗
████╗  ██║██╔════╝╚══██╔══╝    ██╔══██╗████╗  ██║██╔══██╗██║  ╚██╗ ██╔╝╚══███╔╝██╔════╝██╔══██╗
██╔██╗ ██║█████╗     ██║       ███████║██╔██╗ ██║███████║██║   ╚████╔╝   ███╔╝ █████╗  ██████╔╝
██║╚██╗██║██╔══╝     ██║       ██╔══██║██║╚██╗██║██╔══██║██║    ╚██╔╝   ███╔╝  ██╔══╝  ██╔══██╗
██║ ╚████║███████╗   ██║       ██║  ██║██║ ╚████║██║  ██║███████╗██║   ███████╗███████╗██║  ██║
╚═╝  ╚═══╝╚══════╝   ╚═╝       ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝   ╚══════╝╚══════╝╚═╝  ╚═╝
```

[![Python](https://img.shields.io/badge/Python-3.14+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![PyPI](https://img.shields.io/pypi/v/netanal?color=3775A9&logo=pypi&logoColor=white)](https://pypi.org/project/netanal/)

> CLI de captura e análise de tráfego de rede com distribuição de protocolos, principais emissores e visualização de largura de banda.

_Esta é uma visão geral rápida — teoria de segurança, arquitetura e orientações completas estão nos [módulos de aprendizado](#learn)._

## O Que Ele Faz

- Captura tráfego de rede em tempo real em qualquer interface com contagem de pacotes configurável
- Análise de distribuição de protocolos em tempo real com detalhamento de porcentagem
- Identificação dos principais emissores (top talkers) mostrando os endereços IP mais ativos por volume de tráfego
- Cálculo de largura de banda com bytes enviados/recebidos por endpoint
- Modo detalhado (verbose) exibe o fluxo individual de pacotes com detalhes de origem/destino
- Construído sobre o Scapy para inspeção profunda de pacotes e parsing de protocolos

## Início Rápido

```bash
uv tool install netanal
sudo netanal capture -i eth0 -c 100
```

> [!TIP]
> Este projeto usa o [`just`](https://github.com/casey/just) como um executor de comandos. Digite `just` para ver todos os comandos disponíveis.
>
> Instalação: `curl -sSf https://just.systems/install.sh | bash -s -- --to ~/.local/bin`

## Comandos

| Comando           | Descrição                                                                                                          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------ |
| `netanal capture` | Captura de pacotes em tempo real com análise de protocolo, principais emissores e estatísticas de largura de banda |

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
