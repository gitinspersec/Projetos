# Analisador de Tráfego de Rede

## O Que É Isso

Uma ferramenta de captura e análise de pacotes baseada em Python que monitora o tráfego de rede em tempo real, identifica protocolos, rastreia o uso de largura de banda e gera relatórios visuais. Construída com Scapy para captura de pacotes, Rich para saída no terminal e Matplotlib para gráficos.

## Por Que Isso Importa

A visibilidade da rede é a base do monitoramento de segurança. Se você não consegue ver o que está acontecendo em sua rede, não consegue detectar intrusões, exfiltração de dados ou violações de políticas. Este projeto ensina como a captura de pacotes realmente funciona no nível do kernel, não apenas como executar o Wireshark.

**Cenários do mundo real onde isso se aplica:**

- **Resposta a incidentes:** Durante a violação da Target em 2013, o monitoramento de rede poderia ter detectado conexões incomuns entre sistemas de PDV e servidores externos. A análise em nível de pacote mostra quais dados estão saindo da sua rede e para onde estão indo.

- **Solução de problemas de desempenho:** Quando as aplicações ficam lentas, as capturas de pacotes revelam se o problema é latência de rede, retransmissões ou problemas no nível da aplicação. Equipes de rede usam essas ferramentas diariamente para diagnosticar problemas de conectividade.

- **Linha de base de segurança:** Você não consegue detectar anomalias sem saber como é o normal. Analisadores de pacotes estabelecem padrões de tráfego de linha de base, mostrando distribuições típicas de protocolos, uso de largura de banda e padrões de comunicação em sua rede.

## O Que Você Aprenderá

Este projeto ensina como a captura de pacotes de rede funciona no nível do sistema. Ao construí-lo você mesmo, você entenderá:

**Conceitos de Segurança:**

- **Acesso a raw sockets** - Por que a captura de pacotes requer privilégios de root/administrador, o que o CAP_NET_RAW faz no Linux e como o BPF (Berkeley Packet Filter) permite a filtragem eficiente no nível do kernel sem copiar cada pacote para o espaço do usuário.

- **Inspeção de camadas de protocolo** - Como dissecar pacotes da Camada 2 (quadros Ethernet com endereços MAC) até a Camada 7 (requisições HTTP), entendendo quais informações existem em cada camada e por que os atacantes visam camadas específicas.

- **Estabelecimento de linha de base de rede** - Construção de perfis estatísticos de tráfego normal para identificar anomalias. Você rastreará distribuições de protocolos, padrões de largura de banda e comportamento de endpoints que as equipes de segurança usam para detecção de ameaças.

**Habilidades Técnicas:**

- **Padrões de threading produtor-consumidor** - Implementação de processamento de pacotes seguro para threads (thread-safe), onde uma thread captura pacotes na velocidade da rede enquanto outra os analisa sem perder dados. Você usará Queue e threading.Lock do Python para sincronização.

- **Filtragem de pacotes no nível do kernel** - Escrita de filtros BPF que rodam no kernel para descartar pacotes indesejados de forma eficiente antes que cheguem ao espaço do usuário. É assim que sistemas de monitoramento de produção lidam com gigabits de tráfego sem sobrecarregar a CPU.

- **Coleta de dados de séries temporais** - Amostragem de largura de banda e taxas de pacotes em intervalos regulares para construir gráficos que mostram padrões de tráfego ao longo do tempo. Crítico para detectar ataques DDoS ou transferências de dados incomuns.

**Ferramentas e Técnicas:**

- **Manipulação de pacotes com Scapy** - Uso da biblioteca de criação de pacotes mais poderosa do Python para capturar e dissecar o tráfego de rede. Você trabalhará com o sistema de camadas do Scapy para extrair endereços IP, portas, tipos de protocolo e dados de carga útil de pacotes brutos.

- **Interfaces de terminal com Rich** - Construção de dashboards em tempo real que atualizam durante a captura de pacotes, mostrando distribuições de protocolos, principais emissores e uso de largura de banda com tabelas coloridas e indicadores de progresso.

- **Visualização com Matplotlib** - Geração de gráficos de pizza de distribuição de protocolos, cronogramas de largura de banda e gráficos de barras dos principais emissores a partir de dados de captura de pacotes. As mesmas visualizações que analistas de SOC usam para apresentar o comportamento da rede.

## Pré-requisitos

Antes de começar, você deve entender:

**Conhecimento necessário:**

- **Básico de Python** - Você precisa ler código usando dataclasses, type hints, padrões async/await e gerenciadores de contexto. Se `with open() as f:` ou `async def function():` parecerem desconhecidos, revise os fundamentos do Python primeiro.

- **Redes TCP/IP** - Saber o que é um endereço IP, entender a diferença entre TCP e UDP, reconhecer portas comuns (80 para HTTP, 443 para HTTPS, 53 para DNS). Você deve ser capaz de explicar o que um handshake de três vias faz.

- **Conforto com linha de comando** - Esta é uma ferramenta CLI. Você executará comandos em um terminal, passará argumentos, definirá variáveis de ambiente e lerá a saída. Navegação básica no shell (cd, ls, cat) é assumida.

