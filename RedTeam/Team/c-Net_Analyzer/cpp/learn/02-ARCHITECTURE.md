# Arquitetura do Sistema

## Visão Geral de Alto Nível

```
┌─────────────────────────────────────────────────────────────┐
│                     main.cpp                                │
│  • parsing de args    • coordenação de threads              │
│  • offline vs live    • exportação CSV/JSON ao sair         │
└───────────┬─────────────────────────────┬───────────────────┘
            │                             │
     ┌──────▼──────┐             ┌────────▼────────┐
     │ PcapCapture │             │   tela FTXUI    │
     │ (libpcap)   │             │ (thread principal)│
     └──────┬──────┘             └────────▲────────┘
            │ got_packet()                │ PostEvent()
            │                    ┌────────┴────────┐
     ┌──────▼──────┐             │ application_    │
     │  IPv4/IPv6  │             │ thread          │
     │ (analisador)│             │ (loop de UI)    │
     └──────┬──────┘             └────────▲────────┘
            │ Packet                      │ get_snapshot()
     ┌──────▼──────────────────────────┐  │
     │           Stats                 │──┘
     │  add_packet()  push()           │
     │  transport_map  application_map │
     │  ip_map  pairs  deque de pacotes│
     │  bandwidth_history              │
     │  StatsSnapshot (sob mutex)      │
     └─────────────────────────────────┘
```

## Modelo de Threading

Existem três contextos de execução concorrentes:

**Thread de captura** — iniciada por `PcapCapture::start()` em `pcapCapture.cpp:80`. Executa `pcap_loop()`, que chama `callback()` → `got_packet()` para cada pacote. Chama `Stats::add_packet()` e `Stats::push()`. Nunca toca na UI.

**Thread de atualização da UI** (`application_thread`, `main.cpp:107`) — executa um loop que:

1. Avança o temporizador de tempo decorrido.
2. Verifica as condições de parada (limite de tempo, captura finalizada).
3. Chama todos os métodos `Stats::update_*()` para reconstruir as tabelas de snapshot.
4. Chama `view.render(stats.get_snapshot(), ...)` para construir uma nova árvore de elementos FTXUI.
5. Armazena o elemento em `current_render` sob o `render_mtx`.
6. Posta um evento `Custom` para a tela FTXUI para disparar uma repintura.

**Event loop do FTXUI** — roda na thread principal via `screen.Loop(component)` em `main.cpp:139`. A lambda `Renderer` (`main.cpp:92`) lê `current_render` sob o `render_mtx` e o retorna. A lambda `CatchEvent` trata as teclas `q` e `Escape` para definir `ui_running = false` e chamar `screen.Exit()`.

### Pontos de Sincronização

| Recurso compartilhado            | Protetor                            | Padrão de acesso                                                |
| -------------------------------- | ----------------------------------- | --------------------------------------------------------------- |
| Mapas internos de `Stats`        | `Stats::mtx`                        | Thread de captura escreve; thread de UI lê via métodos update_* |
| `StatsSnapshot` dentro de Stats  | `Stats::mtx`                        | Ambas as threads; o snapshot é atualizado no local sob lock     |
| `current_render`                 | `render_mtx`                        | Thread de UI escreve; renderizador FTXUI lê                     |
| `capture_finished`, `ui_running` | `std::atomic<bool>`                 | Múltiplas threads leem/escrevem                                 |
| `timer`                          | `std::atomic<std::chrono::seconds>` | Thread de UI escreve; lambda de renderização lê                 |

## Componentes

### PcapCapture (`include/capture/pcapCapture.hpp`, `src/capture/pcapCapture.cpp`)

Envolve todo o ciclo de vida da libpcap. Detém o handle pcap como um `unique_ptr<pcap_t, decltype(&pcap_close)>` para que seja liberado na destruição, independentemente de como o objeto saia.

Responsabilidades principais:

