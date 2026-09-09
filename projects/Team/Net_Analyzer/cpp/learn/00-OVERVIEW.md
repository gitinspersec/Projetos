# Analisador de Tráfego de Rede em C++

## O Que É Isso

Uma ferramenta CLI em C++20 que captura tráfego de rede ao vivo ou lê arquivos pcap offline, analisa quadros Ethernet/IP/TCP/UDP brutos manualmente e renderiza estatísticas em tempo real em uma UI de terminal (TUI) totalmente interativa. Construída com libpcap para captura de pacotes no nível do kernel, Boost para parsing de CLI e FTXUI para a TUI.

## Por Que Isso Importa

A visibilidade da rede é como os defensores pegam os atacantes. Se você não consegue ver o que está cruzando sua rede, não consegue detectar intrusões, exfiltração de dados ou movimentação lateral. Ferramentas como Wireshark, Zeek e Suricata todas se baseiam na mesma fundação: libpcap.

**Cenários do mundo real onde isso se aplica:**

- **Resposta a incidentes:** Durante a violação da Target em 2013, 40 milhões de números de cartões foram exfiltrados através de sistemas de PDV por meio do malware BlackPOS, que usava conexões TCP padrão para IPs externos. A visibilidade em nível de pacote teria sinalizado o tráfego de saída inesperado das máquinas de caixa da loja.

- **Detecção de APT:** O ataque SolarWinds de 2020 (CVE-2020-10148) usou beaconing HTTP — check-ins periódicos de hosts comprometidos para servidores controlados por atacantes. A detecção de anomalias na camada de pacotes captura isso: hosts que nunca falaram com IPs externos começam a fazê-lo subitamente.

- **Linha de base de protocolo:** Você não pode detectar o que é anormal sem primeiro saber o que é normal. Analisadores de pacotes estabelecem distribuições de linha de base — quanto é DNS versus HTTPS versus SMTP — para que mudanças inesperadas sejam registradas como alertas.

## O Que Você Aprenderá

**Conceitos de segurança:**

- **Acesso a raw sockets e capabilities** — Por que a captura de pacotes requer root ou `CAP_NET_RAW`, o que são as Linux capabilities e como o BPF (Berkeley Packet Filter) permite que o kernel descarte pacotes antes mesmo de chegarem ao espaço do usuário.

- **Parsing de cabeçalho de protocolo** — Como percorrer a cadeia quadro Ethernet → cabeçalho IP → cabeçalho TCP/UDP manualmente, usando offsets de bytes e `reinterpret_cast`. É isso que todo IDS, engine de DPI e firewall faz internamente.

- **Expressões de filtro BPF** — Como escrever e compilar filtros que rodam no kernel (ex: `tcp and port 443 and host 192.168.1.1`), e por que a filtragem no lado do kernel é ordens de magnitude mais rápida que a filtragem no espaço do usuário.

**Padrões de C++:**

- **Estatísticas protegidas por mutex** — Agregação thread-safe com `std::mutex` e um padrão de snapshot lock-copy-return que evita condições de corrida de dados sem bloquear a thread de renderização.

- **Parsing de IP polimórfico** — Uma base abstrata `IP_class` com subclasses `IPv4` e `IPv6`, construídas a partir de bytes brutos de pacotes e despachando o parsing da camada de transporte no construtor.

- **RAII para recursos C** — Envolvendo um handle `pcap_t*` de estilo C em um `std::unique_ptr<pcap_t, decltype(&pcap_close)>` para que o handle seja liberado automaticamente, independentemente de como a função termine.

- **Threading do event loop FTXUI** — Executando a captura de pacotes em uma thread de background enquanto o FTXUI gerencia seu próprio event loop na thread principal, coordenados com atomics e um mutex de renderização compartilhado.

## Pré-requisitos

**Obrigatório:**

- **Básico de C++20** — Você precisa ler código usando structured bindings, `std::format`, ranges, `std::atomic` e lambdas. Se `auto [key, val] : map` parecer estranho, revise o C++ moderno primeiro.

- **Redes TCP/IP** — Conhecer a pilha de camadas Ethernet → IP → TCP/UDP. Entender o que são endereços IP e números de porta, o que um handshake de três vias faz e como o ICMP difere do TCP.

- **Linha de comando Linux** — Você executará comandos, inspecionará interfaces de rede com `ip link` e concederá capabilities com `setcap`. Navegação básica no shell é assumida.

**Ferramentas necessárias:**

- **Linux (Ubuntu/Debian/Arch/Fedora)** — A engine de captura usa headers específicos do Linux (`netinet/tcp.h`, `netinet/ip.h`). O macOS funcionará com pequenas alterações; o Windows não.

- **Root ou CAP_NET_RAW** — A captura de pacotes requer isso. Execute com `sudo` ou conceda a capability ao binário: `sudo setcap cap_net_raw,cap_net_admin=eip ./network-traffic-analyzer`.

