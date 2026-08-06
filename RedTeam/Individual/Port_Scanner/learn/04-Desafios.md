# Desafios de Extensão

Você construiu um scanner de portas TCP concorrente básico. Agora, torne-o pronto para produção com recursos que ferramentas profissionais como o Nmap passaram décadas aperfeiçoando.

Estes desafios estão ordenados por dificuldade. Comece pelos mais fáceis para ganhar confiança e, em seguida, enfrente os mais difíceis quando quiser se aprofundar.

## Desafios Fáceis

### Desafio 1: Formato de Saída CSV

**O que construir:**
Adicione uma flag de linha de comando `-o output.csv` que escreva os resultados em CSV em vez de imprimir no terminal.

**Por que é útil:**
Equipes de segurança precisam de saída legível por máquina para alimentar outras ferramentas. O CSV carrega no Excel, importa para bancos de dados e processa com scripts Python/awk para relatórios.

**O que você aprenderá:**

- E/S de arquivo em C++
- Formatos de saída estruturados
- Tornar ferramentas CLI amigáveis para pipelines

**Dicas:**

- Adicione uma nova opção no `main.cpp` por volta da linha 14: `("output,o", po::value<std::string>(), "CSV output file")`
- Modifique `PortScanner::scan()` para escrever em um stream de arquivo em vez de usar `printf`
- Formato CSV: `port,state,service,banner` com escape adequado para aspas/vírgulas nos banners
- Não se esqueça de fechar o arquivo quando o escaneamento for concluído

**Teste se funciona:**

```bash
./simplePortScanner -i scanme.nmap.org -p 1-1024 -o results.csv
cat results.csv
# Deve mostrar: 22,OPEN,SSH,SSH-2.0-OpenSSH_...
```

### Desafio 2: Indicador de Progresso

**O que construir:**
Mostre a porcentagem de conclusão durante os escaneamentos para que os usuários saibam que está funcionando e quanto tempo devem esperar.

**Por que é útil:**
Escaneamentos TCP completos de 65535 portas levam minutos. Sem feedback, os usuários pensam que a ferramenta travou. Barras de progresso reduzem a ansiedade e as solicitações de suporte.

**O que você aprenderá:**

- Códigos de controle de terminal para sobrescrever linhas
- Calcular a porcentagem de conclusão com workers concorrentes
- Equilibrar atualizações de UI com desempenho (não atualize cada porta, faça em lotes)

**Dicas:**

- Rastreie `scanned_count` (portas finalizadas) e `total_ports` (a partir do intervalo inicial/final)
- Atualize a exibição a cada N portas (não a cada porta - muito lento): `if (scanned_count % 100 == 0)`
- Use `\r` para sobrescrever a linha atual: `printf("\rProgress: %d/%d (%.1f%%)", scanned, total, percent);`
- Limpe o buffer de saída após imprimir: `fflush(stdout);`
- Olhe para `PortScanner.cpp:147,156` onde as estatísticas são incrementadas - adicione o cálculo de progresso lá

**Teste se funciona:**

```bash
./simplePortScanner -i scanme.nmap.org -p 1-10000
# Deve mostrar: Progress: 1000/10000 (10.0%)
#              Progress: 2000/10000 (20.0%)
# ...atualizando no local
```

### Desafio 3: Escanear Múltiplos Hosts

**O que construir:**
Aceitar múltiplos alvos: `./simplePortScanner -i 192.168.1.1,192.168.1.2,192.168.1.3 -p 80,443`

**Por que é útil:**
O pentest exige o escaneamento de sub-redes inteiras. Executar a ferramenta 254 vezes para uma rede /24 é tedioso. O escaneamento em lote é essencial.

**O que você aprenderá:**

- Parsing de valores separados por vírgula
- Gerenciar múltiplos alvos de endpoint
- Coordenar operações assíncronas em diferentes hosts

**Dicas:**

- Modifique o padrão de `parse_port()` para criar um `parse_hosts()` que divide por vírgulas
- Armazene um vector de endpoints em vez de um único endpoint
- Loop externo sobre os hosts, loop interno sobre as portas (ou vice-versa - tente ambos e compare o desempenho)
- Imprima o IP/nome do host com cada resultado para que você possa identificar a qual host uma porta pertence

**Teste se funciona:**

```bash
./simplePortScanner -i 8.8.8.8,1.1.1.1 -p 53
# Deve mostrar:
# 8.8.8.8    53  OPEN  DNS  ...
# 1.1.1.1    53  OPEN  DNS  ...
```

## Desafios Intermediários

### Desafio 4: Saída JSON para Integração de Ferramentas

**O que construir:**
Adicione `-o output.json --format json` para produzir uma saída JSON estruturada compatível com cadeias de ferramentas de segurança.