- `initialize()` — descobre todas as interfaces de rede via `pcap_findalldevs()`.
- `datalink_type()` — detecta o tipo de cabeçalho da camada de link e define o offset de bytes + extrator de EtherType.
- `start()` — abre o dispositivo em modo promíscuo, compila e instala o filtro BPF, inicia a thread de captura.
- `start_offline()` — abre o arquivo pcap, processa de forma síncrona (sem thread extra).
- `got_packet()` — analisa cada quadro bruto: extrai EtherType, constrói `IPv4` ou `IPv6`, cria o `Packet`, encaminha para `Stats`.
- `~PcapCapture()` — chama `stop()`: interrompe o loop pcap, junta a thread, libera o programa de filtro e a lista de interfaces.

O callback `pcap_loop` de estilo C requer uma função estática. `callback()` (linha 132) usa o ponteiro `user` (que contém `this` convertido para `u_char*`) para encaminhar para o método de instância `got_packet()`.

### IP_class / IPv4 / IPv6 (`include/packet/IP.hpp`, `src/packet/IP.cpp`)

Analisador polimórfico de cabeçalho IP. `IP_class` é uma base abstrata que declara manipuladores de transporte virtuais puros (`handle_tcp()`, `handle_udp()`, etc.). Tanto `IPv4` quanto `IPv6` herdam dela.

O parsing é baseado no construtor: tanto `IPv4(const u_char *data)` quanto `IPv6(const u_char *data)` aceitam um ponteiro para o cabeçalho IP (já com o offset após o cabeçalho da camada de link) e completam todo o parsing no construtor. Após a construção, o objeto expõe apenas acessores puros: `get_source()`, `get_dest()`, `get_src_port()`, `get_dest_port()`, `get_protocol()`, `get_payload_len()`, `get_payload_ptr()`.

Despacho de transporte IPv4: `switch(ip_hdr->ip_p)` na linha 28, despachando para `handle_tcp/udp/icmp/icmpv6/igmp`.

Despacho de transporte IPv6: um loop `while(true)` na linha 94 que ou trata um protocolo de transporte (e retorna) ou avança além de um cabeçalho de extensão conhecido e continua.

### Packet (`include/packet/packet.hpp`, `src/packet/packet.cpp`)

Um tipo de valor que contém tudo extraído de um único quadro:

- `ip_version` — `v4` ou `v6` (enum `IPVersion`).
- `transport_protocol` — TCP/UDP/ICMP/ICMP6/IGMP/UNKNOWN (enum class `TransportProtocol`).
- `application_protocol` — HTTP/HTTPS/DNS/SSH/etc (enum class `ApplicationProtocol`).
- `src`, `dst` — endereços IP como strings.
- `src_port`, `dst_port` — números de porta.
- `total_len` — comprimento total do quadro do cabeçalho pcap.
- `payload_len` — comprimento do payload de transporte.
- `payload_ptr` — ponteiro para o buffer do pcap, anulado após a execução de `get_application_protocol()`.

O construtor computa o `application_protocol` via `get_application_protocol()` (packet.cpp:4) e imediatamente anula o `payload_ptr`. Isso evita que os chamadores desreferenciem um ponteiro que só é válido durante o callback.

`get_application_protocol()` usa a inspeção de payload primeiro (verbos HTTP, bytes de cabeçalho de registro TLS), depois recorre à identificação baseada em porta.

### Stats (`include/stats/protocolStats.hpp`, `src/stats/protocolStats.cpp`)

Engine de estatísticas thread-safe. Estado interno:

- `transport_map` — `unordered_map<TransportProtocol, protocolStats>`.
- `application_map` — `unordered_map<ApplicationProtocol, protocolStats>`.
- `ip_map` — `unordered_map<string, IPStats>` (contadores bidirecionais por IP).
- `pairs` — `map<pair<string,string>, protocolStats>` (por par origem→destino).
- `packets` — `deque<Packet>` (anel limitado de pacotes recentes).
- `snapshot` — `StatsSnapshot` (linhas de exibição pré-construídas, atualizadas pelos métodos `update_*`).
- `bandwidth_history` — `vector<BandwidthPoint>` (série temporal).

`add_packet()` (linha 19) obtém um lock e atualiza todos os mapas brutos em uma única seção crítica. Os métodos `update_*()` obtêm o lock, ordenam/formatam os dados e reconstroem os vetores `snapshot.*_rows` correspondentes. `get_snapshot()` retorna uma cópia do snapshot sob o lock.

