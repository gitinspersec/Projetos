# Conceitos de Segurança Fundamentais

Este documento explica os conceitos de segurança que você encontrará ao construir este projeto. Estes não são apenas definições, mas conhecimentos práticos usados diariamente em testes de invasão e segurança de rede.

## TCP Port Scanning

### O Que É

O escaneamento de portas (port scanning) é o processo de sondar um host de destino para determinar quais portas TCP ou UDP estão aceitando conexões. Cada número de porta (0-65535) pode ter um serviço escutando nela. O escaneamento revela qual software está rodando em um sistema sem exigir autenticação.

Pense nisso como verificar cada porta e janela de um edifício para ver quais estão destrancadas. As portas 1-1023 são portas "bem conhecidas" (well-known) atribuídas a serviços padrão (HTTP na 80, SSH na 22), enquanto portas mais altas podem rodar qualquer coisa.

### Por Que Isso Importa

O escaneamento de portas é o **reconhecimento**, a primeira fase da cyber kill chain. Todo teste de invasão, avaliação de vulnerabilidade e muitos ataques reais começam mapeando o que está acessível. A violação da Equifax em 2017 começou com um reconhecimento que encontrou um servidor Apache Struts não corrigido na porta 8080. Encontrar aquela porta aberta foi o passo número um.

No ataque da botnet Mirai em 2016, que derrubou o Dyn DNS, o malware escaneou toda a internet em busca de dispositivos IoT com telnet (porta 23) exposto. Ele encontrou centenas de milhares de câmeras e roteadores vulneráveis porque a porta 23 nunca deveria estar aberta em dispositivos de consumo voltados para a internet.

### Como Funciona

O escaneamento de portas TCP explora o mecanismo do handshake de três vias:

```
Scanner          Alvo
   |               |
   |----SYN------->|  (tentativa de conexão)
   |               |
   |<--SYN-ACK-----|  (porta está ABERTA - serviço escutando)
   |               |
   |----RST------->|  (scanner aborta, não completa o handshake)
```

ou

```
Scanner          Alvo
   |               |
   |----SYN------->|
   |               |
   |<---RST--------|  (porta está FECHADA - sem serviço, mas o host respondeu)
```

ou

```
Scanner          Alvo
   |               |
   |----SYN------->|
   |               |
   |   (silêncio)   |  (porta está FILTRADA - firewall descartou o pacote)
```

Nosso scanner envia um pacote SYN (requisição de conexão) e interpreta a resposta. A biblioteca Boost.Asio lida com os detalhes do handshake, mas entender o que acontece no fio é crucial.

### Ataques Comuns

1. **Reconhecimento total antes da exploração** - Atacantes escaneiam redes inteiras para construir bancos de dados de alvos. O ransomware WannaCry escaneou por SMB (porta 445) antes de lançar o exploit EternalBlue. O escaneamento de portas identificou máquinas vulneráveis.

2. **Ataques específicos de serviço** - Encontrar MySQL na porta 3306 exposto para a internet significa que o atacante pode tentar credential stuffing, SQL injection ou CVEs conhecidos específicos para servidores de banco de dados. Cada porta aberta estreita a superfície de ataque para categorias específicas de exploit.

3. **Fingerprinting de Firewall e IDS** - A diferença entre portas fechadas e filtradas revela regras de firewall. Se as portas 1-1000 retornam RST (fechadas), mas 1001-2000 expiram (filtradas), você sabe que há filtragem seletiva. Essa informação ajuda atacantes a identificar pontos cegos.

### Estratégias de Defesa

**Minimize portas expostas:** Abra apenas o que você realmente precisa. Instalações padrão frequentemente ativam serviços desnecessários. Execute `netstat -tuln` no Linux ou `netsh interface ipv4 show tcpconnections` no Windows para ver o que está escutando. Cada porta aberta é uma superfície de ataque potencial.

**Implemente regras de firewall adequadas:** Negue por padrão (default-deny) o tráfego de entrada, permita explicitamente apenas os serviços necessários. Nosso scanner detecta portas filtradas através de timeouts (`src/PortScanner.cpp:139-147`), portanto, um firewall adequado torna o reconhecimento mais difícil.

**Monitore atividades de escaneamento:** Múltiplas tentativas de conexão para portas sequenciais a partir de um IP de origem é escaneamento. Sistemas IDS como o Snort possuem regras específicas para detecção de port scan. O padrão de pacotes SYN sem completar os handshakes se destaca nos logs.

**Use port knocking ou autorização de pacote único:** Para SSH ou outros serviços de administração, exija uma sequência secreta de tentativas de conexão antes que a porta apareça como aberta. Isso esconde serviços críticos de escaneamentos casuais.

## Estados de Porta e Seu Significado

### O Que É

