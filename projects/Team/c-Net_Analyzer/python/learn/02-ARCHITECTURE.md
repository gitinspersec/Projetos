# Arquitetura do Sistema

Este documento detalha como o sistema foi projetado e por que certas decisões arquiteturais foram tomadas.

## Arquitetura de Alto Nível

```
┌──────────────────────────────────────────────────────────┐
│                   Interface CLI (Typer)                  │
│                      main.py                             │
└────────────────────┬─────────────────────────────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
    ┌────────┐  ┌────────┐  ┌──────────┐
    │Capture │  │Analyze │  │Visualize │
    │ Engine │  │ PCAP   │  │ Gráficos │
    └───┬────┘  └───┬────┘  └────┬─────┘
        │           │             │
        │     ┌─────┴──────┐      │
        │     │            │      │
        ▼     ▼            ▼      ▼
    ┌─────────────────────────────────┐
    │    Fila Produtor-Consumidor     │
    │                                 │
    │  ┌──────────┐   ┌─────────────┐│
    │  │ Produtor │──>│    Fila     ││
    │  │ (Scapy)  │   │  (limitada) ││
    │  └──────────┘   └──────┬──────┘│
    │                        │       │
    │                        ▼       │
    │                  ┌───────────┐ │
    │                  │ Consumidor│ │
    │                  │ (Processo)│ │
    │                  └─────┬─────┘ │
    └────────────────────────┼───────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Coletor de    │
                    │   Estatísticas  │
                    │  (Thread-Safe)  │
                    └────────┬────────┘
                             │
         ┌───────────────────┼────────────────┐
         │                   │                │
         ▼                   ▼                ▼
    ┌────────┐         ┌─────────┐      ┌────────┐
    │ Saída  │         │ Export  │      │Gráficos│
    │ Console│         │JSON/CSV │      │  PNG   │
    └────────┘         └─────────┘      └────────┘
```

### Divisão dos Componentes

**Interface CLI (main.py)**

- Propósito: Fornece comandos voltados para o usuário (capture, analyze, export, chart).
- Responsabilidades: Parsing de argumentos, roteamento de comandos, exibição de erros.
- Interfaces: Chama CaptureEngine, analyze_pcap_file e funções de visualização.

**Engine de Captura (capture.py)**

- Propósito: Captura de pacotes em tempo real com threading produtor-consumidor.
- Responsabilidades: Gerenciamento de raw sockets, verificação de privilégios, desligamento gracioso.
- Interfaces: AsyncSniffer do Scapy, Queue para threading, StatisticsCollector para métricas.

**Analisador (analyzer.py)**

- Propósito: Identificação de protocolos e extração de campos de pacotes.
- Responsabilidades: Dissecação de camadas, classificação de protocolos, conversão de estruturas de dados.
- Interfaces: Aceita objetos Packet do Scapy, retorna dataclasses PacketInfo.

**Coletor de Estatísticas (statistics.py)**

- Propósito: Agregação thread-safe de métricas de pacotes.
- Responsabilidades: Gerenciamento de contadores, amostragem de largura de banda, rastreamento de endpoints.
- Interfaces: record_packet() chamado pela thread consumidora, get_statistics() para snapshots.

**Construtor de Filtros (filters.py)**

- Propósito: Construção de expressões de filtro BPF type-safe.
- Responsabilidades: Validação de entrada, combinação de expressões, geração de sintaxe BPF.
- Interfaces: API fluente para encadeamento de filtros, build() produz string BPF.

**Visualização (visualization.py)**

- Propósito: Gerar gráficos a partir das estatísticas de captura.
- Responsabilidades: Criação de figuras Matplotlib, estilização de gráficos, exportação de arquivos.
- Interfaces: Aceita CaptureStatistics, produz objetos Figure.

**Exportação (export.py)**

- Propósito: Serializar dados de captura para formatos de disco.
- Responsabilidades: Formatação JSON/CSV, conversão de estruturas de dados.
- Interfaces: Recebe listas de CaptureStatistics e PacketInfo, escreve arquivos.

**Saída (output.py)**

- Propósito: Formatação Rich console para exibição no terminal.
- Responsabilidades: Geração de tabelas, barras de progresso, saída colorida.
- Interfaces: Singleton Console, funções print_* para diferentes tipos de dados.

## Fluxo de Dados

