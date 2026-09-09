# Guia de Implementação

Este documento percorre o código real, explicando como o escaneamento de portas assíncrono funciona internamente e destacando as partes complexas que fazem a E/S concorrente funcionar corretamente.

## Passo a Passo da Estrutura de Arquivos

```
simple-port-scanner/
├── src/
│   ├── PortScanner.hpp     # Definição da classe: variáveis de membro, primitivas de E/S assíncrona, assinaturas de métodos
│   └── PortScanner.cpp     # Implementação: lógica de scan assíncrono, handlers de conclusão, banner grabbing
├── main.cpp                # Ponto de entrada: parsing de CLI, inicialização do scanner, chamada run() bloqueante
└── CMakeLists.txt          # Configuração de build: padrão C++20, dependência Boost com program_options
```

## Construindo a Interface CLI

### Passo 1: Parsing de Argumentos

O que estamos construindo: Interface de linha de comando amigável com padrões sensatos

Crie ou examine o `main.cpp`:

```cpp
// main.cpp:7-17
po::options_description desc("Allowed options");
desc.add_options()
    ("help,h", "produce help message")
    ("dname,i", po::value<std::string>()->default_value("127.0.0.1"), "set domain name or IP address")
    ("ports,p", po::value<std::string>()->default_value("1-1024"), "set a port range from 1 to n")
    ("threads,t", po::value<int>()->default_value(100), "max concurrent threads")
    ("expiry_time,e", po::value<uint8_t>()->default_value(2)->value_name("sec"), "timeout in seconds")
    ("verbose,v", "verbose output");
```

**Por que este código funciona:**

- `po::value<T>()->default_value(X)`: Parsing de parâmetros type-safe com validação automática. Se o usuário passar "-t hello", o Boost lança uma exceção em vez de travar.
- Formas de opção curta e longa (`-i` e `--dname`): A convenção padrão Unix faz a ferramenta parecer profissional.
- `uint8_t` para expiry_time: Aplica o intervalo de 0-255 segundos. Timeouts acima de 4 minutos não fazem sentido para escaneamento de portas.

**Erros comuns aqui:**

```cpp
// Errado - sem padrões significa parâmetros obrigatórios
desc.add_options()
    ("dname", po::value<std::string>(), "IP address");

// O usuário deve SEMPRE fornecer -i, o que é irritante para testar o localhost

// Correto - padrões tornam a ferramenta utilizável sem memorizar flags
desc.add_options()
    ("dname", po::value<std::string>()->default_value("127.0.0.1"), "IP address");
```

### Passo 2: Exibindo a Ajuda

Agora precisamos fornecer um texto de ajuda útil com exemplos.

No `main.cpp` (linhas 23-34):

```cpp
if (vm.count("help")) {
    std::cout << desc << "\n";
    std::cout << "Examples:\n"
          << "  Scan common ports on localhost:\n"
          << "    ./port_scanner -i 127.0.0.1 -p 1-1024\n\n"
          << "  Full TCP port scan:\n"
          << "    ./port_scanner -i 192.168.1.1 -p 65535 -t 200\n\n"
          << "  Postscriptum:\n"
          << "  Scan only systems you own or have explicit permission to test.\n";
    return 0;
}
```

**O que está acontecendo:**

1. Verifica se o usuário passou a flag `-h` ou `--help`
2. Imprime as descrições de opções geradas automaticamente a partir de `desc`
3. Adiciona exemplos de uso concretos (crucial - as pessoas aprendem com exemplos, não com descrições abstratas)
4. Inclui um aviso legal/ético (obrigatório para ferramentas de segurança)

**Por que fazemos desta forma:**
O Boost.Program_Options gera descrições automaticamente, mas os exemplos devem ser manuais. Os usuários copiam e colam exemplos para aprender, por isso fornecemos cenários realistas (portas comuns, scan completo, timeout personalizado).

**Abordagens alternativas:**