**Aplicação no mundo real:**
Pipelines de CI/CD executam escaneamentos de portas e verificam os resultados programaticamente. O JSON se integra com scripts de segurança Python, Splunk, ELK stack. Isso torna seu scanner adequado para testes de segurança automatizados.

**O que você aprenderá:**

- Serialização JSON em C++ (use uma biblioteca como nlohmann/json)
- Estruturas de dados aninhadas para representar resultados de scan
- Negociação de formato de saída via flags CLI

**Abordagem de implementação:**

1. **Adicione a dependência da biblioteca JSON** ao CMakeLists.txt
   - Baixe nlohmann/json: `https://github.com/nlohmann/json`
   - Adicione o caminho de inclusão ou use FetchContent no CMake

2. **Colete os resultados durante o scan** em vez de imprimir imediatamente
   - Crie um `std::vector<ScanResult>` onde `ScanResult` tenha os campos port, state, service, banner
   - Nos handlers de conclusão, anexe ao vector em vez de usar `printf`
   - Imprima o JSON ao final no `run()`

3. **Estruture a saída JSON:**

```json
{
  "target": "192.168.1.1",
  "scan_time": "2024-01-30T15:23:45Z",
  "ports_scanned": 1024,
  "results": [
    { "port": 22, "state": "open", "service": "ssh", "banner": "SSH-2.0-..." },
    { "port": 80, "state": "closed", "service": "http", "banner": null }
  ]
}
```

**Dicas:**

- Não tente escrever JSON manualmente com concatenação de strings (propenso a erros)
- Use a biblioteca: `json j; j["port"] = 22; j["state"] = "open";`
- Lide com caracteres especiais nos banners (quebras de linha, aspas)

**Crédito extra:**
Suporte múltiplos formatos de saída simultaneamente: imprima em formato legível por humanos no stdout e escreva JSON em um arquivo.

### Desafio 5: Detecção de Versão de Serviço

**O que construir:**
Além do banner grabbing básico, envie sondagens específicas de protocolo para identificar versões exatas de software, mesmo quando os serviços não se anunciam.

**Aplicação no mundo real:**
Muitos servidores endurecidos (hardened) desativam banners. Servidores HTTP configurados com `ServerTokens Prod` apenas dizem "Apache" sem a versão. O FTP pode não anunciar nada. A sondagem ativa extrai informações de versão para avaliação de vulnerabilidades.

**O que você aprenderá:**

- Protocolos da camada de aplicação (requisições HTTP GET, comandos SMTP EHLO)
- Técnicas de fingerprinting específicas de protocolo
- Gerenciar múltiplos round-trips por porta

**Abordagem de implementação:**

1. **Crie um banco de dados de sondagens** mapeando portas para sequências de sondagem
   - Porta 80: Envie "GET / HTTP/1.0\r\n\r\n", analise o cabeçalho Server
   - Porta 21: Leia o banner, envie "SYST\r\n", analise o tipo de sistema
   - Porta 25: Leia o banner, envie "EHLO scanner\r\n", analise as capacidades

2. **Estenda a lógica de banner grab** em `PortScanner.cpp:143`
   - Após ler o banner inicial, verifique se temos uma sondagem para esta porta
   - Se sim, envie a sondagem via `async_write`
   - Leia a resposta via outro `async_read_some`
   - Analise a resposta para extrair a versão

3. **Analise as strings de versão:**
   - HTTP: Extraia do cabeçalho `Server:`
   - FTP: Analise o formato `220 ProFTPD 1.3.5 Server`
   - SSH: Já está no banner (SSH-2.0-OpenSSH_X.Y)

**Dicas:**

- Olhe o arquivo `nmap-service-probes` do Nmap para inspiração de sondagens
- Lide com protocolos que precisam de respostas específicas (o FTP espera USER após a conexão)
- Algumas sondagens disparam alertas de IDS (tenha cuidado com fingerprinting agressivo)

**Crédito extra:**
Implemente a correspondência de versão com o banco de dados CPE para mapear versões para CVEs automaticamente.

## Desafios Avançados

### Desafio 6: SYN Scan (Escaneamento Furtivo)

**O que construir:**
Implementar o escaneamento SYN half-open que não completa o handshake TCP, tornando-o mais furtivo do que o nosso connect scan atual.

**Por que é difícil:**
Requer raw sockets (privilégios de root), construção manual de pacotes, tratamento de respostas na camada IP. Você está ignorando a pilha TCP do kernel inteiramente.

**O que você aprenderá:**

- Programação de raw sockets no Linux
- Estrutura do pacote TCP (flags SYN, números de sequência, checksums)
- Requisitos de escalonamento de privilégios e implicações de segurança
- Criação de pacotes com bibliotecas como libnet ou raw sockets POSIX

**Mudanças de arquitetura necessárias:**

