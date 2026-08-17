# Guia de Implementação

Este documento percorre o código real. Construiremos os recursos principais passo a passo e explicaremos as decisões ao longo do caminho.

## Passo a Passo da Estrutura de Arquivos

```
simple-vulnerability-scanner/
├── cmd/angela/
│   └── main.go              # 7 linhas: importa cli, chama Execute()
├── internal/
│   ├── cli/
│   │   ├── update.go        # 440 linhas: comandos cobra, orquestração
│   │   └── output.go        # 330 linhas: formatação de terminal, cores
│   ├── pypi/
│   │   ├── client.go        # 200 linhas: cliente HTTP, concorrência
│   │   ├── cache.go         # 88 linhas: cache baseado em arquivo com ETag
│   │   └── version.go       # 280 linhas: parser PEP 440 e comparação
│   ├── osv/
│   │   └── client.go        # 290 linhas: scanner de vulnerabilidades
│   ├── pyproject/
│   │   ├── parser.go        # 90 linhas: extração de dependências TOML
│   │   └── writer.go        # 118 linhas: edição de TOML baseada em regex
│   ├── requirements/
│   │   ├── parser.go        # 70 linhas: parser de requirements.txt
│   │   └── writer.go        # 80 linhas: atualizador de requirements.txt
│   ├── config/
│   │   └── config.go        # 70 linhas: carregador de configuração
│   └── ui/
│       ├── banner.go        # ASCII art e branding
│       ├── color.go         # Funções auxiliares de cor
│       ├── spinner.go       # Spinner de terminal
│       └── symbol.go        # Símbolos Unicode
└── pkg/types/
    └── types.go             # 40 linhas: estruturas de dados compartilhadas
```

## Construindo o Parser de Versão PEP 440

### Passo 1: Definir a Estrutura da Versão

O que estamos construindo: Um parser que lida com cada variante de strings de versão Python conforme a PEP 440.

Crie o tipo `Version` em `internal/pypi/version.go:41-51`:

```go
type Version struct {
    Raw     string
    Epoch   int
    Release []int    // [1, 2, 3] para "1.2.3"
    PreKind string   // "a", "b", ou "rc"
    PreNum  int
    Post    int      // -1 significa ausente
    Dev     int      // -1 significa ausente
    Local   string
}
```

**Por que este código funciona:**

- `Raw`: Armazena a entrada original para depuração. Ao comparar `"v1.0.0"` vs `"1.0.0"`, você quer saber qual forma o usuário escreveu.
- `Release []int`: Slice de comprimento variável lida com `"1.0"`, `"1.0.0"`, `"1.0.0.0"`, etc. Versões Python podem ter profundidade arbitrária.
- `Post int` e `Dev int` usam `-1` como sentinela. Isso distingue "não presente" de "presente com valor 0". Tanto `1.0.post0` quanto `1.0.post` são PEP 440 válidos (zero implícito), mas diferentes de `1.0` (sem componente post).

**Erros comuns aqui:**

```go
// Errado: não consegue distinguir "ausente" de "zero"
type Version struct {
    Post int  // 0 é "sem post-release" ou "post0"?
}

// Por que isso falha: Version("1.0").Post == 0 e Version("1.0.post0").Post == 0
// são idênticos, mas a PEP 440 os trata como iguais de qualquer forma. O problema real é
// na ordenação: o sentinela math.MinInt em preKey() depende de -1 significando "ausente"
```

### Passo 2: Construir o Padrão Regex

Agora precisamos analisar as strings de versão para esta estrutura.

Em `internal/pypi/version.go:53-63`:

```go
var versionRe = regexp.MustCompile(
    `(?i)^v?` +
        `(?:(\d+)!)?` +                  // Epoch (opcional)
        `(\d+(?:\.\d+)*)` +              // Segmentos de release (obrigatório)
        `(?:[-_.]?(alpha|a|beta|b|...|rc)[-_.]?(\d*))?` +  // Pre-release
        `(?:[-_.]?(post|rev|r)[-_.]?(\d*)|-(\d+))?` +      // Post-release
        `(?:[-_.]?(dev)[-_.]?(\d*))?` +  // Dev release
        `(?:\+([a-z0-9]...))?$`,         // Versão local
)
```

**O que está acontecendo:**

1. `(?i)` torna a regex insensível a maiúsculas. `1.0Alpha1` torna-se `1.0a1`.
2. `^v?` remove o prefixo `v` inicial. Desenvolvedores frequentemente escrevem `v1.0.0` em tags de git.
3. `(\d+)` seguido por `!` captura a época. O `?` torna todo o grupo `(?:...)?` opcional.
4. `\d+(?:\.\d+)*` corresponde aos segmentos de release. `\d+` é o primeiro segmento (obrigatório), `(?:\.\d+)*` são zero ou mais segmentos `.N` adicionais.
5. O grupo pre-release corresponde a `alpha`, `a`, `beta`, `b`, `preview`, `pre`, `c`, ou `rc`, com separadores opcionais (`-`, `_`, `.`), seguidos por um número opcional.
6. Post-release tem duas formas: explícita (`post3`) ou hífen-número implícito (`-3`).
7. Versões dev e locais seguem padrões semelhantes.

