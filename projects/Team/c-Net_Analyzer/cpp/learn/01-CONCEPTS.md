# Conceitos

## Captura de Pacotes no Nível do Kernel

Quando você abre o Wireshark e vê pacotes, muita coisa aconteceu antes do primeiro byte chegar à tela. O kernel do SO recebe cada quadro da placa de rede e, normalmente, entrega apenas os quadros endereçados à sua máquina (ou ao endereço de broadcast da sua sub-rede) aos processos do usuário. Um sniffer de pacotes precisa de tudo — incluindo quadros endereçados a outros hosts.

Isso é o modo promíscuo. Quando a libpcap abre um dispositivo com `pcap_open_live(..., 1, ...)` (o `1` é a flag de promíscuo, `pcapCapture.cpp:59`), ela pede ao kernel para passar todos os quadros, independentemente do endereço MAC de destino. A pilha de rede do kernel vê os quadros antes que a camada de roteamento descarte os irrelevantes.

O kernel copia os quadros correspondentes do espaço do kernel para um buffer circular (ring buffer) no espaço do usuário. Seu programa lê desse buffer via `pcap_loop()`. A cópia é o gargalo — é por isso que ferramentas de captura de alto desempenho (como as usadas em data centers) usam mecanismos de bypass de kernel como DPDK ou XDP para pular a cópia inteiramente.

## BPF — Berkeley Packet Filter

O BPF é uma pequena máquina virtual que roda dentro do kernel. Quando você passa uma expressão de filtro como `tcp and port 443`, a libpcap a compila para bytecode BPF e instala esse programa no kernel. O kernel executa o programa BPF em cada quadro antes de decidir se deve copiá-lo para o espaço do usuário.

A vantagem: em uma rede ocupada, 99% dos quadros são descartados no kernel sem nunca tocar no espaço do usuário. Mover a filtragem do espaço do usuário para o BPF reduziu o uso da CPU de ~80% para ~5% em cenários de monitoramento de rede de produção com filtros específicos de porta.

Neste projeto, `filter.cpp` constrói strings de expressão BPF (`get_bpf_filter()`, linha 27), e `pcapCapture.cpp` as compila e instala via `pcap_compile()` + `pcap_setfilter()` (linhas 68–75).

### Escrevendo Expressões BPF

Sintaxe BPF que o pcap aceita:

```
tcp                        — apenas tráfego TCP
port 443                   — porta de origem ou destino 443
host 192.168.1.1           — para ou de um IP específico
src host 10.0.0.1          — de uma origem específica
dst host 10.0.0.1 and port 80  — combinado com AND
tcp or udp                 — combinado com OR
```

O construtor de filtros do projeto mapeia sua própria sintaxe chave:valor para BPF:

- `protocol:https` → `port 443`
- `ip:v4` → `ip`
- `src:192.168.1.1` → `src host 192.168.1.1`
- Múltiplos filtros do mesmo tipo recebem um OR, tipos diferentes recebem um AND.

## Quadros Ethernet e Tipos de Camada de Link

Cada pacote em uma rede física começa com um cabeçalho de camada de link. No Ethernet (o caso comum), esse é um cabeçalho Ethernet de 14 bytes: 6 bytes de MAC de destino, 6 bytes de MAC de origem, 2 bytes de EtherType.

Mas nem toda interface usa cabeçalhos Ethernet. A pseudo-interface `any` do Linux usa `DLT_LINUX_SLL` (um cabeçalho sintético de 16 bytes). Alguns ambientes usam `DLT_LINUX_SLL2` (cabeçalho de 20 bytes). O offset antes da camada IP difere por tipo de link.

`pcapCapture.cpp:datalink_type()` (linhas 13–39) lida com isso com um switch no tipo de link retornado por `pcap_datalink()`. Ele define tanto o `offset` (quantos bytes pular antes da camada IP) quanto uma lambda `get_ether_type` que extrai o campo EtherType da posição correta.

