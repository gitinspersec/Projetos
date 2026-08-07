# Passo a Passo da Implementação

Este documento percorre cada componente principal com referências exatas de arquivos e linhas. Leia o código-fonte junto com este guia.

## Ponto de Entrada — `main.cpp`

### Inicialização (linhas 14–18)

```cpp
Stats stats;
PcapCapture capture;
capture.initialize();
argsParser parser(argc, argv);
```

`Stats` é construído por padrão com todos os mapas vazios e `last_tick` definido como agora. `PcapCapture` inicializa seu `handle` com `nullptr`. `initialize()` chama `pcap_findalldevs()` para popular a lista encadeada `interfaces` para que o `--interfaces` possa imprimi-las.

### Tratamento de Argumentos (linhas 24–47)

```cpp
if (parser.vm.contains("help")) { parser.print_help(); return 0; }
if (parser.vm.contains("interfaces")) { capture.print_interfaces(); return 0; }
```

O `variables_map::contains()` do Boost verifica se a flag foi passada. Saída antecipada antes de qualquer configuração de rede.

```cpp
std::vector<filter> filters;
if (parser.vm.contains("filter")) {
    auto &f = parser.vm["filter"].as<std::vector<std::string>>();
    for (auto &x : f) { filters.push_back(parse(x)); filterString += x + " "; }
}
std::string expression = get_bpf_filter(filters);
```

`--filter` é uma opção de composição — ela pode aparecer múltiplas vezes e o Boost acumula todos os valores em um `vector<string>`. Cada string `chave:valor` é analisada para uma struct `filter`, então `get_bpf_filter()` as combina em uma única expressão BPF.

### Caminho Offline vs Ao Vivo (linhas 51–74)

```cpp
bool isOffline = parser.vm.contains("offline");
capture.set_capabilities(interface, count, expression, limit, &stats);

if (isOffline) {
    capture.start_offline(parser.vm["offline"].as<std::string>());
    stats.update_packets();
    stats.update_application_stats();
    // ...todos os métodos de atualização
}
else {
    capture.start();
}
```

`set_capabilities()` armazena a configuração dentro de `PcapCapture` e chama `stats->set_packets_limit(packets_limit)`. Para o modo offline, `start_offline()` roda de forma síncrona e bloqueia até que todo o arquivo seja processado — sem threading. Todas as estatísticas são então computadas uma vez antes do lançamento da TUI. Para o modo ao vivo, `start()` inicia a thread de captura e retorna imediatamente.

### Configuração do FTXUI (linhas 78–104)

```cpp
auto screen = ftxui::ScreenInteractive::Fullscreen();
View view;
std::mutex render_mtx;
ftxui::Element current_render = isOffline
    ? view.render(stats.get_snapshot(), ...)
    : ftxui::text("Iniciando captura...");

auto component = ftxui::Renderer([&] {
    std::lock_guard<std::mutex> lock(render_mtx);
    return current_render;
});

component |= ftxui::CatchEvent([&](ftxui::Event e) {
    if (e == ftxui::Event::Character('q') || e == ftxui::Event::Escape) {
        ui_running = false;
        screen.Exit();
        return true;
    }
    return true;
});
```

`current_render` mantém o último elemento construído. A lambda `Renderer` é chamada pelo event loop do FTXUI em cada repintura — ela apenas retorna o que estiver em `current_render`, protegida por `render_mtx`. A lambda `CatchEvent` intercepta eventos de teclado. Retornar `true` significa "evento consumido, não propagar".

Nota: `return true` para todos os eventos (não apenas q/Esc) é intencional — evita que o comportamento padrão do FTXUI processe outras teclas.

### Thread de Atualização da UI (linhas 106–137)

```cpp
application_thread = std::thread([&] {
    while (!capture_finished && ui_running) {
        auto now = std::chrono::steady_clock::now();
        timer.store(std::chrono::duration_cast<std::chrono::seconds>(now - begin));

        if (timer.load() >= std::chrono::seconds(time) || !capture.isRunning())
            capture_finished = true;

        stats.update_packets();
        stats.update_application_stats();
        stats.update_transport_stats();
        stats.update_ip_stats(10);
        stats.update_pairs();
        stats.update_bandwidth();

        ftxui::Element new_frame = view.render(stats.get_snapshot(), ...);
        { std::lock_guard<std::mutex> lock(render_mtx); current_render = new_frame; }
        if (ui_running) screen.PostEvent(ftxui::Event::Custom);
    }
});
```

