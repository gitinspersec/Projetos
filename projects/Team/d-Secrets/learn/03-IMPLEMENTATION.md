# Passo a Passo da Implementação

Este documento percorre os principais arquivos de código do Portia. Para cada seção, veremos o que o código faz, por que foi projetado dessa forma e o que deve ser observado.

## Entropia de Shannon (`internal/rules/entropy.go`)

O módulo de entropia responde a uma pergunta: "Esta string é aleatória o suficiente para ser um segredo?"

**Função ShannonEntropy:**
A função recebe uma string e um charset (o conjunto de todos os caracteres possíveis). Ela conta quantas vezes cada caractere aparece, computa a probabilidade de cada caractere (contagem / total) e, em seguida, soma `-p * log₂(p)` para todos os caracteres.

O parâmetro charset é importante para o cálculo. Se você computar a entropia usando apenas os caracteres presentes na string, toda string com todos os caracteres únicos obteria a mesma entropia. Ao computar contra o charset completo (por exemplo, todos os 62 caracteres alfanuméricos), o resultado reflete quanto do espaço de aleatoriedade disponível a string realmente utiliza.

**Função DetectCharset:**
Antes de computar a entropia, o Portia adivinha o charset:

- Se todos os caracteres forem `0-9a-f`, é hex. Usa o charset hex de 16 caracteres.
- Se todos os caracteres forem `A-Za-z0-9+/=`, é base64. Usa o charset base64 de 64 caracteres.
- Caso contrário, usa o charset alfanumérico de 62 caracteres como padrão.

Isso importa porque uma string hex `deadbeefcafe` tem entropia diferente dependendo se você a avalia contra 16 caracteres possíveis (hex) ou 62 (alfanumérico). A avaliação hex é mais generosa, identificando-a corretamente como moderadamente aleatória dentro de seu charset.

**Limites na prática:**

- `password = "admin"` → entropia ~2.3 (abaixo da maioria dos limites, filtrada)
- `password = "xK9mP2vL5nQ8jR3t"` → entropia ~4.0 (acima do limite, sinalizada)
- `AKIAIOSFODNN7EXAMPLE` → sem verificação de entropia necessária (regra estrutural, o prefixo AKIA é suficiente)

## Registro de Regras (`internal/rules/registry.go`)

O registro é um mapa simples do ID da regra para a struct da regra, com alguns métodos principais:

**MatchKeywords** é a função crítica para o desempenho. Para cada regra no registro, ela verifica se alguma das palavras-chave da regra aparece (insensível a maiúsculas) na string de conteúdo. Isso é O(regras * palavras-chave * comprimento_do_conteúdo) no pior caso, mas na prática, `strings.Contains` com palavras-chave curtas contra chunks de comprimento médio é rápido.

O valor de retorno é um slice de regras correspondentes. Se um chunk contém `password`, o registro retorna todas as regras que possuem `password` como palavra-chave. Se o chunk contém `AKIA`, ele retorna as regras de chave de acesso AWS.

**Allowlists globais** são definidas na parte inferior de `registry.go`:

- `GlobalPathAllowlist` - padrões regex para caminhos a serem pulados (go.mod, package-lock.json, node_modules/, vendor/, extensões binárias, JS minificado)
- `GlobalValueAllowlist` - padrões regex para valores a serem ignorados (example, test, dummy, fake, placeholder, YOUR_API_KEY, xxxx..., TODO, CHANGEME)

Estas são separadas das allowlists por regra. Uma allowlist por regra (como a `AKIAIOSFODNN7EXAMPLE` da AWS) aplica-se apenas àquela regra específica. As allowlists globais aplicam-se a todas as regras.

## Regras de Detecção (`internal/rules/builtin.go`)

Cada regra é uma struct `types.Rule` com estes campos:

```go
type Rule struct {
    ID          string         // identificador único como "aws-access-key-id"
    Description string         // descrição legível "AWS Access Key ID"
    Severity    Severity       // SeverityCritical, SeverityHigh, etc.
    Keywords    []string       // pré-filtro rápido: ["AKIA", "ABIA", "ACCA", "ASIA"]
    Pattern     *regexp.Regexp // a regex de detecção real
    SecretGroup int            // qual grupo de captura contém o segredo (0=toda a correspondência)
    Entropy     *float64       // limite mínimo de entropia (nil = sem verificação)
    Allowlist   Allowlist      // overrides de path/value/stopword por regra
    SecretType  SecretType     // classificação: APIKey, Token, Password, etc.
}
```

**Analisando a regra de chave de acesso AWS:**