**Por que fazemos desta forma:**
Grupos de captura de regex única eliminam múltiplas passagens na string. Uma alternativa seria dividir por `.` e verificar cada parte, mas isso falha em `1.0.post1.dev2` (qual ponto pertence a qual componente?).

**Abordagens alternativas:**

- Máquina de estados escrita à mão: 3x mais código, mesma funcionalidade, sem ganho real de desempenho.
- Divisão de string por delimitadores: Não lida com a sintaxe post implícita `-3` ou separadores variados.

### Passo 3: Analisar a String de Versão

Em `internal/pypi/version.go:66-112`:

```go
func ParseVersion(s string) (Version, error) {
    normalized := strings.ToLower(strings.TrimSpace(s))
    m := versionRe.FindStringSubmatch(normalized)
    if m == nil {
        return Version{}, fmt.Errorf("%w: %q", ErrInvalidVersion, s)
    }

    v := Version{
        Raw:  s,
        Post: -1,  // Sentinela para "não presente"
        Dev:  -1,
    }

    // m[1] é a época
    if m[1] != "" {
        v.Epoch = mustAtoi(m[1])
    }

    // m[2] são os segmentos de release como "1.2.3"
    for _, seg := range strings.Split(m[2], ".") {
        v.Release = append(v.Release, mustAtoi(seg))
    }

    // m[3] é o tipo de pre-release, m[4] é o número do pre-release
    if m[3] != "" {
        v.PreKind = normalizePreKind(m[3])  // "alpha" → "a", "preview" → "rc"
        v.PreNum = optionalAtoi(m[4])
    }

    // Post-release: explícito (m[5]/m[6]) ou hífen-número implícito (m[7])
    switch {
    case m[5] != "":
        v.Post = optionalAtoi(m[6])
    case m[7] != "":
        v.Post = mustAtoi(m[7])
    }

    // Dev release
    if m[8] != "" {
        v.Dev = optionalAtoi(m[9])
    }

    v.Local = m[10]

    return v, nil
}
```

**Partes principais explicadas:**

**`mustAtoi()` e `optionalAtoi()`** (linhas 242-250):

```go
func mustAtoi(s string) int {
    n, _ := strconv.Atoi(s)
    return n
}

func optionalAtoi(s string) int {
    if s == "" {
        return 0  // Zero implícito para "1.0a" → "1.0a0"
    }
    n, _ := strconv.Atoi(s)
    return n
}
```

Estes auxiliares ignoram erros porque a regex garante dígitos válidos. Se a regex coincidiu, `\d+` capturou apenas caracteres numéricos.

**Normalização** (`normalizePreKind()` nas linhas 227-237):

```go
func normalizePreKind(s string) string {
    switch strings.ToLower(s) {
    case "a", "alpha":
        return "a"
    case "b", "beta":
        return "b"
    case "rc", "c", "pre", "preview":
        return "rc"
    default:
        return s
    }
}
```

A PEP 440 permite que `alpha`, `a`, `beta`, `b`, `c`, `rc`, `pre`, `preview` signifiquem coisas específicas. Nós normalizamos para as formas canônicas (`a`, `b`, `rc`) para que a lógica de comparação não precise lidar com variantes.

## Construindo o Cliente HTTP com Cache

### O Problema

angela consulta a Simple API do PyPI para listas de versões. Um projeto típico tem de 20 a 50 dependências. Sem cache, você faria de 20 a 50 requisições HTTP toda vez que executasse `angela check`. Isso é lento (5-10 segundos) e indelicado (sobrecarrega o PyPI).

### A Solução

Cache baseado em arquivo com ETags. A primeira requisição busca e armazena em cache. Requisições subsequentes usam o cabeçalho `If-None-Match`. Se o PyPI disser "304 Not Modified", usamos os dados em cache.

### Implementação

Em `internal/pypi/cache.go:20-36`:

```go
type Cache struct {
    dir string
    ttl time.Duration
}

type CacheEntry struct {
    ETag     string    `json:"etag"`
    Versions []string  `json:"versions"`
    CachedAt time.Time `json:"cached_at"`
}

func NewCache(dir string, ttl time.Duration) (*Cache, error) {
    if err := os.MkdirAll(dir, 0o750); err != nil {
        return nil, err
    }
    return &Cache{dir: dir, ttl: ttl}, nil
}
```

**Busca no cache** (linhas 39-51):