- Formato de man page: Mais formal, mas requer a manutenção de documentação separada
- Prompts interativos: Mais amigáveis para iniciantes, mas irritantes para scripters que desejam ferramentas não interativas

### Passo 3: Passando a Configuração para o Scanner

Extraia os argumentos validados e inicialize o scanner:

```cpp
// main.cpp:36-40
std::string ip = vm["dname"].as<std::string>();
std::string port = vm["ports"].as<std::string>();
int threads = vm["threads"].as<int>();
uint8_t expiry_time = vm["expiry_time"].as<uint8_t>();

PortScanner scanner;
scanner.set_options(ip, port, threads, expiry_time);
```

Este padrão (construtor padrão + `set_options`) permite reutilizar um objeto scanner para múltiplos escaneamentos. Uma alternativa seria passar tudo para o construtor, mas isso é menos flexível para uso interativo.

## Construindo o Núcleo do Scanner

### O Algoritmo de Escaneamento

Arquivo: `src/PortScanner.cpp`

O coração do scanner é o método `scan()`, que implementa um padrão assíncrono de autoagendamento:

```cpp
// PortScanner.cpp:123-165
void PortScanner::scan() {
    if (q.empty() || cnt >= MAX_THREADS) return;  // Sair se não houver trabalho ou se estiver no limite de threads

    uint16_t port = q.front();
    q.pop();
    ++cnt;  // Incrementa a contagem de workers ativos

    auto socket = std::make_shared<tcp::socket>(io);
    auto timer = std::make_shared<boost::asio::steady_timer>(io);
    auto complete = std::make_shared<bool>(false);  // Flag para condição de corrida

    tcp::endpoint endpoint(this->endpoint.address(), port);

    timer->expires_after(std::chrono::seconds(expiry_time));

    // Handler do timer - disputa contra a conexão
    timer->async_wait(boost::asio::bind_executor(strand,
        [this, complete, socket, port](boost::system::error_code ec) {
            if (!ec && !*complete)  {
                *complete = true;
                socket->close();
                printf("%i\t%s\t%s\t%s\n", port, "FILTERED", "NULL", "NULL");
                ++filtered_ports;
                --cnt;
                scan();  // Pega recursivamente a próxima porta
            }
        }));

    // Handler de conexão - disputa contra o timer
    socket->async_connect(endpoint, boost::asio::bind_executor(strand,
        [this, socket, timer, port, complete](boost::system::error_code ec) {
            if (*complete) return;  // Perdeu a disputa, o timer já disparou
            *complete = true;
            timer->cancel();  // Venceu a disputa, para o timer

            std::string service = "---";
            auto banner = std::make_shared<std::string>("---");

            // Procura o nome do serviço
            auto it = basicPorts.find(port);
            if (it != basicPorts.end()) {
                service = it->second;
            }

            if (!ec) {
                // Conexão bem-sucedida - porta está OPEN
                auto buf = std::make_shared<std::array<char, 128>>();

                socket->async_read_some(boost::asio::buffer(*buf),
                    boost::asio::bind_executor(strand,
                    [this, port, buf, banner, service](boost::system::error_code ec, std::size_t n) {
                        if (!ec && n > 0) {
                            banner->assign(buf->data(), n);
                        }
                        printf("%i\t%sOPEN%s\t%s\t%s\n", port, GREEN, RESET, service.c_str(), banner->c_str());
                        ++open_ports;
                        --cnt;
                        scan();  // Próxima porta
                    }));
            } else {
                // Conexão falhou - porta está CLOSED
                printf("%i\t%sCLOSED%s\t%s\t%s\n", port, RED, RESET, service.c_str(), banner->c_str());
                ++closed_ports;
                --cnt;
                scan();  // Próxima porta
            }
        }));
}
```

**Partes principais explicadas:**

**Cláusula de guarda** (`linha 123-124`):

```cpp
if (q.empty() || cnt >= MAX_THREADS) return;
```