- **libpcap, Boost, Ninja, CMake** — Tratados pelo `install.sh`.

**Útil, mas não obrigatório:**

- **Experiência com Wireshark** — Se você já leu arquivos pcap ou escreveu filtros de exibição BPF, reconhecerá os conceitos imediatamente. Não é necessário para construir o projeto.

- **Histórico em programação de sistemas** — Entender despacho virtual, vtables e aritmética de ponteiros no nível de bytes ajudará você a acompanhar o `IP.cpp`. Não é obrigatório, mas acelera a compreensão.

## Início Rápido

```bash
# Clone o repositório
git clone https://github.com/gitinspersec/Projetos.git
cd projects/Team/c-Net_Analyzer/cpp/

# Instale as dependências e compile (um único comando)
./install.sh

# Liste as interfaces disponíveis
just interfaces

# Captura ao vivo na eth0
just capture -i eth0

# Capture 100 pacotes e exporte
just run -i wlan0 -c 100 --json result.json

# Analise um arquivo pcap offline
just run --offline traffic.pcap

# Execute a análise estática clang-tidy
just lint

# Formate automaticamente todos os arquivos fonte
just format
```

Saída esperada: a TUI inicia em tela cheia, mostrando uma tabela atualizada ao vivo de protocolos de transporte, protocolos de aplicação, principais IPs, principais pares origem→destino e um gráfico de largura de banda. Pressione `q` ou `Escape` para sair. Ao sair, os resultados são exportados para JSON/CSV se as flags foram passadas.

## Estrutura do Projeto

```
cpp/
├── main.cpp                     # Ponto de entrada — parsing de args, setup da TUI, coordenação de threads
├── CMakeLists.txt               # Definição do build
├── CMakePresets.json            # Presets de debug/release com exportação de compile_commands.json
├── Justfile                     # Comandos de dev (build, run, lint, format, clean)
├── install.sh                   # Setup em um comando: dependências + build
├── .clang-tidy                  # Configuração de análise estática
├── .clang-format                # Configuração de estilo de código
├── include/
│   ├── capture/pcapCapture.hpp  # PcapCapture — wrapper da libpcap
│   ├── cli/
│   │   ├── argsParse.hpp        # argsParser — wrapper do Boost.Program_options
│   │   └── filter.hpp           # struct filter + enum filter_type
│   ├── packet/
│   │   ├── packet.hpp           # Struct Packet, enums de protocolo
│   │   └── IP.hpp               # Declarações de IP_class, IPv4, IPv6
│   ├── stats/protocolStats.hpp  # Classe Stats, StatsSnapshot, todas as structs de estatísticas
│   └── TUI/view.hpp             # View — renderizador FTXUI
└── src/
    ├── capture/pcapCapture.cpp  # Implementação da engine de captura
    ├── cli/
    │   ├── argsParse.cpp        # Definições de opções de CLI
    │   └── filter.cpp           # Construtor de filtro BPF
    ├── packet/
    │   ├── packet.cpp           # Identificação de protocolo de aplicação
    │   └── IP.cpp               # Implementação do parsing de IPv4/IPv6
    ├── stats/protocolStats.cpp  # Agregação de estatísticas, exportação
    └── TUI/view.cpp             # Layout e renderização da TUI
```

## Próximos Passos

1. **Entenda os conceitos** — Leia [01-CONCEPTS.md](./01-CONCEPTS.md) para ver como a libpcap, o BPF e o parsing de protocolos funcionam no nível do kernel.
2. **Estude a arquitetura** — Leia [02-ARCHITECTURE.md](./02-ARCHITECTURE.md) para entender o modelo de threading e o design dos componentes.
3. **Percorra o código** — Leia [03-IMPLEMENTATION.md](./03-IMPLEMENTATION.md) para explicações linha por linha de cada componente principal.
4. **Estenda-o** — Leia [04-CHALLENGES.md](./04-CHALLENGES.md) para ideias sobre como adicionar remontagem de fluxo TCP, detecção de anomalias e muito mais.

## Problemas Comuns

**Permissão negada:**

```
pcap_open_live failed: eth0: You don't have permission to capture on that device
```

Execute com `sudo just run` ou conceda as capabilities: `sudo setcap cap_net_raw,cap_net_admin=eip ./build/release/network-traffic-analyzer`

**Nenhum pacote na interface wireless:**
Muitos drivers de Wi-Fi não passam todos os quadros em modo managed. Tente `lo` (loopback) primeiro para verificar se a ferramenta funciona, depois tente sua interface cabeada.

**clang-tidy não consegue encontrar compile_commands.json:**
Execute `just build` (preset de debug) primeiro — ele gera `build/debug/compile_commands.json` com `CMAKE_EXPORT_COMPILE_COMMANDS=ON`. O comando `just lint` lê de `build/release/compile_commands.json`, então execute um build de release também, se necessário.