### Fluxo de Captura de Pacotes em Tempo Real

Passo a passo do que acontece durante a captura ao vivo:

```
1. Usuário executa comando → main.py:capture() (linha 110)
   Analisa argumentos (interface, filtro, contagem, timeout)
   Cria dataclass CaptureConfig

2. Config → CaptureEngine.__init__() (linha 46)
   Inicializa Queue(maxsize=10000)
   Cria StatisticsCollector
   Configura threading.Event para coordenação de desligamento

3. CaptureEngine.start() → AsyncSniffer.start() (linha 112)
   Scapy inicia a thread produtora
   Chama o callback _enqueue_packet para cada pacote
   Produtor: pacote → Queue.put_nowait()

4. Thread consumidora _process_packets() roda em paralelo (linha 72)
   Loop: Queue.get() → extract_packet_info() → record_packet()
   Pacote → analyzer.py:extract_packet_info() (linha 51)
   PacketInfo → statistics.py:record_packet() (linha 47)

5. Atualização de estatísticas (thread-safe com lock) (linhas 48-67)
   Incrementa contadores (total_packets, total_bytes)
   Atualiza dicionário protocol_distribution
   Atualiza estatísticas de endpoint
   Verifica se o intervalo de amostragem de largura de banda expirou

6. Usuário pressiona Ctrl+C → GracefulCapture trata o sinal
   Define stop_event → thread consumidora sai
   Chama sniffer.stop() → thread produtora sai
   Retorna snapshot final de CaptureStatistics

7. Estatísticas → funções output.py:print_*() (linhas 84-170)
   Formata tabelas Rich para protocolos, principais emissores
   Exibe gráficos de largura de banda
   Mostra painel de resumo da captura
```

Exemplo com referências de código:

```python
# Ponto de entrada: main.py:159
def capture(interface, filter_expr, count, timeout, output, verbose):
    config = CaptureConfig(
        interface = interface,
        bpf_filter = filter_expr,
        packet_count = count,
        timeout_seconds = timeout,
    )

    # Configuração produtor-consumidor: capture.py:112-131
    engine = CaptureEngine(config=config)
    engine.start()  # Inicia as threads

    # Loop de processamento: capture.py:72-90
    while not self._stop_event.is_set():
        packet = self._queue.get()
        info = extract_packet_info(packet)  # analyzer.py:51
        self._stats.record_packet(info)     # statistics.py:47
```

### Fluxo de Análise de Arquivo PCAP

```
1. Usuário: netanal analyze trafego.pcap
   ↓
2. main.py:analyze() (linha 237)
   Valida se o arquivo existe
   ↓
3. analyzer.py:analyze_pcap_file() (linha 162)
   Abre PcapReader (iteração eficiente em memória)
   ↓
4. Para cada pacote no arquivo:
   extract_packet_info() → PacketInfo
   StatisticsCollector.record_packet()
   ↓
5. Retorna CaptureStatistics
   ↓
6. output.py formata e exibe
   Tabela de protocolos, principais emissores, resumo
```

## Padrões de Projeto

### Padrão Produtor-Consumidor

**O que é:**
Separa a geração de dados do processamento de dados usando um buffer de fila. Threads produtoras adicionam itens à fila, threads consumidoras removem e processam os itens. Desacopla a taxa de produção da taxa de consumo.

**Onde usamos:**
`capture.py:46-90` implementa o padrão completo. AsyncSniffer é o produtor, o loop _process_packets é o consumidor.

**Por que escolhemos:**
A captura de pacotes deve rodar na velocidade da rede sem perder pacotes. O processamento (identificação de protocolo, atualizações de estatísticas, callbacks opcionais) é mais lento. O buffering em uma fila evita a perda de pacotes quando o processamento atrasa.

**Trade-offs:**

- Prós: Evita perda de pacotes, desacopla preocupações, permite paralelismo.
- Contras: Usa memória para o buffer da fila, adiciona latência (pacotes atrasados na fila), requer sincronização de threads.

Exemplo de implementação:

```python
# capture.py:64-70 - Callback do produtor
def _enqueue_packet(self, packet: Packet) -> None:
    try:
        self._queue.put_nowait(packet)
    except Full:
        with self._count_lock:
            self._dropped_packets += 1

# capture.py:72-90 - Loop do consumidor
def _process_packets(self) -> None:
    while not self._stop_event.is_set():
        try:
            packet = self._queue.get(timeout=0.1)
        except Empty:
            continue

        info = extract_packet_info(packet)
        self._stats.record_packet(info)
```

