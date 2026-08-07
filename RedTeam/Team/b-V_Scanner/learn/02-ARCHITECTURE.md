# Arquitetura do Sistema

Este documento detalha como a angela foi projetada e por que certas decisões arquiteturais foram tomadas. Vamos rastrear as requisições através do sistema e explicar os trade-offs.

## Arquitetura de Alto Nível

```
┌──────────────┐
│     CLI      │  comandos cobra (update, scan, check)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Parser     │  Extrai dependências do pyproject.toml
│              │  ou requirements.txt
└──────┬───────┘
       │
       ├─────────────────┬─────────────────┐
       ▼                 ▼                 ▼
┌──────────┐      ┌──────────┐      ┌──────────┐
│   PyPI   │      │ OSV.dev  │      │  Config  │
│  Client  │      │  Client  │      │  Loader  │
└────┬─────┘      └────┬─────┘      └────┬─────┘
     │                 │                  │
     ▼                 ▼                  ▼
┌──────────┐      ┌──────────┐      ┌──────────┐
│  Cache   │      │ Vuln DB  │      │ Settings │
└──────────┘      └──────────┘      └──────────┘
       │
       ▼
┌──────────────┐
│   Writer     │  Atualiza arquivo de dependências preservando formatação
└──────────────┘
```

### Divisão dos Componentes

**Camada CLI** (`internal/cli/`)

- Propósito: Analisar argumentos de linha de comando e orquestrar o workflow.
- Responsabilidades: Roteia os comandos `update`, `scan`, `check`, `cache` e `init` para os handlers apropriados.
- Interfaces: `cobra.Command` para parsing de argumentos, retorna erro ou nil.

**Parser** (`internal/pyproject/` e `internal/requirements/`)

- Propósito: Extrair declarações de dependência dos arquivos do projeto.
- Responsabilidades: Analisa TOML ou texto simples, constrói `[]types.Dependency` com nome, especificação de versão, extras e marcadores.
- Interfaces: `ParseFile(path string) ([]types.Dependency, error)`

**Cliente PyPI** (`internal/pypi/`)

- Propósito: Consultar a Simple API do PyPI para versões de pacotes disponíveis.
- Responsabilidades: Requisições HTTP com lógica de retry, cache baseado em ETag, parsing de versão PEP 440.
- Interfaces: `FetchVersions(ctx, name) ([]string, error)` para um único pacote, `FetchAllVersions(ctx, names) []FetchResult` para lote concorrente.

**Cliente OSV** (`internal/osv/`)

- Propósito: Consultar o OSV.dev para vulnerabilidades conhecidas.
- Responsabilidades: Consultas de vulnerabilidade em lote, busca de detalhes individuais de CVE, extração de severidade, deduplicação.
- Interfaces: `ScanPackages(ctx, []PackageQuery) (map[string][]Vulnerability, error)`

**Cache** (`internal/pypi/cache.go`)

- Propósito: Cache baseado em arquivo para respostas do PyPI para evitar sobrecarregar a API.
- Responsabilidades: Serializa JSON para `~/.angela/cache/`, verifica o frescor do TTL, lida com ETags.
- Interfaces: `Get(key) (*CacheEntry, bool)`, `Set(key, entry) error`

**Carregador de Configuração** (`internal/config/`)

- Propósito: Ler as preferências do usuário do `.angela.toml` ou `[tool.angela]` no pyproject.toml.
- Responsabilidades: Analisa a configuração TOML, extrai severidade mínima, listas de ignorados, supressão de vulnerabilidades.
- Interfaces: `Load(pyprojectPath) Config`

**Writer** (`internal/pyproject/writer.go` e `internal/requirements/writer.go`)

- Propósito: Edições cirúrgicas em arquivos para atualizar especificadores de versão sem destruir a formatação.
- Responsabilidades: Busca/substituição baseada em regex nos bytes brutos, validação TOML após edições, escritas atômicas.
- Interfaces: `UpdateFile(path, updates map[string]string) error`

## Fluxo de Dados

### Caso de Uso Principal: Atualizar Dependências

Passo a passo do que acontece quando você executa `angela update --file pyproject.toml`:

