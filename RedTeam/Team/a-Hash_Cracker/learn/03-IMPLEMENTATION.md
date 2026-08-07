# Passo a Passo da Implementação

Este documento percorre o código real, explicando como cada componente funciona e por que foi construído dessa maneira.

## O Hasher Unificado

Os quatro algoritmos de hash (MD5, SHA1, SHA256, SHA512) usam a mesma API EVP do OpenSSL. As únicas diferenças são qual função de digest chamar e o comprimento da saída. Em vez de duplicar a implementação quatro vezes, um único template lida com todos eles:

```cpp
template <auto Algorithm, auto Name, std::size_t DigestLen>
class EVPHasher {
public:
    std::string hash(std::string_view input) const;
    static constexpr std::string_view name() { return Name; }
    static constexpr std::size_t digest_length() { return DigestLen; }
};
```

Cada hasher concreto é apenas um alias de tipo:

```cpp
using MD5Hasher    = EVPHasher<EVP_md5, "MD5", 32>;
using SHA256Hasher = EVPHasher<EVP_sha256, "SHA256", 64>;
```

Os parâmetros do template são resolvidos em tempo de compilação, então o compilador gera quatro implementações separadas de `hash()`, cada uma com a função de digest específica fixada no código. Mesmo desempenho que código escrito à mão, zero duplicação.

### O Caminho Crítico: Computação do Hash

O método `hash()` é a função mais crítica para o desempenho em toda a base de código. Cada senha candidata passa por ele. A implementação usa a interface EVP do OpenSSL com limpeza RAII:

```cpp
std::string EVPHasher::hash(std::string_view input) const {
    auto ctx = std::unique_ptr<EVP_MD_CTX, decltype(&EVP_MD_CTX_free)>(
        EVP_MD_CTX_new(), EVP_MD_CTX_free);

    if (!ctx
        || !EVP_DigestInit_ex(ctx.get(), Algorithm(), nullptr)
        || !EVP_DigestUpdate(ctx.get(), input.data(), input.size())
        || !EVP_DigestFinal_ex(ctx.get(), digest.data(), &len)) {
        return "";
    }

    // Converter bytes do digest para string hex
}
```

O `unique_ptr` com um deletor personalizado (`EVP_MD_CTX_free`) garante que o contexto seja liberado mesmo se algo falhar. O `if` encadeado verifica cada valor de retorno do OpenSSL. Retornar uma string vazia em caso de falha é o fail-safe correto: uma string vazia nunca coincidirá com um hash alvo válido, então uma execução de quebra degrada graciosamente em vez de produzir resultados errados.

### Codificação Hex com uma Tabela de Consulta

A abordagem ingênua usa `std::ostringstream` com `std::hex` e `std::setw(2)`. Isso cria um objeto de stream alocado no heap para cada hash. Com milhões de hashes por segundo, são milhões de alocações desnecessárias.

Em vez disso, uma tabela de consulta pré-computada converte cada byte em dois caracteres hexadecimais com zero alocação:

```cpp
static constexpr std::array<std::array<char, 2>, 256> HEX_TABLE = [] {
    std::array<std::array<char, 2>, 256> t{};
    constexpr char digits[] = "0123456789abcdef";
    for (int i = 0; i < 256; ++i) {
        t[i] = {digits[i >> 4], digits[i & 0xF]};
    }
    return t;
}();
```

A tabela é computada em tempo de compilação (lambda `constexpr`). Para cada valor de byte de 0 a 255, ela armazena os dois caracteres hex. O nibble alto (`i >> 4`) torna-se o primeiro caractere, o nibble baixo (`i & 0xF`) torna-se o segundo. O byte `0xAB` mapeia para `{'a', 'b'}`.

Converter o digest completo é um loop fechado:

```cpp
std::string hex(len * 2, '\0');
for (unsigned int i = 0; i < len; ++i) {
    hex[i * 2]     = HEX_TABLE[digest[i]][0];
    hex[i * 2 + 1] = HEX_TABLE[digest[i]][1];
}
```

Uma alocação para a string de saída (tamanho conhecido antecipadamente), duas consultas em array por byte. Esta é a mesma abordagem que o hashcat utiliza.

## Detecção Automática de Hash

`HashDetector::detect()` identifica o algoritmo de hash a partir da string hexadecimal:

```cpp
std::expected<HashType, CrackError> HashDetector::detect(std::string_view hash) {
    // Validar se todos os caracteres são hexadecimais
    if (!std::ranges::all_of(hash, is_hex)) {
        return std::unexpected(CrackError::InvalidHash);
    }

    // Corresponder comprimento ao algoritmo
    switch (hash.size()) {
        case config::MD5_HEX_LENGTH:    return HashType::MD5;
        case config::SHA1_HEX_LENGTH:   return HashType::SHA1;
        case config::SHA256_HEX_LENGTH: return HashType::SHA256;
        case config::SHA512_HEX_LENGTH: return HashType::SHA512;
        default: return std::unexpected(CrackError::InvalidHash);
    }
}
```

Isso funciona porque cada algoritmo produz um comprimento de digest único. MD5 tem sempre 32 caracteres hex, SHA1 tem 40, SHA256 tem 64, SHA512 tem 128. A validação hex captura erros de digitação e entradas que não são hash antes que a execução de quebra perca tempo.

## Ataque de Dicionário com mmap

### Mapeando o Arquivo em Memória

Em vez de ler a wordlist linha por linha com `std::ifstream` (que copia dados do espaço do kernel para o espaço do usuário em cada leitura), mapeamos o arquivo inteiro no espaço de endereçamento do processo:

```cpp
auto* mapped = static_cast<const char*>(
    mmap(nullptr, file_size, PROT_READ, MAP_PRIVATE, fd, 0));
madvise(mapped, file_size, MADV_SEQUENTIAL);
```

Após esta chamada, `mapped` é um ponteiro para o conteúdo do arquivo na memória. Ler uma palavra é apenas aritmética de ponteiros. A dica `MADV_SEQUENTIAL` informa ao kernel para buscar páginas à frente da posição de leitura atual, já que estamos escaneando linearmente.

### Particionamento de Threads

Para N threads, o arquivo é dividido em N intervalos contando as quebras de linha:

```cpp
std::size_t lines_per_thread = total_lines / total_threads;
std::size_t my_start_line = thread_index * lines_per_thread + ...;
```

Cada thread caminha para frente através do arquivo para encontrar o offset de bytes de sua linha inicial, e então escaneia seu intervalo de forma independente. Sem cursor compartilhado, sem locks, sem coordenação entre threads durante o loop de quebra.

### Lendo Palavras

O método `next()` escaneia do offset atual até a próxima quebra de linha:

```cpp
std::expected<std::string, AttackComplete> DictionaryAttack::next() {
    while (current_offset_ < end_offset_) {
        // Encontrar quebra de linha
        while (line_end < end_offset_ && file_.data()[line_end] != '\n') {
            ++line_end;
        }

        // Remover \r para quebras de linha do Windows
        if (word_end > line_start && file_.data()[word_end - 1] == '\r') {
            --word_end;
        }

        // Pular linhas vazias (iterativo, não recursivo)
        if (word_end > line_start) {
            return std::string(file_.data() + line_start, word_end - line_start);
        }
    }
    return std::unexpected(AttackComplete{});
}
```

Linhas vazias são puladas iterativamente. Uma versão anterior usava recursão (`return next()`), mas uma wordlist com muitas linhas vazias consecutivas poderia, teoricamente, estourar a pilha.

## Geração de Keyspace para Força Bruta

### Computando o Keyspace Total

Para um charset de tamanho C e comprimento máximo L:

```cpp
std::size_t compute_keyspace(std::size_t charset_size, std::size_t max_length) {
    std::size_t total = 0;
    std::size_t power = 1;
    for (std::size_t len = 1; len <= max_length; ++len) {
        power *= charset_size;
        total += power;
    }
    return total;
}
```

Isso computa `C + C^2 + C^3 + ... + C^L`. Para letras minúsculas (C=26) e L=4, isso é 26 + 676 + 17576 + 456976 = 475.254.

### Conversão de Índice para Candidato

Cada candidato possui um índice plano único no intervalo `[0, total)`. Converter um índice para uma string é como converter um número para uma base de comprimento variável:

```cpp
std::string index_to_candidate(std::size_t index) const {
    // Determinar em qual balde de comprimento este índice cai
    std::size_t cumulative = 0;
    std::size_t power = base;
    std::size_t length = 1;
    while (cumulative + power <= index && length < max_length_) {
        cumulative += power;
        ++length;
        power *= base;
    }

    // Converter o offset dentro desse balde para caracteres
    std::size_t offset = index - cumulative;
    std::string result(length, charset_[0]);
    for (std::size_t i = length; i > 0; --i) {
        result[i - 1] = charset_[offset % base];
        offset /= base;
    }
    return result;
}
```

Este é o mesmo algoritmo de conversão de um número decimal para base-N, exceto que os "dígitos" são caracteres do charset. O índice 0 mapeia para a primeira string de um único caractere, e os índices aumentam através de todas as strings de um caractere, depois todas as strings de dois caracteres, e assim por diante.

## Mutações Baseadas em Regras com std::generator

### Regras Individuais

Cada regra é uma coroutine que produz mutações de forma preguiçosa (lazily):

```cpp
std::generator<std::string> RuleSet::leet_speak(std::string_view word) {
    std::string result(word);
    for (auto& c : result) {
        auto lower = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
        for (auto [from, to] : LEET_MAP) {
            if (lower == from) { c = to; break; }
        }
    }
    co_yield std::move(result);
}
```

A palavra-chave `co_yield` suspende a função e retorna o valor. Quando o chamador solicita o próximo valor, a execução recomeça de onde parou. Para regras simples como leet speak, há apenas um yield. Para append_digits, há 1000 yields (um por dígito de 0 a 999).

### Compondo Regras

`apply_all()` delega para cada regra usando `std::ranges::elements_of`:

```cpp
std::generator<std::string> RuleSet::apply_all(std::string_view word) {
    co_yield std::ranges::elements_of(capitalize_first(word));
    co_yield std::ranges::elements_of(uppercase_all(word));
    co_yield std::ranges::elements_of(leet_speak(word));
    co_yield std::ranges::elements_of(append_digits(word));
    co_yield std::ranges::elements_of(prepend_digits(word));
    co_yield std::ranges::elements_of(reverse(word));
    co_yield std::ranges::elements_of(toggle_case(word));
}
```

`elements_of` é um recurso do C++23 para delegar para sub-geradores. Sem ele, você escreveria `for (auto&& s : sub_gen) { co_yield std::move(s); }` para cada regra, o que é verboso e tem overhead de O(profundidade) por elemento.

### O Mapa Leet

A tabela de substituição usa um array constexpr em vez de `std::unordered_map`:

```cpp
static constexpr std::array<std::pair<char, char>, 6> LEET_MAP = {{
    {'a', '@'}, {'e', '3'}, {'i', '1'},
    {'o', '0'}, {'s', '$'}, {'t', '7'}
}};
```

Seis entradas. Um escaneamento linear sobre 6 elementos é mais rápido do que computar um hash, procurar um balde e desreferenciar um ponteiro de nó. O `unordered_map` também alocaria no heap no momento da construção, o que o array constexpr evita inteiramente.

## O Template da Engine

A Engine conecta tudo. É uma função de template estática em um header porque deve ser instanciada para cada combinação de hasher/ataque:

```cpp
template <Hasher H, AttackStrategy A>
auto Engine::crack(const CrackConfig& cfg)
    -> std::expected<CrackResult, CrackError>
```

### Lambda do Worker

Cada thread executa uma lambda que cria sua própria partição de ataque, sua própria instância de hasher e faz um loop até encontrar uma correspondência ou esgotar os candidatos:

```cpp
pool.run([&](unsigned tid, unsigned total, SharedState& state) {
    H hasher;
    auto attack = create_attack();  // particionado para esta thread

    std::size_t local_count = 0;
    while (!state.found.load(std::memory_order_relaxed)) {
        auto candidate = attack->next();
        if (!candidate.has_value()) { break; }

        std::string to_hash = *candidate;
        // Aplicar salt se configurado...

        if (hasher.hash(to_hash) == cfg.target_hash) {
            state.tested_count.fetch_add(local_count, std::memory_order_relaxed);
            state.set_result(std::move(*candidate));
            break;
        }

        ++local_count;
        if ((local_count & 0x3FF) == 0) {
            state.tested_count.fetch_add(local_count, std::memory_order_relaxed);
            local_count = 0;
        }
    }
    state.tested_count.fetch_add(local_count, std::memory_order_relaxed);
});
```