O loop atualiza as estatísticas, constrói uma nova árvore de elementos FTXUI a partir do snapshot, troca em `current_render` (sob lock) e diz ao event loop do FTXUI para repintar. `PostEvent(Custom)` não é bloqueante — ele enfileira o evento e retorna.

Não há `sleep_for` explícito no loop (está comentado na linha 134). O loop roda tão rápido quanto os métodos de atualização terminam, o que é limitado pela contenção do mutex de estatísticas.

---

## PcapCapture — `src/capture/pcapCapture.cpp`

### `start()` (linhas 50–88)

```cpp
handle.reset(pcap_open_live(interface.c_str(), SNAP_LEN, 1, 1000, errbuf));
```

- `SNAP_LEN = 1518` — máximo de bytes para capturar por pacote (MTU Ethernet padrão + cabeçalhos).
- `1` — modo promíscuo ativado.
- `1000` — timeout de leitura em milissegundos (quanto tempo o pcap_loop bloqueia esperando por pacotes).

```cpp
datalink_type(pcap_datalink(handle.get()));
```

Detecta o tipo de link e define `offset` + `get_ether_type` antes que qualquer pacote chegue.

```cpp
if (pcap_compile(handle.get(), &fp, filter_exp.c_str(), 0, net) == -1)
    throw std::runtime_error(...);
if (pcap_setfilter(handle.get(), &fp) == -1)
    throw std::runtime_error(...);
```

A compilação BPF é feita na `struct bpf_program fp` (alocada na pilha). Após a instalação, o kernel executa este programa BPF em cada quadro de entrada.

```cpp
thread = std::thread([this]() {
    if (pcap_loop(handle.get(), num_packets, &PcapCapture::callback, reinterpret_cast<u_char *>(this)) < 0) {}
    running = false;
});
```

`pcap_loop` bloqueia a thread até que `num_packets` sejam capturados (0 = ilimitado) ou `pcap_breakloop()` seja chamado. `this` é passado como o ponteiro `user` — a função estática `callback` o converte de volta para `PcapCapture*` para chamar `got_packet()`.

### `stop()` (linhas 90–108)

```cpp
pcap_freecode(&fp);          // libera a memória do programa BPF
if (!handle) return;
running = false;
pcap_breakloop(handle.get()); // sinaliza para o pcap_loop sair no próximo pacote
if (thread.joinable()) thread.join(); // espera a thread de captura terminar
handle.reset();               // chama pcap_close via deleter do unique_ptr
if (interfaces) { pcap_freealldevs(interfaces); interfaces = nullptr; }
```

Chamado a partir do destrutor. A ordem importa: interromper o loop primeiro, depois dar o join, depois fechar o handle.

### `got_packet()` (linhas 152–179)

```cpp
uint16_t ether_type = get_ether_type(packet);

if (ether_type == ETHERTYPE_IP) {
    IPv4 ip(packet + offset);
    TransportProtocol prot = ip.get_protocol();
    Packet packetView(v4, prot, ip.get_source(), ip.get_dest(),
                      ip.get_src_port(), ip.get_dest_port(),
                      header->len, ip.get_payload_len(), ip.get_payload_ptr());
    stats->add_packet(packetView);
    stats->push(packetView);
}
```

`packet + offset` pula o cabeçalho da camada de link (14, 16 ou 20 bytes dependendo do tipo DLT). `IPv4 ip(packet + offset)` analisa todos os cabeçalhos no construtor. A construção de `Packet` chama `get_application_protocol()` e anula o `payload_ptr`. Então, tanto `add_packet()` (atualiza todos os mapas) quanto `push()` (insere no deque de pacotes recentes) são chamados — ambos obtêm o mutex de estatísticas internamente.

---

## Parsing de IP — `src/packet/IP.cpp`

### Construtor IPv4 (linhas 18–50)

```cpp
ip_hdr = reinterpret_cast<const ip *>(data);
src = inet_ntoa(ip_hdr->ip_src);    // converte in_addr para string "a.b.c.d"
dst = inet_ntoa(ip_hdr->ip_dst);
ip_hdr_len = ip_hdr->ip_hl * 4;    // ip_hl é um campo de 4 bits: comprimento do cabeçalho em palavras de 32 bits
if (ip_hdr_len < 20) throw std::runtime_error("Falha ao inicializar IPv4 ");
```

`ip_hl * 4`: o campo Internet Header Length tem 4 bits, medido em palavras de 32 bits. O valor mínimo é 5 (= 20 bytes, sem opções). Converte para bytes multiplicando por 4.