```
Atual:
  ┌───────────┐
  │  Kernel   │ ← Lida com o handshake TCP
  │ Pilha TCP │
  └───────────┘
       ↑
  ┌───────────┐
  │  Scanner  │ ← Chama connect()
  └───────────┘

SYN Scan:
  ┌───────────┐
  │  Kernel   │ ← Ignorado para envio, usado para recebimento
  └───────────┘
       ↑
  ┌───────────┐
  │ Raw Socket│ ← Cria pacotes SYN manualmente
  └───────────┘
       ↑
  ┌───────────┐
  │  Scanner  │ ← Constrói pacotes, escuta por SYN-ACK
  └───────────┘
```

**Etapas de implementação:**

1. **Fase de pesquisa**
   - Leia as seções da RFC 793 sobre o handshake SYN
   - Estude a implementação do SYN scan do Nmap (código aberto)
   - Entenda o cálculo do checksum TCP (pseudo-header + cabeçalho TCP + dados)

2. **Fase de design**
   - Decida: Usar raw sockets ou libnet/libpcap?
   - Raw sockets = mais controle, mas mais difícil. libnet = mais fácil, mas é uma dependência.
   - Planeje a estrutura do pacote: cabeçalho IP + cabeçalho TCP com flag SYN
   - Considere: Você enviará de portas de origem aleatórias? (O Nmap faz isso para evasão)

3. **Fase de implementação**
   - Crie o raw socket: `socket(AF_INET, SOCK_RAW, IPPROTO_TCP)` (requer root)
   - Construa o pacote TCP SYN:

```cpp
     struct tcphdr syn;
     syn.th_sport = htons(random_port);
     syn.th_dport = htons(target_port);
     syn.th_seq = htonl(random_seq);
     syn.th_flags = TH_SYN;
     // ... definir outros campos
     syn.th_sum = tcp_checksum(&syn);
```

- Envie via `sendto()`
- Escute pela resposta com `recvfrom()` ou filtro pcap
- Analise a resposta:
  - SYN-ACK = porta aberta
  - RST = porta fechada
  - Nada = filtrada (ou pacote perdido)

4. **Fase de teste**
   - Teste contra o localhost primeiro (mais fácil de depurar)
   - Use o Wireshark para verificar se os pacotes estão corretos
   - Compare os resultados com o connect scan (devem coincidir)
   - Teste a detecção de filtragem (a lógica de timeout ainda se aplica)

**Armadilhas:**

- **O kernel envia RST após o SYN-ACK:** Quando você recebe um SYN-ACK, o kernel envia um RST automaticamente (ele não sabe sobre a sua conexão via raw socket). Isso é normal, mas deixa rastros nos logs.
- **O cálculo do checksum é complexo:** O checksum TCP inclui um pseudo-header com os IPs de origem/destino. Erre isso e os pacotes serão descartados silenciosamente.
- **Detecção de IDS:** Scans SYN sem completar o handshake disparam alertas em IDSs modernos. Menos furtivo do que você imagina.

**Recursos:**

- RFC 793 - Especificação TCP
- Código fonte do Nmap - `scan_engine.cc` possui a lógica do SYN scan
- Documentação da libnet - mais fácil que raw sockets

### Desafio 7: Fingerprinting de SO via Diferenças na Pilha TCP/IP

**O que construir:**
Identificar o sistema operacional de destino analisando peculiaridades da implementação TCP/IP (TTL inicial, tamanho da janela, opções TCP, tratamento de fragmentação).

**Por que é difícil:**
Requer conhecimento profundo de comportamentos TCP específicos de SO, análise estatística de múltiplas sondagens e manutenção de bancos de dados de assinaturas. Você está explorando diferenças de implementação, não vulnerabilidades de protocolo.

**O que você aprenderá:**

- Diferenças de implementação da pilha TCP/IP entre famílias de SO
- Técnicas de fingerprinting passivas vs ativas
- Classificação estatística a partir do comportamento da rede
- Como ferramentas como p0f e a detecção de SO do Nmap funcionam

**Etapas de implementação:**

**Fase 1: Coleta de Dados** (2-4 horas)

- Capture características TCP/IP das respostas:
  - TTL inicial (Linux: 64, Windows: 128, Cisco: 255)
  - Tamanho da janela TCP (varia por SO e versão)
  - Ordem das opções TCP (MSS, SACK, Timestamps, Window Scale)
  - Comportamento do IPID (incremental, aleatório, zero)
  - Uso do bit Don't Fragment (DF)
- Envie pacotes criados para obter respostas:
  - SYN com tamanhos de janela incomuns
  - SYN com opções TCP específicas
  - ACK vazio para porta fechada (a resposta RST revela informações)

**Fase 2: Banco de Dados de Assinaturas** (3-5 horas)

- Crie um banco de dados de fingerprinting de SO:

```json
{
  "Linux 5.x": {
    "ttl": 64,
    "window_size": 29200,
    "tcp_options": "M*,S,T,N,W*",
    "df_bit": true
  },
  "Windows 10": {
    "ttl": 128,
    "window_size": 8192,
    "tcp_options": "M*,N,W*,S,T",
    "df_bit": true
  }
}
```

- Teste contra sistemas conhecidos para validar as assinaturas
- Lide com variações de versão (Windows 7 vs 10, Ubuntu 18.04 vs 22.04)

**Fase 3: Lógica de Correspondência** (4-6 horas)

- Implemente correspondência difusa (fuzzy matching) (correspondências exatas são raras):
  - O TTL pode ter sido decrementado por roteadores
  - Os tamanhos de janela podem ser configurados
  - Pondere diferentes sinais (o TTL é o mais confiável)
- Calcule pontuações de confiança:

```cpp
  int score = 0;
  if (ttl_matches) score += 50;
  if (window_matches) score += 30;
  if (options_match) score += 20;
  return score >= 70 ? "High confidence" : "Uncertain";
```

**Fase 4: Integração** (2-3 horas)

- Conecte à lógica existente do scanner após o banner grab
- Envie sondagens adicionais para fingerprinting
- Exiba o palpite do SO com a confiança: "Linux 2.6.X - 5.X (95%)"

**Estratégia de teste:**

- Teste contra VMs com SOs conhecidos (Ubuntu, Windows, FreeBSD)
- Teste através de NAT (mudanças de TTL complicam as coisas)
- Compare os resultados com o Nmap: `nmap -O target` deve concordar com o seu palpite

**Desafios conhecidos:**

1. **Ambiguidade de TTL**
   - Problema: TTL 64 pode ser Linux (inicial=64) ou Windows (inicial=128, cruzou 64 saltos)
   - Dica: Use outros sinais para desambiguar ou faça uma sondagem com traceroute primeiro

2. **Mascaramento de virtualização**
   - Problema: VMs podem imitar diferentes SOs na camada IP
   - Dica: Combine com a análise de banner (strings de versão do kernel) para confirmação

**Critérios de sucesso:**
Sua implementação deve:

- [ ] Identificar corretamente Linux vs Windows vs macOS > 90% das vezes
- [ ] Distinguir versões principais (Windows 10 vs 11, CentOS 7 vs 8)
- [ ] Lidar com casos ambíguos com saída de "múltiplas possibilidades"
- [ ] Evitar falsos positivos (não dar palpites errados com confiança)
- [ ] Processar mais de 10 assinaturas de teste em < 5 segundos

## Desafios Especialistas

### Desafio 8: Engine de Escaneamento Completa Estilo Nmap

**O que construir:**
Uma engine de scanner de nível de produção que suporte múltiplos tipos de scan (SYN, ACK, FIN, Xmas, NULL), templates de temporização (Paranoid a Insane), detecção de SO, versionamento de serviço e scripting estilo NSE. Este é um projeto de várias semanas.

**Tempo estimado:**
4-6 semanas de desenvolvimento focado para uma implementação básica. 3-6 meses para qualidade de produção.

**Pré-requisitos:**
Você deve ter concluído os Desafios 1-7 primeiro, pois este se baseia no SYN scanning, detecção de versão, fingerprinting de SO e formatos de saída.

**O que você aprenderá:**

- Arquitetura de scanner de produção
- Técnicas de evasão de IDS
- Temporização de rede avançada e controle de congestionamento
- Sistemas de plugins extensíveis
- Casos extremos de rede do mundo real

**Planejando este recurso:**

Antes de codificar, pense sobre:

- Como a seleção do tipo de scan altera a criação do pacote? (Scans SYN vs FIN usam flags diferentes)
- Quais são as implicações de desempenho de mais de 10.000 operações concorrentes? (Limites de descritores de arquivo, memória)
- Como você migra de estados de porta simples para metadados de serviço ricos? (Mudança de esquema de banco de dados)
- Qual é o seu plano de rollback se os templates de temporização sobrecarregarem a rede? (Rate limiting, backoff adaptativo)

**Arquitetura de alto nível:**

```
┌──────────────────────────────────────┐
│       CLI / Configuração             │
│ (Tipo de scan, tempo, formato saída) │
└──────────────┬───────────────────────┘
               │
     ┌─────────┼─────────┐
     ▼         ▼         ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│SYN Scan │ │ACK Scan │ │FIN Scan │
│ Engine  │ │ Engine  │ │ Engine  │
└────┬────┘ └────┬────┘ └────┬────┘
     │           │           │
     └───────────┼───────────┘
                 ▼
     ┌───────────────────────┐
     │ Construtor de Pacotes │
     │ (Criação cabeçalho TCP)│
     └───────────┬───────────┘
                 │
     ┌───────────┼───────────┐
     ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌──────────┐
│  Timer  │ │Raw Sock │ │  Filtro  │
│ Engine  │ │ E/S     │ │  (BPF)   │
└─────────┘ └─────────┘ └──────────┘
```