```
DLT_EN10MB  → offset = 14, EtherType nos bytes 12-13
DLT_LINUX_SLL  → offset = 16, protocolo nos bytes 14-15
DLT_LINUX_SLL2 → offset = 20, protocolo nos bytes 18-19
```

EtherType `0x0800` = IPv4, `0x86DD` = IPv6. A função `got_packet()` (linha 152) lê o EtherType do pacote usando `get_ether_type(packet)` e despacha para `IPv4` ou `IPv6` adequadamente.

## Parsing de Cabeçalho de Protocolo

Após pular o cabeçalho da camada de link, o cabeçalho IP começa em `packet + offset`. O parsing é feito via cast de ponteiro bruto:

```cpp
// IP.cpp:19 — cast de bytes brutos para struct de cabeçalho ip
ip_hdr = reinterpret_cast<const ip *>(data);
```

A struct `ip` de `<netinet/ip.h>` mapeia os campos em offsets de bytes conhecidos — `ip_hl` nos bits 0–3 do byte 0 (o comprimento do cabeçalho IP em palavras de 4 bytes), `ip_src` e `ip_dst` nos bytes 12–15 e 16–19.

O comprimento do cabeçalho IP é `ip_hl * 4`. O mínimo é 20 bytes (sem opções). IPv4.cpp valida isso na linha 25:

```cpp
if (ip_hdr_len < 20) throw std::runtime_error("Failed to initial IPv4 ");
```

O cabeçalho de transporte segue imediatamente o cabeçalho IP:

```cpp
// IP.cpp:53 — avançar além do cabeçalho IP para alcançar o TCP
const auto *tcp = reinterpret_cast<const tcphdr *>(
    reinterpret_cast<const u_char *>(ip_hdr) + ip_hdr_len
);
```

O cabeçalho TCP tem seu próprio comprimento variável: `tcp->doff * 4` bytes (campo Data Offset, mínimo 20 bytes). O payload começa imediatamente depois:

```cpp
// IP.cpp:58 — ponteiro para o payload TCP
payload_ptr = reinterpret_cast<const u_char *>(tcp) + tcp->doff * 4;
payload_len = ntohs(ip_hdr->ip_len) - (ip_hdr_len + tcp->doff * 4);
```

Note o `reinterpret_cast<const u_char *>(tcp)` antes da adição. A aritmética de ponteiros em um ponteiro tipado avança por múltiplos de `sizeof(T)` — sem o cast para ponteiro de byte, `tcp + doff * 4` avançaria por `doff * 4 * sizeof(tcphdr)` bytes, o que seria 20x longe demais.

## Identificação de Protocolo de Aplicação

A detecção de protocolo de aplicação usa duas estratégias, tentadas em ordem (`packet.cpp:4–57`):

**Inspeção de payload (deep packet inspection):** Verifica os primeiros bytes do payload contra valores mágicos conhecidos:

- HTTP: os primeiros 4 bytes são `GET `, `POST`, `HEAD`, `PUT ` ou `HTTP` (linha 9)
- TLS/HTTPS: o primeiro byte é `0x16` (tipo de registro TLS = handshake), o segundo é `0x03` (versão major) (linha 18)

**Fallback baseado em porta:** Quando o payload está ausente ou não é reconhecido, verifica portas bem conhecidas:

- TCP 22 → SSH, 25 → SMTP, 80 → HTTP, 443 → HTTPS
- UDP 53 → DNS, 443 → QUIC, 123 → NTP

A identificação do protocolo acontece no construtor de `Packet` (packet.hpp:52):

```cpp
application_protocol = get_application_protocol();
this->payload_ptr = nullptr;  // nulo após identificação — payload não é mais necessário
```

Definir `payload_ptr = nullptr` após o uso é intencional. O ponteiro aponta para o buffer circular interno da libpcap, que só é válido durante o callback `pcap_loop`. Uma vez que o `Packet` é armazenado no deque `Stats.packets`, o ponteiro estaria pendente (dangling). Anulá-lo torna isso explícito.

## Segurança de Threads e o Padrão Snapshot