```
1. CLI analisa argumentos → update.go:runUpdate() (internal/cli/update.go:200-291)
   Extrai o caminho do arquivo, carrega a configuração da angela (listas de ignorados, severidade mínima)

2. runUpdate() → pyproject.ParseFile() (internal/pyproject/parser.go:18-50)
   Desserializa o TOML, extrai [project.dependencies] e [project.optional-dependencies]
   Retorna []types.Dependency com nome, especificação, extras, marcadores, grupo

3. runUpdate() → pypi.FetchAllVersions() (internal/pypi/client.go:135-167)
   Inicia até 10 goroutines concorrentes (uma por pacote)
   Cada uma chama FetchVersions() que:
   - Verifica no cache por uma entrada não expirada com ETag correspondente
   - Se houver hit no cache: retorna as versões em cache
   - Se houver miss no cache: HTTP GET para https://pypi.org/simple/{package}/
   - Analisa a resposta JSON, extrai o array "versions"
   - Armazena no cache com a ETag dos cabeçalhos da resposta

4. runUpdate() → resolveUpdates() (internal/cli/update.go:293-350)
   Para cada dependência:
   - Analisa a versão atual usando pypi.ParseVersion() (internal/pypi/version.go:60-112)
   - Encontra a versão estável mais recente com pypi.LatestStable() (filtra pre-releases)
   - Compara versões usando Version.Compare() (ordenação PEP 440)
   - Se for mais nova: classifica a mudança (major/minor/patch) e constrói UpdateResult
   - Se a flag --safe estiver ativa: pula saltos de versão major
   - Se estiver em config.Ignore: pula com o motivo

5. runUpdate() → scanForVulns() (internal/cli/update.go:352-372) [se a flag --vulns estiver ativa]
   Constrói []osv.PackageQuery a partir das dependências (nome + versão extraída)
   Chama osv.ScanPackages() que:
   - Faz um POST para https://api.osv.dev/v1/querybatch com todos os pacotes
   - Extrai IDs de vulnerabilidade únicos da resposta
   - Busca detalhes completos para cada vulnerabilidade com requisições concorrentes (máx 15 workers)
   - Remove duplicatas de aliases CVE/GHSA/PYSEC
   - Extrai severidade, resumo, versão corrigida, link
   Retorna map[packageName][]Vulnerability

6. runUpdate() → pyproject.UpdateFile() (internal/pyproject/writer.go:99-118)
   Para cada pacote com atualizações:
   - Constrói uma regex que corresponde ao nome do pacote com forma normalizada (PEP 503)
   - Encontra a linha da dependência nos bytes brutos do arquivo
   - Substitui apenas o especificador de versão, mantém aspas, extras, marcadores
   - Valida se o resultado ainda é um TOML válido
   - Escrita atômica: arquivo temporário + renomeação

7. runUpdate() → Imprime resultados (internal/cli/output.go:35-93)
   Exibe atualizações no terminal com codificação de cores (vermelho=major, amarelo=minor, verde=patch)
   Mostra vulnerabilidades por severidade (crítica → alta → moderada → baixa)
   Imprime resumo com total de pacotes, atualizações aplicadas, vulnerabilidades encontradas
```

### Caso de Uso Secundário: Verificar Sem Atualizar

O comando `check` segue os passos 1-5 acima, mas pula o passo 6 (escrita no arquivo). É um modo de simulação (dry run).

### Apenas Scan de Vulnerabilidade

O comando `scan` pula a verificação de versão inteiramente:

```
1. CLI → comando scan (internal/cli/update.go:403-440)
2. Analisa dependências do arquivo
3. scanForVulns() contra as versões instaladas atuais
4. Imprime relatório de vulnerabilidades
```

Isso é mais rápido que `update --vulns` porque não consulta o PyPI por dados de versão.

## Padrões de Projeto

### Padrão 1: Concorrência Limitada com errgroup

**O que é:**
O pacote `errgroup` do Go fornece execução coordenada de goroutines com propagação de erro e cancelamento de contexto. `SetLimit()` limita quantas goroutines rodam simultaneamente.

**Onde usamos:**
`internal/pypi/client.go:135-167` para requisições paralelas ao PyPI:

```go
g, ctx := errgroup.WithContext(ctx)
g.SetLimit(c.maxWorkers)  // Máximo de 10 requisições concorrentes

for _, name := range names {
    g.Go(func() (err error) {
        defer func() {
            if r := recover(); r != nil {
                err = fmt.Errorf("panic fetching %s: %v", name, r)
            }
        }()

        versions, fetchErr := c.FetchVersions(ctx, name)
        mu.Lock()
        results = append(results, FetchResult{...})
        mu.Unlock()
        return nil  // Não propaga falhas individuais
    })
}

_ = g.Wait()
```

**Por que escolhemos:**
O PyPI limita a taxa de clientes agressivos. 10 requisições concorrentes equilibram velocidade (vs sequencial) com polidez (vs 50 concorrentes). Abordagens alternativas:

- Worker pool com channels: Mais código repetitivo, mesma funcionalidade.
- Goroutines ilimitadas: Sobrecarrega o PyPI, pode resultar em banimento de IP.
- Requisições sequenciais: Leva mais de 30 segundos para projetos típicos.

**Trade-offs:**

- Prós: Código simples, respeita limites de taxa, cancelamento automático de contexto.
- Contras: Limite de concorrência fixo (não adaptativo), sem priorização de requisições.

### Padrão 2: Cirurgia de Arquivo Baseada em Regex

**O que é:**
Em vez de analisar o TOML → modificar a struct → re-serializar, a angela usa padrões regex compilados para localizar e substituir apenas o especificador de versão nos bytes brutos do arquivo.

**Onde usamos:**
`internal/pyproject/writer.go:54-84` e `internal/requirements/writer.go:17-47`

```go
func buildDepPattern(name string, quote byte) *regexp.Regexp {
    normalized := pypi.NormalizeName(name)
    parts := strings.Split(normalized, "-")
    for i, p := range parts {
        parts[i] = regexp.QuoteMeta(p)
    }
    namePattern := strings.Join(parts, `[-_.]?`)

    q := string(quote)
    notQ := `[^` + q + `]`

    return regexp.MustCompile(
        `(?i)` +
        q +
        `(` + namePattern + `)` +           // Grupo 1: nome do pacote
        `(\[[^\]]*\])?` +                   // Grupo 2: extras
        `(\s*[><=!~]` + notQ + `*?)` +     // Grupo 3: especificação de versão
        `(;` + notQ + `*)?` +              // Grupo 4: marcadores
        q,
    )
}
```

**Por que escolhemos:**
As bibliotecas TOML do Go (BurntSushi/toml, pelletier/go-toml) não preservam comentários ou formatação durante o unmarshal/marshal. Comentários, linhas em branco e estilos de aspas seriam todos destruídos. A cirurgia por regex mantém tudo intacto, exceto o número da versão.

**Trade-offs:**

- Prós: Preserva toda a formatação, funciona em qualquer TOML válido.
- Contras: Mais complexo que a manipulação de structs, requer validação após a edição, não consegue lidar graciosamente com arquivos malformados.

### Padrão 3: Cache Baseado em Arquivo com Suporte a ETag

**O que é:**
ETags HTTP são identificadores opacos que os servidores enviam para indicar a versão do recurso. Os clientes incluem `If-None-Match: {etag}` em requisições subsequentes. Se não houver alteração, o servidor retorna 304 Not Modified em vez da resposta completa.

**Onde usamos:**
`internal/pypi/cache.go:23-88`

```go
type CacheEntry struct {
    ETag     string    `json:"etag"`
    Versions []string  `json:"versions"`
    CachedAt time.Time `json:"cached_at"`
}

// Verifica o cache antes de fazer a requisição
entry, hit := c.cache.Get(normalized)
if hit && c.cache.IsFresh(entry) {
    return entry.Versions, nil
}

// Adiciona ETag à requisição se tivermos uma
if entry != nil && entry.ETag != "" {
    req.Header.Set("If-None-Match", entry.ETag)
}

// Lida com a resposta 304
if resp.StatusCode == http.StatusNotModified {
    c.cache.Touch(normalized)  // Atualiza o TTL
    return entry.Versions, nil
}
```