O produtor nunca bloqueia em um processamento lento. O consumidor processa em seu próprio ritmo. Se a fila encher, os pacotes são descartados com incremento de contador em vez de travar.

### Padrão Builder

**O que é:**
Constrói objetos complexos passo a passo através de uma interface fluente. Cada método retorna `self`, permitindo o encadeamento de métodos. A chamada final build() produz o resultado.

**Onde usamos:**
`filters.py:48-175` implementa o FilterBuilder para expressões BPF.

**Por que escolhemos:**
A sintaxe BPF é propensa a erros. Os usuários podem construir filtros type-safe com validação em cada etapa, em vez de concatenação de strings propensa a erros.

**Trade-offs:**

- Prós: Segurança de tipo, validação de entrada, API legível, evita injeção.
- Contras: Mais código do que strings brutas, requer compreensão do builder.

Exemplo:

```python
# filters.py:48-175
filter_expr = (
    FilterBuilder()
    .protocol(Protocol.TCP)
    .port(443)
    .host("192.168.1.1")
    .build()
)
# Resultado: "(tcp) and port 443 and host 192.168.1.1"

# Valida cada entrada:
# filters.py:30-37
def _validate_port(port_number: int) -> None:
    if not PortRange.MIN <= port_number <= PortRange.MAX:
        raise ValidationError(f"Porta deve ser 0-65535, recebido {port_number}")
```

### Padrão Dataclass com Slots

**O que é:**
Dataclasses Python com `slots=True` reduzem o uso de memória armazenando atributos em slots fixos em vez de um dicionário. Dataclasses frozen são imutáveis.

**Onde usamos:**
Todos os modelos em `models.py:11-159` usam dataclasses com slots.

**Por que escolhemos:**
Capturas de pacotes geram de milhares a milhões de objetos PacketInfo. Slots reduzem a memória por objeto em ~40%. A imutabilidade evita modificações acidentais.

**Trade-offs:**

- Prós: Menor uso de memória, segurança de imutabilidade, esquema claro.
- Contras: Não é possível adicionar atributos dinamicamente, instanciação ligeiramente mais lenta.

Exemplo:

```python
# models.py:22-35
@dataclass(frozen = True, slots = True)
class PacketInfo:
    timestamp: float
    src_ip: str
    dst_ip: str
    protocol: Protocol
    size: int
    src_port: int | None = None
    dst_port: int | None = None
    src_mac: str | None = None
    dst_mac: str | None = None
```

Com 1 milhão de pacotes, os slots economizam ~40MB em comparação com atributos baseados em dicionário.

### Padrão Context Manager

**O que é:**
Objetos que implementam `__enter__` e `__exit__` para configuração e limpeza de recursos. Usados com instruções `with` para garantir a limpeza mesmo em caso de exceções.

**Onde usamos:**
`capture.py:197-230` implementa o gerenciador de contexto GracefulCapture.

**Por que escolhemos:**
Garante o desligamento gracioso mesmo se o usuário pressionar Ctrl+C ou se ocorrerem exceções. Os manipuladores de sinal são restaurados adequadamente e a captura para de forma limpa.

**Trade-offs:**

- Prós: Limpeza garantida, sintaxe limpa, seguro contra exceções.
- Contras: Código repetitivo adicional, necessidade de entender o protocolo `__enter__/__exit__`.

Exemplo:

```python
# capture.py:197-230
class GracefulCapture:
    def __enter__(self) -> CaptureEngine:
        # Configuração: Instala manipuladores de sinal
        self._original_sigint = signal.signal(signal.SIGINT, self._handle_signal)
        self._engine.start()
        return self._engine

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Limpeza: Restaura manipuladores, para a captura
        signal.signal(signal.SIGINT, self._original_sigint)
        self._engine.stop()

# Uso: main.py:159-167
with GracefulCapture(engine) as cap:
    stats = cap.wait()
```

## Separação de Camadas

