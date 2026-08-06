# Arquitetura do Sistema

Este documento detalha como o scanner de portas foi projetado e por que a E/S assíncrona com workers concorrentes oferece tanto velocidade quanto clareza.

## Arquitetura de Alto Nível

```
┌─────────────────────────────────────┐
│      Interface de Linha de Comando  │
│   (Parser Boost.Program_Options)    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│        Objeto PortScanner           │
│   - Gerenciamento de Configuração   │
│   - Fila de Trabalho (portas)       │
│   - Controle de Thread/Concorrência │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│       Boost.Asio io_context         │
│    (Event Loop / Runtime Assíncrono)│
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
┌─────────────┐  ┌─────────────┐
│   Socket    │  │    Timer    │
│   (Conexão  │  │ (Detecção de│
│     TCP)    │  │   Timeout)  │
└─────────────┘  └─────────────┘
       │               │
       └───────┬───────┘
               ▼
       ┌───────────────┐
       │     Alvo      │
       │  Host:Porta   │
       └───────────────┘
```

### Divisão dos Componentes

**Interface de Linha de Comando (main.cpp)**

- Propósito: Analisar a entrada do usuário e inicializar o scanner com a configuração.
- Responsabilidades: Validar argumentos, definir padrões, exibir texto de ajuda e exemplos de uso.
- Interfaces: Cria e configura um objeto `PortScanner`, então chama `start()` e `run()`.

**Controlador PortScanner (classe PortScanner)**

- Propósito: Orquestrar o processo de escaneamento e gerenciar operações concorrentes.
- Responsabilidades: Manter a fila de trabalho das portas a serem escaneadas, aplicar limites de threads, rastrear estatísticas (contagens de abertas/fechadas/filtradas), fornecer formatação de resultados.
- Interfaces: Expõe os métodos `set_options()`, `start()` e `run()`; internamente utiliza primitivas do Boost.Asio.

**Boost.Asio io_context**

- Propósito: Event loop que conduz todas as operações assíncronas.
- Responsabilidades: Agendar operações de socket assíncronas e callbacks de timer, despachar handlers de conclusão quando a E/S termina, gerenciar a execution strand para segurança de threads.
- Interfaces: Fornece as operações async_connect, async_read_some e async_wait que nosso scanner utiliza.

**Par de Socket e Timer**

- Propósito: Cada escaneamento de porta usa um socket (para conexão) e um timer (para timeout).
- Responsabilidades: O socket tenta a conexão TCP; o timer corre contra o socket para detectar portas filtradas.
- Interfaces: Handlers de conclusão são disparados quando o socket conecta/falha ou o timer expira.

## Fluxo de Dados

### Fluxo de Escaneamento Principal

Passo a passo do que acontece quando você executa `./simplePortScanner -i 192.168.1.1 -p 80-443`:

```
1. main.cpp:12-23 → Analisa os argumentos da linha de comando
   Extrai IP (192.168.1.1), intervalo de portas (80-443), contagem de threads (padrão 100), timeout (padrão 2 seg)

2. main.cpp:37-40 → Inicializa o PortScanner
   Chama set_options() que resolve o DNS para o endpoint do endereço IP

3. PortScanner.cpp:77-82 → setup_queue()
   Preenche a fila com as portas 80, 81, 82, ... 443 (364 portas no total)

4. PortScanner.cpp:109-115 → start()
   Posta itens de trabalho MAX_THREADS para o io_context via strand
   Cada item de trabalho é uma chamada para a função scan()

5. main.cpp:41 → run()
   Chama io.run() que bloqueia até que todas as operações assíncronas sejam concluídas

6. PortScanner.cpp:123-165 → scan() (chamada MAX_THREADS vezes concorrentemente)
   Retira uma porta da fila, cria socket e timer, coloca-os em disputa

   SE o timeout expirar primeiro (linha 130-136):
       → Porta está FILTRADA
       → Imprime resultado, decrementa contador, chama scan() recursivamente para a próxima porta

   SE a conexão for bem-sucedida (linha 144-151):
       → Porta está ABERTA
       → Tenta banner grab (async_read_some)
       → Imprime resultado com banner, decrementa contador, chama scan() novamente

   SE a conexão falhar (linha 153-158):
       → Porta está FECHADA
       → Imprime resultado, decrementa contador, chama scan() novamente

7. Quando a fila estiver vazia → io.run() termina → main.cpp:117-120 imprime o resumo
```