Isso evita a criação de workers infinitos. Se a fila estiver vazia, terminamos. Se estivermos no limite de threads, não inicia outro scan mesmo que restem portas (os workers que já estão rodando eventualmente chamarão `scan()` novamente).

**Gerenciamento de tempo de vida de shared pointer** (`linhas 125-127`):

```cpp
auto socket = std::make_shared<tcp::socket>(io);
auto timer = std::make_shared<boost::asio::steady_timer>(io);
auto complete = std::make_shared<bool>(false);
```

Estes objetos devem sobreviver à operação assíncrona. Capturar shared pointers em closures lambda incrementa as contagens de referência, mantendo os objetos vivos até que os handlers de conclusão terminem. Sem isso, o socket/timer poderia ser destruído enquanto as operações assíncronas estivessem pendentes (use-after-free).

**Coordenação de disputa com flag de conclusão** (`linha 127, 131, 139`):

```cpp
auto complete = std::make_shared<bool>(false);

// No handler do timer:
if (!ec && !*complete) {
    *complete = true;  // Eu venci!
    socket->close();
    // ...
}

// No handler de conexão:
if (*complete) return;  // Eu perdi, o timer já venceu
*complete = true;  // Eu venci!
timer->cancel();
```

Ambos os handlers verificam e definem `complete` atomicamente (protegidos pela strand). Aquele que disparar primeiro define a flag, e o perdedor retorna antecipadamente. Isso evita o processamento duplo da mesma porta.

**Distribuição de trabalho por recursão de cauda** (`linhas 136, 151, 158`):
Cada handler de conclusão termina com `scan()`. Isso implementa um padrão de work-stealing — assim que uma porta termina, aquele worker pega a próxima porta da fila. Nenhum despachante central é necessário.

**Por que esta implementação específica:**

A disputa entre timer/socket resolve elegantemente a detecção de portas filtradas. Sem o timer, esperaríamos indefinidamente em portas filtradas (o firewall descarta pacotes, sem resposta). O timer dispara após `expiry_time` segundos se o socket não tiver conectado, marcando a porta como filtrada.

As chamadas recursivas de `scan()` significam que nunca criamos mais operações assíncronas do que `MAX_THREADS`. Iniciamos `MAX_THREADS` scans, e cada conclusão cria exatamente um novo scan, mantendo a concorrência constante.

**Erros comuns aqui:**

```cpp
// Errado - causaria vazamento se a operação assíncrona falhasse
tcp::socket socket(io);  // Alocado na pilha
timer->async_wait([&socket](...) {
    socket.close();  // Se o timer disparar após a função retornar, o socket é destruído, crash!
});

// Correto - shared pointer o mantém vivo
auto socket = std::make_shared<tcp::socket>(io);
timer->async_wait([socket](...) {  // Captura shared_ptr, estende o tempo de vida
    socket->close();  // Seguro mesmo se a função externa retornar
});
```

## Implementação de Segurança

### Banner Grabbing

Arquivo: `PortScanner.cpp:143-151`

```cpp
auto buf = std::make_shared<std::array<char, 128>>();

socket->async_read_some(boost::asio::buffer(*buf),
    boost::asio::bind_executor(strand,
    [this, port, buf, banner, service](boost::system::error_code ec, std::size_t n) {
        if (!ec && n > 0) {
            banner->assign(buf->data(), n);
        }
        printf("%i\t%sOPEN%s\t%s\t%s\n", port, GREEN, RESET, service.c_str(), banner->c_str());
        // ...
    }));
```

**O que isso evita:**
Nada — banner grabbing é uma técnica ofensiva, não uma defesa. Mas entendê-la ajuda você a proteger seus serviços.

**Como funciona:**

1. Após uma conexão bem-sucedida, aloca um buffer de 128 bytes
2. Chama `async_read_some`, que retorna imediatamente
3. Quando os dados chegam (ou ocorre um erro), o handler de conclusão dispara
4. Se bytes foram lidos (`n > 0`), copia-os para a string do banner
5. Imprime o resultado com o conteúdo do banner