**Por que escolhemos:**
As respostas do PyPI raramente mudam (versões de pacotes são imutáveis uma vez publicadas). ETags nos permitem pular o download do mesmo JSON repetidamente. Combinado com um TTL de 1 hora, o uso típico tem uma taxa de hit no cache >90%.

**Trade-offs:**

- Prós: Reduz a carga no PyPI, scans repetidos mais rápidos, respeita a semântica de cache HTTP.
- Contras: Dados obsoletos são possíveis dentro da janela do TTL, o diretório de cache pode crescer muito.

## Separação de Camadas

angela usa uma arquitetura simples de três camadas:

```
┌────────────────────────────────────┐
│    Camada 1: CLI / Apresentação    │
│    - Handlers de comando Cobra     │
│    - Formatação de saída terminal  │
│    - UI de cores e spinners        │
└────────────────────────────────────┘
           ↓
┌────────────────────────────────────┐
│    Camada 2: Lógica de Negócio     │
│    - Resolução de versão           │
│    - Scan de vulnerabilidades      │
│    - Lógica de decisão de atualiz. │
└────────────────────────────────────┘
           ↓
┌────────────────────────────────────┐
│    Camada 3: Acesso a Dados        │
│    - Cliente HTTP PyPI             │
│    - Cliente HTTP OSV.dev          │
│    - E/S de arquivo (cache, configs)│
└────────────────────────────────────┘
```

### Por que Camadas?

Separação de preocupações. A camada CLI não conhece o formato da API do PyPI. O cliente PyPI não conhece as cores do terminal. Se o PyPI mudar seu esquema JSON, apenas a Camada 3 muda. Se quisermos um modo de saída JSON em vez de uma UI de terminal bonita, apenas a Camada 1 muda.

### O Que Vive Onde

**Camada 1 (CLI):**

- Arquivos: `internal/cli/update.go`, `internal/cli/output.go`, `internal/ui/`
- Importações: Pode importar da Camada 2 e Camada 3.
- Proibido: Não deve conter lógica HTTP, parsing de versão ou E/S de arquivo.

**Camada 2 (Lógica de Negócio):**

- Arquivos: `internal/pypi/version.go`, `internal/config/config.go`
- Importações: Pode importar da Camada 3, não da Camada 1.
- Proibido: Não deve fazer saída para o terminal ou conhecer flags da CLI.

**Camada 3 (Acesso a Dados):**

- Arquivos: `internal/pypi/client.go`, `internal/osv/client.go`, `internal/pypi/cache.go`
- Importações: Apenas pkg/types e biblioteca padrão.
- Proibido: Não deve importar nada de internal/cli ou internal/ui.

## Modelos de Dados

### Dependency

```go
// pkg/types/types.go:8-15
type Dependency struct {
    Name    string     // Nome do pacote (ex: "requests")
    Spec    string     // Especificador de versão (ex: ">=2.28.0")
    Extras  []string   // Extras opcionais (ex: ["async", "security"])
    Markers string     // Marcadores de ambiente (ex: "python_version>='3.8'")
    Group   string     // Grupo de dependência (ex: "dev", "test")
}
```

**Campos explicados:**

- `Name`: Nome do pacote normalizado pela PEP 503. angela usa `pypi.NormalizeName()`, que converte para minúsculas e trata `-`, `_`, `.` como equivalentes.
- `Spec`: Especificador de versão PEP 440. Pode ser `>=2.0`, `==1.5.0`, `>=3.0,<4.0`, etc.
- `Extras`: Conjuntos de recursos opcionais como `requests[security]`. Pacotes PyPI podem definir extras que trazem dependências adicionais.
- `Markers`: Condições do ambiente Python como `platform_system=="Windows"`. O Pip só instala a dependência se os marcadores forem avaliados como verdadeiros.
- `Group`: Para optional-dependencies do pyproject.toml, rastreia de qual grupo ela veio.

**Relacionamentos:**
Analisado do arquivo → verificado contra o PyPI → escaneado por vulnerabilidades → potencialmente atualizado.

### Vulnerability

