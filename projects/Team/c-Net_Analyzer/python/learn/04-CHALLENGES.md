# Desafios de Extensão

Você construiu o projeto base. Agora torne-o seu estendendo-o com novos recursos.

Estes desafios estão ordenados por dificuldade. Comece pelos mais fáceis para ganhar confiança e, em seguida, enfrente os mais difíceis quando quiser se aprofundar.

## Desafios Fáceis

### Desafio 1: Adicionar Exibição de Suporte a IPv6

**O que construir:**
Melhorar a identificação de protocolo para reconhecer e exibir explicitamente pacotes IPv6 separadamente do IPv4. Atualmente, ambos aparecem como endereços IP, mas não são distinguidos.

**Por que é útil:**
A adoção do IPv6 está crescendo. Ferramentas de monitoramento de rede precisam rastrear o tráfego IPv4 vs IPv6 separadamente para entender o progresso da migração e diagnosticar problemas de dual-stack.

**O que você aprenderá:**

- Trabalhar com a camada IPv6 do Scapy
- Estender o enum Protocol
- Modificar a lógica do analisador

**Dicas:**

- Veja `analyzer.py:51-103` onde extract_packet_info() lida com a camada IP
- Adicione uma verificação para `packet.haslayer(IPv6)` junto com a verificação de IP
- Pode ser interessante adicionar Protocol.IPv6 ao enum ou rastrear como metadado
- Não se esqueça de lidar com casos onde ambos IPv4 e IPv6 estão presentes (túneis)

**Teste se funciona:**

```bash
# Gerar tráfego IPv6
ping6 ::1

# Capturar e verificar se o IPv6 aparece separadamente
sudo netanal capture -i lo -c 10 --verbose
```

Você deve ver endereços IPv6 na saída e estatísticas rastreando ambas as versões do protocolo.

### Desafio 2: Consulta OUI de Endereço MAC

**O que construir:**
Adicionar identificação de fabricante a partir de endereços MAC usando o OUI (primeiros 3 bytes). Exibir "Apple Inc." em vez de apenas "a4:83:e7:...".

**Por que é útil:**
Durante a resposta a incidentes, saber os fabricantes dos dispositivos ajuda a identificar o que está na rede. "Dispositivo Apple desconhecido" é mais útil do que um endereço MAC críptico.

**O que você aprenderá:**

- Parsing de endereço MAC
- Consultas em bancos de dados OUI
- Estratégias de cache

**Abordagem de implementação:**

1.  **Baixar banco de dados OUI** da IEEE
    - Arquivo: http://standards-oui.ieee.org/oui/oui.txt
    - Analisar em um dicionário: `{"A483E7": "Apple, Inc."}`

2.  **Adicionar função de consulta** em um novo arquivo `netanal/mac_lookup.py`

    ```python
    def lookup_manufacturer(mac_address: str) -> str:
        oui = mac_address.replace(":", "")[:6].upper()
        return OUI_DATABASE.get(oui, "Unknown")
    ```

3.  **Integrar com a saída** em `output.py:print_packet()`
    - Mostrar o fabricante após o endereço MAC
    - Exemplo: "a4:83:e7:12:34:56 (Apple Inc.)"

**Teste se funciona:**
Capture tráfego em sua rede local. Os fabricantes devem aparecer para dispositivos reconhecidos.

### Desafio 3: Limite de Alerta de Largura de Banda

**O que construir:**
Adicionar o argumento de linha de comando `--alert-threshold` que dispara um alerta visual quando a largura de banda excede o valor especificado em MB/s.

**Por que é útil:**
Alertas em tempo real durante a captura permitem que os operadores reajam imediatamente a picos de tráfego, ataques potenciais ou configurações incorretas.

**O que você aprenderá:**

- Padrões de monitoramento em tempo real
- Técnicas de notificação no console
- Comparações de limites em dados de streaming

**Dicas:**

- Adicione ao CaptureConfig em `models.py:135-145`
- Verifique o limite em `statistics.py:112-127` ao registrar amostras de largura de banda
- Use `output.py:print_warning()` ou print_error() para alertas
- Considere usar o Panel do Rich para alertas de destaque

**Teste se funciona:**