Duas threads acessam o objeto `Stats` concorrentemente: a thread de captura (chama `add_packet()`, `push()`) e a thread de atualização da UI (chama todos os métodos `update_*()` e `get_snapshot()`).

Todos os métodos de `Stats` bloqueiam o `mtx` na entrada (`protocolStats.cpp:20`, `94`, `116`, `141`, etc.). As operações de escrita são concluídas sob o lock. As leituras via `get_snapshot()` (protocolStats.hpp:89) retornam uma cópia da struct de snapshot sob o mesmo lock:

```cpp
StatsSnapshot get_snapshot() {
    std::lock_guard<std::mutex> lock(mtx);
    return snapshot;  // cópia na saída
}
```

A lambda de renderização do FTXUI em `main.cpp` (linha 92) lê de `current_render` sob `render_mtx`, não de `Stats` diretamente. A thread de atualização da UI em `application_thread` (linha 107) chama `get_snapshot()`, constrói uma nova árvore de elementos FTXUI, armazena-a em `current_render` sob `render_mtx`, e então posta um evento personalizado para disparar uma repintura:

```cpp
ftxui::Element new_frame = view.render(stats.get_snapshot(), ...);
{
    std::lock_guard<std::mutex> lock(render_mtx);
    current_render = new_frame;
}
screen.PostEvent(ftxui::Event::Custom);
```

Este design significa que a thread do event loop do FTXUI nunca toca em `Stats` diretamente — ela apenas lê o elemento `current_render` pré-construído.

## Cabeçalhos de Extensão IPv6

O IPv6 removeu o campo de opções do cabeçalho fixo e o substituiu por cabeçalhos de extensão — uma cadeia de cabeçalhos opcionais entre o cabeçalho base de 40 bytes e a camada de transporte. Cada cabeçalho de extensão possui um campo `Next Header` apontando para o próximo na cadeia.

O construtor de `IPv6` (`IP.cpp:82–136`) percorre esta cadeia em um loop `while(true)`. Em cada iteração, ele lê o tipo de cabeçalho atual e ou despacha para o manipulador de transporte (TCP/UDP/ICMP/ICMPV6/IGMP) e retorna, ou avança além de um cabeçalho de extensão conhecido (Hop-by-Hop Options, Routing, Destination Options, Fragment) e continua:

```cpp
case IPPROTO_HOPOPTS:
case IPPROTO_ROUTING:
case IPPROTO_DSTOPTS: {
    const auto *ext = reinterpret_cast<const ip6_ext *>(ptr);
    hdr = ext->ip6e_nxt;
    ptr += (ext->ip6e_len + 1) * 8;  // len em unidades de 8 bytes, sem contar os primeiros 8
    break;
}
```

A aritmética `(ext->ip6e_len + 1) * 8` é a fórmula padrão da RFC 2460: o campo de comprimento conta unidades de 8 bytes, excluindo os primeiros 8 bytes.

## Cálculo de Largura de Banda

A largura de banda é computada uma vez por segundo em `update_bandwidth()` (`protocolStats.cpp:230–252`):

```
delta_bytes = total_bytes_agora - total_bytes_ultimo_tick
largura_banda = delta_bytes / segundos_passados  (bytes/seg)
```

A largura de banda bruta é ruidosa (tráfego em rajadas, temporização de tick variável), então uma média móvel exponencial a suaviza:

```cpp
const double alpha = 0.2;
smooth_bandwidth = alpha * snapshot.bandwidth + (1.0 - alpha) * smooth_bandwidth;
```

Um alpha de 0.2 dá às amostras recentes 20% de peso e à média histórica 80% de peso. Um alpha menor = mais suave, mas com mais atraso. O valor suavizado é armazenado em `bandwidth_history` para o gráfico da TUI.

O gráfico da TUI em `view.cpp:138–174` mapeia as últimas 50 amostras de largura de banda na largura do widget de gráfico usando interpolação linear entre as amostras — escalonando cada amostra para um valor de altura baseado na largura de banda máxima atual.