**Fases de implementação:**

**Fase 1: Fundação** (1-2 semanas)

- Refatore o código existente em uma interface de engine de scan modular
- Abstraia a construção de pacotes (atualmente fixa para o connect scan)
- Implemente um registro de tipos de scan (mapeie nomes de scan para implementações)
- Crie um armazenamento de resultados unificado (banco de dados ou estrutura em memória)

**Fase 2: Tipos de Scan** (2-3 semanas)

- Implemente o SYN scan (Desafio 6)
- Adicione o FIN scan (envia FIN em vez de SYN, portas abertas não respondem)
- Adicione o Xmas scan (flags FIN+PSH+URG definidas, parece uma árvore de Natal no Wireshark)
- Adicione o NULL scan (nenhuma flag definida, a violação da RFC dispara respostas diferentes)
- Adicione o ACK scan (mapeamento de firewall, não detecção de estado de porta)

**Fase 3: Templates de Temporização** (1 semana)

- T0 Paranoid: atrasos de 5 minutos entre as sondagens (evasão de IDS, extremamente lento)
- T1 Sneaky: escaneamento serializado com pausas (evade detecção básica)
- T2 Polite: reduz a carga na rede (bom para sistemas de produção)
- T3 Normal: nosso padrão atual (equilíbrio entre velocidade e furtividade)
- T4 Aggressive: timeouts mais rápidos, mais paralelismo
- T5 Insane: velocidade máxima, assume rede local rápida

**Fase 4: Recursos Avançados** (1-2 semanas)

- Integre o fingerprinting de SO (Desafio 7)
- Adicione a detecção de versão de serviço (Desafio 5)
- Implemente formatos de saída (JSON, XML, grepable) (Desafio 4)
- Adicione a retomada de scan (salve o estado, reinicie scans interrompidos)

**Estratégia de teste:**

- **Testes unitários**: Simule respostas de rede para cada tipo de scan
- **Testes de integração**: Escaneie VMs de teste com configurações conhecidas
- **Testes de desempenho**: Escaneie 10.000 portas, meça o tempo e o uso de recursos
- **Testes de evasão**: Execute contra o IDS Snort, meça a taxa de detecção

**Desafios conhecidos:**

1. **Tratamento de Perda de Pacotes**
   - Problema: Scans UDP perdem pacotes, precisam de retransmissões
   - Dica: Backoff exponencial, limite máximo de retransmissões por porta

2. **Detecção de Congestionamento de Rede**
   - Problema: Escaneamento agressivo inunda a rede, descarta tráfego legítimo
   - Dica: Monitore a variância do RTT, recue quando a rede desacelerar

**Critérios de sucesso:**
Sua implementação deve:

- [ ] Suportar mais de 5 tipos de scan (SYN, ACK, FIN, Xmas, NULL)
- [ ] Implementar templates de temporização T0-T5 com diferenças de velocidade mensuráveis
- [ ] Lidar corretamente com a seleção do tipo de scan via flags CLI
- [ ] Detectar e se adaptar ao congestionamento da rede (taxa de descarte de pacotes)
- [ ] Passar em testes de comparação contra o Nmap em alvos idênticos
- [ ] Processar uma sub-rede /24 completa (254 hosts × 1000 portas) em < 10 minutos (T4)

### Desafio 9: Técnicas de Evasão de IDS

**O que construir:**
Implementar fragmentação, decoy scans, manipulação de porta de origem e randomização de temporização para evadir sistemas de detecção de intrusão.

**Tempo estimado:**
2-3 semanas (requer entender o funcionamento interno do IDS primeiro)

**Pré-requisitos:**
Concluir a implementação do SYN scan (Desafio 6), pois estas técnicas modificam o comportamento no nível do pacote.

**O que você aprenderá:**

- Como sistemas IDS como o Snort detectam scans
- Fragmentação e remontagem de IP
- Técnicas de spoofing e limitações
- O jogo de gato e rato entre atacantes e defensores

**Etapas de implementação:**

**Fase 1: Pesquisa de Assinaturas de Detecção de IDS** (3-5 horas)
Leia as regras do Snort para detecção de port scan:

```
alert tcp any any -> any any (flags:S; threshold: type both, track by_src, count 10, seconds 60; msg:"Possible SYN scan";)
```

Isso dispara com mais de 10 pacotes SYN para portas diferentes de uma única origem em 60 segundos. Nosso scanner excede isso facilmente.

**Fase 2: Fragmentação de Pacotes** (1 semana)
Divida os pacotes TCP SYN em múltiplos fragmentos IP:

```cpp
// Pacote normal: [Cabeçalho IP][Cabeçalho TCP][Opções]

// Fragmentado:
// Pacote 1: [Cabeçalho IP (MF=1, offset=0)][Cabeçalho TCP parcial]
// Pacote 2: [Cabeçalho IP (MF=0, offset=8)][Cabeçalho TCP restante][Opções]
```