```go
func (c *Cache) Get(key string) (*CacheEntry, bool) {
    data, err := os.ReadFile(c.path(key))
    if err != nil {
        return nil, false  // Cache miss
    }

    var entry CacheEntry
    if err := json.Unmarshal(data, &entry); err != nil {
        return nil, false  // Cache corrompido, trata como miss
    }
    return &entry, true
}
```

Observe que não verificamos o TTL aqui. `Get()` retorna o que estiver no arquivo. O chamador decide se está fresco o suficiente via `IsFresh()`.

**Verificação de frescor** (linhas 53-56):

```go
func (c *Cache) IsFresh(entry *CacheEntry) bool {
    return time.Since(entry.CachedAt) <= c.ttl
}
```

Comparação de tempo simples. O TTL padrão é de 1 hora (`internal/pypi/cache.go:11`).

**Escrita no cache** (linhas 58-77):

```go
func (c *Cache) Set(key string, entry *CacheEntry) error {
    data, err := json.Marshal(entry)
    if err != nil {
        return err
    }

    tmp, err := os.CreateTemp(c.dir, "tmp-*.json")
    if err != nil {
        return err
    }

    if _, writeErr := tmp.Write(data); writeErr != nil {
        _ = tmp.Close()
        _ = os.Remove(tmp.Name())
        return writeErr
    }
    _ = tmp.Close()

    return os.Rename(tmp.Name(), c.path(key))
}
```

Padrão de escrita atômica: arquivo temporário + renomeação. Se a angela travar no meio da escrita, a entrada de cache original permanece intocada. `os.Rename()` é atômico em sistemas POSIX.

**Proteção contra path traversal** (linhas 85-88):

```go
func (c *Cache) path(key string) string {
    safe := filepath.Base(key)  // Remove separadores de diretório
    return filepath.Join(c.dir, safe+".json")
}
```

Mesmo que alguém passe `../../../etc/passwd` como nome de pacote, `filepath.Base()` retorna apenas `passwd`, então o arquivo de cache vai para o diretório de cache como `passwd.json`. Isso evita a escrita fora de `~/.angela/cache/`.

### Usando o Cache no Cliente HTTP

Em `internal/pypi/client.go:73-128`:

```go
func (c *Client) FetchVersions(ctx context.Context, name string) ([]string, error) {
    normalized := NormalizeName(name)

    // 1. Verifica o cache
    entry, hit := c.cache.Get(normalized)
    if hit && c.cache.IsFresh(entry) {
        return entry.Versions, nil
    }

    // 2. Constrói a requisição com ETag se tivermos uma
    url := simpleAPIBase + normalized + "/"
    req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
    if err != nil {
        return nil, fmt.Errorf("build request for %s: %w", name, err)
    }
    req.Header.Set("Accept", simpleAPIAccept)
    req.Header.Set("User-Agent", c.userAgent)

    if entry != nil && entry.ETag != "" {
        req.Header.Set("If-None-Match", entry.ETag)
    }

    // 3. Faz a requisição com retry
    resp, err := c.doWithRetry(ctx, req)
    if err != nil {
        if entry != nil {
            return entry.Versions, nil  // Usa cache obsoleto em erro de rede
        }
        return nil, fmt.Errorf("fetch %s: %w", name, err)
    }
    defer resp.Body.Close()

    // 4. Lida com diferentes códigos de status
    switch resp.StatusCode {
    case http.StatusNotModified:
        c.cache.Touch(normalized)  // Atualiza o TTL
        return entry.Versions, nil

    case http.StatusNotFound:
        return nil, fmt.Errorf("package %q not found on PyPI", name)

    case http.StatusOK:
        var result simpleAPIResponse
        if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
            return nil, fmt.Errorf("decode %s: %w", name, err)
        }
        _ = c.cache.Set(normalized, &CacheEntry{
            ETag:     resp.Header.Get("ETag"),
            Versions: result.Versions,
            CachedAt: time.Now(),
        })
        return result.Versions, nil

    default:
        return nil, fmt.Errorf("PyPI returned %d for %s", resp.StatusCode, name)
    }
}
```

**Por que este tratamento específico:**

- `StatusNotModified (304)`: Os dados não mudaram. Atualiza o cache para renovar o TTL e retorna as versões em cache.
- `StatusNotFound (404)`: O pacote não existe. Retorna erro imediatamente, não tenta novamente.
- `StatusOK (200)`: Novos dados. Analisa o JSON, armazena no cache e retorna ao chamador.
- `StatusInternalServerError (5xx)`: Erro de servidor. A lógica de retry em `doWithRetry()` cuida disso.

## Exemplo de Fluxo de Dados: Escaneando por Vulnerabilidades

Vamos rastrear uma requisição completa através do sistema.

**Cenário:** Usuário executa `angela scan --file pyproject.toml`

### A Requisição Chega

Ponto de entrada: `cmd/angela/main.go:7-9`