```cpp
switch (ip_hdr->ip_p) {
case IPPROTO_TCP:  IPv4::handle_tcp();  break;
case IPPROTO_UDP:  IPv4::handle_udp();  break;
case IPPROTO_ICMP: IPv4::handle_icmp(); break;
// ...
}
```

`ip_p` é o campo Protocol (byte 9 do cabeçalho IP). A IANA atribui estes: 6 = TCP, 17 = UDP, 1 = ICMP.

### Manipulador TCP IPv4 (linhas 52–62)

```cpp
const auto *tcp = reinterpret_cast<const tcphdr *>(
    reinterpret_cast<const u_char *>(ip_hdr) + ip_hdr_len
);
src_port = ntohs(tcp->source);
dest_port = ntohs(tcp->dest);
payload_ptr = reinterpret_cast<const u_char *>(tcp) + tcp->doff * 4;
payload_len = ntohs(ip_hdr->ip_len) - (ip_hdr_len + tcp->doff * 4);
```

`ip_hdr` aponta para o cabeçalho IP. Adicionar `ip_hdr_len` bytes (convertido para `u_char*` primeiro para aritmética de bytes) chega ao cabeçalho TCP. `tcp->doff` é o TCP Data Offset: número de palavras de 32 bits no cabeçalho TCP. `tcp->doff * 4` fornece os bytes. O payload começa após o cabeçalho TCP.

`ntohs()` converte da ordem de bytes da rede (big-endian) para a ordem de bytes do host. Todos os campos de múltiplos bytes em protocolos de rede são big-endian.

### Percorrendo Cabeçalhos de Extensão IPv6 (linhas 82–136)

```cpp
ptr = reinterpret_cast<const uint8_t *>(ip_hdr + 1); // após o cabeçalho fixo de 40 bytes
while (true) {
    switch (hdr) {
    case IPPROTO_TCP: IPv6::handle_tcp(); return;
    // ...
    case IPPROTO_HOPOPTS:
    case IPPROTO_ROUTING:
    case IPPROTO_DSTOPTS: {
        const auto *ext = reinterpret_cast<const ip6_ext *>(ptr);
        hdr = ext->ip6e_nxt;
        ptr += (ext->ip6e_len + 1) * 8;
        break;
    }
    case IPPROTO_FRAGMENT: {
        const auto *frag = reinterpret_cast<const ip6_frag *>(ptr);
        hdr = frag->ip6f_nxt;
        ptr += sizeof(ip6_frag);
        break;
    }
    default: protocol = TransportProtocol::UNKNOWN; return;
    }
}
```

`ip_hdr + 1` — a aritmética de ponteiros em `ip6_hdr*` avança `sizeof(ip6_hdr) = 40` bytes, chegando exatamente no primeiro cabeçalho de extensão ou cabeçalho de transporte.

`(ext->ip6e_len + 1) * 8` — fórmula da RFC 2460. `ip6e_len` é o comprimento em unidades de 8 bytes, sem contar os primeiros 8 bytes. Portanto, total de bytes = `(len + 1) * 8`.

---

## Detecção de Protocolo de Aplicação — `src/packet/packet.cpp`

### Identificação em Duas Fases (linhas 4–57)

```cpp
ApplicationProtocol Packet::get_application_protocol() {
    if (!payload_ptr || payload_len < 4) goto check_port;

    if (transport_protocol == TransportProtocol::TCP) {
        if (!memcmp(payload_ptr, "GET ", 4) || !memcmp(payload_ptr, "POST", 4) || ...)
            return ApplicationProtocol::HTTP;
    }
    if ((src_port == 53 || dst_port == 53) && payload_len >= 12)
        return ApplicationProtocol::DNS;
    if (transport_protocol == TransportProtocol::TCP && payload_len >= 3) {
        if (payload_ptr[0] == 0x16 && payload_ptr[1] == 0x03)
            return ApplicationProtocol::HTTPS;
    }

check_port:
    uint16_t port = (src_port < dst_port) ? src_port : dst_port;
    // switch na porta ...
}
```

Fase 1 — inspeção de payload. `memcmp(payload_ptr, "GET ", 4)` compara os primeiros 4 bytes do payload com a string literal. Requisições HTTP/1.x sempre começam com um verbo. Registros TLS começam com `0x16 0x03` (Content-Type=Handshake, Version=3.x).

Fase 2 — fallback por porta via `goto check_port`. Usando `goto` para pular a Fase 1 quando o payload é nulo ou muito curto. `port = min(src_port, dst_port)` — para conexões cliente→servidor, a porta do servidor é tipicamente a bem conhecida e será numericamente menor.