Exemplo com referências de código:

```
1. Usuário executa o comando → main() (main.cpp:6)
   Boost.Program_Options analisa para as variáveis

2. Variáveis → PortScanner.set_options() (PortScanner.cpp:85-95)
   A resolução de DNS acontece: resolver.resolve(domainName, "")
   Armazena o endpoint para uso posterior

3. PortScanner.start() → Preenche a fila, posta o trabalho (PortScanner.cpp:109-115)
   100 operações scan() assíncronas começam

4. Cada scan() → Cria o par socket + timer (PortScanner.cpp:123-127)
   Ambas as operações começam simultaneamente
   Quem concluir primeiro cancela a outra

5. Handler de conclusão → Determina o estado da porta (PortScanner.cpp:129-165)
   Imprime o resultado, decrementa o contador ativo, chama scan() para pegar a próxima porta da fila

6. Fila esgotada → io.run() retorna (main.cpp:41)
   Estatísticas finais são impressas
```

### Fluxo Secundário de Resolução de DNS

Antes de qualquer escaneamento de porta acontecer, resolvemos o nome de domínio:

```
1. Usuário fornece "-i scanme.nmap.org" → armazenado como string
2. PortScanner.set_options() chama resolver.resolve(domainName, "")
3. Boost.Asio realiza a busca DNS (registro A ou AAAA)
4. Resultado convertido para tcp::endpoint com endereço IP
5. Todas as conexões subsequentes usam este endpoint em cache
```

Isso acontece de forma síncrona na inicialização. Se o DNS falhar, o programa apresenta erro imediatamente antes de qualquer escaneamento começar. Para endereços IP (como 192.168.1.1), a resolução é trivial e apenas valida o formato.

## Padrões de Projeto

### E/S Assíncrona com Handlers de Conclusão

**O que é:**
E/S não bloqueante onde as operações retornam imediatamente e os callbacks são disparados quando concluídos. Em vez de esperar por uma conexão de socket (que pode levar segundos), iniciamos a operação e fornecemos uma função para ser chamada quando ela terminar.

**Onde usamos:**
Em cada operação de rede no scanner:

- `async_connect` para conexões TCP (PortScanner.cpp:138)
- `async_read_some` para banner grabbing (PortScanner.cpp:143)
- `async_wait` para detecção de timeout (PortScanner.cpp:128)

**Por que escolhemos:**
Escanear 65.535 portas de forma síncrona levaria horas. Mesmo a 100ms por porta (rede local rápida), seriam 1,8 horas. Com E/S assíncrona e 100 operações concorrentes, concluímos em minutos. O padrão também é escalável — alterar a contagem de threads é apenas um parâmetro.

**Trade-offs:**

- Prós: Concorrência massiva com poucas threads reais, uso eficiente de recursos, escala para milhares de operações simultâneas.
- Contras: Fluxo de código mais complexo (callbacks em vez de lógica linear), mais difícil de depurar (stack traces mostram o mecanismo assíncrono), requer compreensão de event loops.

Exemplo de implementação:

```cpp
// PortScanner.cpp:138-165
socket->async_connect(endpoint, boost::asio::bind_executor(strand,
    [this, socket, timer, port, complete](boost::system::error_code ec) {
        if (*complete) return;  // Timer já disparou, ignore isso
        *complete = true;
        timer->cancel();        // Para a disputa, nós vencemos

        if (!ec) {
            // Conexão bem-sucedida - porta está ABERTA
            async_read_some(...);  // Tenta capturar o banner
        } else {
            // Conexão falhou - porta está FECHADA
            print_result(...);
        }
        scan();  // Recursão de cauda para pegar a próxima porta
    }
));
```