Muitos IDSs antigos não conseguem remontar fragmentos, então eles perdem o scan. IDSs modernos lidam com isso, mas ainda é útil contra sistemas legados.

**Fase 3: Decoy Scanning** (4-5 dias)
Envie scans de IPs de origem falsos misturados com o seu IP real:

```
Scanner real: 10.0.0.100
Decoys: 10.0.0.50, 10.0.0.75, 10.0.0.125

O alvo vê pacotes SYN de:
10.0.0.50:12345 -> target:80
10.0.0.75:12346 -> target:80
10.0.0.100:12347 -> target:80  ← Scanner real
10.0.0.125:12348 -> target:80
```

O IDS vê o escaneamento vindo de múltiplas fontes e não consegue determinar qual é a real. Apenas você vê as respostas SYN-ACK (enviadas para o seu IP).

**Armadilhas:**

- Os IPs de decoy devem estar ativos (responder a pings) ou o alvo pode filtrar fontes "mortas"
- Muitos decoys = padrão de ataque óbvio
- O roteamento assimétrico quebra isso (o alvo pode responder por um caminho diferente)

**Fase 4: Randomização de Temporização** (2-3 dias)
Adicione jitter à temporização da sondagem:

```cpp
// Ruim: Intervalos regulares de 100ms
send_probe(); sleep(0.1);
send_probe(); sleep(0.1);

// Bom: Intervalos aleatórios entre 50-150ms
send_probe(); sleep(random(0.05, 0.15));
send_probe(); sleep(random(0.05, 0.15));
```

Derrota a detecção baseada em tempo (rajada de sondagens regulares = assinatura de scanner).

**Critérios de sucesso:**

- [ ] O conjunto de regras padrão do Snort não alerta sobre seus scans
- [ ] A fragmentação ignora IDSs básicos (teste com remontagem via tcpdump)
- [ ] Scans com decoy escondem seu IP real nos logs (confirmado via logs do alvo)
- [ ] A randomização derrota a detecção baseada em limite (o detector de rajada não dispara)

## Misture e Combine

Combine recursos para projetos maiores:

**Ideia de Projeto 1: Scanner de Segurança em Nuvem**

- Combine o Desafio 3 (múltiplos hosts) + Desafio 4 (saída JSON) + Desafio 5 (detecção de versão)
- Adicione integração com nuvem AWS/GCP (escaneie VPCs inteiras)
- Resultado: Alimente os resultados em funções lambda para verificação automatizada de CVE

**Ideia de Projeto 2: Dashboard de Monitoramento Contínuo**

- Desafio 2 (barras de progresso) + Desafio 4 (JSON) + UI web
- Execute scans periodicamente, armazene os resultados em um banco de dados
- Visualize as mudanças de portas ao longo do tempo (novas portas = potencial comprometimento)

## Desafios de Integração no Mundo Real

### Integrar com o Metasploit para Exploração Automatizada

**O objetivo:**
Após o escaneamento, lance automaticamente módulos do Metasploit contra serviços vulneráveis descobertos.

**O que você precisará:**

- Metasploit Framework instalado
- Acesso à API RPC para o msfconsole
- Detecção de versão implementada (Desafio 5)

**Plano de implementação:**

1. Saída dos resultados do scan com versões de serviço para JSON
2. Mapeie as versões de serviço para módulos do Metasploit (busca no banco de dados MSF)
3. Use o RPC do MSF para lançar exploits:

```ruby
   client = Msf::RPC::Client.new(...)
   client.call('module.execute', 'exploit', 'exploit/linux/ssh/...')
```

4. Colete os resultados da exploração

**Cuidado com:**

- Ética: Execute apenas em sistemas que você possui ou tem permissão por escrito para testar
- Falsos positivos: A detecção de versão não é perfeita, pode visar os sistemas errados
- Rate limiting: Não lance 100 exploits simultaneamente

### Implantar no AWS Lambda para Escaneamento Serverless

**O objetivo:**
Executar scans distribuídos a partir de funções Lambda em diferentes regiões.

**O que você aprenderá:**

- Padrões de arquitetura serverless
- Restrições de rede no Lambda (sem raw sockets)
- Distribuir o trabalho entre funções de nuvem

**Etapas:**

1. Empacote o scanner como um deployment Lambda (zip com dependências)
2. Configure a role IAM para acesso à rede
3. Dispare o Lambda com a lista de alvos (fila SQS)
4. Colete os resultados no S3 ou DynamoDB
5. Agregue a partir do processador de resultados do Lambda

**Checklist de produção:**