```go
{
    ID:          "aws-access-key-id",
    Description: "AWS Access Key ID",
    Severity:    types.SeverityCritical,
    Keywords:    []string{"AKIA", "ABIA", "ACCA", "ASIA"},
    Pattern:     regexp.MustCompile(`\b((?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16})\b`),
    SecretGroup: 1,
    SecretType:  types.SecretTypeAPIKey,
}
```

- **Keywords**: Quatro prefixos possíveis. Se o chunk não contiver nenhuma dessas quatro strings, pule esta regra inteiramente.
- **Pattern**: Fronteira de palavra `\b`, então um dos quatro prefixos, então exatamente 16 caracteres alfanuméricos maiúsculos, então fronteira de palavra. A correspondência inteira é capturada no grupo 1.
- **SecretGroup**: 1 significa extrair do primeiro grupo entre parênteses (a chave inteira).
- **Sem limite de entropia**: Chaves AWS possuem uma estrutura fixa, então a validação de entropia não é necessária. O prefixo + comprimento é suficiente.
- **Sem allowlist**: A allowlist de valor global já captura `AKIAIOSFODNN7EXAMPLE`.

**Analisando a regra de senha genérica:**

```go
{
    ID:          "generic-password",
    Description: "Password in Assignment",
    Severity:    types.SeverityHigh,
    Keywords:    []string{"password", "passwd", "pwd"},
    Pattern:     regexp.MustCompile(`(?i)(?:password|passwd|pwd)\s*[:=]\s*['"]([^'"]{8,})['"]`),
    SecretGroup: 1,
    Entropy:     ptr(3.5),
    SecretType:  types.SecretTypePassword,
}
```

- **Keywords**: Três variações de "password"
- **Pattern**: Correspondência insensível a maiúsculas para password/passwd/pwd, seguida por `:` ou `=`, espaço em branco opcional, e então uma string entre aspas de pelo menos 8 caracteres. O grupo 1 captura apenas o valor da senha.
- **Limite de entropia**: 3.5 bits. Isso filtra `password = "admin123"` (baixa entropia) enquanto captura `password = "xK9mP2vL5nQ8jR3t"` (alta entropia).
- A função auxiliar `ptr()` cria um `*float64` a partir de um literal, já que o Go não permite obter o endereço de uma constante diretamente.

## Directory Source (`internal/source/directory.go`)

A source de diretório percorre um sistema de arquivos e produz chunks:

**Callback WalkDir**: Para cada entrada do sistema de arquivos:

1. Verifica o cancelamento do contexto (permite desligamento limpo)
2. Pula diretórios conhecidos como não interessantes (`.git`, `node_modules`, `vendor`, `__pycache__`, `.venv`)
3. Verifica se o caminho relativo corresponde a algum padrão de exclusão
4. Pula extensões de arquivos binários (`.png`, `.jpg`, `.exe`, `.zip`, etc.)
5. Verifica o tamanho do arquivo contra o limite máximo (padrão 1MB)
6. Se todas as verificações passarem, chama `emitChunks`

**emitChunks**: Abre o arquivo e o lê linha por linha usando `bufio.Scanner`:

- Acumula linhas em um `strings.Builder`
- A cada 50 linhas, envia o texto acumulado como um `types.Chunk` com o caminho relativo do arquivo e o número da linha inicial
- Após o loop, envia quaisquer linhas restantes como um chunk final

**Por que chunks de 50 linhas?** Este é um trade-off entre uso de memória e precisão de detecção. Chunks maiores usam mais memória por worker. Chunks menores podem dividir um segredo de múltiplas linhas entre dois chunks. 50 linhas é um meio-termo prático: a maioria dos segredos cabe em uma única linha, e 50 linhas é pequeno o suficiente para processar rapidamente.

**Função isExcluded**: Verifica dois padrões:

- `filepath.Match` contra o nome do arquivo (apenas o nome base). Isso lida com padrões como `*.env`
- `strings.Contains` contra o caminho relativo completo. Isso lida com padrões como `test/fixtures`

## Git Source (`internal/source/git.go`)

A source git usa o go-git v5 para escaneamento do histórico do repositório sem depender do binário `git`.

**scanHistory**: Abre o repositório com `git.PlainOpen`, então:

1. Obtém um iterador de commits filtrado por branch (se especificado)
2. Para cada commit, verifica se a data é posterior a `--since` e dentro de `--depth`
3. Obtém a árvore do commit e percorre todas as entradas
4. Para cada blob (arquivo), lê o conteúdo, verifica tamanho/exclusões/extensões binárias
5. Divide em chunks de 50 linhas com metadados do commit (SHA, autor, data)