**O que acontece se você remover isso:**
Você ainda detectaria portas abertas, mas não saberia qual software está rodando. O banner "SSH-2.0-OpenSSH_7.4" informa que é a versão 7.4 do SSH, que possui CVEs conhecidos. Sem banners, você teria que se conectar manualmente a cada porta aberta.

### Detecção de Filtragem Baseada em Timeout

Arquivo: `PortScanner.cpp:128-137`

```cpp
timer->expires_after(std::chrono::seconds(expiry_time));

timer->async_wait(boost::asio::bind_executor(strand,
    [this, complete, socket, port](boost::system::error_code ec) {
        if (!ec && !*complete)  {
            *complete = true;
            socket->close();
            printf("%i\t%s\t%s\t%s\n", port, "FILTERED", "NULL", "NULL");
            ++filtered_ports;
            --cnt;
            scan();
        }
    }));
```

**O que isso evita:**
Travamentos infinitos em portas filtradas. Sem timeouts, o `async_connect` espera indefinidamente se um firewall descartar os pacotes.

**Como funciona:**

1. Define o timer para expirar em `expiry_time` segundos (padrão 2)
2. Se o timer disparar E a conexão não tiver sido concluída (`!*complete`), a porta está filtrada
3. Fecha a operação de socket pendente
4. Marca a porta como FILTERED

**O que acontece se você remover isso:**
O scanner travaria para sempre na primeira porta filtrada. Você escanearia a porta 1 (filtrada), esperaria eternamente e nunca chegaria à porta 2. Timeouts são essenciais para lidar com alvos que não respondem.

## Exemplo de Fluxo de Dados

Vamos rastrear um escaneamento completo da porta 22 (SSH) em um host onde ela está aberta.

### Início da Requisição

```cpp
// Ponto de entrada: main.cpp:37-38
PortScanner scanner;
scanner.set_options("192.168.1.100", "22", 100, 2);
```

Neste ponto:

- O resolvedor de DNS traduz "192.168.1.100" para o endereço IP (trivial para IPs)
- O endpoint é armazenado como `tcp::endpoint` com o IP
- A fila contém uma única entrada: `22`

### Início do Scanner

```cpp
// PortScanner.cpp:111-114
for (int i = 0; i < MAX_THREADS; i++) {
    boost::asio::post(strand, [this]() {
        scan();
    });
}
```

Este código posta 100 itens de trabalho (já que `MAX_THREADS=100`), mas apenas 1 porta na fila, então 99 retornam imediatamente na cláusula de guarda. Um worker prossegue:

```cpp
// PortScanner.cpp:123-127
uint16_t port = 22;  // Retirado da fila
q.pop();  // Fila agora vazia
++cnt;  // cnt = 1

auto socket = std::make_shared<tcp::socket>(io);
auto timer = std::make_shared<boost::asio::steady_timer>(io);
```

### Tentativa de Conexão

```cpp
// PortScanner.cpp:128-137
timer->expires_after(std::chrono::seconds(2));
timer->async_wait([...](...) { ... });  // Agendado, ainda não disparado

// PortScanner.cpp:138
socket->async_connect(endpoint, [...](...) { ... });  // Inicia o handshake TCP
```

No fio:

1. O scanner envia um pacote SYN para 192.168.1.100:22
2. O alvo responde com SYN-ACK (o SSH está escutando)
3. O scanner completa o handshake com ACK
4. Conexão estabelecida (tipicamente < 100ms)

### Conexão Bem-sucedida

```cpp
// PortScanner.cpp:139-151
// O handler de conclusão dispara com ec = success
if (*complete) return;  // complete=false, então continua
*complete = true;  // Define a flag
timer->cancel();  // Impede o timer de disparar

auto it = basicPorts.find(22);  // Encontrado: "SSH"
std::string service = "SSH";

// A porta está aberta, tenta banner grab
auto buf = std::make_shared<std::array<char, 128>>();
socket->async_read_some(boost::asio::buffer(*buf), [...](...) { ... });
```