Cada porta em um sistema em rede existe em um de três estados sob a perspectiva de um scanner: aberta, fechada ou filtrada. Estes estados contam histórias fundamentalmente diferentes sobre o alvo.

### Por Que Isso Importa

O estado revela tanto a configuração do serviço quanto a postura de segurança:

- **Aberta (Open)**: Algo está escutando. Esta é a sua superfície de ataque. No ataque à cadeia de suprimentos da SolarWinds em 2020, os atacantes usaram credenciais roubadas para acessar um repositório de código interno. Eles o encontraram escaneando por portas de servidor git abertas (comumente 443 ou portas personalizadas para GitLab/GitHub Enterprise).

- **Fechada (Closed)**: O host está vivo e acessível, mas nada escuta naquela porta. Portas fechadas confirmam que o alvo existe e responde, ajudando no mapeamento da rede mesmo quando os serviços não estão expostos.

- **Filtrada (Filtered)**: Um firewall ou filtro de pacotes está entre você e o alvo. Isso diz aos atacantes que existe uma infraestrutura de segurança, mas também pode revelar fraquezas de configuração se algumas portas estiverem filtradas e outras não.

### Como Funciona

Nosso scanner implementa a detecção de estado em `src/PortScanner.cpp:123-165`:

**Detecção de porta aberta** (`PortScanner.cpp:138-151`):

```cpp
socket->async_connect(endpoint, [](boost::system::error_code ec) {
    if (!ec) {
        // Conexão bem-sucedida = OPEN
        // Tentar capturar banner
    }
});
```

Se o `async_connect` for concluído sem erro, o handshake TCP foi bem-sucedido. Algo aceitou nossa conexão.

**Detecção de porta fechada** (`PortScanner.cpp:153-158`):

```cpp
else {
    // Conexão falhou = CLOSED
    printf("%i\t%sCLOSED%s\t%s\t%s\n", port, RED, RESET, ...);
}
```

Se o `async_connect` retornar um erro rapidamente (geralmente "connection refused"), o host nos enviou um pacote RST. A porta está fechada.

**Detecção de porta filtrada** (`PortScanner.cpp:128-137`):

```cpp
timer->async_wait([](boost::system::error_code ec) {
    if (!ec && !*complete) {
        // Timer expirou antes da conexão = FILTERED
        printf("%i\t%s\t%s\t%s\n", port, "FILTERED", ...);
    }
});
```

Se nem o sucesso nem o erro ocorrerem dentro do timeout (padrão de 2 segundos), assumimos que um firewall descartou nossos pacotes. A tentativa de conexão simplesmente trava até desistirmos.

### Armadilhas Comuns

**Erro 1: Confundir fechada com filtrada**

```cpp
// Errado - expirar o tempo não significa fechada
if (connection_timeout) {
    state = "CLOSED";  // Não! Isso é FILTERED
}

// Correto - fechada é uma rejeição ativa
if (error_code == "connection_refused") {
    state = "CLOSED";
}
```

Fechada significa que o host rejeitou você ativamente. Filtrada significa que seus pacotes desapareceram em um firewall. Esta distinção é importante para entender a topologia da rede.

**Erro 2: Não lidar com falsos positivos**
Alguns hosts possuem firewalls que enviam pacotes RST para parecerem fechados mesmo quando estão filtrados. Escaneamentos avançados precisam de múltiplas técnicas de sondagem (scans SYN, ACK, FIN) para distinguir estes casos limítrofes. Nosso scanner simples aceita as respostas pelo seu valor nominal.

## Banner Grabbing

### O Que É

Banner grabbing significa conectar-se a um serviço e ler qualquer mensagem inicial que ele envie. Muitos protocolos se anunciam imediatamente após a conexão. Servidores SSH dizem "SSH-2.0-OpenSSH_8.2p1", servidores web enviam cabeçalhos HTTP com "Server: Apache/2.4.41", e assim por diante.

### Por Que Isso Importa

Banners de serviço vazam informações de versão que atacantes usam para seleção de exploits. Se o seu banner SSH diz "OpenSSH_7.4", eu posso verificar bancos de dados CVE por vulnerabilidades conhecidas naquela versão exata. O ataque Heartbleed de 2014 (CVE-2014-0160) afetou OpenSSL 1.0.1 até 1.0.1f. O banner grabbing informou aos atacantes quais servidores estavam vulneráveis.

Os ataques ao Microsoft Exchange Server de 2021 (ProxyLogon) visaram versões específicas do Exchange. Atacantes escanearam por servidores Exchange, capturaram banners para identificar versões e então lançaram exploits direcionados. A informação de versão transformou um escaneamento genérico em um ataque de precisão.

### Como Funciona

Após conectar-se com sucesso a uma porta aberta, tentamos ler os dados iniciais:

```cpp
// src/PortScanner.cpp:143-149
socket->async_read_some(boost::asio::buffer(*buf),
    [](boost::system::error_code ec, std::size_t n) {
        if (!ec && n > 0) {
            banner->assign(buf->data(), n);
        }
        printf("%i\tOPEN\t%s\t%s\n", port, service.c_str(), banner->c_str());
    });
```

Alocamos um buffer de 128 bytes e tentamos uma leitura não bloqueante. Se o serviço enviar qualquer coisa imediatamente, nós a capturamos. Caso contrário (muitos serviços esperam pela entrada do cliente primeiro), prosseguimos sem um banner. Esta é uma captura passiva - não enviamos sondagens específicas de protocolo.

Alguns serviços exigem que você fale o protocolo deles primeiro. Servidores HTTP precisam que você envie "GET / HTTP/1.1" antes de responderem. Nosso scanner apenas escuta, o que funciona para serviços "falantes" como SSH, SMTP e FTP que se anunciam.

### Ataques Comuns

1. **Direcionamento de exploit específico de versão** - Após encontrar MySQL na porta 3306 e capturar "5.5.62-0ubuntu0.14.04.1", atacantes pesquisam no Exploit-DB por vulnerabilidades do MySQL 5.5.x. O banner grabbing transforma a descoberta genérica de portas em um mapeamento preciso de vulnerabilidades.

2. **Identificação de software desatualizado** - Qualquer servidor anunciando uma versão de 2015 provavelmente é vulnerável a múltiplos CVEs. Atacantes priorizam estes alvos. Em 2017, o Shadow Brokers vazou exploits da NSA especificamente vinculados à detecção de versão do Windows que vinham de banners SMB.

3. **Fingerprinting para movimentação lateral** - Dentro de uma rede, o banner grabbing revela a infraestrutura. Encontrar "VMware ESXi 6.0" na porta 443 diz a um atacante que este é um host de virtualização que vale a pena comprometer (um host ESXi controla muitas VMs).

### Estratégias de Defesa

**Suprima informações de versão em banners:** A maioria dos serviços permite que você personalize o que eles anunciam. A configuração do SSH tem `DebianBanner no`, o Apache tem `ServerTokens Prod` e o Nginx tem `server_tokens off`. Não anuncie sua versão exata.

**Use mensagens de erro genéricas:** Não deixe que os erros da sua aplicação vazem versões de framework. "Erro 500" é melhor do que "Ruby on Rails 5.2.3 - NoMethodError in UsersController#create".

**Implemente randomização de banner ou honeypots:** Configurações avançadas randomizam strings de banner ou anunciam versões vulneráveis falsas para desperdiçar o tempo do atacante. Se o seu banner SSH afirma ser de 2012, mas você está totalmente corrigido, os scanners marcarão você como um alvo fácil enquanto você detecta as sondagens deles.

## Como Estes Conceitos se Relacionam

Escaneamento de portas, detecção de estado e banner grabbing formam um pipeline de reconhecimento:

```
Port Scan
    ↓
Identifica portas ABERTAS
    ↓
Banner Grab
    ↓
Revela versões de serviço
    ↓
Mapeamento de Vulnerabilidades
    ↓
Exploração
```

Cada passo se baseia no anterior. Você não pode capturar banners sem encontrar portas abertas primeiro. Você não pode identificar vulnerabilidades sem saber as versões. Entender esta cadeia ajuda tanto atacantes (que a executam) quanto defensores (que devem quebrá-la).

## Padrões e Frameworks da Indústria

### OWASP Top 10

Este projeto se relaciona com:

- **A05:2021 – Configuração Incorreta de Segurança** - Portas abertas desnecessárias são configurações incorretas. Cada serviço exposto que não precisa ser público aumenta a superfície de ataque. O escaneamento de portas identifica estes erros.

- **A01:2021 – Quebra de Controle de Acesso** - Serviços escutando em interfaces públicas quando deveriam ser apenas localhost representam quebra de controle de acesso. O escaneamento revela estas falhas arquiteturais.

### MITRE ATT&CK

Técnicas relevantes:

- **T1046 - Network Service Discovery** - O escaneamento de portas é explicitamente listado como uma técnica para descobrir serviços. Nossa ferramenta implementa diretamente este método de reconhecimento.

- **T1595.001 - Active Scanning: Scanning IP Blocks** - Ferramentas automatizadas escaneiam intervalos de IP para encontrar alvos. Este projeto demonstra como tais ferramentas funcionam no nível de implementação.

### CWE

Enumerações de fraquezas comuns cobertas:

- **CWE-200 - Exposição de Informações Sensíveis a um Ator Não Autorizado** - O banner grabbing explora serviços que revelam informações de versão. Corrigir a CWE-200 significa sanitizar os banners.

- **CWE-1188 - Inicialização Padrão Insegura de Recurso** - Instalações padrão frequentemente abrem portas desnecessárias. Escaneamentos de portas encontram estas exposições não intencionais.

