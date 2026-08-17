# Arquitetura do Sistema

Este documento detalha como o Portia foi projetado e por que certas decisões arquiteturais foram tomadas. Vamos rastrear as requisições através do sistema e explicar os trade-offs.

## Arquitetura de Alto Nível

```
┌──────────────────────────────────────────────────────┐
│                       CLI                            │
│           root.go, scan.go, git.go                   │
└───────────────────────┬──────────────────────────────┘
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
      ┌──────────────┐   ┌──────────────┐
      │   Directory   │   │     Git      │
      │    Source     │   │    Source     │
      │ directory.go  │   │   git.go     │
      └──────┬───────┘   └──────┬───────┘
             │                   │
             └─────────┬─────────┘
                       │
                       ▼ chan types.Chunk
              ┌─────────────────┐
              │    Pipeline     │
              │  pipeline.go    │
              ├─────────────────┤
              │                 │
              │  ┌───────────┐  │
              │  │ Worker 1  │  │
              │  │ detector  │  │
              │  └───────────┘  │
              │  ┌───────────┐  │
              │  │ Worker 2  │  │
              │  │ detector  │  │
              │  └───────────┘  │
              │  ┌───────────┐  │
              │  │ Worker N  │  │
              │  │ detector  │  │
              │  └───────────┘  │
              │                 │
              └────────┬────────┘
                       │
                       ▼ chan types.Finding
              ┌─────────────────┐
              │   Collector     │
              │  dedup + merge  │
              └────────┬────────┘
                       │
              ┌────────┴────────┐
              │                 │
              ▼                 ▼
      ┌──────────────┐  ┌──────────────┐
      │  HIBP Check  │  │   Reporter   │
      │  (opcional)  │  │  term/json/  │
      │  client.go   │  │    sarif     │
      └──────┬───────┘  └──────────────┘
             │                 ▲
             └─────────────────┘
```

## Divisão dos Componentes

### Camada CLI (`internal/cli/`)

**Propósito:** Analisar argumentos de linha de comando e orquestrar o workflow de escaneamento.

**Responsabilidades:**

- Roteia os comandos `scan`, `git`, `init`, `pyproject`, `config` para seus respectivos handlers.
- Mescla as flags da CLI com os valores do arquivo de configuração TOML (as flags da CLI têm precedência).
- Cria a Source apropriada, executa o Pipeline, opcionalmente verifica o HIBP e produz a saída.

**Interfaces:** Usa o Cobra para parsing de argumentos. Cada comando é um `cobra.Command` com uma função `RunE`. A função `executeScan` em `scan.go` é compartilhada entre os comandos `scan` e `git`.

### Carregador de Configuração (`internal/config/`)

**Propósito:** Carregar e mesclar a configuração dos arquivos `.portia.toml`.

**Responsabilidades:**

- Procura por arquivos de configuração em três locais: diretório atual, `.portia/config.toml`, `~/.config/portia/config.toml`.
- Recorre ao `pyproject.toml` (tabela `[tool.portia]`) quando nenhum `.portia.toml` é encontrado.
- Analisa o TOML em uma struct `Config` com seções para Rules, Scan, Output, HIBP, Allowlist.
- Fornece templates padrão para `portia init` e `portia pyproject`.

**Interfaces:** `Load(path string) (*Config, error)` retorna uma configuração ou erro. Um caminho vazio dispara a auto-descoberta.

### Interface Source (`internal/source/`)

**Propósito:** Produzir chunks de texto a partir de várias entradas (diretórios, histórico git).

**Responsabilidades:**

- Percorre o sistema de arquivos ou a árvore de objetos git.
- Pula arquivos binários, caminhos excluídos, arquivos excessivamente grandes.
- Divide o conteúdo em chunks de 50 linhas com metadados de caminho de arquivo e número de linha.
- Envia os chunks para um canal para consumo pelo pipeline.

**Interfaces:**

```go
type Source interface {
    Chunks(ctx context.Context, out chan<- types.Chunk) error
    String() string
}
```

**Directory source** (`directory.go`):

- Usa `filepath.WalkDir` para travessia do sistema de arquivos.
- Pula `.git`, `node_modules`, `vendor`, `__pycache__`, `.venv`.
- Verifica o tamanho do arquivo contra o máximo configurável (padrão 1MB).
- Divide os arquivos em segmentos de 50 linhas usando um scanner com buffer.

**Git source** (`git.go`):

- Usa o go-git v5 para operações git em processo.
- `scanHistory`: percorre o log de commits de trás para frente, extrai o conteúdo do arquivo da árvore de cada commit.
- `scanStaged`: lê as entradas do índice git para escaneamento apenas de arquivos em staging.
- Suporta filtros `--branch`, `--since`, `--depth`.

### Registro de Regras (`internal/rules/`)

**Propósito:** Armazenar regras de detecção e fornecer busca rápida baseada em palavras-chave.

**Responsabilidades:**

- Armazena regras em um mapa indexado pelo ID da regra.
- Fornece `MatchKeywords(content)` que retorna apenas as regras cujas palavras-chave aparecem no conteúdo.
- Suporta ativação/desativação de regras.
- Mantém allowlists globais de caminhos e valores.