```bash
# Alerta em >1 MB/s
sudo netanal capture -i eth0 --alert-threshold 1.0

# Gerar tráfego para disparar
curl -O https://speed.hetzner.de/100MB.bin
```

O alerta deve aparecer em vermelho quando o limite for excedido.

## Desafios Intermediários

### Desafio 4: Rastreamento de Conexão TCP

**O que construir:**
Rastrear o handshake de três vias do TCP e os estados da conexão (SYN, SYN-ACK, ACK, FIN). Exibir handshakes incompletos (potenciais SYN floods) e conexões de longa duração.

**Aplicação no mundo real:**
Ataques DDoS de SYN flood enviam pacotes SYN sem completar o handshake. Detectar handshakes incompletos identifica ataques em andamento. Conexões de longa duração podem indicar backdoors persistentes.

**O que você aprenderá:**

- Máquina de estados TCP
- Rastreamento de tuplas de conexão (src_ip, src_port, dst_ip, dst_port)
- Dados de séries temporais com tempos de vida de conexão

**Abordagem de implementação:**

1.  **Criar rastreador de estado de conexão** em um novo arquivo `netanal/tcp_tracker.py`

    ```python
    @dataclass
    class TCPConnection:
        src_ip: str
        src_port: int
        dst_ip: str
        dst_port: int
        state: str  # SYN_SENT, ESTABLISHED, FIN_WAIT, etc.
        start_time: float
        last_seen: float

    class TCPTracker:
        def __init__(self):
            self._connections: dict[tuple, TCPConnection] = {}

        def process_packet(self, packet: PacketInfo):
            # Extrair flags TCP
            # Atualizar estado da conexão baseado nas flags
            # Rastrear no dicionário com chave (src_ip, src_port, dst_ip, dst_port)
    ```

2.  **Integrar com o coletor de estatísticas**
    - Adicionar TCPTracker ao StatisticsCollector
    - Chamar tracker.process_packet() em record_packet()

3.  **Adicionar relatórios** para mostrar:
    - Handshakes incompletos (SYN sem SYN-ACK)
    - Conexões em cada estado
    - Conexões de maior duração

**Armadilhas:**

- Flags TCP no Scapy: `packet[TCP].flags` é um bitmask, verifique flags específicas
- A direção da conexão importa: (A→B) é diferente de (B→A)
- Definir timeout para conexões antigas para evitar vazamento de memória

**Crédito extra:**
Detectar port scans rastreando muitas conexões de um IP para diferentes portas apenas com flags SYN.

### Desafio 5: Correlação de Consulta/Resposta DNS

**O que construir:**
Correlacionar consultas DNS com suas respostas. Rastrear a latência da consulta, consultas que falharam e quais domínios são mais consultados.

**Aplicação no mundo real:**
O DNS é frequentemente o primeiro indicador de comprometimento. Rastrear padrões de consulta detecta tunelamento DNS, beaconing de C2 e malware DGA (algoritmo de geração de domínio).

**O que você aprenderá:**

- Correlação de requisição/resposta usando IDs de transação
- Estrutura do protocolo DNS (flag de consulta vs resposta)
- Detecção de padrões baseada em tempo

**Abordagem de implementação:**

1.  **Melhorar a extração de DNS** em `analyzer.py`

    ```python
    def extract_dns_info(packet: Packet) -> dict | None:
        if not packet.haslayer(DNS):
            return None

        dns = packet[DNS]
        return {
            "transaction_id": dns.id,
            "query": dns.qr == 0,  # 0 = consulta, 1 = resposta
            "domain": dns.qd.qname.decode() if dns.qd else None,
            "response_code": dns.rcode if dns.qr == 1 else None,
            "answers": [str(rr.rdata) for rr in dns.an] if dns.an else []
        }
    ```

2.  **Rastrear consultas** em uma nova classe DNSTracker
    - Armazenar consultas pendentes com chave pelo ID da transação
    - Corresponder respostas às consultas
    - Calcular latência: tempo_resposta - tempo_consulta
    - Rastrear falhas (NXDOMAIN, SERVFAIL)

3.  **Relatar estatísticas**:
    - Latência média de DNS
    - Domínios mais consultados
    - Porcentagem de consultas com falha
    - Padrões suspeitos (muitos domínios únicos, domínios com alta entropia)

