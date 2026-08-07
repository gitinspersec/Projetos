# Analisador de Tráfego de Rede

Duas implementações do mesmo analisador de tráfego de rede — uma em Python, outra em C++. Ambas capturam pacotes no nível do kernel, analisam cabeçalhos de protocolo e exibem estatísticas em tempo real.

**[Capturas de tela e demonstração →](DEMO.md)**

## Implementações

| Implementação          | Stack                      | Destaques                                                                                  |
| ---------------------- | -------------------------- | ------------------------------------------------------------------------------------------ |
| [**C++**](./cpp)       | C++20 • libpcap • FTXUI    | TUI interativa, parser de IP polimórfico, engine de estatísticas protegida por mutex       |
| [**Python**](./python) | Python 3.14 • Scapy • Rich | Threading produtor-consumidor, construtor de filtro BPF, exportação de gráficos Matplotlib |

## Início Rápido

**C++ — TUI interativa de alto desempenho:**

```bash
cd cpp
./install.sh
just run -i eth0
```

**Python — scriptável com exportação de gráficos:**

```bash
cd python
uv sync
sudo netanal capture -i eth0
```

Ambos requerem root ou a capability `CAP_NET_RAW` para captura de pacotes.

---

@CarterPerez-dev | Copyright (C) 2026 Murilo Miacci