---

## Engine de Estatísticas — `src/stats/protocolStats.cpp`

### `add_packet()` (linhas 19–42)

```cpp
void Stats::add_packet(const Packet &packet) {
    std::lock_guard<std::mutex> lock(mtx);

    ++snapshot.total_p;
    snapshot.total_b += packet.total_len;

    auto &t = transport_map[packet.transport_protocol];
    t.packets++;
    t.bytes += packet.total_len;

    auto &a = application_map[packet.application_protocol];
    a.packets++;
    a.bytes += packet.payload_len;

    ip_map[packet.src].packets_sent++;
    ip_map[packet.src].bytes_sent += packet.total_len;
    ip_map[packet.dst].packets_received++;
    ip_map[packet.dst].bytes_received += packet.total_len;

    auto key = std::make_pair(packet.src, packet.dst);
    pairs[key].packets++;
    pairs[key].bytes += packet.total_len;
}
```

O `unordered_map::operator[]` constrói o valor por padrão se a chave não existir. `protocolStats` tem todos os membros inicializados com zero por padrão, então o primeiro pacote para qualquer protocolo insere uma struct zerada e depois incrementa. O mesmo padrão é usado para `IPStats` e para o mapa `pairs`.

Nota: `total_p` e `total_b` são atualizados diretamente no `snapshot` (não em uma struct separada) para que fiquem imediatamente visíveis no `get_snapshot()` sem uma chamada extra de `update_*`.

### `update_transport_stats()` (linhas 93–107)

```cpp
std::vector<std::pair<TransportProtocol, protocolStats>> tps(transport_map.begin(), transport_map.end());
std::sort(tps.begin(), tps.end(), [](auto &a, auto &b) { return a.second.packets > b.second.packets; });
```

Não é possível ordenar um `unordered_map` no local — copie para um vetor primeiro e depois ordene. A lambda compara pela contagem de pacotes de forma decrescente. Cada linha é então formatada com `std::format("{:.2f}", ...)` para valores de MB e porcentagem.

### `update_bandwidth()` (linhas 230–252)

```cpp
auto now = steady_clock::now();
double elapsed = duration_cast<duration<double>>(now - last_tick).count();

if (elapsed >= 1.0) {
    uint32_t delta_bytes = snapshot.total_b - last_b;
    snapshot.bandwidth = delta_bytes / elapsed;
    last_b = snapshot.total_b;
    last_tick = now;

    const double alpha = 0.2;
    smooth_bandwidth = alpha * snapshot.bandwidth + (1.0 - alpha) * smooth_bandwidth;
    snapshot.bandwidth_history.push_back({ts, smooth_bandwidth});
}
snapshot.max_bandwidth = std::max(snapshot.max_bandwidth, snapshot.bandwidth);
```

Amostra apenas uma vez por segundo (quando `elapsed >= 1.0`). `delta_bytes = total_atual - total_ultimo_snapshot`. Dividido pelos segundos decorridos = bytes/seg. O EMA com alpha=0.2 suaviza os picos. O `max_bandwidth` é atualizado em cada chamada (não apenas quando um segundo se passou) para rastrear o pico real.

---

## Construtor de Filtros — `src/cli/filter.cpp`

### `parse()` (linhas 5–25)

```cpp
filter parse(const std::string &str) {
    auto pos = str.find(':');
    if (pos == std::string::npos)
        throw std::invalid_argument("Formato de filtro inválido: '" + str + "' (esperado chave:valor)");
    std::string type = str.substr(0, pos);
    std::string value = str.substr(pos + 1);
    if (type == "protocol") return {PROTOCOL, value};
    if (type == "port")     return {PORT, value};
    if (type == "dest")     return {IP_DEST, value};
    if (type == "src")      return {IP_SRC, value};
    if (type == "ip")       return {IP_TYPE, value};
    return {NONE, value};
}
```

`find(':')` retorna `string::npos` (valor máximo de `size_t`) se não for encontrado. O throw evita o bug de overflow de `npos + 1` que faria o `substr(npos + 1)` retornar a string inteira como valor.

### `get_bpf_filter()` (linhas 27–97)