O servidor SSH envia imediatamente seu banner (requisito do protocolo):

```
SSH-2.0-OpenSSH_7.4p1 Debian-10+deb9u7
```

### Banner Recebido

```cpp
// PortScanner.cpp:144-151
[](boost::system::error_code ec, std::size_t n) {
    if (!ec && n > 0) {  // Sucesso, lidos 43 bytes
        banner->assign(buf->data(), 43);  // "SSH-2.0-OpenSSH_7.4p1 Debian-10+deb9u7"
    }
    printf("%i\t%sOPEN%s\t%s\t%s\n", 22, GREEN, RESET, "SSH", "SSH-2.0-OpenSSH_7.4p1...");
    ++open_ports;  // Estatísticas
    --cnt;  // Workers ativos agora 0
    scan();  // Verifica a fila por mais trabalho (vazia, então retorna imediatamente)
}
```

O resultado é impresso em verde: `22  OPEN  SSH  SSH-2.0-OpenSSH_7.4p1 Debian-10+deb9u7`

## Padrões de Tratamento de Erros

### Conexão Recusada (Porta Fechada)

Ao escanear a porta 8080 em um sistema onde nada está escutando:

```cpp
// PortScanner.cpp:153-158
else {
    // ec = "Connection refused" (ECONNREFUSED)
    printf("%i\t%sCLOSED%s\t%s\t%s\n", port, RED, RESET, service.c_str(), banner->c_str());
    ++closed_ports;
    --cnt;
    scan();
}
```

**Por que este tratamento específico:**
Conexão recusada significa que o alvo enviou um pacote RST (porta explicitamente fechada). Isso é diferente de timeout (filtrada). Nós codificamos com a cor vermelha para distinguir visualmente das portas abertas.

**O que NÃO fazer:**

```cpp
// Ruim: capturar e silenciar erros
socket->async_connect(endpoint, [](boost::system::error_code ec) {
    // Ignorar todos os erros - ideia terrível
});
```

Isso esconde problemas de rede (falha de DNS, rota inacessível) que devem ser relatados. Sempre verifique os códigos de erro.

### Timeout (Porta Filtrada)

Ao escanear a porta 12345 em um host atrás de um firewall que descarta pacotes:

```cpp
// PortScanner.cpp:129-136
timer->async_wait([](boost::system::error_code ec) {
    if (!ec && !*complete) {  // O timer expirou naturalmente (não foi cancelado)
        *complete = true;
        socket->close();  // Aborta a conexão pendente
        printf("%i\t%s\t%s\t%s\n", port, "FILTERED", "NULL", "NULL");
        ++filtered_ports;
        --cnt;
        scan();
    }
});
```

A verificação de `ec` é crucial — se o timer for cancelado (pela conexão bem-sucedida), `ec` é definido e pulamos este handler. Apenas a expiração natural significa que está filtrada.

## Otimizações de Desempenho

### Antes: Escaneamento Síncrono

Esta implementação ingênua seria desastrosamente lenta:

```cpp
// Não faça isso na prática
for (int port = 1; port <= 65535; port++) {
    try {
        tcp::socket s(io);
        s.connect(tcp::endpoint(address, port));  // Bloqueia!
        // Se chegarmos aqui, a porta está aberta
    } catch (...) {
        // Porta fechada ou filtrada (não é possível distinguir)
    }
}
```

Isso era lento porque cada `connect()` bloqueia pela duração do timeout. Em um timeout de 2 segundos:

- 65535 portas × 2 segundos = 131.070 segundos = 36 horas (!)

Mesmo com conexões de 100ms:

- 65535 portas × 0,1 segundos = 6553 segundos = 1,8 horas

### Depois: Escaneamento Assíncrono Concorrente