```go
func main() {
    cli.Execute()
}
```

`Execute()` configura os comandos Cobra em `internal/cli/update.go:57-83`:

```go
func Execute() {
    root := &cobra.Command{
        Use:   "angela",
        Short: "Python dependency updater and vulnerability scanner",
        // ...
    }

    root.AddCommand(
        newInitCmd(),
        newUpdateCmd(),
        newCheckCmd(),
        newScanCmd(),  // Nosso comando
        newCacheCmd(),
    )

    if err := root.Execute(); err != nil {
        PrintError(err.Error())
        os.Exit(1)
    }
}
```

Neste ponto:

- O Cobra analisou os argumentos da CLI.
- A função `RunE` do comando `scan` foi identificada.
- O contexto está disponível via `cmd.Context()` para cancelamento.

### Camada de Processamento: runScan()

`internal/cli/update.go:403-440`:

```go
func runScan(ctx context.Context, file string) error {
    start := time.Now()
    cfg := config.Load(file)  // Carrega listas de ignorados, severidade mínima

    // 1. Analisa o arquivo de dependências
    deps, err := parseDeps(file)
    if err != nil {
        return err
    }

    // 2. Mostra o spinner
    spin := ui.NewSpinner(fmt.Sprintf(
        "Scanning %d dependencies for vulnerabilities...",
        len(deps),
    ))
    spin.Start()

    // 3. Escaneia por vulnerabilidades
    minSev := resolveMinSeverity(cfg.MinSeverity)
    vulns, scanErr := scanForVulns(ctx, deps)

    spin.Stop()

    if scanErr != nil {
        PrintError(scanErr.Error())
    }

    // 4. Filtra os resultados
    vulns = filterIgnoredVulns(vulns, cfg.IgnoreVulns)
    vulns = filterVulnsBySeverity(vulns, minSev)

    // 5. Imprime os resultados
    PrintVulnerabilities(vulns)

    // 6. Imprime o resumo
    totalVulns := 0
    for _, vl := range vulns {
        totalVulns += len(vl)
    }

    PrintSummary(types.ScanResult{
        TotalPackages: len(deps),
        TotalVulns:    totalVulns,
        VulnsScanned:  true,
        Duration:      time.Since(start),
    }, false)

    return nil
}
```

Este código:

- Carrega a configuração do usuário para verificar se ele ignorou CVEs específicas ou definiu um limite de severidade.
- Analisa o arquivo de dependências para obter nomes e versões dos pacotes.
- Mostra um spinner no terminal durante o scan pesado de rede.
- Consulta o OSV.dev (é aqui que o trabalho real acontece).
- Filtra os resultados baseados na configuração do usuário.
- Formata e imprime o relatório de vulnerabilidades.

### Armazenamento/Saída: scanForVulns()

`internal/cli/update.go:352-372`:

```go
func scanForVulns(
    ctx context.Context,
    deps []types.Dependency,
) (map[string][]types.Vulnerability, error) {
    var queries []osv.PackageQuery
    for _, dep := range deps {
        ver := pyproject.ExtractMinVersion(dep.Spec)
        if ver == "" {
            continue  // Pula dependências sem versão especificada
        }
        queries = append(queries, osv.PackageQuery{
            Name:    dep.Name,
            Version: ver,
        })
    }

    if len(queries) == 0 {
        return nil, nil
    }

    client := osv.NewClient()
    vulns, err := client.ScanPackages(ctx, queries)
    if err != nil {
        return nil, fmt.Errorf("vulnerability scan: %w", err)
    }
    return vulns, nil
}
```

O resultado é um mapa: `map[string][]types.Vulnerability` onde a chave é o nome do pacote e o valor são todas as vulnerabilidades que afetam aquele pacote.

### Cliente OSV: Consulta em Lote + Busca Individual

`internal/osv/client.go:40-95`:

```go
func (c *Client) ScanPackages(
    ctx context.Context,
    packages []PackageQuery,
) (map[string][]types.Vulnerability, error) {
    // Passo 1: Consulta em lote pelos IDs de vulnerabilidade
    batch, err := c.queryBatch(ctx, packages)
    if err != nil {
        return nil, fmt.Errorf("osv batch query: %w", err)
    }

    // Passo 2: Coleta IDs únicos
    allIDs := collectUniqueIDs(batch)
    if len(allIDs) == 0 {
        return nil, nil
    }

    // Passo 3: Busca detalhes completos para cada vulnerabilidade
    vulnMap, err := c.hydrateAll(ctx, allIDs)
    if err != nil {
        return nil, fmt.Errorf("osv hydrate: %w", err)
    }

    // Passo 4: Constrói resultados por pacote com deduplicação
    return buildResults(packages, batch, vulnMap), nil
}
```

**queryBatch()** envia um POST para `https://api.osv.dev/v1/querybatch`:

```json
{
  "queries": [
    {
      "package": { "name": "requests", "ecosystem": "PyPI" },
      "version": "2.28.0"
    },
    { "package": { "name": "django", "ecosystem": "PyPI" }, "version": "3.2.0" }
  ]
}
```

A resposta inclui referências mínimas de vulnerabilidade:

```json
{
  "results": [
    { "vulns": [{ "id": "GHSA-j8r2-6x86-q33q", "modified": "..." }] },
    { "vulns": [{ "id": "CVE-2023-31047", "modified": "..." }] }
  ]
}
```

**hydrateAll()** então busca os detalhes completos para cada ID único usando requisições concorrentes com `errgroup.SetLimit(15)`:

```go
func (c *Client) hydrateAll(
    ctx context.Context,
    ids []string,
) (map[string]*osvVuln, error) {
    var mu sync.Mutex
    result := make(map[string]*osvVuln, len(ids))

    g, ctx := errgroup.WithContext(ctx)
    g.SetLimit(maxHydrate)  // 15 requisições concorrentes

    for _, id := range ids {
        g.Go(func() (err error) {
            defer func() {
                if r := recover(); r != nil {
                    err = fmt.Errorf("panic hydrating %s: %v", id, r)
                }
            }()

            v, fetchErr := c.fetchVuln(ctx, id)
            if fetchErr != nil {
                return fetchErr
            }
            mu.Lock()
            result[id] = v
            mu.Unlock()
            return nil
        })
    }

    if err := g.Wait(); err != nil {
        return nil, err
    }
    return result, nil
}
```

Cada `fetchVuln()` faz: `GET https://api.osv.dev/v1/vulns/{id}`

O mutex protege o mapa `result` compartilhado contra escritas concorrentes.

## Padrões de Tratamento de Erro

### Padrão 1: Retry com Backoff Exponencial

Quando a rede está instável, tentar novamente uma vez pode funcionar. Quando o PyPI está sobrecarregado, tentar imediatamente piora as coisas. O backoff exponencial espaça as tentativas.

`internal/pypi/client.go:169-200`:

```go
func (c *Client) doWithRetry(
    ctx context.Context,
    req *http.Request,
) (*http.Response, error) {
    var lastErr error

    for attempt := range maxRetries {  // 0, 1, 2
        if attempt > 0 {
            shift := uint(attempt - 1)  // 0, 1
            delay := time.Duration(1<<shift) * baseRetryMs * time.Millisecond
            // delay é: 500ms, 1000ms
            select {
            case <-ctx.Done():
                return nil, ctx.Err()
            case <-time.After(delay):
            }
        }

        resp, err := c.http.Do(req)
        if err != nil {
            lastErr = err
            continue  // Erro de rede, tenta novamente
        }

        if resp.StatusCode >= http.StatusInternalServerError {
            _ = resp.Body.Close()
            lastErr = fmt.Errorf("server error: %d", resp.StatusCode)
            continue  // Erro de servidor (5xx), tenta novamente
        }

        return resp, nil  // Sucesso ou erro de cliente (4xx), não tenta novamente
    }

    return nil, fmt.Errorf("after %d attempts: %w", maxRetries, lastErr)
}
```

**Por que este tratamento específico:**

O bit shift `1<<shift` dobra o atraso a cada tentativa. Para `baseRetryMs=500`:

- Tentativa 0: sem atraso.
- Tentativa 1: 500ms (2^0 * 500).
- Tentativa 2: 1000ms (2^1 * 500).

O `select` respeita o cancelamento do contexto. Se o usuário pressionar Ctrl+C enquanto espera, o retry aborta imediatamente em vez de terminar o atraso.

**O que NÃO fazer:**

```go
// Ruim: atraso fixo não respeita a sobrecarga
time.Sleep(1 * time.Second)

// Por que isso falha: Se o PyPI estiver sobrecarregado, tentar novamente após 1s adiciona mais carga.
// O backoff exponencial dá tempo para o servidor se recuperar.
```

### Padrão 2: Recuperação de Pânico em Goroutines

Um pânico não recuperado em uma goroutine mata todo o processo. Em uma ferramenta CLI, isso significa que o usuário vê um stack trace em vez de uma mensagem de erro adequada.

`internal/pypi/client.go:144-156`:

```go
g.Go(func() (err error) {
    defer func() {
        if r := recover(); r != nil {
            err = fmt.Errorf("panic fetching %s: %v", name, r)
        }
    }()

    versions, fetchErr := c.FetchVersions(ctx, name)
    mu.Lock()
    results = append(results, FetchResult{
        Name: name, Versions: versions, Err: fetchErr,
    })
    mu.Unlock()
    return nil
})
```

O retorno nomeado `(err error)` é crucial. Sem ele, a função deferida não pode definir o valor de retorno. Este padrão converte pânicos em erros que fluem através do caminho normal de tratamento de erros.