Detalhes chave:

- A ordenação de memória `relaxed` na flag `found` é intencional. Não precisamos de visibilidade imediata. Se uma thread definir `found` e outra thread rodar por mais algumas iterações antes de ver isso, está tudo bem. O custo de uma ordenação mais forte (barreiras de memória em cada iteração) não vale a garantia de parar instantaneamente.
- O contador local agrupa atualizações atômicas a cada 1024 iterações (`& 0x3FF` é uma verificação de máscara de bits, mais rápida que módulo). O `fetch_add` final após o loop descarrega qualquer contagem restante.

## Despacho da CLI

A função main usa uma lambda de template para despachar com base no tipo de hash sem polimorfismo em tempo de execução:

```cpp
template <Hasher H>
static auto dispatch_attack(const CrackConfig& cfg)
    -> std::expected<CrackResult, CrackError> {
    if (cfg.bruteforce) return Engine::crack<H, BruteForceAttack>(cfg);
    if (cfg.use_rules) return Engine::crack<H, RuleAttack>(cfg);
    return Engine::crack<H, DictionaryAttack>(cfg);
}

static auto dispatch_hasher(HashType type, const CrackConfig& cfg)
    -> std::expected<CrackResult, CrackError> {
    switch (type) {
        case HashType::MD5:    return dispatch_attack<MD5Hasher>(cfg);
        case HashType::SHA1:   return dispatch_attack<SHA1Hasher>(cfg);
        case HashType::SHA256: return dispatch_attack<SHA256Hasher>(cfg);
        case HashType::SHA512: return dispatch_attack<SHA512Hasher>(cfg);
    }
    return std::unexpected(CrackError::UnsupportedAlgorithm);
}
```

O `switch` é o único ponto onde uma decisão em tempo de execução é tomada. Cada caso instancia o template da Engine com um tipo de hasher concreto. A partir desse ponto, tudo é resolvido em tempo de compilação.

## Estratégia de Testes

A suíte de testes possui 38 testes organizados por componente:

**Testes de Hasher** verificam contra vetores de resposta conhecida do NIST. Se `SHA256Hasher::hash("password")` não produzir exatamente `5e884898da28...`, a implementação está errada. Estes são os testes mais importantes porque um bug sutil de hashing faria com que toda a ferramenta falhasse silenciosamente.

**Testes de HashDetector** verificam a detecção de tipo (baseada no comprimento) e a validação de entrada (rejeição de não-hex).

**Testes de DictionaryAttack** verificam a leitura de palavras, o particionamento de threads (duas threads juntas leem todas as palavras), a contagem total e o tratamento de erro de arquivo não encontrado.

**Testes de BruteForceAttack** verificam a matemática do keyspace, a completude da geração de candidatos (todas as combinações produzidas) e o particionamento de threads (sem duplicatas, sem lacunas).

**Testes de RuleSet** verificam cada regra de mutação contra a saída esperada. O teste `AllRulesProduceMutations` confirma que a contagem total excede 2000 (7 regras aplicadas a "password", com append_digits e prepend_digits produzindo 1000 cada).

**Testes de Engine** são testes de integração. `CracksSHA256WithDictionary` executa o pipeline completo com 2 threads e verifica se ele encontra "password". `CracksWithSalt` verifica se o prefixo de salt funciona de ponta a ponta.

## Armadilhas Comuns

**Esquecer de descarregar o contador local**: Se uma thread encontrar a senha e interromper sem descarregar o `local_count`, a contagem final testada estará errada. O `fetch_add` após o loop resolve isso.

**Comparar hashes com caixas diferentes**: O SHA256 pode produzir hex em maiúsculas em algumas plataformas. Nosso codificador hex sempre produz minúsculas, e o hash alvo é usado como está da CLI. Se alguém colar um hash em maiúsculas, ele não coincidirá. Uma ferramenta de produção real normalizaria ambos para minúsculas.

**mmap e truncamento de arquivo**: Se o arquivo da wordlist for modificado enquanto a ferramenta estiver rodando, o comportamento é indefinido. `MAP_PRIVATE` ajuda (recebemos um snapshot copy-on-write), mas para uma ferramenta que processa um arquivo uma vez e sai, isso não é uma preocupação prática.