## Exemplos do Mundo Real

### Estudo de Caso 1: A Botnet Mirai (2016)

A botnet de IoT Mirai escravizou centenas de milhares de dispositivos escaneando toda a internet por telnet (porta 23) e SSH (porta 22) com credenciais padrão. A sequência de ataque foi:

1. Escanear endereços IP aleatórios por portas 23/22 abertas (descoberta de serviço de rede)
2. Capturar banners telnet para identificar tipos de dispositivos (alguns dispositivos IoT anunciam números de modelo)
3. Tentar credenciais padrão (admin/admin, root/root) baseadas nos fingerprints dos dispositivos
4. Instalar malware e juntar-se à botnet

O ataque DDoS ao Dyn DNS que derrubou Twitter, Netflix e Reddit em outubro de 2016 veio de dispositivos infectados pela Mirai. Isso começou com escaneamento de portas. A infecção se espalhou porque dispositivos IoT de consumo eram enviados com telnet ativado e senhas padrão inalteráveis.

**Como isso poderia ter sido evitado:** Fabricantes deveriam ter desativado o telnet por padrão, exigido mudanças de senha no primeiro boot e implementado detecção de port scan que coloca scanners automaticamente em uma lista de bloqueio. ISPs poderiam ter filtrado o tráfego de saída da porta 23 de redes de consumo.

### Estudo de Caso 2: Ataque à Cadeia de Suprimentos da SolarWinds (2020)

Embora o comprometimento inicial tenha ocorrido através de uma atualização de software com trojan, os atacantes usaram escaneamento de portas durante a movimentação lateral dentro das redes das vítimas. Após obter o acesso inicial, eles:

1. Escanearam redes internas por portas de gerenciamento comuns (3389 para RDP, 5985 para WinRM)
2. Identificaram servidores de Active Directory (portas 88, 389, 636)
3. Encontraram sistemas de backup e ferramentas de segurança para desativá-los
4. Mapearam a arquitetura da rede correlacionando portas abertas em sub-redes

Os atacantes passaram meses dentro das redes, escaneando e documentando metodicamente a infraestrutura antes de exfiltrar dados. O escaneamento de portas foi sua ferramenta de criação de mapas.

**Como isso poderia ter sido evitado:** Segmentação de rede com regras rígidas de firewall entre zonas, monitoramento de escaneamento de portas interno (análise de tráfego leste-oeste) e implantação de tecnologia de decepção (serviços falsos em portas honeypot que alertam quando escaneados).

## Testando Seu Entendimento

Antes de passar para a arquitetura, certifique-se de que você consegue responder:

1. **Por que nosso scanner usa timeouts para detectar portas filtradas em vez de apenas esperar por pacotes RST?** (Dica: o que acontece com pacotes que atingem um firewall configurado com DROP em vez de REJECT?)

2. **Se você escanear um servidor web na porta 80 e capturar o banner "Server: Apache/2.4.41 (Ubuntu)", quais informações específicas você aprendeu que ajudam um atacante?** (Pense sobre SO, versão de software e vulnerabilidades potenciais.)

3. **Explique por que portas fechadas ainda fornecem informações de reconhecimento úteis, mesmo que nenhum serviço esteja rodando.** (O que uma resposta RST diz a você sobre o alvo?)

Se estas perguntas parecerem obscuras, releia as seções relevantes. A implementação fará mais sentido quando você entender o que cada estado de porta significa e por que o banner grabbing importa para ataques reais.

## Leitura Adicional

**Essencial:**

- **RFC 793 - Especificação TCP** - A RFC original do TCP explica o handshake de três vias e o comportamento do RST. A Seção 3.4 cobre o estabelecimento de conexão. Entender isso torna a teoria do escaneamento de portas clara.

- **Nmap Network Scanning por Gordon Lyon** - O livro definitivo sobre técnicas de escaneamento de portas. Os capítulos 3-5 cobrem métodos de escaneamento TCP, incluindo scans SYN, connect e ACK. Disponível gratuitamente em nmap.org/book/.

**Aprofundamentos:**

- **IANA Service Name and Transport Protocol Port Number Registry** - Lista oficial de portas registradas e seus serviços. Quando nosso scanner mostra "SSH" para a porta 22, é daqui que vem esse mapeamento: iana.org/assignments/service-names-port-numbers/.

- **Documentação de regras do Snort IDS** - As regras 1-1999 cobrem detecção de scan. Ler estas regras mostra quais padrões disparam alertas e como evadir IDSs básicos: snort.org/rules.

**Contexto histórico:**

- **Phrack Issue 49 (1996) - The Art of Port Scanning** - Artigo original de Fyodor introduzindo técnicas de escaneamento furtivo. Embora datado, ele explica a teoria fundamental que as ferramentas modernas ainda usam.