**Teste:**

```bash
# Gerar tráfego DNS
nslookup google.com
nslookup domain-inexistente-12345.com

# Capturar e analisar
sudo netanal capture -i lo -c 20
```

Deve mostrar consultas bem-sucedidas e com falha com medições de latência.

### Desafio 6: Histograma de Distribuição de Tamanho de Pacote

**O que construir:**
Rastrear a distribuição dos tamanhos dos pacotes e gerar um gráfico de histograma. Útil para detectar padrões de tráfego incomuns.

**Aplicação no mundo real:**
Distribuições de tamanho de pacote revelam tipos de aplicação. VoIP possui pacotes pequenos consistentes. Transferências de arquivos possuem pacotes grandes. Ataques DDoS frequentemente usam tamanhos específicos (minúsculos para amplificação, grandes para volumétricos).

**O que você aprenderá:**

- Geração de histograma com bins
- Análise de distribuição estatística
- Visualizações personalizadas com matplotlib

**Abordagem de implementação:**

1.  **Adicionar rastreamento de tamanho** ao StatisticsCollector

    ```python
    # Em statistics.py
    def __init__(self):
        # ... init existente
        self._size_buckets: dict[int, int] = defaultdict(int)
        self._size_bins = [64, 128, 256, 512, 1024, 1500, 9000]

    def _get_size_bucket(self, size: int) -> int:
        for bin_size in self._size_bins:
            if size <= bin_size:
                return bin_size
        return self._size_bins[-1]
    ```

2.  **Criar gráfico de histograma** em `visualization.py`

    ```python
    def create_size_histogram(
        stats: CaptureStatistics,
        title: str = "Packet Size Distribution"
    ) -> Figure:
        # Criar gráfico de barras com os bins de tamanho
        # Eixo X: intervalos de tamanho de pacote
        # Eixo Y: contagem ou porcentagem
    ```

3.  **Adicionar à CLI** no comando `main.py:chart()`
    - Novo tipo de gráfico: `--type size-histogram`

**Teste se funciona:**
Misture tipos de tráfego e observe as diferenças na distribuição:

```bash
# Tráfego HTTP (tamanhos variados)
curl http://example.com

# Tráfego DNS (tamanhos pequenos consistentes)
for i in {1..10}; do nslookup google.com; done

# Analisar
sudo netanal capture -i lo -c 100
netanal chart captured.pcap --type size-histogram
```

## Desafios Avançados

### Desafio 7: Mapeamento de IP por Geolocalização

**O que construir:**
Adicionar consulta GeoIP para mostrar país/cidade para IPs externos. Exibir os principais emissores com localização geográfica e gerar uma visualização em mapa mundial.

**Por que é difícil:**
Requer um banco de dados GeoIP externo, transformação de coordenadas para plotagem no mapa e tratamento de casos especiais (IPs privados, localhost, localizações desconhecidas).

**O que você aprenderá:**

- Integração de banco de dados GeoIP (MaxMind ou IP2Location)
- Visualização de dados geográficos
- Transformações de sistemas de coordenadas
- Manipulação e atualização de arquivos de banco de dados

**Mudanças de arquitetura necessárias:**

```
Novos Componentes:
- netanal/geoip.py → Classe de consulta GeoIP
- Matplotlib basemap → Plotagem de mapa mundial
- Arquivo de banco de dados → GeoLite2 ou similar

Modificado:
- EndpointStats → Adicionar campos de localização
- statistics.py → Chamar GeoIP em novos endpoints
- visualization.py → Nova função de gráfico de mapa
```

**Etapas de implementação:**

1.  **Fase de pesquisa**
    - Ler a documentação do MaxMind GeoLite2
    - Entender o formato do banco de dados (MMDB)
    - Olhar a biblioteca Python geoip2

2.  **Fase de design**
    - Decidir: banco de dados embutido vs download pelo usuário?
    - Considerar: cache de consultas para evitar acessos repetidos ao banco
    - Planejar: o que fazer com IPs privados (não consultar)