- [ ] Tratamento de erros para timeouts do Lambda (limite de 15 min)
- [ ] Configuração de VPC se estiver escaneando redes privadas
- [ ] Estimativa de custo (Lambda + transferência de dados pode ficar caro)
- [ ] Rate limiting para evitar sobrecarregar os alvos

## Desafios de Desempenho

### Desafio: Lidar com 100.000 Conexões Concorrentes

**O objetivo:**
Escanear 1000 hosts × 1000 portas cada = 1.000.000 de portas sem travar.

**Gargalo atual:**
Limites de descritores de arquivo. O Linux define como padrão 1024 arquivos abertos por processo. Nosso scanner cria socket + timer por porta = 2 FDs por operação concorrente. Com 100 threads, usamos ~200 FDs. Com 100.000, precisaríamos de 200.000 (impossível).

**Abordagens de otimização:**

**Abordagem 1: Aumentar o Limite de FD**

- Como: `ulimit -n 100000` (temporário), modifique `/etc/security/limits.conf` (permanente)
- Ganho: Suporta mais conexões concorrentes
- Tradeoff: Memória do kernel para rastrear FDs, ainda limitado pelo limite de todo o sistema

**Abordagem 2: Pooling e Reuso de Socket**

- Como: Feche os sockets imediatamente após os resultados, reutilize o FD
- Implementação: No handler de conclusão, feche o socket antes de chamar `scan()` novamente
- Ganho: Precisa apenas de FDs para sondagens ativas
- Tradeoff: Gerenciamento de ciclo de vida ligeiramente mais complexo

**Abordagem 3: Processamento em Lote Híbrido**

- Como: Escaneie em lotes de 10k portas, processe os resultados, escaneie o próximo lote
- Ganho: Uso de memória limitado
- Tradeoff: Não aproveita todo o potencial de concorrência

**Faça o benchmark:**

```bash
# Monitore o uso de FD
watch -n 0.1 'ls -l /proc/$(pgrep simplePortScanner)/fd | wc -l'

# Execute um scan grande
./simplePortScanner -i target -p 65535 -t 10000
```

Métricas alvo:

- O uso de FD permanece abaixo do limite do sistema
- Uso de memória < 1GB mesmo em alta concorrência
- O scan é concluído sem travamentos

### Desafio: Reduzir o Uso de Largura de Banda da Rede

**O objetivo:**
Cortar a largura de banda em 50% mantendo a precisão do scan.

**Faça o perfil primeiro:**

```bash
# Monitore a largura de banda
iftop -i eth0

# Uso atual: ~5 Mbps para 100 scans concorrentes
```

**Áreas comuns de otimização:**

- Reduzir o timeout de 2s para 1s (menos retransmissões em redes lentas)
- Apenas capturar banners para portas interessantes (80, 443, 22), não para cada porta aberta
- Implementar timeout adaptativo baseado em medições de RTT

## Desafios de Segurança

### Desafio: Implementar Detecção de Sequência de Port Knock

**O que implementar:**
Antes de escanear, bata em portas específicas em sequência para sinalizar um scanner "amigável" e evitar disparar alertas.

**Modelo de ameaça:**
Isso protege contra:

- IDS automatizado bloqueando o IP do seu scanner
- Irritação do administrador com testes de segurança legítimos
- Revelar sua atividade de escaneamento para revisores de log casuais

**Implementação:**

```cpp
void knock_sequence(const std::string& target, const std::vector<int>& sequence) {
    for (int port : sequence) {
        tcp::socket s(io);
        s.connect(tcp::endpoint(address, port));
        s.close();
        sleep(0.5);  // Atraso entre as batidas
    }
    // Agora execute o scan real
}

// Uso:
knock_sequence("target.com", {1234, 5678, 9012});  // Sequência secreta
```

**Testando a segurança:**

- Configure o servidor de destino com um daemon de port knock (knockd no Linux)
- Escaneie sem bater - deve ser bloqueado/registrado agressivamente
- Escaneie com a sequência de batidas - deve prosseguir sem alertas
- Verifique se os logs mostram comportamentos diferentes

### Desafio: Adicionar Marca d'água de Atribuição de Scan

**O objetivo:**
Tornar este projeto compatível com a divulgação responsável, incorporando a identidade do scanner nos pacotes.

**Modelo de ameaça:**
Isso protege contra:

- Seu scanner ser confundido com um atacante malicioso
- Dificuldade em identificar a fonte do escaneamento durante a resposta a incidentes
- Questões éticas com testes de segurança anônimos

**Implementação:**
Adicione uma opção TCP personalizada ou uma requisição de banner que identifique seu scanner:

```cpp
// A sondagem HTTP inclui o User-Agent
"GET / HTTP/1.1\r\n"
"Host: " + target + "\r\n"
"User-Agent: PortScanner-Learning-Project/1.0 (Educational; Contact: seu@email.com)\r\n"
"\r\n"
```

