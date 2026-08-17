# Arquitetura do Sistema

Este documento detalha como o sistema foi projetado e por que certas decisões arquiteturais foram tomadas.

## Arquitetura de Alto Nível

```
┌────────────────────┐
│     Camada CLI     │  (main.cpp)
│  - parse args      │  Boost.program_options
│  - detect hash     │  Auto-tipo pelo comprimento
│  - dispatch        │  Instanciação de template
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│   Camada Engine    │  (Engine.hpp)
│  - criar threads   │  Pool de std::jthread
│  - particionar trab│  Fatias de ataque por thread
│  - coordenar       │  Atomics compartilhados
│  - exibir          │  Thread de progresso
└─────────┬──────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
┌────────┐ ┌──────────┐
│ Hasher │ │ Attack   │
│ Policy │ │ Strategy │
└────────┘ └──────────┘
    │           │
    ▼           ▼
┌────────┐ ┌──────────────────────────────────┐
│ EVP    │ │ DictionaryAttack (mmap)          │
│ Hasher │ │ BruteForceAttack (keyspace math) │
│        │ │ RuleAttack (dict + mutações)     │
└────────┘ └──────────────────────────────────┘
```

### Divisão dos Componentes

**Camada CLI (main.cpp)**

- Propósito: Analisar os argumentos da linha de comando e despachar para a instanciação correta da Engine.
- Responsabilidades: Validação de argumentos, detecção do tipo de hash, construção do charset, saída JSON.
- Decisão chave de design: Usa uma lambda de template para evitar polimorfismo em tempo de execução. O `switch` no tipo de hash cria um caminho de chamada resolvido em tempo de compilação.

**Camada Engine (Engine.hpp)**

- Propósito: Coordenar o hashing, a estratégia de ataque, o threading e a exibição do progresso.
- Responsabilidades: Gerenciamento do pool de threads, aplicação de salt, coleta de resultados, temporização.
- Decisão chave de design: Função de template header-only. Os tipos de hasher e estratégia de ataque são parâmetros de template, para que o compilador faça o inline da função de hash diretamente no loop de quebra.

**Política de Hasher (EVPHasher.hpp)**

- Propósito: Computar hashes criptográficos via OpenSSL.
- Responsabilidades: Gerenciamento do contexto EVP, computação do digest, codificação hex.
- Decisão chave de design: Template único parametrizado por ponteiro de função do algoritmo. Todos os quatro tipos de hash são aliases de tipo da mesma implementação.

**Estratégias de Ataque (attack/)**

- Propósito: Gerar senhas candidatas.
- Responsabilidades: Leitura de wordlist, geração de keyspace, aplicação de mutações, particionamento de threads.
- Decisão chave de design: Cada estratégia satisfaz o conceito `AttackStrategy` e lida com seu próprio particionamento via `create(path, thread_index, total_threads)`.

**Exibição de Progresso (display/)**

- Propósito: Mostrar o progresso da quebra em tempo real.
- Responsabilidades: Renderização da barra de progresso, cálculo de velocidade/ETA, formatação de resultados.
- Decisão chave de design: Roda em sua própria thread, lê atomics compartilhados com ordenação relaxada, não faz nada quando o stdout não é um terminal.

## Design Central: Templates Baseados em Políticas

A decisão arquitetural central é resolver o hasher e a estratégia de ataque em tempo de compilação, em vez de tempo de execução. Compare as duas abordagens:

**Polimorfismo em tempo de execução (o que não fizemos):**

```cpp
class IHasher {
public:
    virtual std::string hash(std::string_view input) = 0;
    virtual ~IHasher() = default;
};

void crack(IHasher* hasher, ...) {
    for (cada candidato) {
        hasher->hash(candidato);  // chamada virtual em cada iteração
    }
}
```

Cada chamada `hash()` passa pela vtable, o que significa um desvio indireto. A CPU não pode fazer o inline do corpo da função, não pode otimizar através da fronteira da chamada e paga uma penalidade de previsão de desvio. Em um loop que roda milhões de vezes por segundo, isso se acumula.

**Polimorfismo em tempo de compilação (o que fizemos):**

```cpp
template <Hasher H, AttackStrategy A>
auto crack(const CrackConfig& cfg) -> std::expected<CrackResult, CrackError> {
    H hasher;
    // ... hasher.hash(candidato) é uma chamada direta, sofre inline
}
```

Quando você escreve `Engine::crack<SHA256Hasher, DictionaryAttack>(cfg)`, o compilador gera uma versão de `crack` com o SHA256Hasher fixo no código. A chamada `hash()` torna-se uma chamada de função direta que sofre inline no loop. Sem vtable, sem indireção, sem overhead.

O trade-off: você obtém uma cópia separada da função para cada combinação de hasher/ataque (12 no total: 4 hashers x 3 ataques). Isso aumenta ligeiramente o tamanho do binário. Para uma ferramenta CLI, isso é irrelevante.