A lambda captura o estado compartilhado (`socket`, `timer`, flag `complete`) e executa mais tarde quando a tentativa de conexão termina. Este fluxo não linear permite a concorrência.

### Fila de Trabalho com Concorrência Fixa

**O que é:**
Uma fila de trabalho pendente (portas para escanear) com um número fixo de workers retirando itens dela. Conforme cada worker termina, ele pega o próximo item. Isso evita a criação de 65.535 threads e a sobrecarga do sistema.

**Onde usamos:**

- Fila: `std::queue<uint16_t> q` (PortScanner.hpp:24) preenchida em `setup_queue()` (PortScanner.cpp:77-82)
- Limite de concorrência: `MAX_THREADS` (padrão 100) controla quantos escaneamentos rodam simultaneamente.
- Captura de trabalho: `scan()` retira da fila (PortScanner.cpp:123), processa e então chama a si mesma recursivamente para a próxima porta.

**Por que escolhemos:**
Simples de entender e implementar. A fila lida naturalmente com a distribuição de trabalho — sem lógica de agendamento complexa. Quando um escaneamento termina rápido (porta fechada), o worker imediatamente pega outro. Escaneamentos lentos (portas abertas com banner grabs) não bloqueiam outras portas.

**Trade-offs:**

- Prós: Fácil de raciocinar, balanceamento de carga automático, aplicação simples de limite de threads.
- Contras: Não é perfeitamente eficiente (se as últimas portas forem lentas, os workers ficam ociosos), não prioriza portas interessantes.

### Strand para Segurança de Threads

**O que é:**
Um construtor do Boost.Asio que serializa a execução de handlers. Quando múltiplas operações assíncronas terminam, a strand garante que seus handlers não rodem simultaneamente. Isso fornece segurança de threads sem travas (locks) explícitas.

**Onde usamos:**

```cpp
// PortScanner.hpp:23
boost::asio::strand<boost::asio::io_context::executor_type> strand{io.get_executor()};

// Todas as operações assíncronas envolvidas em bind_executor(strand, ...)
// PortScanner.cpp:111, 129, 139, 144
boost::asio::post(strand, [this]() { scan(); });
boost::asio::bind_executor(strand, [...](...) { ... });
```

**Por que escolhemos:**
Múltiplos handlers de conclusão modificam o estado compartilhado (`cnt`, `q`, contadores de estatísticas). Sem sincronização, condições de corrida corrompem os dados. A strand garante que, embora 100 operações rodem concorrentemente, seus handlers de conclusão executem um de cada vez.

**Trade-offs:**

- Prós: Seguro para threads sem locks manuais, sem risco de deadlock, código limpo sem gerenciamento de mutex.
- Contras: Pequeno custo de desempenho pela serialização (insignificante para nossa carga de trabalho), todos os handlers devem ser envolvidos de forma consistente.

## Separação de Camadas

O scanner possui três camadas distintas:

```
┌────────────────────────────────────┐
│    Camada de Apresentação          │
│    - Parsing de CLI (main.cpp)      │
│    - Formatação de saída           │
│    - Códigos de cor para terminal  │
└────────────────────────────────────┘
           ↓
┌────────────────────────────────────┐
│    Camada de Lógica de Negócio     │
│    - Classe PortScanner            │
│    - Algoritmo de escaneamento     │
│    - Gerenciamento de estado       │
└────────────────────────────────────┘
           ↓
┌────────────────────────────────────┐
│    Camada de E/S                   │
│    - Runtime Boost.Asio            │
│    - Operações de socket           │
│    - Operações de timer            │
└────────────────────────────────────┘
```

### Por que Camadas?

A separação de preocupações torna cada componente testável e substituível:

- Quer uma GUI em vez de CLI? Substitua a camada de apresentação, mantenha a lógica de negócio.
- Quer mudar do Boost.Asio para sockets POSIX puros? Substitua a camada de E/S, a lógica de negócio permanece inalterada.
- Quer adicionar diferentes tipos de scan (UDP, SYN scan)? Estenda a lógica de negócio sem tocar na apresentação.

### O Que Vive Onde

**Camada de Apresentação (main.cpp):**

- Arquivos: `main.cpp`
- Importações: Pode importar a lógica de negócio (classe PortScanner), usa Boost.Program_Options para parsing de CLI.
- Proibido: Não deve criar sockets ou timers diretamente, não deve implementar a lógica de escaneamento.

**Camada de Lógica de Negócio (classe PortScanner):**

- Arquivos: `src/PortScanner.hpp`, `src/PortScanner.cpp`
- Importações: Pode importar a camada de E/S (Boost.Asio), não pode importar a camada de apresentação.
- Proibido: Não deve lidar com parsing de linha de comando ou formatação de saída (apenas retorna dados).

**Camada de E/S (Boost.Asio):**

- Arquivos: Biblioteca externa (Boost)
- Importações: Biblioteca padrão, APIs de socket de nível de SO.
- Proibido: Nenhuma lógica de negócio sobre portas ou escaneamento.

Esta estrutura significa que o main.cpp conhece o PortScanner, o PortScanner conhece o Asio, mas o Asio não conhece o escaneamento, e o escaneamento não conhece as flags de CLI.

## Modelos de Dados

### Entrada da Fila de Portas

```cpp
// PortScanner.hpp:24
std::queue<std::uint16_t> q;
```

**Campos explicados:**

- Apenas o número da porta (0-65535) armazenado como `uint16_t` para economizar memória.
- Fila processada em FIFO — portas escaneadas em ordem (80, 81, 82, ...).

**Relacionamentos:**

- Preenchida por `parse_port()` que converte a entrada do usuário como "80-443" em números de porta individuais.
- Consumida por `scan()` que retira as portas uma por uma.

### Estado do Scanner

```cpp
// PortScanner.hpp:25-29
int cnt = 0;                // Escaneamentos concorrentes ativos
int MAX_THREADS = 0;        // Limite de concorrência
int open_ports = 0;         // Estatísticas
int closed_ports = 0;
int filtered_ports = 0;
```

**Campos explicados:**

- `cnt`: Quantas operações `scan()` estão em andamento no momento. Evita a criação de muitos workers.
- `MAX_THREADS`: Limite de concorrência configurável pelo usuário. O padrão é 100 em main.cpp:15.
- Contadores de estatísticas: Incrementados conforme os resultados chegam, impressos ao final para o resumo.

**Relacionamentos:**

- `cnt` protege a fila de trabalho — se `cnt >= MAX_THREADS`, nenhum novo escaneamento começa mesmo que a fila tenha portas.
- Estatísticas rastreadas por handler de conclusão (PortScanner.cpp:135, 148, 156).

### Mapa de Portas Bem Conhecidas

```cpp
// PortScanner.cpp:3-24
const std::unordered_map<uint16_t, std::string> PortScanner::basicPorts{
    {21, "FTP"},
    {22, "SSH"},
    {80, "HTTP"},
    {443, "HTTPS"},
    ...
};
```

**Campos explicados:**

- Mapeamento constante estático de números de porta para nomes de serviço.
- Usado apenas para exibição — não afeta a lógica de escaneamento.

**Relacionamentos:**

- Consultado no handler de conclusão (PortScanner.cpp:142) para mostrar o nome do serviço em vez de apenas o número da porta.
- Portas ausentes são exibidas como "---" (PortScanner.cpp:140).

## Arquitetura de Segurança

### Modelo de Ameaça

O que estamos protegendo contra:

1. **Interrupção acidental da rede** - Escanear de forma muito agressiva pode travar sistemas de destino ou equipamentos de rede. Limites de threads e timeouts evitam sobrecarregar os alvos.