**Ferramentas necessárias:**

- **Python 3.14+** - O projeto usa recursos modernos do Python, como match statements e type hints aprimorados. Versões anteriores não funcionarão.

- **Acesso root/admin** - A captura de pacotes requer permissões de raw socket. No Linux, você precisa de root ou da capability CAP_NET_RAW. No macOS, você precisa de root ou acesso aos dispositivos /dev/bpf. No Windows, você precisa de privilégios de Administrador e do Npcap instalado.

- **Scapy, Rich, Matplotlib** - Instale via pip. O Scapy faz a captura de pacotes, o Rich torna a saída do terminal bonita e o Matplotlib gera os gráficos.

**Útil, mas não obrigatório:**

- **Experiência com Wireshark** - Se você já usou o Wireshark para analisar arquivos pcap, reconhecerá conceitos como hierarquias de protocolos, expressões de filtro e rastreamento de conversas. Mas não é necessário.

- **Programação de sistemas** - Entender como as chamadas de sistema funcionam, o que o kernel faz versus o espaço do usuário e por que as trocas de contexto são caras ajudará você a apreciar as escolhas de arquitetura. Não é obrigatório para construir o projeto.

## Início Rápido

Coloque o projeto para rodar localmente:

```bash
# Navegue até o diretório do projeto
cd RedTeam/Team/c-Net_Analyzer

# Instale as dependências
pip install -e .

# Liste as interfaces de rede disponíveis
sudo netanal interfaces

# Capture 50 pacotes em sua interface de loopback
sudo netanal capture -i lo -c 50 --verbose

# Analise um arquivo pcap existente
netanal analyze traffic.pcap --top-talkers 20

# Gere gráficos a partir dos dados capturados
netanal chart traffic.pcap --type all -d ./charts/
```

Saída esperada: Você verá um fluxo de pacotes em tempo real mostrando IPs de origem/destino, protocolos e tamanhos de pacotes. Quando a captura terminar, você receberá estatísticas de resumo mostrando a distribuição de protocolos, os principais emissores por volume de tráfego e gráficos de largura de banda.

## Estrutura do Projeto

```
network-traffic-analyzer/
├── src/netanal/
│   ├── capture.py        # Engine de captura de pacotes produtor-consumidor
│   ├── analyzer.py       # Identificação de protocolo e parsing de pacotes
│   ├── filters.py        # Construtor de filtro BPF com validação
│   ├── statistics.py     # Coletor de estatísticas thread-safe
│   ├── models.py         # Estruturas de dados (PacketInfo, Protocol enum)
│   ├── visualization.py  # Geração de gráficos Matplotlib
│   ├── export.py         # Exportação de dados JSON/CSV
│   ├── output.py         # Formatação de console Rich
│   ├── main.py           # Definições de comando Typer CLI
│   ├── constants.py      # Valores de configuração
│   └── exceptions.py     # Hierarquia de exceções personalizadas
├── tests/
│   ├── test_filters.py   # Testes do construtor de filtro BPF
│   └── test_models.py    # Testes de modelo de dados
└── pyproject.toml        # Dependências e metadados do projeto
```

## Próximos Passos

1. **Entenda os conceitos** - Leia [01-CONCEPTS.md](./01-CONCEPTS.md) para aprender sobre captura de pacotes, análise de protocolos e fundamentos de monitoramento de rede.
2. **Estude a arquitetura** - Leia [02-ARCHITECTURE.md](./02-ARCHITECTURE.md) para ver o padrão produtor-consumidor e o design thread-safe.
3. **Percorra o código** - Leia [03-IMPLEMENTATION.md](./03-IMPLEMENTATION.md) para explicações detalhadas do código com números de linha.
4. **Estenda o projeto** - Leia [04-CHALLENGES.md](./04-CHALLENGES.md) para ideias como adicionar remontagem de fluxo TCP ou detecção de anomalias.

## Problemas Comuns

**Permissão negada ao capturar pacotes**

```
PermissionError: [Errno 1] Operation not permitted
```

Solução: A captura de pacotes requer privilégios de root. Execute com `sudo netanal capture` ou adicione a capability CAP_NET_RAW ao seu binário Python no Linux: `sudo setcap cap_net_raw+ep $(which python3)`

**Npcap não instalado (apenas Windows)**

```
NpcapNotFoundError: Npcap is not installed
```

Solução: Baixe e instale o Npcap de https://npcap.com. Este é o driver de captura de pacotes do Windows. O WinPcap está obsoleto e não funcionará com o Scapy moderno.

**Nenhum pacote capturado na interface wireless**

```
Total Packets: 0
```

Solução: Muitos adaptadores wireless não suportam o modo promíscuo, ou seu SO o bloqueia. Tente capturar na interface de loopback (`lo` no Linux/Mac, `Loopback Pseudo-Interface 1` no Windows) primeiro para verificar se a ferramenta funciona. Para wireless, você pode precisar do modo monitor, que requer ferramentas diferentes.