### View (`include/TUI/view.hpp`, `src/TUI/view.cpp`)

Compositor de layout FTXUI sem estado (stateless). `render()` (view.cpp:5) constrói o layout completo do terminal a partir de um `StatsSnapshot`:

```
┌─────── cabeçalho ───────────────────────────────────┐
│ título | interface | filtro │ resumo de tráfego     │
├─────────────────────────────────────────────────────┤
│ tabela transp │ tabela app  │ tabela de pares       │  ← hbox, com borda
├─────────────────────────────────────────────────────┤
│ tabela IP (rolável)    │ gráfico de largura banda   │  ← hbox
├─────────────────────────────────────────────────────┤
│ tabela pacotes (painel direito, rolável, larg=100)  │
├─────────────────────────────────────────────────────┤
│ rodapé: timer + dica de saída                       │
└─────────────────────────────────────────────────────┘
```

`render_bandwidth()` (linha 138) define uma `GraphFunction` — uma lambda que recebe as dimensões em pixels do widget de gráfico e retorna um `vector<int>` mapeando cada pixel-x a uma altura-y. Ela interpola entre as últimas 50 amostras de largura de banda e escala pelo `max_bandwidth`.

Todas as seções de tabela usam `ftxui::Table` com estilização de linha de cabeçalho (borda `DOUBLE` na linha 0, `LIGHT` nas demais).

### Filter (`include/cli/filter.hpp`, `src/cli/filter.cpp`)

Módulo de duas funções:

`parse(str)` (filter.cpp:5) — divide uma string `chave:valor` no primeiro `:`. Mapeia nomes de chaves conhecidos (`protocol`, `port`, `src`, `dst`, `ip`) para o enum `filter_type`. Lança `std::invalid_argument` se nenhum `:` estiver presente.

`get_bpf_filter(filters)` (filter.cpp:27) — agrupa múltiplos filtros por tipo em um `map<filter_type, vector<string>>`. Mapeia valores voltados para o usuário para a sintaxe BPF (ex: `protocol:dns` → `port 53`, `ip:v4` → `ip`). Combina filtros do mesmo tipo com `or`, tipos diferentes com `and`. Retorna a string de expressão BPF resultante.

### argsParser (`include/cli/argsParse.hpp`, `src/cli/argsParse.cpp`)

Wrapper fino em torno do `Boost.Program_options`. Define todas as opções de CLI no construtor e armazena os resultados analisados em um `po::variables_map vm` público. Opções:

| Flag                | Padrão          | Descrição                                     |
| ------------------- | --------------- | --------------------------------------------- |
| `-i`, `--interface` | `wlan0`         | Interface de rede                             |
| `-c`, `--count`     | `0` (ilimitado) | Limite de contagem de pacotes                 |
| `--time`, `-t`      | `INT_MAX`       | Duração da captura (segundos)                 |
| `-r`, `--offline`   | —               | Ler de arquivo pcap                           |
| `-f`, `--filter`    | —               | Expressões de filtro (componíveis, múltiplas) |
| `-n`, `--limit`     | `43`            | Máximo de entradas exibidas                   |
| `--csv` / `--json`  | —               | Caminhos de exportação                        |

## Fluxo de Dados

### Captura ao Vivo