3.  **Fase de implementação**
    - Começar com consulta simples de país
    - Adicionar cidade e lat/long
    - Criar gráfico de dispersão (scatter plot) no mapa mundial com matplotlib
    - Dimensionar os pontos pelo volume de tráfego

4.  **Fase de teste**
    - Testar com IPs públicos (8.8.8.8, 1.1.1.1)
    - Verificar se IPs privados pulam a consulta
    - Verificar a renderização do mapa com tráfego real

**Armadilhas:**

- MaxMind requer cadastro de conta gratuita para download do banco de dados
- IPs privados (192.168.x.x, 10.x.x.x) devem pular a consulta
- Localhost (127.0.0.1) não possui localização geográfica
- Arquivos de banco de dados são grandes (~100MB), considere o gitignore

**Recursos:**

- MaxMind GeoLite2 (https://dev.maxmind.com/geoip/geolite2-free-geolocation-data)
- Documentação da biblioteca Python geoip2
- Tutorial de matplotlib Basemap

### Desafio 8: Extração de Certificado SSL/TLS

**O que construir:**
Extrair e exibir informações de certificado SSL/TLS de handshakes HTTPS. Mostrar o assunto do certificado, emissor, datas de validade e cadeia de certificados.

**Por que é difícil:**
Requer o parsing do protocolo de handshake TLS, lidar com múltiplas versões de TLS, extrair certificados X.509 e lidar com handshakes fragmentados.

**O que você aprenderá:**

- Estrutura do protocolo de handshake TLS
- Formato de certificado X.509
- Uso da camada TLS do Scapy
- Conceitos de validação de cadeia de certificados

**Etapas de implementação:**

**Fase 1: Extração Básica de Certificado** (8-10 horas)

```python
# No analyzer.py, adicione a extração TLS
from scapy.layers.tls.record import TLS
from scapy.layers.tls.handshake import TLSServerHello, TLSCertificate

def extract_tls_info(packet: Packet) -> dict | None:
    if not packet.haslayer(TLS):
        return None

    # Extrair certificados do handshake TLS
    # Analisar campos do certificado X.509
    # Retornar dicionário com assunto, emissor, datas
```

**Fase 2: Tratamento de Cadeia de Certificados** (10-12 horas)

- Lidar com múltiplos certificados na cadeia
- Rastrear certificados raiz, intermediários e folha
- Mostrar a hierarquia de certificados

**Fase 3: Integração e Exibição** (6-8 horas)

- Adicionar ao rastreamento de estatísticas
- Criar tabela de relatório de certificados
- Sinalizar certificados expirados ou autoassinados

**Fase 4: Recursos Avançados** (8-10 horas)

- Extração de SNI (Server Name Indication)
- Detecção de cipher suite
- Rastreamento de versão TLS
- Alertas de cifras fracas

**Estratégia de teste:**

```bash
# Gerar tráfego HTTPS
curl https://google.com
curl https://expired.badssl.com  # Testar certificado expirado

# Capturar e analisar
sudo netanal capture -i eth0 --filter "tcp port 443" -c 50
```

**Desafios conhecidos:**

1.  **Fragmentação TLS**
    - Problema: Certificados abrangem múltiplos segmentos TCP
    - Dica: Pode precisar de remontagem de fluxo TCP (o Desafio 4 ajuda)

2.  **Versões TLS**
    - Problema: TLS 1.0, 1.1, 1.2, 1.3 possuem estruturas diferentes
    - Dica: Use a camada TLS do Scapy que abstrai as versões

**Critérios de sucesso:**
Sua implementação deve:

- [ ] Extrair assunto e emissor do certificado
- [ ] Mostrar datas de validade (não antes de, não depois de)
- [ ] Lidar com cadeias de certificados
- [ ] Exibir o hostname SNI
- [ ] Sinalizar certificados expirados
- [ ] Funcionar com TLS 1.2 e 1.3

### Desafio 9: Detecção de Anomalias em Tempo Real

**O que construir:**
Implementar detecção estatística de anomalias que alerte sobre padrões de tráfego incomuns em tempo real durante a captura. Detectar picos de largura de banda, proporções de protocolo incomuns e novas conexões para portas estranhas.

**Tempo estimado:**
2-3 semanas para implementação completa

**Pré-requisitos:**
Concluir o Desafio 4 (rastreamento TCP) e o Desafio 6 (distribuição de tamanho) primeiro, pois este se baseia nesses padrões.

**O que você aprenderá:**

- Controle estatístico de processo
- Cálculos de Z-score para detecção de outliers
- Médias móveis e desvios padrão
- Geração de alertas em tempo real
- Modos de aprendizado de linha de base vs detecção de anomalias

**Planejando este recurso:**

Antes de codificar, pense sobre:

- Como estabelecer uma linha de base? (Precisa de um período de "modo de aprendizado")
- Quais métricas indicam anomalias? (Largura de banda, proporção de protocolo, taxa de conexão)
- Como evitar a fadiga de alertas? (Ajuste de limites, períodos de cooldown)
- Qual é a sua tolerância a falsos positivos? (Limites de Z-score)

**Arquitetura de alto nível:**

```
┌─────────────────────────────────────┐
│    Estabelecimento de Linha de Base │
│ (Modo Aprendizado: 5-10 minutos)    │
│                                     │
│ - Coletar amostras de tráfego normal│
│ - Calcular média e desvio padrão    │
│ - Armazenar métricas de linha de base│
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│     Detecção em Tempo Real          │
│   (Modo Detecção: Contínuo)         │
│                                     │
│ - Comparar atual vs linha de base   │
│ - Calcular Z-scores                 │
│ - Disparar alertas em outliers      │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│       Manipulador de Alertas        │
│                                     │
│ - Registrar detalhes da anomalia    │
│ - Exibir alerta no terminal         │
│ - Opcional: notificação por webhook │
└─────────────────────────────────────┘
```

**Fases de implementação:**

**Fase 1: Coleta de Linha de Base** (12-16 horas)
Criar novo arquivo `netanal/anomaly.py`:

```python
@dataclass
class BaselineMetrics:
    bandwidth_mean: float
    bandwidth_stddev: float
    protocol_ratios: dict[Protocol, float]
    connection_rate_mean: float
    connection_rate_stddev: float

class AnomalyDetector:
    def __init__(self, learning_period: int = 300):  # 5 minutos
        self._learning_mode = True
        self._samples: list[float] = []
        # ... mais init

    def learn(self, stats: CaptureStatistics):
        # Coletar amostras durante o período de aprendizado
        # Calcular estatísticas
        pass

    def detect(self, stats: CaptureStatistics) -> list[Anomaly]:
        # Comparar contra a linha de base
        # Retornar lista de anomalias detectadas
        pass
```

**Fase 2: Detecção Estatística** (16-20 horas)
Implementar cálculos de Z-score:

```python
def calculate_zscore(value: float, mean: float, stddev: float) -> float:
    if stddev == 0:
        return 0
    return (value - mean) / stddev

def is_anomaly(zscore: float, threshold: float = 3.0) -> bool:
    return abs(zscore) > threshold
```

Rastrear múltiplas métricas:

- Largura de banda (bytes/segundo)
- Taxa de pacotes (pacotes/segundo)
- Distribuição de protocolos (% TCP vs UDP vs outros)
- Taxa de conexão (novas conexões/segundo)
- Portas de destino únicas

**Fase 3: Geração de Alertas** (8-10 horas)
Criar tipos de alerta:

```python
@dataclass
class Anomaly:
    timestamp: float
    metric: str  # "bandwidth", "protocol_ratio", etc.
    value: float
    expected: float
    severity: str  # "low", "medium", "high"
    description: str

def format_alert(anomaly: Anomaly) -> str:
    # Criar mensagem de alerta legível por humanos
    # Incluir o que é incomum e por quanto
```

**Fase 4: Integração** (6-8 horas)

- Adicionar ao CaptureEngine
- Chamar o detector durante a amostragem de largura de banda
- Exibir alertas em tempo real
- Registrar anomalias em arquivo

**Estratégia de teste:**

Testar com anomalias sintéticas:

```python
# Teste 1: Pico de largura de banda
# Linha de base: tráfego normal
# Injetar: download de arquivo grande
# Esperado: alerta de anomalia de largura de banda

# Teste 2: Mudança de protocolo
# Linha de base: 80% TCP, 20% UDP
# Injetar: flood UDP
# Esperado: anomalia de proporção de protocolo

# Teste 3: Port scan
# Linha de base: conexões para portas normais
# Injetar: scan nmap
# Esperado: alta taxa de conexão + portas incomuns
```

**Desafios conhecidos:**

1.  **Problema de cold start**
    - Problema: Nenhuma linha de base na primeira execução
    - Dica: Salvar linhas de base aprendidas no disco, carregar em execuções subsequentes

2.  **Desvio de conceito (Concept drift)**
    - Problema: O comportamento da rede muda ao longo do tempo (novos serviços, hora do dia)
    - Dica: Implementar linhas de base adaptativas que se atualizam lentamente

**Critérios de sucesso:**
Sua implementação deve:

- [ ] Aprender a linha de base em um período de 5-10 minutos
- [ ] Detectar picos de largura de banda (>3 desvios padrão)
- [ ] Detectar distribuições de protocolo incomuns
- [ ] Detectar anomalias na taxa de conexão
- [ ] Exibir alertas em tempo real
- [ ] Incluir pontuação de confiança/severidade
- [ ] Evitar falsos positivos excessivos (<10% durante tráfego normal)
- [ ] Salvar e carregar linhas de base aprendidas

## Desafios de Desempenho

### Desafio: Lidar com Tráfego de 10 Gbps

**O objetivo:**
Otimizar a engine de captura para lidar com tráfego de 10 gigabits por segundo sem perder pacotes.

**Gargalo atual:**
A 10 Gbps, você está processando ~10 milhões de pacotes/segundo. O código atual descarta pacotes porque:

- A fila enche (o buffer de 10K é muito pequeno)
- Contenção de lock de estatísticas (milhões de aquisições de lock/seg)
- O GIL do Python limita o paralelismo
- Alocações de memória desaceleram o garbage collection

**Abordagens de otimização:**

**Abordagem 1: Múltiplas Threads de Processamento**

- Como: Usar um thread pool com N workers retirando da fila
- Ganho: N× throughput de processamento
- Tradeoff: Necessidade de estatísticas lock-free ou agregação por thread

**Abordagem 2: Estatísticas Lock-Free**

- Como: Usar contadores por thread, agregação periódica
- Ganho: Elimina o gargalo de contenção de lock
- Tradeoff: Código mais complexo, consistência eventual

**Abordagem 3: Amostragem (Sampling)**

- Como: Processar 1 a cada N pacotes
- Ganho: Reduz a carga da CPU proporcionalmente
- Tradeoff: Aproximação estatística, pode perder eventos raros

**Abordagem 4: Agregação BPF**

- Como: Usar eBPF para agregar no kernel antes do espaço do usuário
- Ganho: Melhoria massiva de desempenho
- Tradeoff: Requer Linux, habilidades de programação eBPF

**Faça o benchmark:**

```bash
# Gerar tráfego de alta velocidade com iperf3
iperf3 -s &  # Servidor
iperf3 -c localhost -b 10G  # Cliente

# Monitorar pacotes descartados
sudo netanal capture -i lo --verbose | grep "Dropped"
```

Métricas alvo:

- Pacotes descartados: <1% a 10 Gbps
- Uso de CPU: <80% em sistema de 8 núcleos
- Memória: <4 GB

## Desafios de Segurança

### Desafio: Adicionar Criptografia PCAP

**O que implementar:**
Criptografar arquivos PCAP capturados para proteger dados sensíveis da rede. Adicionar a flag `--encrypt` que solicita uma senha e criptografa a saída usando AES-256.

**Modelo de ameaça:**
Isso protege contra:

- Acesso não autorizado a arquivos capturados
- Divulgação acidental de tráfego sensível
- Requisitos de conformidade (HIPAA, PCI-DSS)

**Implementação:**
Usar a biblioteca cryptography:

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

def encrypt_pcap(filepath: Path, password: str):
    # Derivar chave da senha usando PBKDF2
    # Criptografar arquivo com Fernet (AES-128-CBC + HMAC)
    # Escrever saída criptografada com extensão .enc
```

**Testando a segurança:**

- Tentar abrir o arquivo criptografado com o Wireshark (deve falhar)
- Verificar se a senha é exigida para descriptografia
- Verificar se senhas fracas são rejeitadas

### Desafio: Passar no Checklist de Benchmark do CIS

**O objetivo:**
Tornar este projeto compatível com os controles relevantes do CIS (Center for Internet Security) para ferramentas de monitoramento de rede.

**Lacunas atuais:**

**Lacuna 1: Sem log de auditoria**

- Faltando: Quem executou as capturas, quando, quais filtros foram usados
- Remediação: Adicionar log de auditoria em ~/.netanal/audit.log

**Lacuna 2: Sem documentação de sanitização de entrada**

- Faltando: Documentação clara das entradas validadas
- Remediação: Documentar toda a validação em security.md

**Lacuna 3: Sem limites de recursos**

- Faltando: Memória ilimitada se mal configurado
- Remediação: Adicionar limites rígidos com configuração

**Lacuna 4: Escalação de privilégios sem log**

- Faltando: Nenhum registro de quando privilégios de root foram usados
- Remediação: Registrar todas as operações elevadas

**Lacuna 5: Sem padrões seguros**

- Faltando: Padrões permitem modo promíscuo, qualquer interface
- Remediação: Exigir especificação explícita da interface

Cada lacuna mapeia para controles específicos do CIS. Implemente as correções e documente a conformidade.

## Misture e Combine

Combine recursos para projetos maiores:

**Ideia de Projeto 1: Dashboard de Segurança de Rede**

- Combine o Desafio 4 (rastreamento TCP) + Desafio 9 (detecção de anomalias) + Desafio 7 (geolocalização)
- Adicione uma UI web mostrando um mapa de conexões em tempo real com destaques de anomalias
- Resultado: Dashboard visual de SOC para monitoramento de rede

**Ideia de Projeto 2: Monitor de Segurança DNS**

- Combine o Desafio 5 (rastreamento DNS) + Desafio 9 (detecção de anomalias)
- Adicione detecção de DGA (análise de entropia de domínio)
- Resultado: Ferramenta de monitoramento de segurança específica para DNS

**Ideia de Projeto 3: Análise de Tráfego Criptografado**

- Combine o Desafio 8 (extração TLS) + Desafio 4 (rastreamento TCP)
- Adicione fingerprinting JA3 (identificação de cliente TLS)
- Resultado: Detectar malware por padrões TLS sem descriptografia

## Desafios de Integração no Mundo Real

### Integrar com SIEM (Splunk/ELK)

**O objetivo:**
Enviar estatísticas de captura para um SIEM para log centralizado e correlação.

**O que você precisará:**

- Instância de SIEM (Splunk gratuito ou stack ELK)
- HTTP Event Collector (Splunk) ou endpoint Logstash (ELK)
- Formatação JSON para eventos

**Plano de implementação:**

1. Criar `netanal/siem.py` com o cliente SIEM
2. Adicionar argumento CLI `--siem-url`
3. Serializar estatísticas para JSON
4. POST para o endpoint do SIEM a cada N segundos
5. Lidar com falhas de conexão graciosamente

**Cuidado com:**

- Limites de taxa na ingestão do SIEM
- Autenticação (chaves de API)
- Falhas de rede (enfileirar eventos não enviados)
- Privacidade de dados (não enviar cargas úteis de pacotes)

**Checklist de produção:**

- [ ] TLS para conexão com SIEM
- [ ] Chave de API de variável de ambiente
- [ ] Lógica de retry com backoff exponencial
- [ ] Fila local para operação offline

### Implantar no Kubernetes

**O objetivo:**
Empacotar a ferramenta como um container e implantar como DaemonSet para monitoramento de rede em todo o cluster.

**O que você aprenderá:**

- Conteinerização com Docker
- Redes no Kubernetes
- Gerenciamento de privilégios em containers
- Coleta de dados distribuída

**Etapas:**

1.  **Criar Dockerfile**

    ```dockerfile
    FROM python:3.14-slim
    RUN apt-get update && apt-get install -y libpcap-dev
    COPY . /app
    WORKDIR /app
    RUN pip install -e .
    CMD ["netanal", "capture"]
    ```

2.  **Build do container**

    ```bash
    docker build -t netanal:latest .
    ```

3.  **Criar manifesto Kubernetes**

    ```yaml
    apiVersion: apps/v1
    kind: DaemonSet
    metadata:
      name: netanal
    spec:
      template:
        spec:
          hostNetwork: true # Necessário para captura de pacotes
          containers:
            - name: netanal
              image: netanal:latest
              securityContext:
                capabilities:
                  add: ["NET_RAW", "NET_ADMIN"]
    ```

4.  **Implantar**
    ```bash
    kubectl apply -f netanal-daemonset.yaml
    ```

**Checklist de produção:**

- [ ] Usuário não-root no container
- [ ] Apenas capabilities necessárias (NET_RAW)
- [ ] Limites de recursos (CPU/memória)
- [ ] Agregação de logs para coletor central
- [ ] Endpoints de health check

## Obtendo Ajuda

Travou em um desafio?

1.  **Depure sistematicamente**
    - O que você esperava que acontecesse?
    - O que realmente aconteceu?
    - Qual é o menor caso de teste que reproduz o problema?
    - Você pode adicionar instruções print para restringir o problema?

2.  **Leia o código existente**
    - O Desafio 4 (rastreamento TCP) é semelhante ao Desafio 5 (rastreamento DNS) - use os mesmos padrões
    - O código de visualização já lida com múltiplos tipos de gráficos - estenda-o

3.  **Pesquise por problemas semelhantes**
    - "Scapy TCP flags" → encontra exemplos de parsing de flags
    - "Python statistical anomaly detection" → encontra algoritmos de Z-score
    - "matplotlib world map" → encontra exemplos de basemap

4.  **Peça ajuda**
    - Descreva o que você está tentando construir
    - Mostre o que você já tentou
    - Explique o que deu errado
    - Inclua trechos de código e mensagens de erro relevantes

Não apenas cole "não funciona" com um stack trace. Explique seu entendimento do problema.

## Conclusão de Desafios

Acompanhe seu progresso:

**Fácil:**

- [ ] Exibição de Suporte a IPv6
- [ ] Consulta OUI de Endereço MAC
- [ ] Limite de Alerta de Largura de Banda

**Intermediário:**

- [ ] Rastreamento de Conexão TCP
- [ ] Correlação de Consulta/Resposta DNS
- [ ] Histograma de Distribuição de Tamanho de Pacote

**Avançado:**

- [ ] Mapeamento de IP por Geolocalização
- [ ] Extração de Certificado SSL/TLS
- [ ] Detecção de Anomalias em Tempo Real

**Desempenho:**

- [ ] Lidar com Tráfego de 10 Gbps

**Segurança:**

- [ ] Criptografia PCAP
- [ ] Conformidade com Benchmark CIS

**Integração:**

- [ ] Integração com SIEM
- [ ] Implantação no Kubernetes

Completou todos eles? Você dominou a análise de pacotes de rede. Considere contribuir com suas soluções de volta para o projeto ou construir algo novo, como um IDS ou uma ferramenta de perícia de rede.

## Desafie-se Ainda Mais

### Construa Algo Novo

Use os conceitos que você aprendeu aqui para construir:

- **Analisador de pacotes wireless** - Estenda para monitorar quadros 802.11, detectar ataques de deauth.
- **Analisador de protocolos industriais** - Adicione suporte para protocolos Modbus/SCADA.
- **Ferramenta de perícia de rede** - Reconstrua transferências de arquivos, extraia artefatos de pcaps.

### Estude Implementações Reais

Compare sua implementação com ferramentas de produção:

- **Wireshark/tshark** - Veja os filtros de exibição vs BPF, dissetores de protocolo.
- **Zeek (antigo Bro)** - Estude a arquitetura orientada a eventos, extensibilidade por script.
- **Suricata** - Examine a abordagem de multi-threading, aceleração por GPU.

Leia o código deles, entenda seus trade-offs, roube suas boas ideias.

### Escreva Sobre Isso

Documente sua extensão:

- Post em blog explicando "Como adicionei detecção de anomalias a um analisador de pacotes".
- Tutorial para que outros implementem seu recurso.
- Comparação: Sua abordagem vs como o Wireshark faz.

Ensinar os outros é a melhor maneira de verificar se você realmente entendeu.