## Conceitos como Contratos

Os conceitos (concepts) do C++20 definem o que um Hasher ou AttackStrategy deve fornecer:

```cpp
template <typename T>
concept Hasher = requires(T h, std::string_view input) {
    { h.hash(input) } -> std::same_as<std::string>;
    { T::name() } -> std::convertible_to<std::string_view>;
    { T::digest_length() } -> std::same_as<std::size_t>;
};
```

Este é um contrato em tempo de compilação. Se você escrever um novo hasher que não satisfaça `Hasher`, você receberá uma mensagem de erro clara na compilação, em vez de um erro misterioso de linker ou crash em tempo de execução. Ele documenta a interface sem exigir herança.

## Fluxo de Dados

### Fluxo do Ataque de Dicionário

```
1. CLI analisa --hash e --wordlist
   main.cpp despacha Engine::crack<SHA256Hasher, DictionaryAttack>(cfg)

2. Engine resolve a contagem de threads (hardware_concurrency se for 0)
   Cria o ThreadPool, inicia N jthreads

3. Cada thread chama DictionaryAttack::create(path, thread_id, N)
   create() abre o arquivo com mmap, conta as linhas,
   computa o intervalo de bytes desta thread [start_offset, end_offset)

4. Loop da thread:
   a. attack.next() lê a próxima palavra da região mmap
   b. Se o salt estiver definido, prefixa/anexa ao candidato
   c. hasher.hash(candidato) computa o digest
   d. Compara com o hash alvo
   e. Se coincidir: define a flag atomic 'found', armazena o resultado, interrompe (break)
   f. Incrementa o contador local, descarrega para o atomic compartilhado a cada 1024 iterações

5. Thread de exibição acorda a cada 100ms, lê atomics compartilhados,
   renderiza a barra de progresso no terminal

6. Todas as threads se juntam (jthread RAII)
   Engine retorna CrackResult ou CrackError::Exhausted
```

### Particionamento de Força Bruta

O keyspace total para um charset de tamanho C e comprimento máximo L é:

```
total = C^1 + C^2 + C^3 + ... + C^L
```

Cada thread recebe uma fatia contígua do espaço de índices plano. A Thread 0 recebe os índices `[0, total/N)`, a thread 1 recebe `[total/N, 2*total/N)`, e assim por diante. A conversão de um índice plano para uma string candidata usa decomposição de base mista, semelhante à conversão de um número decimal para uma base arbitrária, mas com saída de comprimento variável.

Isso significa que as threads nunca se comunicam durante o loop de quebra. Sem fila compartilhada, sem roubo de trabalho, sem locks. Cada thread é completamente independente.

## Modelo de Threading

### Estado Compartilhado

Apenas dois valores são compartilhados entre as threads:

```cpp
struct SharedState {
    alignas(64) std::atomic<bool> found{false};
    alignas(64) std::atomic<std::size_t> tested_count{0};
    std::mutex result_mutex;
    std::optional<std::string> result;
};
```

O `alignas(64)` coloca cada atomic em sua própria linha de cache. Sem isso, as escritas em `tested_count` de uma thread invalidariam as leituras de `found` em outras threads porque elas compartilham uma linha de cache de 64 bytes. Isso é chamado de "false sharing" e pode causar uma lentidão de 5x.

### Loteamento de Contadores

Em vez de fazer um incremento atômico em cada candidato:

```cpp
// Ruim: escrita atômica em cada iteração (tráfego de cache entre núcleos)
state.tested_count.fetch_add(1, std::memory_order_relaxed);
```

Cada thread mantém um contador local e o descarrega a cada 1024 iterações:

```cpp
++local_count;
if ((local_count & 0x3FF) == 0) {
    state.tested_count.fetch_add(local_count, std::memory_order_relaxed);
    local_count = 0;
}
```

Isso reduz o tráfego atômico entre núcleos em 1024x. A exibição de progresso lê uma contagem aproximada, o que é suficiente para uma atualização de UI a cada 100ms.

## Estratégia de Tratamento de Erros

Todas as operações que podem falhar retornam `std::expected<T, CrackError>`. Não há exceções na base de código.

```cpp
enum class CrackError {
    FileNotFound,
    InvalidHash,
    UnsupportedAlgorithm,
    OpenSSLError,
    InvalidConfig,
    Exhausted
};
```

O tipo de erro está na assinatura da função. Os chamadores são forçados a lidar com ele:

```cpp
auto attack = DictionaryAttack::create(path, tid, total);
if (!attack.has_value()) { return; }
```

Isso torna os caminhos de erro explícitos e visíveis. Você nunca precisa adivinhar se uma função pode lançar um erro.

## E/S Mapeada em Memória (Memory-Mapped I/O)