## Otimizações de Desempenho

### Antes: Requisições Sequenciais Ingênuas

```go
// Não faça isso
var results []FetchResult
for _, name := range names {
    versions, err := client.FetchVersions(ctx, name)
    results = append(results, FetchResult{Name: name, Versions: versions, Err: err})
}
```

Para 50 dependências a 200ms por requisição, isso leva 10 segundos.

### Depois: Requisições Concorrentes com Workers Limitados

`internal/pypi/client.go:135-167`:

```go
func (c *Client) FetchAllVersions(
    ctx context.Context,
    names []string,
) []FetchResult {
    var (
        mu      sync.Mutex
        results = make([]FetchResult, 0, len(names))
    )

    g, ctx := errgroup.WithContext(ctx)
    g.SetLimit(c.maxWorkers)  // 10 requisições concorrentes

    for _, name := range names {
        g.Go(func() (err error) {
            defer func() {
                if r := recover(); r != nil {
                    err = fmt.Errorf("panic fetching %s: %v", name, r)
                }
            }()

            versions, fetchErr := c.FetchVersions(ctx, name)
            mu.Lock()
            results = append(results, FetchResult{
                Name: name, Versions: versions, Err: fetchErr,
            })
            mu.Unlock()
            return nil
        })
    }

    _ = g.Wait()
    return results
}
```

**O que mudou:**

- Inicia uma goroutine por pacote, mas apenas 10 rodam por vez.
- Usa mutex para proteger o slice `results` compartilhado.
- A recuperação de pânico evita que um pacote ruim mate o scan.

**Benchmarks:**

- Antes (sequencial): 10 segundos para 50 pacotes.
- Depois (concorrente): 1-2 segundos para 50 pacotes (assumindo cache misses).
- Com cache hits: <100ms.

## Gerenciamento de Configuração

### Carregando a Configuração

angela suporta dois locais de configuração:

1. `.angela.toml` no diretório atual.
2. Seção `[tool.angela]` no `pyproject.toml`.

`internal/config/config.go:27-43`:

```go
func Load(pyprojectPath string) Config {
    // Tenta a configuração independente primeiro
    if cfg, err := loadFile(".angela.toml"); err == nil {
        return cfg
    }

    // Recai para [tool.angela] no pyproject.toml
    if cfg, ok := loadFromPyproject(pyprojectPath); ok {
        return cfg
    }

    return Config{}  // Configuração vazia se nenhuma for encontrada
}
```

A função `loadFromPyproject()` usa uma struct wrapper para extrair a seção `[tool.angela]`:

```go
type pyprojectWrapper struct {
    Tool struct {
        Angela Config `toml:"angela"`
    } `toml:"tool"`
}

func loadFromPyproject(path string) (Config, bool) {
    data, err := os.ReadFile(path)
    if err != nil {
        return Config{}, false
    }

    var wrapper pyprojectWrapper
    if err := toml.Unmarshal(data, &wrapper); err != nil {
        return Config{}, false
    }

    cfg := wrapper.Tool.Angela
    if cfg.MinSeverity == "" && len(cfg.Ignore) == 0 && len(cfg.IgnoreVulns) == 0 {
        return Config{}, false  // Configuração vazia
    }

    return cfg, true
}
```

Validamos antes de aplicar:

```go
cfg.MinSeverity = strings.ToLower(strings.TrimSpace(cfg.MinSeverity))
```

Isso normaliza `"CRITICAL"` e `"  critical  "` para `"critical"` para uma comparação consistente.

## Edição Cirúrgica de TOML

### O Desafio

As bibliotecas TOML do Go destroem comentários e formatação ao fazer o unmarshal e re-marshal. Precisamos atualizar os especificadores de versão sem tocar em mais nada.

### A Solução

Busca/substituição baseada em regex nos bytes brutos.

`internal/pyproject/writer.go:54-84`:

```go
func (u *Updater) UpdateDependency(pkg, newSpec string) error {
    for _, q := range []byte{'"', '\''} {  // Tenta ambos os estilos de aspas
        pattern := buildDepPattern(pkg, q)
        found := false
        u.content = pattern.ReplaceAllFunc(
            u.content,
            func(match []byte) []byte {
                found = true
                return replaceSpec(pattern, match, newSpec, q)
            },
        )
        if found {
            // Valida se a edição não quebrou a sintaxe TOML
            var probe map[string]any
            if err := toml.Unmarshal(u.content, &probe); err != nil {
                return fmt.Errorf("update produced invalid TOML: %w", err)
            }
            return nil
        }
    }
    return fmt.Errorf("dependency %q not found", pkg)
}
```

O padrão corresponde à string de dependência completa:

```
"requests>=2.28.0"
```

Grupos de captura isolam:

1. Nome do pacote (`requests`).
2. Extras (`[async]` ou vazio).
3. Especificação de versão (`>=2.28.0`).
4. Marcadores (`;python_version>='3.8'` ou vazio).

Substituímos apenas o grupo 3:

```go
func replaceSpec(
    re *regexp.Regexp, match []byte, newSpec string, quote byte,
) []byte {
    groups := re.FindSubmatch(match)
    if len(groups) < 5 {
        return match  // O padrão não correspondeu à estrutura esperada
    }

    name := groups[1]
    extras := groups[2]
    markers := groups[4]

    var b []byte
    b = append(b, quote)
    b = append(b, name...)
    b = append(b, extras...)     // Mantém os extras
    b = append(b, []byte(newSpec)...)  // Substitui a versão
    b = append(b, markers...)    // Mantém os marcadores
    b = append(b, quote)
    return b
}
```

Resultado final: `"requests>=2.32.3"` com as mesmas aspas, extras e marcadores de antes.

## Testando Este Recurso

Teste o atualizador TOML em `internal/pyproject/writer_test.go:11-34`:

```go
func TestUpdaterPreservesComments(t *testing.T) {
    const sampleTOML = `# Project configuration
[project]
dependencies = [
    "requests>=2.28.0",  # HTTP library
]`

    u, err := NewUpdater([]byte(sampleTOML))
    if err != nil {
        t.Fatalf("NewUpdater error: %v", err)
    }

    if err := u.UpdateDependency("requests", ">=2.31.0"); err != nil {
        t.Fatalf("UpdateDependency error: %v", err)
    }

    result := string(u.Bytes())

    if !strings.Contains(result, `"requests>=2.31.0"`) {
        t.Error("version was not updated")
    }
    if !strings.Contains(result, "# HTTP library") {
        t.Error("inline comment was lost")
    }
}
```

Saída esperada:

```toml
# Project configuration
[project]
dependencies = [
    "requests>=2.31.0",  # HTTP library
]
```

Se você vir `[2.31.0](file:///mnt/user-data/outputs)` em vez disso, a regex está quebrada. Se o comentário sumiu, algo está fazendo unmarshal/remarshal em vez de usar a cirurgia por regex.

## Armadilhas Comuns de Implementação

### Armadilha 1: Não Normalizar Nomes de Pacotes

**Sintoma:**
O usuário tem `Django>=3.2.0` no seu pyproject.toml, mas a angela diz "pacote não encontrado".

**Causa:**

```go
// Errado: comparação sensível a maiúsculas
if dep.Name == "django" {
    // Não coincidirá com "Django"
}
```

**Correção:**

```go
// Correto: normalizar antes de comparar
normalized := pypi.NormalizeName(dep.Name)  // "Django" → "django"
```

A PEP 503 especifica a normalização de nomes de pacotes: minúsculas, substitui `[-_.]` por `-`. Tanto o PyPI quanto a angela devem usar a mesma normalização ou as buscas falharão.

### Armadilha 2: Assumir Apenas Versões Estáveis

**Sintoma:**
O usuário é atualizado para `package==3.0a1` (um pre-release alpha).

**Causa:**

```go
// Errado: escolhe qualquer versão mais recente
latest := versions[len(versions)-1]
```

**Correção:**

```go
// Correto: filtrar pre-releases
latest, err := pypi.LatestStable(versions)
```

A função `LatestStable()` pula qualquer versão com `PreKind != ""` ou `Dev >= 0`.

### Armadilha 3: Ignorar o Cancelamento do Contexto

**Sintoma:**
O usuário pressiona Ctrl+C, mas a angela continua rodando por mais 10 segundos.

**Causa:**

```go
// Errado: não respeita o contexto
time.Sleep(10 * time.Second)
```

**Correção:**

```go
// Correto: usar select com contexto
select {
case <-ctx.Done():
    return ctx.Err()
case <-time.After(10 * time.Second):
}
```

Sempre passe o `context.Context` através da pilha de chamadas e verifique `ctx.Done()` em loops ou sleeps.

## Dicas de Depuração

### Problema: Cache Sempre Dá Miss

**Problema:** angela faz requisições HTTP novas toda vez, ignorando o cache.

**Como depurar:**

1. Verifique `~/.angela/cache/` por arquivos JSON: `ls -lah ~/.angela/cache/`
2. Olhe os timestamps: `cat ~/.angela/cache/requests.json | jq '.cached_at'`
3. Verifique o TTL: `cached_at` tem mais de 1 hora?

**Causas comuns:**

- O diretório de cache não existe (problema de permissão).
- O tempo `CachedAt` está no futuro (relógio do sistema errado).
- Incompatibilidade na normalização do nome do pacote (cacheado como `Django.json`, mas procurando por `django.json`).

### Problema: "Invalid TOML syntax" Após Atualização