```cpp
// PortScanner.cpp:111-115
for (int i = 0; i < MAX_THREADS; i++) {
    boost::asio::post(strand, [this]() { scan(); });
}
io.run();  // Bloqueia até que todas as operações assíncronas terminem
```

**O que mudou:**

- Iniciadas 100 operações assíncronas simultaneamente
- Cada uma termina de forma independente e inicia outra
- Tempo total = (total de portas / concorrência) × tempo médio de conexão
- 65535 portas / 100 workers × 0,1 segundos = 66 segundos

**Benchmarks:**

- Antes (síncrono): 36 horas para scan completo com timeout de 2 segundos
- Depois (100 threads): ~2 minutos para o mesmo scan
- Melhoria: 1080× mais rápido

Para scans de rede local com latência inferior a 10ms:

- Antes: 11 minutos (65535 × 0,01s)
- Depois: 7 segundos (throughput de 655 portas/seg)
- Melhoria: 95× mais rápido

## Gerenciamento de Configuração

### Parsing de Intervalo de Portas

```cpp
// PortScanner.cpp:26-53
void PortScanner::parse_port(std::string& port) {
    auto t = std::find(port.begin(), port.end(), '-');
    if (t == port.end()) {
        // Sem hífen - porta única ou intervalo máximo
        startPort = 1;
        endPort = std::stoi(port);  // "1024" significa 1-1024
        return;
    }

    // Analisa o formato "início-fim"
    std::string s = "", e = "";
    auto it = port.begin();
    while (it != port.end() && *it != '-') {
        s += *it;
        ++it;
    }
    ++it;  // Pula o hífen
    while (it != port.end()) {
        e += *it;
        ++it;
    }

    int start = std::stoi(s);
    int end = std::stoi(e);

    // Valida os limites
    if (start == 0 || end > MAX_PORT || start > end) {
        startPort = 1;
        endPort = MAX_PORT;  // Entrada inválida = scan completo
    } else {
        startPort = static_cast<uint16_t>(start);
        endPort = static_cast<uint16_t>(end);
    }
}
```

**Detalhes importantes:**

- **Validação de entrada**: A verificação de limites garante que não escanearemos a porta 0 (inválida) ou > 65535 (impossível)
- **Comportamento de fallback**: Entrada inválida (como "5000-100") assume como padrão o scan completo em vez de travar
- **Parsing de string**: Iteração manual de caracteres em vez de regex (mais simples, sem dependência)

Validamos cedo porque intervalos de portas inválidos causam erros estranhos mais tarde (a fila pode estar vazia ou conter mais de 65535 portas se a matemática estourar). Falhar rápido no momento da configuração é melhor do que travamentos misteriosos em tempo de execução.

### Resolução de DNS

```cpp
// PortScanner.cpp:89-92
auto result = resolver.resolve(this->domainName, "");
endpoint = *result.begin();
```

**Como isso funciona:**
O resolvedor do Boost.Asio consulta o DNS por registros A/AAAA. Para "scanme.nmap.org", ele retorna 45.33.32.156. Para endereços IP como "192.168.1.1", ele valida o formato e retorna imediatamente.

**Tratamento de erros:**
Se a resolução falhar (o domínio não existe, o servidor DNS está inacessível), o `resolve()` lança uma exceção. Isso é intencional — melhor falhar na inicialização do que escanear silenciosamente o host errado.

## Armadilhas Comuns de Implementação

### Armadilha 1: Esquecer de Vincular à Strand

**Sintoma:**
Travamentos aleatórios, estatísticas corrompidas, portas escaneadas múltiplas vezes ou ignoradas.

**Causa:**

```cpp
// Errado - sem proteção de strand
socket->async_connect(endpoint, [this, port](...) {
    ++open_ports;  // CONDIÇÃO DE CORRIDA!
    q.pop();       // CORROMPE A FILA!
});
```