O DictionaryAttack usa `mmap` em vez de `std::ifstream` para ler wordlists:

```cpp
auto* mapped = static_cast<const char*>(
    mmap(nullptr, file_size, PROT_READ, MAP_PRIVATE, fd, 0));
madvise(mapped, file_size, MADV_SEQUENTIAL);
```

O conteúdo do arquivo é mapeado diretamente no espaço de endereçamento do processo. Ler uma palavra é aritmética de ponteiros (avançar até a próxima quebra de linha). Sem chamadas de sistema `read()`, sem cópias de buffer do kernel para o usuário. Para uma wordlist de 140MB como a rockyou.txt, isso faz diferença.

O wrapper RAII `MappedFile` cuida da limpeza:

```cpp
class MappedFile {
    ~MappedFile() {
        munmap(data_, size_);
        close(fd_);
    }
};
```

O DictionaryAttack possui um membro `MappedFile`. O compilador gera as operações de movimentação (move) corretas automaticamente (Regra do Zero).

## Configuração

Todos os números mágicos vivem em `Config.hpp`:

```cpp
namespace config {
constexpr unsigned DEFAULT_THREAD_COUNT = 0;
constexpr std::size_t DEFAULT_MAX_BRUTE_LENGTH = 6;
constexpr int PROGRESS_UPDATE_MS = 100;
constexpr std::string_view CHARSET_LOWER = "abcdefghijklmnopqrstuvwxyz";
// ...
}
```

A configuração em tempo de execução flui através de `CrackConfig`, preenchida pelo parser da CLI e passada para a Engine. Nenhuma global é alterada após a inicialização.

## Considerações de Desempenho

**Caminho crítico (Hot path)**: O loop interno em `Engine.hpp` é o de hash-e-comparação. Cada microssegundo economizado aqui se multiplica por milhões de iterações. O EVPHasher usa um codificador hex baseado em tabela de consulta em vez de `std::ostringstream`, evitando alocação no heap por hash.

**Gargalo**: Na CPU, o gargalo é a própria computação do hash (internos do EVP do OpenSSL). O código ao redor (geração de candidatos, comparação, atualização de contador) é insignificante em comparação. A aceleração por GPU (CUDA/OpenCL) seria o próximo passo para ganhos reais de desempenho.

**Memória**: mmap significa que a wordlist é carregada em páginas sob demanda pelo kernel. A pegada de memória real da ferramenta é pequena, independentemente do tamanho da wordlist.

## Decisões de Design

| Decisão                 | Alternativa               | Por que desta forma                                       |
| ----------------------- | ------------------------- | --------------------------------------------------------- |
| Políticas de template   | Interfaces virtuais       | Zero overhead no loop crítico                             |
| `std::expected`         | Exceções                  | Caminhos de erro explícitos, sem fluxo de controle oculto |
| `std::generator`        | Retornar `vector<string>` | Avaliação preguiçosa, terminação antecipada               |
| mmap                    | `std::ifstream`           | Zero-copy, sem syscall por linha                          |
| Particionamento de trab | Fila de roubo de trab     | Zero contenção entre threads                              |
| Atomics relaxados       | seq_cst                   | Progresso aproximado está ok, economiza custo de fence    |
| Engine header-only      | .cpp compilado            | O template deve estar no header de qualquer forma         |

## Extensibilidade

**Adicionando um novo algoritmo de hash:**

1. Adicione um alias de tipo em um novo header:
   ```cpp
   using SHA3_256Hasher = EVPHasher<EVP_sha3_256, "SHA3-256", 64>;
   ```
2. Adicione um caso em `HashDetector::detect()` (se o comprimento do digest for único)
3. Adicione um caso no switch de despacho do `main.cpp`
4. Escreva testes contra vetores conhecidos

**Adicionando uma nova estratégia de ataque:**

1. Crie uma classe que satisfaça o conceito `AttackStrategy` (precisa de `next()`, `total()`, `progress()`)
2. Adicione uma factory `create(path, thread_index, total_threads)`
3. Adicione um caminho de despacho em `main.cpp` e `Engine.hpp`

Ambos os pontos de extensão exigem zero alterações na Engine em si.

## Limitações

- Apenas CPU. Sem aceleração por GPU. Uma ferramenta dedicada como o hashcat em uma GPU moderna é ~1000x mais rápida.
- Sem suporte a bcrypt/scrypt/argon2. Estes exigem bibliotecas diferentes e estratégias de quebra fundamentalmente diferentes (a lentidão intencional muda a economia).
- Sem quebra distribuída. Cada execução usa uma única máquina.
- A flag `--chain-rules` gera um grande número de candidatos por palavra, o que pode tornar os ataques de regras lentos em wordlists grandes.
- Apenas Linux/macOS (mmap é POSIX). O Windows precisaria de `CreateFileMapping`.