Agora, quando os administradores investigarem, os logs mostrarão claramente o escaneamento educacional com informações de contato.

## Ideias de Contribuição

Terminou um desafio? Compartilhe-o de volta:

1. **Faça um fork do repositório** (se este estivesse hospedado no GitHub)
2. **Implemente sua extensão** em uma nova branch: `git checkout -b feature/syn-scan`
3. **Documente-a** - Adicione uma seção a este arquivo explicando sua implementação
4. **Envie um PR** com:
   - Mudanças no código com comentários
   - Testes unitários, se aplicável
   - README.md atualizado mencionando o novo recurso
   - Exemplo de uso na documentação

Boas extensões podem ser mescladas ao projeto principal e ajudar futuros aprendizes.

## Desafie-se Ainda Mais

### Construa Algo Novo

Use os conceitos que você aprendeu aqui para construir:

- **Scanner de Vulnerabilidades** - Após o port scan, execute verificações de vulnerabilidades conhecidas (Heartbleed, ShellShock) nos serviços descobertos
- **Mapeador de Topologia de Rede** - Use traceroute + port scanning para visualizar a estrutura da rede e os limites do firewall
- **Monitor de Segurança Contínuo** - Escaneamento agendado com alertas quando novas portas abrirem (indicador de comprometimento)

### Estude Implementações Reais

Compare sua implementação com ferramentas de produção:

- **Nmap** - Leia o código fonte em https://github.com/nmap/nmap - veja como eles lidam com casos extremos que você não pensou
- **masscan** - Scanner assíncrono que pode escanear toda a internet (4 bilhões de IPs). Estude o rate limiting de pacotes deles.
- **ZMap** - Semelhante ao masscan, mas com arquitetura mais simples. Bom para aprender padrões de escaneamento de alto desempenho.

Leia o código deles, entenda seus tradeoffs, adapte as técnicas deles ao seu scanner.

### Escreva Sobre Isso

Documente sua extensão:

- Post em blog: "Construindo um SYN Scanner do Zero em C++"
- Tutorial: "Port Scanning 101: Da Teoria à Implementação"
- Comparação: "Connect Scan vs SYN Scan: Análise de Desempenho e Detecção"

Ensinar os outros força você a entender verdadeiramente os conceitos. Se você não consegue explicar de forma simples, você não entende bem o suficiente.

## Obtendo Ajuda

Travou em um desafio?

1. **Depure sistematicamente**
   - O que você esperava que acontecesse?
   - O que realmente aconteceu?
   - Qual é a menor mudança no código que reproduz o problema?

2. **Leia implementações existentes**
   - Como o Nmap lida com isso? (O código é aberto)
   - Veja exemplos do Boost.Asio para padrões assíncronos
   - Pesquise por "TCP SYN scan implementation C++" se estiver fazendo o Desafio 6

3. **Pesquise por problemas semelhantes**
   - Tag do Stack Overflow: [boost-asio]
   - Reddit: r/netsec, r/cpp
   - Issues do GitHub nos repositórios do Nmap/masscan

4. **Peça ajuda de forma construtiva**
   - Mostre o que você tentou: trechos de código, mensagens de erro
   - Explique seu entendimento: "Eu acho que isso deveria funcionar porque..."
   - Seja específico: "Os pacotes SYN não estão disparando respostas" em vez de "não funciona"

## Rastreador de Conclusão de Desafios

Acompanhe seu progresso:

- [ ] Desafio Fácil 1: Saída CSV
- [ ] Desafio Fácil 2: Indicador de Progresso
- [ ] Desafio Fácil 3: Múltiplos Hosts
- [ ] Desafio Intermediário 4: Saída JSON
- [ ] Desafio Intermediário 5: Detecção de Versão de Serviço
- [ ] Desafio Avançado 6: SYN Scan
- [ ] Desafio Avançado 7: Fingerprinting de SO
- [ ] Desafio Especialista 8: Engine de Scan Completa
- [ ] Desafio Especialista 9: Evasão de IDS

Concluiu todos eles? Você passou de um scanner de portas iniciante para uma ferramenta de reconhecimento de rede avançada. Você entende de E/S assíncrona, protocolos de rede e fundamentos de segurança em um nível profundo. É hora de construir algo inteiramente novo ou contribuir para ferramentas de segurança de código aberto como o Nmap ou o Metasploit.

&nbsp;

## Fim

<p align="center">
  <img src="../assets/cat.gif" width="300" alt="Cat">
</p>

Agora você chegou ao final de seu projeto. Se conseguiu realizar a maioria dos desafios, saiba que estará pronto para o que virá em seguida. **Parabéns!**

Minha recomendação agora é que você _se arrisque em mais um projeto disponível_, mas no seu tempo. Aliás, esse é o ponto mais forte de qualquer currículo ao lado das experiências: **os projetos**. Então, sem medo, quanto mais fizer, melhor.