Múltiplos handlers de conclusão rodam concorrentemente, modificando o estado compartilhado (`open_ports`, fila) sem sincronização. Isso causa condições de corrida de dados e comportamento indefinido.

**Correção:**

```cpp
// Correto - a strand serializa os handlers
socket->async_connect(endpoint, boost::asio::bind_executor(strand,
    [this, port](...) {
        ++open_ports;  // Seguro - apenas um handler roda por vez
        q.pop();       // Seguro
    }));
```

**Por que isso importa:**
Corridas de dados são assassinos silenciosos. Seu programa pode funcionar 99% do tempo e travar de forma imprevisível no 1% onde dois handlers disputam. Sempre use strand para estado compartilhado.

### Armadilha 2: Capturar Variáveis Locais por Referência

**Sintoma:**
Crashes de use-after-free, dados lixo nas conclusões.

**Causa:**

```cpp
void scan() {
    uint16_t port = q.front();
    socket->async_connect(endpoint, [&port](...) {  // ERRADO!
        printf("Port %d\n", port);  // 'port' é destruído quando scan() retorna
    });
}
```

A lambda captura `port` por referência, mas `port` é uma variável local que é destruída quando `scan()` retorna. A operação assíncrona ainda não terminou, então quando o handler finalmente roda, ele acessa memória liberada.

**Correção:**

```cpp
void scan() {
    uint16_t port = q.front();
    socket->async_connect(endpoint, [port](...) {  // Cópia por valor
        printf("Port %d\n", port);  // Seguro - port foi copiado para a lambda
    });
}
```

**Por que isso importa:**
A programação assíncrona inverte o fluxo de controle. A função retorna muito antes do handler rodar. Sempre capture por valor ou use shared pointers para objetos com tempos de vida complexos.

## Dicas de Depuração

### Problema: "Todas as portas aparecem como FILTERED"

**Problema:** Todas as portas expiram, nada aparece como OPEN ou CLOSED.

**Como depurar:**

1. Verifique o firewall na máquina que está escaneando — conexões de saída podem estar bloqueadas
2. Verifique se o alvo está acessível: `ping 192.168.1.100`
3. Teste com uma porta aberta conhecida: `telnet scanme.nmap.org 80` deve conectar
4. Reduza a contagem de threads e aumente o timeout: `-t 1 -e 10` elimina problemas de concorrência e rede

**Causas comuns:**

- O firewall do host de destino descarta todas as conexões de entrada (funcionando conforme projetado)
- O firewall da rede entre você e o alvo bloqueia o tráfego de escaneamento de portas
- O host de destino está desligado ou inacessível
- Você está escaneando de uma rede restrita (corporativa, provedor de nuvem) que bloqueia scans de saída

### Problema: "Segmentation fault no handler de conclusão"

**Problema:** Travamentos com stack trace nos componentes internos do Boost.Asio.

**Como depurar:**

1. Compile com símbolos de depuração: `cmake -DCMAKE_BUILD_TYPE=Debug ..`
2. Execute sob o valgrind: `valgrind --leak-check=full ./simplePortScanner`
3. Verifique por referências capturadas: use grep no código por `[&` para encontrar capturas de referência
4. Verifique o uso de shared pointer: sockets/timers alocados na pilha causam isso

**Causas comuns:**

- Variáveis locais capturadas por referência (Armadilha 2 acima)
- Objetos assíncronos alocados na pilha que são destruídos enquanto as operações estão pendentes
- Double-free por gerenciamento manual de memória (deve usar shared_ptr)

## Estendendo o Código

### Adicionando Escaneamento UDP

Quer escanear portas UDP? Aqui está o processo:

1. **Crie o tipo de socket UDP** no `PortScanner.hpp`

```cpp
   enum class Protocol { TCP, UDP };
   Protocol protocol = Protocol::TCP;
```

2. **Modifique a criação do socket** no `scan()`