**Interfaces:** `Register(rule)`, `Get(id)`, `All()`, `MatchKeywords(content)`, `Disable(ids...)`, `Len()`.

### Engine de Detecção (`internal/engine/`)

**Propósito:** Aplicar regras aos chunks e produzir descobertas (findings).

**Detector** (`detector.go`):

- Recebe um chunk, executa o pré-filtro de palavras-chave via registro.
- Para cada regra correspondente, escaneia linha por linha com regex.
- Extrai o segredo do grupo de captura.
- Valida a entropia se a regra tiver um limite de entropia.
- Passa pelo FilterFinding para redução de falsos positivos.

**Filter** (`filter.go`):

- `IsPlaceholder` - verifica contra padrões da GlobalValueAllowlist.
- `IsTemplated` - verifica por `${...}`, `{{...}}`, `os.getenv()`, `process.env.`.
- `IsStopword` - divide o segredo nos delimitadores `_-./`, verifica as partes contra mais de 700 stopwords.
- `IsAllowedPath` - verifica o caminho do arquivo contra a GlobalPathAllowlist.
- `FilterFinding` - orquestra todas as verificações, retorna verdadeiro se a descoberta for real.

**Pipeline** (`pipeline.go`):

- Cria um errgroup com a goroutine da source + N goroutines de worker + goroutine de collector.
- Os workers retiram chunks do canal, executam o detector e enviam as descobertas para o canal de findings.
- O collector mescla todas as descobertas, removendo duplicatas por ruleID+filePath+secret+commitSHA.

### Cliente HIBP (`internal/hibp/`)

**Propósito:** Verificar segredos detectados contra o banco de dados de violações Have I Been Pwned.

**Responsabilidades:**

- Computação de hash SHA-1.
- Consultas à API de k-anonymity (prefixo de 5 caracteres).
- Cache LRU (10.000 entradas) para buscas repetidas.
- Circuit breaker (5 falhas = 60s de cooldown).
  **Interfaces:** `Check(ctx, secret) (Result, error)`.

### Reporters (`internal/reporter/`)

**Propósito:** Formatar os resultados do escaneamento para saída.

**Terminal** (`terminal.go`): Saída colorida com cores baseadas na severidade (vermelho para CRITICAL, amarelo para MEDIUM), mascaramento de segredo (mostra os primeiros/últimos caracteres), truncamento de SHA para commits git, status de violação HIBP.

**JSON** (`json.go`): JSON estruturado com um array `findings` e um objeto `summary`. Os segredos são mascarados na saída.

**SARIF** (`sarif.go`): Saída compatível com SARIF v2.1.0 com metadados da ferramenta, definições de regras, resultados com localizações e propriedades.

**Interfaces:** Interface `Reporter` com `Report(w io.Writer, result *types.ScanResult) error`. A função factory `New(format) Reporter` retorna a implementação apropriada.

## Fluxo de Dados

### Rastreamento: `portia scan ./meuprojeto`

Passo a passo do que acontece durante um escaneamento de diretório:

```
1. CLI analisa os argumentos
   root.go:init() → cobra.OnInitialize(initConfig)
   scan.go:runScan() recebe path="./meuprojeto"

2. Carregamento da configuração
   root.go:initConfig() → config.Load(cfgFile)
   Mescla flags da CLI com o TOML de configuração
   Format assume "terminal" por padrão, maxSize assume 1MB

3. Configuração do registro
   scan.go:runScan() → rules.NewRegistry() + rules.RegisterBuiltins(reg)
   Carrega 150 regras no mapa do registro
   Aplica regras desativadas da config: reg.Disable(cfg.Rules.Disable...)

4. Criação da Source
   scan.go:runScan() → source.NewDirectory(path, maxSize, excludes)
   Cria a struct Directory com caminho, tamanho máximo de arquivo, padrões de exclusão

5. Execução do Pipeline
   scan.go:executeScan() → engine.NewPipeline(reg).Run(ctx, src)

   5a. Goroutine da Source inicia
       Chama src.Chunks(ctx, chunks)
       WalkDir percorre ./meuprojeto
       Pula .git, node_modules, vendor, extensões binárias
       Divide cada arquivo em chunks de 50 linhas
       Envia cada chunk para o canal de chunks

   5b. Goroutines de Worker iniciam (2-16 baseadas em NumCPU)
       Cada uma retira chunks do canal
       Chama detector.Detect(chunk):
         - reg.MatchKeywords(chunk.Content) → apenas regras com palavras-chave correspondentes
         - Para cada regra correspondente, escaneia cada linha com a regex rule.Pattern
         - Extrai o segredo do grupo de captura
         - Se a regra tiver limite de entropia, computa a entropia de Shannon e compara
         - Executa FilterFinding: IsPlaceholder → IsTemplated → IsStopword → path allowlist
         - Se todas as verificações passarem, cria um Finding e envia para o canal de findings

   5c. Goroutine do Collector
       Retira descobertas do canal de findings
       Anexa ao slice allFindings (protegido por mutex)

   5d. Aguarda por todas as goroutines (errgroup.Wait)
       Remove duplicatas de findings por ruleID+filePath+secret+commitSHA

6. Verificação HIBP (se a flag --hibp estiver presente)
   scan.go:checkHIBP(ctx, result)
   Para cada descoberta, chama client.Check(ctx, finding.Secret)
   Atualiza finding.HIBPStatus e finding.BreachCount

7. Saída do Reporter
   scan.go:executeScan() → reporter.New(format).Report(os.Stdout, result)
   Terminal: tabela colorida com severidade, regra, arquivo:linha, segredo mascarado
   JSON: JSON estruturado para o stdout
   SARIF: JSON SARIF v2.1.0 para o stdout
```