**Problema:** angela atualiza uma dependência, mas produz um TOML quebrado.

**Como depurar:**

1. Olhe o arquivo antes e depois: `git diff pyproject.toml`
2. Tente analisar com `toml.Unmarshal()` manualmente para ver onde quebra.
3. Verifique se o padrão regex coincidiu com algo inesperado (como um comentário contendo o nome do pacote).

**Causas comuns:**

- A dependência aparece múltiplas vezes (uma vez em `dependencies`, outra em `optional-dependencies["dev"]`).
- O nome do pacote aparece em um comentário: `# Nota: requests está desatualizado`.
- TOML original malformado (aspas quebradas, colchetes não fechados).

## Princípios de Organização do Código

### Por que pyproject/ é Separado de requirements/

```
internal/
├── pyproject/
│   ├── parser.go
│   └── writer.go
└── requirements/
    ├── parser.go
    └── writer.go
```

Eles são separados porque:

- Formatos de arquivo diferentes (TOML vs texto simples).
- Lógica de parsing diferente (toml.Unmarshal vs escaneamento linha por linha).
- Estratégias de atualização diferentes (regex no TOML vs regex no texto simples).

Mas eles compartilham a mesma interface:

```go
func ParseFile(path string) ([]types.Dependency, error)
func UpdateFile(path string, updates map[string]string) error
```

Isso torna a camada CLI genérica. Ela não se importa com qual formato você usa:

```go
func parseDeps(file string) ([]types.Dependency, error) {
    if isRequirementsTxt(file) {
        return requirements.ParseFile(file)
    }
    return pyproject.ParseFile(file)
}
```

### Convenções de Nomenclatura

- `*Client` = Cliente de rede (PyPI, OSV).
- `Parse*` = Ler e extrair dados estruturados.
- `Update*` = Modificar dados existentes.
- `Fetch*` = Fazer requisição HTTP.
- `Extract*` = Extrair valor específico de uma estrutura maior.

Seguir estes padrões facilita encontrar funcionalidades. Se você precisar extrair números de versão de uma string de especificação, procure por `Extract*`. Se precisar fazer uma chamada de rede, procure por `Fetch*`.

## Estendendo o Código

### Adicionando Suporte para Comentários no requirements.txt

Atualmente, a angela preserva comentários no pyproject.toml, mas não no requirements.txt. Vamos adicioná-lo.

1. **Modifique o parser** em `internal/requirements/parser.go:23-57`:

```go
// Adicione este campo para rastrear a linha original com comentário
type dependencyLine struct {
    dep     types.Dependency
    comment string  // Texto após o # na linha
}

// Modifique parseLine() para retornar ambos
func parseLine(s string) (types.Dependency, string) {
    var comment string
    if idx := strings.Index(s, " #"); idx >= 0 {
        comment = s[idx:]  // Armazena " # texto do comentário"
        s = strings.TrimSpace(s[:idx])
    }
    // ... restante do parsing ...
    return dep, comment
}
```

2. **Atualize o writer** em `internal/requirements/writer.go:17-47`:

```go
// Preserva comentários na substituição por regex
func replaceSpec(
    re *regexp.Regexp, match []byte, newSpec string,
) []byte {
    groups := re.FindSubmatch(match)
    if len(groups) < 4 {
        return match
    }

    // Extrai o comentário se presente
    fullLine := string(match)
    var comment string
    if idx := strings.Index(fullLine, " #"); idx >= 0 {
        comment = fullLine[idx:]
    }

    var b []byte
    b = append(b, groups[1]...)  // Nome do pacote
    b = append(b, groups[2]...)  // Extras
    b = append(b, []byte(newSpec)...)  // Nova versão
    b = append(b, []byte(comment)...)  // Preserva o comentário
    return b
}
```

3. **Adicione testes** em `internal/requirements/writer_test.go`:

```go
func TestUpdateFilePreservesComments(t *testing.T) {
    content := "requests>=2.28.0  # HTTP library\n"
    // ... escreve em arquivo temporário, atualiza, verifica se o comentário permanece ...
}
```

Isso segue o mesmo padrão da preservação de comentários do pyproject.toml, mas adaptado para o formato mais simples do requirements.txt.

## Próximos Passos

Você viu como o código funciona. Agora:

1. **Tente os desafios** - [04-CHALLENGES.md](./04-CHALLENGES.md) tem ideias de extensão como adicionar scan de dependências transitivas, geração de SBOM e fontes de vulnerabilidade personalizadas.
2. **Modifique o TTL do cache** - Altere `DefaultCacheTTL` em `internal/pypi/cache.go:11` de 1 hora para 5 minutos e observe o comportamento do cache.
3. **Adicione um novo nível de severidade** - Estenda a classificação de severidade em `internal/osv/client.go:262-270` para incluir "INFO" para avisos de baixa prioridade.