```
Usuário: just run -i eth0 -f protocol:tcp
  ↓
main.cpp:33-47   Analisa args, constrói vetor de filtros
main.cpp:49      get_bpf_filter() → string BPF "tcp"
main.cpp:54      capture.set_capabilities(interface, count, "tcp", limit, &stats)
main.cpp:73      capture.start()
  ↓
pcapCapture.cpp:52-64  pcap_lookupnet → pcap_open_live (promíscuo, SNAP_LEN=1518)
pcapCapture.cpp:64     datalink_type() → define offset + lambda get_ether_type
pcapCapture.cpp:68-75  pcap_compile + pcap_setfilter (BPF "tcp" instalado no kernel)
pcapCapture.cpp:80-87  inicia thread → pcap_loop(callback)
  ↓
[Thread de captura: por pacote]
pcapCapture.cpp:132-136  callback() → got_packet()
pcapCapture.cpp:158      get_ether_type(packet) → ETHERTYPE_IP ou ETHERTYPE_IPV6
pcapCapture.cpp:162      IPv4 ip(packet + offset) — construtor analisa cabeçalhos
  IP.cpp:18-50              extrai src/dst, avança para manipulador TCP/UDP
  IP.cpp:52-61              handle_tcp: portas, payload_ptr, payload_len
pcapCapture.cpp:165-168  Packet packetView(...) — construtor executa get_application_protocol()
  packet.cpp:4-57            memcmp bytes do payload, fallback baseado em porta
                             payload_ptr = nullptr
pcapCapture.cpp:167      stats->add_packet(packetView) — lock, atualiza todos os mapas
pcapCapture.cpp:168      stats->push(packetView)       — lock, insere no deque
  ↓
[Thread de atualização da UI: a cada iteração do loop]
main.cpp:117-121  update_transport_stats(), update_application_stats(),
                  update_ip_stats(10), update_pairs(), update_bandwidth()
main.cpp:124-126  view.render(stats.get_snapshot(), ...) → Element
main.cpp:127-130  armazena em current_render sob render_mtx, PostEvent para FTXUI
  ↓
[Thread principal FTXUI: no evento Custom]
main.cpp:92-95  Lambda Renderer lê current_render sob render_mtx → exibição
```

### Análise Offline

```
main.cpp:61-70   capture.start_offline(pcap_file) — executa de forma síncrona
  pcapCapture.cpp:199-211  pcap_open_offline → pcap_loop (sem thread)
  [mesmo fluxo por pacote acima]
main.cpp:64-69   stats.update_packets() + update_application_stats() + ...
  ↓
main.cpp:86-88   view.render(stats.get_snapshot(), ...) → current_render inicial
screen.Loop()    FTXUI exibe resultado estático (nenhuma thread de atualização de UI iniciada)
```

## Decisões de Design

### Decisão: Parsing Baseado em Construtor vs Getters Preguiçosos

O design original da `IP_class` tinha o `get_protocol()` como ponto de entrada para todo o parsing — um getter com efeitos colaterais. Isso cria dependências de ordem ocultas: chamar `get_src_port()` antes de `get_protocol()` retorna 0 no IPv4 ou lixo no IPv6.

O código mesclado (visível nos construtores atuais de `IPv4`/`IPv6`) analisa tudo no momento da construção. Os getters retornam valores já computados. Sem requisitos de ordenação para os chamadores.

### Decisão: StatsSnapshot como Tipo de Valor

`StatsSnapshot` contém os dados de exibição pré-formatados como linhas `vector<vector<string>>`. A thread de UI chama `get_snapshot()`, que copia esta struct sob o mutex. O renderizador FTXUI então trabalha a partir de sua própria cópia, sem necessidade de manter nenhum lock.

A alternativa — fazer o renderizador bloquear o `Stats` diretamente — significaria que o mutex de renderização e o mutex de estatísticas interagiriam, arriscando deadlock ou bloqueando a thread de captura em tarefas de UI.

### Decision: Handle RAII para pcap_t

`pcap_t*` é um recurso C com `pcap_close()` como seu destrutor. Armazená-lo como `unique_ptr<pcap_t, decltype(&pcap_close)>` significa que ele é liberado automaticamente quando o `PcapCapture` é destruído, mesmo se ocorrerem exceções. `handle.reset()` em `stop()` o libera explicitamente de forma antecipada quando a captura termina.

### Decisão: Offset + Lambda para Tipos de Link

Em vez de cadeias de `if` espalhadas pelo `got_packet()`, o método `datalink_type()` define tanto o inteiro `offset` quanto o objeto de função `get_ether_type` uma única vez quando o dispositivo abre. O `got_packet()` permanece limpo: `uint16_t ether_type = get_ether_type(packet)`.

Isso torna a adição de um novo tipo de link uma simples adição de um `case` em `datalink_type()`, em vez de uma alteração no caminho crítico.