```cpp
   if (protocol == Protocol::UDP) {
       auto socket = std::make_shared<udp::socket>(io);
       // O escaneamento UDP usa sendto em vez de connect
   } else {
       auto socket = std::make_shared<tcp::socket>(io);
   }
```

3. **Implemente a lógica de sondagem UDP**

```cpp
   // O UDP não possui handshake de conexão
   // Envie um payload específico para o serviço (consulta DNS para a porta 53)
   // Espere pela resposta ou ICMP unreachable
   socket->async_send_to(boost::asio::buffer(probe), endpoint, ...);
```

O escaneamento UDP é mais difícil porque o UDP não possui estados de conexão. Você deve enviar sondagens específicas de protocolo e interpretar as respostas para determinar se uma porta está aberta.

## Dependências

### Por que Cada Dependência

- **Boost.Asio** (1.70+): Framework de E/S assíncrona que abstrai APIs de socket específicas do SO (epoll/kqueue/IOCP). Nós o usamos para `async_connect`, timers e o event loop. Alternativa: sockets POSIX puros, mas requer a implementação do nosso próprio event loop.

- **Boost.Program_Options** (1.70+): Parser de argumentos CLI com segurança de tipo e geração automática de ajuda. Nós o usamos no `main.cpp` para as flags `-i`, `-p`, `-t`. Alternativa: parsing manual de `argv`, mas propenso a erros e com muito código repetitivo.

### Segurança de Dependências

Verifique por vulnerabilidades:

```bash
# O Boost não possui escaneamento automatizado de CVE, mas verifique sua versão
dpkg -l | grep libboost  # No Debian/Ubuntu
brew info boost          # No macOS

# Visite https://www.cvedetails.com/vendor/14185/Boost.html
```

Se você vir um CVE do Boost afetando o Asio (raro), atualize:

```bash
sudo apt update && sudo apt upgrade libboost-all-dev
```

A maioria das vulnerabilidades do Boost está em módulos específicos (Boost.Python, Boost.Beast). O Asio é bem auditado e estável.

## Build e Deploy

### Build

```bash
mkdir build && cd build
cmake ..
make
```

Isso produz o executável `simplePortScanner` no diretório de build. O processo de build:

1. O CMake lê o `CMakeLists.txt` e encontra as bibliotecas Boost
2. Gera Makefiles específicos da plataforma (ou projetos Ninja/Xcode)
3. O compilador é invocado com a flag `-std=c++20`
4. Faz o link contra Boost.Program_Options e pthread (implícito)

### Desenvolvimento Local

```bash
# Recompile após as alterações
cd build
make

# Execute com saída detalhada para ver todos os scans
./simplePortScanner -i 127.0.0.1 -p 1-100 -v

# Teste portas específicas
./simplePortScanner -i localhost -p 22,80,443
```

### Deploy em Produção

Para trabalho de escaneamento real:

```bash
# Compile com otimizações
cmake -DCMAKE_BUILD_TYPE=Release ..
make

# Instale no sistema
sudo cp simplePortScanner /usr/local/bin/
```

Principais diferenças do desenvolvimento:

- Builds de Release são 3-5× mais rápidos (otimizações do compilador)
- Símbolos de depuração removidos (binário menor)
- Asserções desativadas (sem verificações em tempo de execução)

## Próximos Passos

Você viu como a E/S assíncrona, o escaneamento concorrente e a detecção de estado funcionam. Agora:

1. **Tente os desafios** — [04-Desafios.md](./04-Desafios.md) tem ideias de extensão como escaneamento SYN, detecção de versão de serviço e formatos de saída.

2. **Modifique a concorrência** — Altere `MAX_THREADS` para 1 e observe o escaneamento serial (lento). Altere para 1000 e observe o pico no uso de recursos. Encontre o ponto ideal para sua rede.

3. **Compare com o Nmap** — Execute `nmap -sT scanme.nmap.org` (TCP connect scan, igual ao nosso) e compare os resultados. O Nmap possui décadas de tratamento de casos extremos que nós não temos.