2. **Responsabilidade legal** - Escanear redes que você não possui é frequentemente ilegal (CFAA nos EUA). A ferramenta inclui avisos de uso para educar os usuários sobre os limites legais.

3. **Detecção por IDS/IPS** - Embora não seja focado em furtividade, o scanner pode ser configurado com contagens de threads mais baixas e timeouts mais longos para reduzir a probabilidade de detecção.

O que NÃO estamos protegendo contra (fora do escopo):

- **Evasão de detecção** - Este é um scanner básico. IDSs avançados irão capturá-lo. Técnicas furtivas (scans SYN, fragmentação, iscas) estão fora do escopo para um projeto iniciante.
- **DoS no sistema alvo** - Limitamos as threads, mas não implementamos limitação de taxa (rate limiting) sofisticada ou backoff. Um escaneamento mal configurado ainda pode sobrecarregar um alvo fraco.

### Camadas de Defesa

O scanner em si é uma ferramenta de reconhecimento, mas entender a defesa em profundidade ajuda os usuários a se protegerem de serem escaneados:

```
Camada 1: Firewall (impede a conclusão do scan)
    ↓
Camada 2: IDS (detecta o padrão do scan)
    ↓
Camada 3: Rate limiting (desacelera o atacante)
```

**Por que múltiplas camadas?**

Se o firewall falhar (regra mal configurada), o IDS alerta a equipe de segurança. Se o IDS perder o escaneamento (técnica de evasão), o rate limiting impede a enumeração rápida. Cada camada compensa falhas nas outras.

## Configuração

### Variáveis de Ambiente

Este scanner usa argumentos de linha de comando, não variáveis de ambiente:

```bash
./simplePortScanner \
  -i TARGET          # IP ou nome de domínio (padrão: 127.0.0.1)
  -p PORT_RANGE      # "80" ou "1-1024" ou "22,80,443" (padrão: 1-1024)
  -t THREADS         # Máximo de escaneamentos concorrentes (padrão: 100)
  -e TIMEOUT         # Segundos para esperar antes de marcar como filtrada (padrão: 2)
  -v                 # Saída detalhada (ainda não implementado)
  -h                 # Mensagem de ajuda
```

### Estratégia de Configuração

**Desenvolvimento:**
Use contagens de threads baixas (`-t 10`) e intervalos de portas pequenos (`-p 80-100`) para testar sem sobrecarregar sua rede. Escaneie o localhost para verificar a funcionalidade.

**Produção:**
Escaneamentos reais usam concorrência mais alta (`-t 200` ou mais) para velocidade. Ajuste o timeout com base na latência da rede — redes locais podem usar 1 segundo, escaneamentos na internet precisam de 3-5 segundos. Sempre obtenha permissão antes de escanear hosts externos.

## Considerações de Desempenho

### Gargalos

Onde este sistema fica lento sob carga:

1. **A latência da rede domina** - Mesmo com alta concorrência, você não pode escanear mais rápido do que o tempo de ida e volta (round-trip) da rede. Em uma conexão com 50ms de latência, cada porta leva pelo menos 50ms, independentemente de quantas threads você use.

2. **A resolução de DNS é síncrona** - A chamada inicial `resolver.resolve()` bloqueia. Para domínios com DNS lento, isso atrasa o início do escaneamento. Fazer cache de IPs resolvidos poderia ajudar em escaneamentos repetidos.

### Otimizações

O que fizemos para torná-lo mais rápido:

- **E/S Assíncrona**: A grande vitória. Escaneamento síncrono de 10.000 portas a 100ms cada = 16 minutos. Assíncrono com 100 threads = ~10 segundos.

- **Otimização de shared pointer** (PortScanner.cpp:125-127): Socket e timer criados como `std::shared_ptr`. Handlers de conclusão capturam estes, garantindo o gerenciamento de tempo de vida sem limpeza manual.

### Escalabilidade

**Escalonamento vertical:**
Aumente o MAX_THREADS (até ~1000 antes de atingir os limites de descritores de arquivo na maioria dos sistemas). Mais threads = mais escaneamentos concorrentes = conclusão mais rápida, mas com retornos decrescentes além da capacidade da rede.