**scanStaged**: Para escaneamento de pre-commit:

1. Abre o repositório e lê o índice git (área de staging)
2. Para cada entrada do índice, lê o conteúdo do blob do object store
3. Produz chunks apenas para os arquivos que estão atualmente em staging

**readBlob**: Lê um objeto blob do git para uma string:

```go
func readBlob(obj *object.Blob) (string, error) {
    reader, err := obj.Reader()
    if err != nil {
        return "", err
    }
    defer reader.Close()
    data, err := io.ReadAll(reader)
    if err != nil {
        return "", err
    }
    return string(data), nil
}
```

Isso usa `io.ReadAll` em vez de `strings.Builder.ReadFrom` porque o `strings.Builder` não possui um método `ReadFrom`. Um erro comum ao trabalhar com blobs do go-git.

## Detector (`internal/engine/detector.go`)

O detector é onde as regras encontram o conteúdo:

**Fluxo da função Detect:**

1. Chama `registry.MatchKeywords(chunk.Content)` para obter apenas as regras relevantes
2. Se nenhuma regra corresponder às palavras-chave, retorna nil imediatamente (caminho rápido)
3. Divide o conteúdo do chunk em linhas
4. Para cada regra correspondente, para cada linha:
   - Executa `rule.Pattern.FindAllStringSubmatchIndex(line, -1)` para encontrar todas as correspondências
   - Para cada correspondência, chama `extractSecret` para obter o segredo do grupo de captura
   - Se a regra tiver um limite de entropia, computa a entropia e pula se estiver abaixo do limite
   - Chama `FilterFinding` para verificações de falsos positivos
   - Se todas as verificações passarem, anexa às descobertas

**Função extractSecret:**

```go
func extractSecret(line string, loc []int, group int) string {
    if group > 0 && len(loc) > group*2+1 {
        start := loc[group*2]
        end := loc[group*2+1]
        if start >= 0 && end >= 0 {
            return line[start:end]
        }
    }
    if len(loc) >= 2 {
        return line[loc[0]:loc[1]]
    }
    return ""
}
```

O array `loc` de `FindAllStringSubmatchIndex` contém pares de índices de início/fim para cada grupo de captura. O grupo 0 é a correspondência inteira (índices 0,1), o grupo 1 é o primeiro grupo entre parênteses (índices 2,3), etc. Se o grupo solicitado não existir ou tiver índices negativos (significando que o grupo não participou da correspondência), recorre à correspondência inteira.

## Filter (`internal/engine/filter.go`)

A cadeia de filtros é a defesa final contra falsos positivos:

**IsStopword**: A correção crítica aqui foi mudar da correspondência de substring para a correspondência exata dividida por delimitadores. A implementação original verificava se qualquer stopword era uma substring do segredo. Isso fazia com que `AKIAIOSFODNN7EXAMPLE` correspondesse porque "example" aparecia como uma substring. A correção:

```go
parts := strings.FieldsFunc(lower, func(r rune) bool {
    return r == '_' || r == '-' || r == '.' || r == '/'
})
for _, part := range parts {
    if _, ok := stopwords[part]; ok {
        return true
    }
}
```

Isso divide em caracteres delimitadores comuns e verifica cada parte independentemente. `AKIAIOSFODNN7EXAMPLE` não se divide em "example" porque não há delimitador antes dele. Mas `module_controller_config` se divide em ["module", "controller", "config"], todos os quais são stopwords.

**Orquestração do FilterFinding:**

```
IsPlaceholder(secret) → true = pular
IsTemplated(secret)   → true = pular
IsStopword(secret)    → true = pular
rule.Allowlist.Values  → correspondência = pular
GlobalPathAllowlist    → correspondência = pular
rule.Allowlist.Paths   → correspondência = pular
Todas as verificações passam → descoberta é real
```

Cada camada é independente. Uma descoberta só precisa ser capturada por uma camada para ser filtrada.

## Pipeline (`internal/engine/pipeline.go`)

O pipeline conecta tudo com as primitivas de concorrência do Go:

**Configuração:**

```go
chunks := make(chan types.Chunk, p.workers*4)
findingsCh := make(chan types.Finding, p.workers*4)
g, gctx := errgroup.WithContext(ctx)
```

Dois canais com buffer: um para chunks (source → workers), um para descobertas (workers → collector). O tamanho do buffer é `workers * 4` para equilíbrio de backpressure.

**Goroutine Source:** Executa `src.Chunks(gctx, chunks)` e usa `defer close(chunks)`. Quando a source termina (ou o contexto é cancelado), o canal fecha e os workers processam os itens restantes.