```cpp
std::map<filter_type, std::vector<std::string>> groups;
for (const auto &x : f) {
    switch (x.type) {
    case PROTOCOL:
        if (x.val == "dns") groups[PROTOCOL].emplace_back("port 53");
        else if (x.val == "http") groups[PROTOCOL].emplace_back("port 80");
        // ...
        break;
    case IP_TYPE:
        if (x.val == "v4" || x.val == "4" || x.val == "ipv4") groups[IP_TYPE].emplace_back("ip");
        else if (x.val == "v6" || ...) groups[IP_TYPE].emplace_back("ip6");
        else throw std::invalid_argument("Tipo de IP desconhecido: '" + x.val + "'");
        break;
    }
}
// combinar: mesmo tipo = OR, tipos diferentes = AND
for (auto &[type, parts] : groups) {
    if (!first_group) result += " and ";
    if (parts.size() > 1) result += "(";
    for (size_t i = 0; i < parts.size(); ++i) {
        result += parts[i];
        if (i + 1 < parts.size()) result += " or ";
    }
    if (parts.size() > 1) result += ")";
}
```

O `std::map` (ordenado) garante uma ordem de saída determinística, independentemente da ordem de inserção. A combinação AND/OR do BPF segue a semântica padrão de filtros de rede: o mesmo tipo de filtro com múltiplos valores significa "corresponder a qualquer um destes" (OR), enquanto tipos de filtro diferentes devem todos corresponder (AND).

Exemplo: `-f protocol:http -f protocol:https -f port:8080` → `(port 80 or port 443 or port 8080)`

---

## Renderização da TUI — `src/TUI/view.cpp`

### Composição do Layout (linhas 5–47)

```cpp
auto transport_section = hbox({
    render_transport(data) | flex,
    separator(),
    render_application(data) | flex,
    separator(),
    render_pairs(data) | flex,
}) | border;

auto ip_section = hbox({
    render_ip(data) | border | size(HEIGHT, LESS_THAN, 10) | frame | vscroll_indicator,
    render_bandwidth(data) | border | flex
});

auto right_panel = render_packets(data) | border | size(WIDTH, EQUAL, 100) | frame | vscroll_indicator;
```

O FTXUI usa um modelo de layout declarativo. `hbox` coloca os elementos lado a lado. `| flex` faz um elemento expandir para preencher o espaço disponível. `| size(HEIGHT, LESS_THAN, 10)` limita a altura. `| frame | vscroll_indicator` adiciona suporte a scroll.

`separator()` desenha uma linha vertical entre os elementos.

### Gráfico de Largura de Banda (linhas 138–175)

```cpp
GraphFunction fn = [this, data](int width, int height) {
    std::vector<int> output(width, 0);
    size_t n = data.bandwidth_history.size();
    size_t start = n > 50 ? n - 50 : 0;  // últimas 50 amostras

    double max_bw = 1.0;
    for (size_t i = start; i < n; ++i)
        max_bw = std::max(max_bw, data.bandwidth_history[i].bytes_per_sec);

    for (int x = 0; x < width; ++x) {
        double t = (double)x / (width - 1);
        double idx_f = start + t * (n - start - 1);
        size_t i0 = (size_t)idx_f;
        size_t i1 = std::min(i0 + 1, n - 1);
        double frac = idx_f - i0;
        double bw = data.bandwidth_history[i0].bytes_per_sec * (1.0 - frac)
                  + data.bandwidth_history[i1].bytes_per_sec * frac;
        output[x] = static_cast<int>(bw / max_bw * (height - 1));
    }
    return output;
};
```

A `GraphFunction` mapeia as colunas da tela `width` para alturas inteiras limitadas por `height`. Para cada coluna de pixel `x`, ela computa um índice fracionário no array de amostras (mapeando a largura da tela para o intervalo de amostras), interpola linearmente entre amostras adjacentes e então normaliza para a altura do gráfico. `max_bw = 1.0` como base evita a divisão por zero quando nenhum tráfego foi visto ainda.

### Renderização de Tabela (linhas 83–93, padrão repetido para todas as tabelas)

```cpp
Table table(data.transport_rows);
table.SelectAll().Border(LIGHT);
table.SelectRow(0).Decorate(bold);
table.SelectRow(0).SeparatorVertical(LIGHT);
table.SelectRow(0).Border(DOUBLE);
return vbox({text("=== Transport protocols === ") | bold, table.Render()}) | flex;
```

`data.transport_rows` é um `vector<vector<string>>` onde a linha 0 é o cabeçalho. `SelectAll().Border(LIGHT)` desenha bordas leves ao redor de todas as células. `SelectRow(0).Border(DOUBLE)` sobrepõe a linha de cabeçalho com uma borda dupla para distingui-la visualmente. `SelectRow(0).Decorate(bold)` torna o texto do cabeçalho negrito.