```
┌────────────────────────────────────┐
│    Camada CLI (main.py)            │
│    - Definições de comando         │
│    - Parsing de argumentos         │
│    - Interação com o usuário       │
└────────────────────────────────────┘
           ↓ chama
┌────────────────────────────────────┐
│    Camada de Serviço               │
│    - capture.py: CaptureEngine     │
│    - analyzer.py: Lógica protocolo │
│    - filters.py: Construção filtro │
└────────────────────────────────────┘
           ↓ usa
┌────────────────────────────────────┐
│    Camada de Dados                 │
│    - statistics.py: Agregação      │
│    - models.py: Estruturas dados   │
│    - constants.py: Configuração    │
└────────────────────────────────────┘
           ↓ produz
┌────────────────────────────────────┐
│    Camada de Saída                 │
│    - output.py: Exibição console   │
│    - visualization.py: Gráficos    │
│    - export.py: E/S de arquivo     │
└────────────────────────────────────┘
```

### Por que Camadas?

A separação de preocupações evita o acoplamento forte. Os comandos CLI não conhecem os internos do Scapy. O CaptureEngine não conhece a formatação Rich. Mudanças na visualização não afetam a coleta de estatísticas.

### O Que Vive Onde

**Camada CLI (main.py):**

- Arquivos: main.py, **main**.py
- Importações: Pode importar de todas as camadas.
- Proibido: Uso direto do Scapy, formatação Rich (delegar para output.py), Matplotlib (delegar para visualization.py).

**Camada de Serviço:**

- Arquivos: capture.py, analyzer.py, filters.py
- Importações: Apenas camada de dados, sem dependências de CLI ou saída.
- Proibido: Instruções print (retornar dados em vez disso), sys.exit() (lançar exceções).

**Camada de Dados:**

- Arquivos: statistics.py, models.py, constants.py, exceptions.py
- Importações: Apenas biblioteca padrão e type hints.
- Proibido: Qualquer E/S, qualquer importação de terceiros (exceto para verificação de tipo).

**Camada de Saída:**

- Arquivos: output.py, visualization.py, export.py
- Importações: Camada de dados para modelos, bibliotecas de formatação de terceiros.
- Proibido: Lógica de negócio, processamento de pacotes.

## Modelos de Dados

### PacketInfo

```python
# models.py:22-35
@dataclass(frozen = True, slots = True)
class PacketInfo:
    timestamp: float
    src_ip: str
    dst_ip: str
    protocol: Protocol
    size: int
    src_port: int | None = None
    dst_port: int | None = None
    src_mac: str | None = None
    dst_mac: str | None = None
```

**Campos explicados:**

- `timestamp`: Tempo Unix epoch da captura do pacote. Float para precisão de microssegundos. Usado para cálculos de largura de banda e análise de séries temporais.
- `src_ip/dst_ip`: Endereços IP em string (IPv4 ou IPv6). Não validados no nível do modelo (o analisador valida). Usados para rastreamento de endpoints.
- `protocol`: Enum Protocol (TCP, UDP, ICMP, etc). Determinado por analyzer.identify_protocol(). Usado para estatísticas de distribuição.
- `size`: Tamanho total do pacote em bytes, incluindo todos os cabeçalhos. Usado para cálculos de largura de banda e volume de tráfego.
- `src_port/dst_port`: Opcionais porque ICMP/ARP não possuem portas. None significa não aplicável ou não extraído.
- `src_mac/dst_mac`: Endereços de Camada 2 opcionais. Úteis para análise de rede local, menos relevantes para tráfego roteado.

**Relacionamentos:**

- Dataclass frozen evita modificação acidental após a criação.
- Criado por analyzer.extract_packet_info() a partir de objetos Packet do Scapy.
- Consumido por statistics.StatisticsCollector.record_packet().
- Armazenado em listas para exportação, mas não mantido em memória durante a captura ao vivo (apenas estatísticas).

### EndpointStats

```python
# models.py:38-61
@dataclass(slots = True)
class EndpointStats:
    ip_address: str
    packets_sent: int = 0
    packets_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0

    @property
    def total_packets(self) -> int:
        return self.packets_sent + self.packets_received

    @property
    def total_bytes(self) -> int:
        return self.bytes_sent + self.bytes_received
```

**Propósito:** Rastrear o tráfego bidirecional para cada endereço IP. Usado para identificação de "principais emissores" e estabelecimento de linha de base.

**Relacionamentos:**