**Goroutines Worker:** Cada worker faz um loop sobre o canal de chunks:

```go
for chunk := range chunks {
    if gctx.Err() != nil {
        return gctx.Err()
    }
    results := p.detector.Detect(chunk)
    for _, f := range results {
        findingsCh <- f
    }
}
```

Os workers compartilham um `sync.WaitGroup` separado do errgroup. Quando todos os workers terminam, uma goroutine fecha o canal de descobertas.

**Goroutine Collector:** Loop simples que coleta todas as descobertas em um slice:

```go
for f := range findingsCh {
    mu.Lock()
    allFindings = append(allFindings, f)
    mu.Unlock()
}
```

O mutex não é estritamente necessário, já que há apenas uma goroutine de collector, mas ele protege contra mudanças futuras e deixa o detector de data race feliz.

**Deduplicação:** Após a conclusão de todas as goroutines, o `dedup` remove descobertas duplicadas criando uma chave composta de `ruleID + "|" + filePath + "|" + secret + "|" + commitSHA`. Isso lida com casos onde o mesmo segredo aparece em chunks sobrepostos ou em múltiplos commits do git.

## Cliente HIBP (`internal/hibp/client.go`)

O cliente HIBP verifica segredos contra o banco de dados de violações de Troy Hunt:

**Hashing SHA-1:** O segredo é hasheado com SHA-1 (sim, o SHA-1 está criptograficamente quebrado, mas o HIBP o usa como uma chave de busca, não para segurança). O hash é convertido para maiúsculas e dividido: os primeiros 5 caracteres são o prefixo, os 35 restantes são o sufixo.

**Consulta k-anonymity:** Envia o prefixo para `https://api.pwnedpasswords.com/range/{prefix}`. A API retorna todos os sufixos de hash que compartilham esse prefixo, junto com as contagens de ocorrência:

```
0018A45C4D1DEF81644B54AB7F969B88D65:21
00D4F6E8FA6EECAD2A3AA415EEC418D38EC:2
```

O cliente analisa cada linha, divide em `:`, e verifica se algum sufixo corresponde ao nosso. Se sim, o segredo foi encontrado em uma violação.

**Cache LRU:** Antes de fazer uma chamada de API, verifica o cache usando o prefixo de 5 caracteres como chave. O cache LRU armazena 10.000 entradas. Como cada prefixo cobre todos os segredos com aquele prefixo, o cache é muito eficaz ao escanear grandes bases de código com segredos semelhantes.

**Circuit breaker:** Envolve a chamada HTTP em um `gobreaker.CircuitBreaker`. Configurações:

- Máximo de falhas consecutivas: 5
- Timeout (período de recuperação): 60 segundos
- Após 5 falhas seguidas, o circuito abre e retorna imediatamente um erro para todas as chamadas subsequentes. Após 60 segundos, entra no estado half-open e permite que uma requisição passe para testar se a API voltou.

**Campo baseURL:** O cliente possui um campo `baseURL` que assume como padrão a URL real da API do HIBP. Nos testes, isso é sobrescrito para apontar para um `httptest.Server`. Isso evita a necessidade de mocking baseado em interface e mantém o código simples.

## Reporters (`internal/reporter/`)

**Terminal reporter** (`terminal.go`):

- Ordena as descobertas por severidade (CRITICAL primeiro)
- Cores: vermelho para CRITICAL, vermelho (sem negrito) para HIGH, amarelo para MEDIUM, ciano para LOW
- Mascara segredos: mostra os primeiros 4-6 e os últimos 4-6 caracteres com asteriscos entre eles
- Trunca SHAs de commit para 8 caracteres para legibilidade
- Mostra valores de entropia quando presentes
- Mostra o status de violação HIBP e a contagem quando verificado

**JSON reporter** (`json.go`):

- Produz um objeto JSON com um array `findings` e um objeto `summary`
- Cada descoberta possui: rule_id, description, severity, secret (mascarado), entropy, file, line, commit, author, hibp_status, breach_count
- O resumo possui: total_findings, total_rules, duration, hibp_checked, hibp_breached

**SARIF reporter** (`sarif.go`):

- Produz um JSON compatível com SARIF v2.1.0
- Mapeia a severidade do Portia para níveis SARIF: CRITICAL/HIGH = "error", MEDIUM = "warning", LOW = "note"
- Cada descoberta torna-se um `result` SARIF com `ruleId`, `message`, `level` e `locations`
- Definições de regras são incluídas no array `tool.driver.rules`
- Propriedades personalizadas (entropia, status HIBP, segredo mascarado) vão em `result.properties`