```go
// pkg/types/types.go:26-34
type Vulnerability struct {
    ID       string     // ID primário (ex: "CVE-2023-32681")
    Aliases  []string   // IDs alternativos (ex: ["GHSA-j8r2...", "PYSEC-2023-80"])
    Summary  string     // Descrição legível por humanos
    Severity string     // CRITICAL, HIGH, MODERATE, LOW, UNKNOWN
    FixedIn  string     // Primeira versão que corrige a vulnerabilidade (ex: "2.31.0")
    Link     string     // URL para o aviso (GitHub, NVD, página do fornecedor)
}
```

**Campos explicados:**

- `ID`: Identificador primário do OSV.dev. Pode ser CVE, GHSA ou PYSEC dependendo da fonte.
- `Aliases`: Mesma vulnerabilidade sob IDs diferentes. angela usa isso para deduplicação.
- `Summary`: Primeira frase do aviso. Truncada para caber na largura do terminal.
- `Severity`: Extraída da pontuação CVSS ou database_specific.severity. Recai para "UNKNOWN" se estiver ausente.
- `FixedIn`: Analisado do campo `affected[].ranges[].events[].fixed` do OSV. Vazio se não houver correção disponível.
- `Link`: Ordem de preferência: tipo ADVISORY > tipo WEB > primeira referência. Fornece ao usuário um lugar para ler mais.

**Relacionamentos:**
Retornado pela consulta OSV → filtrado por severidade/lista de ignorados → exibido com codificação de cores.

## Arquitetura de Segurança

### Modelo de Ameaça

O que estamos protegendo contra:

1. **Instalação de dependências vulneráveis** - O usuário possui versões antigas de pacotes com CVEs conhecidas. angela mostra a eles quais pacotes possuem correções disponíveis e quais são as CVEs.

2. **Atualização acidental para pre-releases** - O usuário quer pacotes estáveis, mas uma lógica ingênua de "versão mais recente" poderia escolher `3.0a1` em vez de `2.5.0`. angela filtra pre-releases por padrão.

3. **Mudanças que quebram (breaking changes) de saltos major** - O usuário possui código funcionando no `django==3.2`. Atualizar para `4.0` pode quebrar APIs. A flag `--safe` da angela pula saltos de versão major.

O que NÃO estamos protegendo contra (fora do escopo):

- **Código malicioso em dependências** - angela não faz análise estática ou sandboxing. Ela confia na integridade dos pacotes do PyPI.
- **Vulnerabilidades de dependências transitivas** - angela apenas escaneia pacotes explicitamente no seu arquivo de dependências. Se o `requests` depende de um `urllib3` vulnerável, angela não o detectará a menos que você também liste o `urllib3`.
- **Ataques à cadeia de suprimentos via sequestro de pacote** - Se alguém sequestrar um pacote legítimo e publicar uma versão com backdoor sem CVE ainda, angela não a detectará.

### Camadas de Defesa

angela implementa defesa em profundidade:

```
Camada 1: Validação de configuração
    ↓ (Rejeita TOML inválido, especificações de versão malformadas)
Camada 2: Padrões seguros
    ↓ (Filtra pre-releases, limita requisições concorrentes)
Camada 3: Scan de vulnerabilidades
    ↓ (Consulta OSV.dev por CVEs conhecidas)
```

**Por que múltiplas camadas?**

Se o carregador de configuração tiver um bug e não validar a severidade mínima corretamente, o limite padrão "low" ainda fornecerá alguma proteção. Se o PyPI retornar um JSON lixo, o parser de versão o rejeitará em vez de corromper o estado. Cada camada captura um modo de falha diferente.

## Estratégia de Armazenamento

### Cache Baseado em Arquivo

**O que armazenamos:**

- Listas de versões do PyPI (nome do pacote → `["1.0", "1.1", "2.0"]`)
- ETags HTTP para requisições condicionais.
- Timestamps para expiração do TTL.

**Por que este armazenamento:**
Simples, sem dependências, funciona em todas as plataformas. Uma alternativa seria algo como SQLite, mas isso adiciona complexidade e uma dependência C (para cgo). O cache baseado em arquivo é rápido o suficiente (latência de leitura de 50-100μs) e requer configuração zero.

**Design do esquema:**

```
~/.angela/cache/
├── requests.json
├── django.json
└── flask.json
```

Cada arquivo contém:

```json
{
  "etag": "\"686897696a7c876b7e\"",
  "versions": ["2.0.0", "2.28.0", "2.31.0"],
  "cached_at": "2024-01-15T10:30:00Z"
}
```

A chave do cache é o nome do pacote normalizado. `filepath.Base()` evita o traversal de diretório (veja `internal/pypi/cache.go:85-88`):

```go
func (c *Cache) path(key string) string {
    safe := filepath.Base(key)  // Remove separadores de caminho
    return filepath.Join(c.dir, safe+".json")
}
```

Mesmo que alguém tente fazer o cache de `../../../etc/passwd`, ele se torna `passwd.json` no diretório de cache.

## Considerações de Desempenho

### Gargalos

Onde este sistema fica lento sob carga:

1. **Requisições à Simple API do PyPI** - O tempo de ida e volta da rede domina para consultas não cacheadas. A latência típica é de 50-200ms por requisição. Com 50 dependências, o modo sequencial levaria de 2,5 a 10 segundos. O modo concorrente + cache reduz para 500ms.

2. **Consultas em lote ao OSV.dev** - O endpoint de lote lida com até 1000 pacotes por requisição, mas a resposta pode ter mais de 100KB para pacotes muito afetados. Buscar detalhes individuais de vulnerabilidade adiciona outro round-trip por CVE única.

3. **Parsing de TOML** - pelletier/go-toml v2 é rápido (menos de um milissegundo para um pyproject.toml típico), mas a validação por regex após as atualizações adiciona custo. Cada compilação de regex leva ~10μs, e fazemos isso duas vezes (aspas duplas, depois aspas simples).

### Otimizações

O que fizemos para torná-lo mais rápido:

- **Reuso de conexão HTTP**: `internal/pypi/client.go:53-58` configura `MaxIdleConnsPerHost` para coincidir com o limite de concorrência. As conexões permanecem abertas entre as requisições, economizando o tempo do handshake TCP.

- **Goroutines limitadas**: `errgroup.SetLimit(10)` evita iniciar mais de 50 goroutines e esgotar os descritores de arquivo. Cada goroutine tem um overhead (stack de 2KB+), então limitá-las ajuda.

- **Cache com TTL de 1 hora**: `internal/pypi/cache.go:11` define `DefaultCacheTTL = 1 * time.Hour`. Executar a angela duas vezes dentro de uma hora tem latência próxima de zero (hit no cache).

- **Padrões regex compilados**: angela compila padrões regex uma vez em `buildDepPattern()` em vez de em cada correspondência. O `regexp.MustCompile()` do Go na inicialização seria ainda melhor, mas precisamos de padrões dinâmicos (o nome do pacote varia).

### Escalabilidade

**Escalonamento vertical:**
angela é limitada pela CPU durante a correspondência de regex e limitada pela memória durante as requisições HTTP concorrentes. Adicionar mais núcleos de CPU não ajuda muito (já usando 10 goroutines). Adicionar RAM ajuda se você estiver escaneando mais de 1000 dependências (o cache cresce muito).

**Escalonamento horizontal:**
Não aplicável. angela é uma ferramenta CLI que roda em uma máquina. Se você quisesse escanear 10.000 projetos, rodaria 10.000 processos angela em paralelo (ex: em jobs do Kubernetes).

O que precisa mudar para suportar uma escala maior: Camada de cache compartilhada (Redis/Memcached) em vez de arquivos por processo. Pooling de conexões com suporte do lado do servidor. Coordenação de limite de taxa entre processos.

## Decisões de Design

### Decisão 1: Go em vez de Python

**O que escolhemos:**
Escrever o scanner de dependências em Go, não em Python.

**Alternativas consideradas:**

- Python com a biblioteca `packaging`: Ecossistema nativo, mais fácil de usar o próprio parser de versão do Python.
- Rust: Melhor desempenho, mais difícil de aprender.
- Shell script com curl/jq: O mais simples possível, mas com tratamento de erros terrível.

**Trade-offs:**
O que ganhamos:

- Binário estático (não requer instalação do Python).
- Tempo de inicialização rápido (sem overhead de importação).
- Excelentes primitivas de concorrência (goroutines, errgroup).

O que abrimos mão:

- Tivemos que implementar a PEP 440 do zero.
- Não podemos usar a lógica do resolvedor do pip diretamente.
- Ecossistema menor para bibliotecas TOML.

**Raciocínio**: angela precisa ser rápida (escanear 50 pacotes em <1 segundo) e portátil (rodar em qualquer máquina). O Go compila para um único binário sem dependências de runtime. O Python funcionaria, mas seria mais lento e exigiria a versão correta do Python instalada.

### Decisão 2: Cache Baseado em Arquivo vs Em Memória

**O que escolhemos:**
Cache baseado em arquivo em `~/.angela/cache/` com TTL de 1 hora.

**Alternativas consideradas:**

- Apenas em memória: Mais rápido, mas perdido ao sair.
- SQLite: Mais recursos (consultas, índices), mas dependência mais pesada.
- Sem cache: Código mais simples, mas execuções repetidas lentas.

**Trade-offs:**
O que ganhamos:

- Persistente entre execuções (o desenvolvedor escaneia o mesmo projeto várias vezes).
- Implementação simples (apenas serialização JSON).
- Nenhum daemon necessário (ao contrário do Redis).

O que abrimos mão:

- O diretório de cache cresce sem limites (sem limpeza automática).
- Sem expulsão LRU (arquivos ficam até o TTL expirar).
- Mais lento que em memória (E/S de disco vs RAM).

**Raciocínio**: O caso de uso típico da angela é "rodá-la a cada hora no CI" ou "rodá-la ao atualizar dependências manualmente". O cache baseado em arquivo cobre ambos. O tamanho do cache é pequeno (50 pacotes × 5KB cada = 250KB), então o espaço em disco não é uma preocupação.

## Arquitetura de Implantação

angela roda como uma ferramenta CLI local, não como um servidor. Não há topologia de implantação. Os usuários instalam o binário via:

```bash
go install github.com/CarterPerez-dev/angela/cmd/angela@latest
```

Ou baixam dos releases do GitHub. O binário não possui dependências externas (o runtime do Go é linkado estaticamente).

## Estratégia de Tratamento de Erros

### Tipos de Erro

1. **Erros de rede** - PyPI ou OSV.dev inacessíveis, timeout, falha de DNS. Tratados com retries e backoff exponencial em `internal/pypi/client.go:169-200`.

2. **Erros de parsing** - Sintaxe TOML inválida, strings de versão malformadas, respostas JSON impossíveis de analisar. Propagados com `fmt.Errorf("parse %s: %w", path, err)` para contexto.

3. **Erros de sistema de arquivos** - Permissão negada, disco cheio, caminho não encontrado. Verificados nos pontos de entrada (`os.ReadFile`, `os.WriteFile`) e envolvidos com o contexto do caminho.

### Mecanismos de Recuperação

**Cenário de falha de rede:**

- Detecção: `c.http.Do(req)` retorna erro ou código de status ≥500.
- Resposta: Tenta novamente com backoff exponencial (500ms, 1s, 2s).
- Recuperação: No sucesso da terceira tentativa, registra um aviso, mas continua. Se todas as tentativas falharem, retorna erro e usa dados em cache se disponíveis.

Exemplo de `internal/pypi/client.go:169-200`:

```go
for attempt := range maxRetries {
    if attempt > 0 {
        delay := time.Duration(1<<shift) * baseRetryMs * time.Millisecond
        select {
        case <-ctx.Done():
            return nil, ctx.Err()
        case <-time.After(delay):
        }
    }

    resp, err := c.http.Do(req)
    if err != nil {
        lastErr = err
        continue  // Tenta novamente
    }

    if resp.StatusCode >= 500 {
        _ = resp.Body.Close()
        lastErr = fmt.Errorf("server error: %d", resp.StatusCode)
        continue  // Tenta novamente em erros de servidor
    }

    return resp, nil  // Sucesso
}

return nil, fmt.Errorf("after %d attempts: %w", maxRetries, lastErr)
```

## Extensibilidade

### Onde Adicionar Recursos

Quer adicionar a geração de SBOM (Software Bill of Materials)? Aqui está onde ela entra:

1. Adicione um novo comando em `internal/cli/update.go:` seguindo o padrão de `newScanCmd()`.
2. Crie `internal/sbom/generator.go` para construir a estrutura JSON do SBOM.
3. Use o `internal/pyproject/parser.go` existente para obter a lista de dependências.
4. Formate a saída em `internal/cli/output.go` (ou escreva diretamente em um arquivo).

A chave é: parsers e clientes são reutilizáveis. Comandos CLI os orquestram.

### Arquitetura de Plugins

angela ainda não possui plugins. Se tivesse, a interface seria algo como:

```go
type VulnerabilitySource interface {
    QueryVulnerabilities(ctx context.Context, packages []Package) ([]Vulnerability, error)
}
```

Então angela poderia suportar OSV.dev, Snyk, GitHub Advisory e bancos de dados internos personalizados através da mesma interface. Isso é deixado como um exercício para os leitores (veja 04-CHALLENGES.md).

## Limitações

Limitações arquiteturais atuais:

1. **Sem scan de dependências transitivas** - angela apenas verifica pacotes explicitamente no seu arquivo de dependências. Se o `requests` depende de um `urllib3` vulnerável, você não saberá a menos que também liste o `urllib3`. Corrigir isso requer um resolvedor de dependências completo (como o do pip), o que é complexo.

2. **Sem modo offline** - angela requer acesso à rede para o PyPI e o OSV.dev. Adicionar suporte offline exigiria snapshots do banco de dados de vulnerabilidades embutidos e mirrors locais do PyPI.

3. **Um único projeto por vez** - Você não pode apontar a angela para 10 projetos e obter resultados agregados. A CLI foi projetada para um `pyproject.toml` por invocação.

Estes não são bugs, são trade-offs conscientes para manter o escopo do projeto iniciante gerenciável. O [04-CHALLENGES.md](./04-CHALLENGES.md) explica como abordar cada um.

## Comparação com Sistemas Semelhantes

### vs pip-audit

Como somos diferentes:

- pip-audit requer uma instalação do Python e usa o resolvedor do pip. angela é um binário Go independente.
- pip-audit escaneia pacotes instalados (saída do `pip list`). angela escaneia arquivos de dependência antes da instalação.
- pip-audit não atualiza versões. angela faz tanto o scan quanto a atualização.

Por que fizemos escolhas diferentes: angela foi projetada para CI/CD onde você quer verificar _antes_ de instalar. pip-audit é melhor para auditar ambientes de produção.

### vs Dependabot

Como somos diferentes:

- Dependabot é um bot do GitHub que abre PRs. angela é uma ferramenta CLI local.
- Dependabot conhece todos os ecossistemas (npm, PyPI, Maven, etc.). angela faz apenas PyPI.
- Dependabot possui resolução de versão sofisticada com trade-offs entre segurança e compatibilidade. angela possui uma lógica simples de "mais recente estável".

Por que fizemos escolhas diferentes: Dependabot é um serviço de produção com uma equipe mantendo-o. angela é um projeto de aprendizado. A arquitetura reflete isso (simples e hackeável vs robusta e abrangente).

## Referência de Arquivos Chave

Mapa rápido de onde encontrar as coisas:

- `cmd/angela/main.go` - Ponto de entrada, apenas chama cli.Execute().
- `internal/cli/update.go` - Todas as implementações de comando (update, scan, check).
- `internal/pypi/client.go` - Cliente HTTP com retries e cache.
- `internal/pypi/version.go` - Parser PEP 440 e lógica de comparação.
- `internal/osv/client.go` - Scanner de vulnerabilidades com consultas em lote.
- `internal/pyproject/writer.go` - Edição de TOML baseada em regex.
- `internal/ui/spinner.go` - Animação de spinner no terminal.
- `pkg/types/types.go` - Structs compartilhadas (Dependency, Vulnerability, etc.).

## Próximos Passos

Agora que você entende a arquitetura:

1. Leia [03-IMPLEMENTATION.md](./03-IMPLEMENTATION.md) para o passo a passo do código linha por linha.
2. Tente modificar o TTL do cache em `internal/pypi/cache.go:11` e veja como isso afeta o desempenho.
3. Adicione um novo comando (como `angela stats` para mostrar a taxa de hit do cache) seguindo os padrões da CLI.