- Mutável (não frozen) porque os contadores incrementam durante a captura.
- Uma instância por endereço IP único visto.
- Armazenado no dicionário statistics.StatisticsCollector._endpoints.
- Propriedades permitem a ordenação pelo volume total sem armazenar campos redundantes.

## Arquitetura de Segurança

### Modelo de Ameaça

O que estamos protegendo contra:

1. **Escalação de privilégios** - Garantir que a captura de pacotes só funcione com as permissões adequadas. Sem burlar a segurança do SO. Verificar as capabilities explicitamente antes de tentar a captura.

2. **Injeção de filtro** - Strings de filtro maliciosas podem travar o kernel ou burlar restrições pretendidas. Validar toda a entrada do usuário antes de passar para o compilador BPF.

3. **Exaustão de recursos** - Filas ilimitadas ou uso excessivo de memória podem causar DoS no sistema de monitoramento. Usar buffers limitados e limites razoáveis.

O que NÃO estamos protegendo contra (fora do escopo):

- **Acesso físico à rede** - Assume-se que o atacante pode se conectar à rede. Esta ferramenta não impede isso.
- **Inspeção de carga útil criptografada** - Analisamos metadados e cabeçalhos, não conteúdo criptografado. A descriptografia TLS requer proxies MITM.
- **Ameaças de computação quântica** - Ataques futuros a protocolos criptográficos não são abordados por ferramentas de captura de pacotes.

### Camadas de Defesa

```
Camada 1: Validação de Privilégios
    ↓ (capture.py:341-375)
Camada 2: Validação de Entrada
    ↓ (filters.py:30-66, main.py)
Camada 3: Limites de Recursos
    ↓ (capture.py:46, constants.py)
Camada 4: Tratamento de Erros
    ↓ (exceptions.py, try/except em todo o código)
```

**Por que múltiplas camadas?**

Defesa em profundidade. Se a validação de entrada tiver um bug, os limites de recursos evitam o DoS. Se a verificação de privilégios for burlada, o kernel ainda impõe as permissões. Cada camada captura diferentes vetores de ataque.

## Estratégia de Armazenamento

### Estatísticas em Memória

**O que armazenamos:**

- Contadores agregados (total de pacotes, bytes)
- Distribuições por protocolo
- Estatísticas por endpoint
- Amostras de largura de banda (séries temporais)

**Por que em memória:**
Desempenho. E/S de disco durante a captura de alta velocidade causa perda de pacotes. As estatísticas são atualizadas a cada pacote, exigindo latência de nanossegundos. A RAM fornece isso, o disco não.

**Gerenciamento de memória:**

```python
# constants.py:36-41
class CaptureDefaults:
    QUEUE_SIZE: Final[int] = 10_000
    BANDWIDTH_SAMPLE_INTERVAL_SECONDS: Final[float] = 1.0
```

O tamanho da fila limita a memória a ~10K pacotes × ~1.5KB = 15MB no máximo. Amostras de largura de banda a 1/segundo significam 3600 amostras/hora = ~100KB/hora. As estatísticas de endpoint dependem dos IPs únicos vistos.

### Exportação para Disco

Exportação opcional para JSON/CSV para persistência:

```python
# export.py:80-107
def export_to_json(
    stats: CaptureStatistics,
    filepath: Path,
    packets: list[PacketInfo] | None = None,
    options: ExportOptions | None = None,
) -> None:
```

Ocorre apenas sob demanda, não durante a captura. Separa o caminho quente (captura) do caminho frio (análise).

## Configuração

### Variáveis de Ambiente

```bash
NO_COLOR=1           # Desativa a saída colorida para ambientes de CI/CD
CI=1                 # Otimiza a saída para integração contínua
PYTHONUNBUFFERED=1   # Força o stdout sem buffer para logs em tempo real
```

### Estratégia de Configuração

Constantes em `constants.py` fornecem padrões sensatos. Argumentos de linha de comando substituem os padrões. Sem arquivos de configuração para evitar complexidade em uma ferramenta simples.

**Desenvolvimento:**

```python
# constants.py fornece padrões substituíveis
CaptureDefaults.QUEUE_SIZE = 10_000  # Equilíbrio entre memória e perda de pacotes
```

**Produção:**
Ajuste o tamanho da fila com base na memória disponível e na taxa de pacotes esperada. Uma fila de 10K lida com tráfego sustentado de ~1-2 Gbps.

## Considerações de Desempenho

### Gargalos