## Modelo de Concorrência

O pipeline usa o padrão errgroup do Go para concorrência estruturada:

```
                    errgroup
                   ┌────────────────────────────────┐
                   │                                │
  Goroutine Source │  ──chunks──▶  Worker 1          │
                   │              Worker 2          │
                   │              ...               │
                   │              Worker N          │
                   │              ──findings──▶     │
                   │                    Collector   │
                   │                                │
                   └────────────────────────────────┘
```

**Por que workers limitados?** A correspondência de regex limitada pela CPU não se beneficia do paralelismo ilimitado. Muitas goroutines competindo por tempo de CPU causam overhead de troca de contexto. A fórmula `min(max(NumCPU, 2), 16)` fornece 2 workers em máquinas de núcleo único e limita a 16 em servidores grandes.

**Por que errgroup?** Ele fornece duas coisas: (1) se qualquer goroutine retornar um erro, o contexto é cancelado e todas as goroutines são encerradas de forma limpa, e (2) `g.Wait()` bloqueia até que todas as goroutines terminem, fornecendo um único ponto para verificar erros.

**Dimensionamento de canais:** Os canais possuem buffer de `workers * 4`. Isso permite que a source permaneça à frente dos workers (evitando bloqueio nos envios) sem crescimento ilimitado de memória. Se os workers estiverem lentos, a source bloqueará assim que o buffer encher, fornecendo backpressure natural.

**A dança do detectWg:** Os workers compartilham um `sync.WaitGroup` separado para que saibamos quando toda a detecção terminou. A goroutine do collector roda no mesmo errgroup, mas só fecha após todos os workers terminarem. Isso evita que o collector saia prematuramente enquanto descobertas ainda estão sendo produzidas. Veja `pipeline.go:52-77`.

## Resolução de Configuração

A configuração é resolvida nesta ordem (a posterior sobrescreve a anterior):

```
1. Padrões (hardcoded)
   Format: "terminal"
   MaxSize: 1MB (1 << 20)
   Workers: min(max(NumCPU, 2), 16)
   HIBP: desativado
   Verbose: false
   NoColor: false

2. Arquivo de configuração (.portia.toml)
   Procurado na ordem:
     .portia.toml (diretório atual)
     .portia/config.toml
     ~/.config/portia/config.toml
   O primeiro encontrado é carregado. Caminhos posteriores não são verificados.
   Se nenhum for encontrado, recorre ao pyproject.toml (tabela [tool.portia]).

3. Flags da CLI
   --format, --verbose, --no-color, --exclude, --max-size, --hibp, --config
   Estas sempre vencem os valores do arquivo de configuração.
```

Esta lógica de mesclagem está em `internal/cli/root.go:initConfig()`. O padrão é: verificar se a flag da CLI foi explicitamente definida (não-zero/não-vazia) e apenas recorrer ao valor do arquivo de configuração se a flag não tiver sido definida.

## Estratégia de Correspondência de Regras

O pipeline de detecção é otimizado para velocidade. A correspondência de regex é cara, então o objetivo é evitar rodar regex contra conteúdo que nunca corresponderá.

```
Chunk de conteúdo (50 linhas de código)
        │
        ▼
┌───────────────────┐
│ Filtro de Keywords│  ← O(rules * keywords) string.Contains
│ ~95% eliminados   │
└────────┬──────────┘
         │ Apenas regras cujas keywords aparecem neste chunk
         ▼
┌───────────────────┐
│ Correspondência   │  ← O(lines * matched_rules) regex
│ Regex Linha a Linha│
└────────┬──────────┘
         │ Correspondências brutas com grupos de captura
         ▼
┌───────────────────┐
│ Extração Segredo  │  ← Extração do grupo de captura
│ + Check Entropia  │     Descarta se abaixo do limite
└────────┬──────────┘
         │ Candidatos validados
         ▼
┌───────────────────┐
│ Cadeia de Filtros │  ← IsPlaceholder → IsTemplated
│ Check de 5 camadas│     → IsStopword → Allowlists
└────────┬──────────┘
         │ Apenas descobertas reais
         ▼
      Finding
```

O filtro de palavras-chave é a otimização de desempenho fundamental. Se um chunk de 50 linhas de HTML não contém nenhuma string como `password`, `secret`, `key`, `token`, `AKIA`, `ghp_`, `sk_live`, etc., então zero regras corresponderão e zero padrões regex precisarão rodar contra ele. Na prática, isso elimina a grande maioria dos chunks.