**Escalonamento horizontal:**
Divida os intervalos de IP entre múltiplas instâncias do scanner. Escaneie 192.168.1.0/24 executando 4 instâncias, cada uma lidando com 64 IPs. Isso paraleliza o gargalo (latência da rede) entre as máquinas.

## Decisões de Projeto

### Decisão 1: Connect Scan vs SYN Scan

**O que escolhemos:**
TCP connect scan completo (handshake de três vias completo).

**Alternativas consideradas:**

- SYN scan (half-open scan): Enviar SYN, ler SYN-ACK, enviar RST em vez de completar o handshake.
- ACK scan: Enviar pacote ACK para detectar regras de firewall.
- UDP scan: Enviar pacotes UDP para verificar serviços não-TCP.

**Por que escolhemos o connect scan:**
O escaneamento SYN requer raw sockets, que precisam de privilégios de root no Linux. Isso adiciona complexidade de implantação e risco de segurança. Connect scans funcionam como usuários não privilegiados e se integram de forma limpa com a API de alto nível do Boost.Asio.

**Trade-offs:**

- Prós: Nenhum privilégio especial necessário, código mais simples, multiplataforma (funciona em Windows/Linux/macOS), menos propenso a travar pilhas de rede com bugs.
- Contras: Mais barulhento (aparece claramente nos logs como conexões concluídas), ligeiramente mais lento (handshake completo vs apenas SYN), alguns sistemas registram tentativas de conexão de forma diferente de SYNs.

### Decisão 2: Filtragem Baseada em Timer vs. Análise ICMP

**O que escolhemos:**
Usar a duração do timeout para inferir portas filtradas.

**Alternativas consideradas:**

- Escutar mensagens ICMP "port unreachable" para distinguir fechadas de filtradas.
- Enviar múltiplos tipos de sondagem (SYN, ACK, FIN) e correlacionar as respostas.

**Por que escolhemos timeouts:**
A escuta de ICMP requer raw sockets (novamente, privilégios de root). Filtros de pacotes frequentemente descartam ICMP de qualquer maneira, tornando-o não confiável. Timeouts funcionam em qualquer lugar e lidam corretamente com o caso comum (firewall descarta pacotes silenciosamente).

**Trade-offs:**

- Prós: Funciona sem privilégios, lida com portas filtradas corretamente, simples de implementar.
- Contras: Adiciona latência aos escaneamentos (deve esperar o timeout completo), não consegue distinguir "filtrado por firewall" de "rede fora do ar", falsos positivos se a rede estiver apenas lenta.

### Decisão 3: scan() Recursivo vs. Pool de Workers

**O que escolhemos:**
Chamadas recursivas de cauda para `scan()` para distribuição de trabalho.

**Alternativas consideradas:**

- Pré-criar N threads de worker que fazem um loop retirando da fila.
- Usar uma biblioteca de thread pool com roubo de trabalho (work stealing).

**Por que escolhemos a recursão:**
Encaixa-se naturalmente com handlers de conclusão assíncronos. Quando um escaneamento termina, o handler de conclusão apenas chama `scan()` novamente. O event loop do Boost.Asio cuida do agendamento.

**Trade-offs:**

- Prós: Código mínimo, sem gerenciamento manual de threads, distribuição automática de trabalho.
- Contras: A profundidade da pilha aumenta (embora a otimização de chamada de cauda ajude), menos controle sobre o ciclo de vida do worker, mais difícil de implementar agendamento avançado.

## Próximos Passos

Agora que você entende a arquitetura:

1. Leia [03-Implementação.md](./03-Implementação.md) para um passo a passo detalhado do código mostrando como as operações assíncronas se coordenam.
2. Tente modificar o modelo de concorrência — o que acontece se você remover a strand? (Condições de corrida irão corromper os contadores).
3. Experimente com valores de timeout para ver como a latência da rede afeta a duração do escaneamento.