Onde este sistema fica lento sob carga:

1. **Contenção de fila** - Produtor e consumidor acessam a fila. Em taxas extremas (10+ Gbps), as operações de fila tornam-se o ponto de serialização. Mitigue com múltiplas filas e threads de worker.

2. **Lock de estatísticas** - Cada aquisição de pacote requer um lock em record_packet(). Em milhões de pacotes/segundo, a contenção de lock domina. Mitigue com contadores lock-free ou estatísticas por thread com mesclagem periódica.

### Otimizações

O que fizemos para torná-lo mais rápido:

- **Filtragem BPF no kernel**: Descarta ~99% dos pacotes irrelevantes antes que o espaço do usuário os veja. Mudar do espaço do usuário para o filtro BPF reduziu o uso da CPU de 80% para 5% em testes com filtro na porta 80 em uma rede ocupada.

- **Fila limitada com put não bloqueante**: Usar `put_nowait()` com contador de descartados explícito evita o bloqueio do produtor. A thread de captura nunca espera por um consumidor lento.

- **Slots de dataclass**: Reduz a memória por pacote em 40%. Com uma fila de 10K, economiza 6MB. Permite filas maiores no mesmo orçamento de memória.

- **Formatação de string mínima**: Formata a saída apenas ao exibir, não durante a captura. `print_packet()` só é chamado se a flag `--verbose` estiver definida.

### Escalabilidade

**Escalonamento vertical:**
Adicione mais CPU/RAM a uma única máquina. A captura de pacotes é limitada pela CPU (parsing de protocolo) e pela memória (armazenamento em fila). Um sistema de 8 núcleos com 32GB de RAM pode lidar com ~5-10 Gbps, dependendo do mix de tráfego.

**Escalonamento horizontal:**
Requer mudanças arquiteturais:

- Espelhar o tráfego para múltiplos hosts de captura.
- Usar fila distribuída (Kafka/RabbitMQ) em vez de Queue em memória.
- Agregar estatísticas de múltiplos coletores.
- O código atual não suporta isso sem modificação.

## Decisões de Design

### Decisão 1: AsyncSniffer vs sniff() síncrono

**O que escolhemos:**
AsyncSniffer com thread de background.

**Alternativas consideradas:**

- `sniff(prn=callback)` - Rejeitado porque bloqueia a thread principal, impedindo o desligamento gracioso e a exibição de progresso.
- `sniff(timeout=1)` em loop - Rejeitado porque introduz lacunas onde pacotes podem ser perdidos entre o timeout e o reinício.

**Trade-offs:**
Ganhos: UI responsiva, desligamento gracioso, processamento concorrente.
Perdas: Lógica de threading ligeiramente mais complexa, necessidade de gerenciamento de fila.

### Decisão 2: Locks de thread vs algoritmos lock-free

**O que escolhemos:**
`threading.Lock()` para proteção de estatísticas.

**Alternativas consideradas:**

- Atomics lock-free - Rejeitado porque o Python não possui operações atômicas verdadeiras (o GIL existe, mas não ajuda aqui).
- Sem sincronização - Rejeitado porque causa condições de corrida e corrupção de dados.

**Trade-offs:**
Ganhos: Correção, simplicidade, padrões padrão.
Perdas: Algum desempenho em taxas de pacotes extremas (milhões/seg), potencial para contenção de lock.

### Decisão 3: Dataclasses vs named tuples

**O que escolhemos:**
Dataclasses frozen com slots.

**Alternativas consideradas:**

- Named tuples - Rejeitado porque carecem de verificação de tipo, valores padrão e são mais difíceis de estender.
- Classes regulares - Rejeitado devido ao código repetitivo, falta de `__repr__` automático e mais memória.

**Trade-offs:**
Ganhos: Segurança de tipo, padrões, menos código repetitivo, melhor uso de memória.
Perdas: Requer Python 3.10+ para slots em dataclasses.

## Próximos Passos

Agora que você entende a arquitetura:

1. Leia [03-IMPLEMENTATION.md](./03-IMPLEMENTATION.md) para o passo a passo do código mostrando como cada componente realmente funciona.
2. Tente modificar o tamanho da fila em constants.py e observe o impacto na perda de pacotes sob carga.
3. Rastreie um único pacote desde a captura, passando pelas estatísticas até a saída, adicionando prints de depuração.
