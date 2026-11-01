# Desafios de Extensão

Os desafios estão organizados por dificuldade e mantêm sua numeração. Para a entrega final da trilha **Headers → V_Scanner**, haverá **um trio e uma dupla**. O projeto é um scanner de dependências Python implementado em Go.

**Base comum obrigatória:** desafios **1, 2 e 3**, preservando leitura de dependências, consulta ao OSV, análise de versões, cache e atualização de arquivos. Cada grupo mantém sua própria versão funcional, com testes das mudanças e demonstração reproduzível. As estatísticas devem usar contadores reais de hit/miss; JSON deve sair válido, sem cores ou progresso misturados ao documento.

| Grupo | Foco do projeto final                  | Desafios obrigatórios      | Exigência principal                                                 |
| ----- | -------------------------------------- | -------------------------- | ------------------------------------------------------------------- |
| **1** | Mapa de dependências e inventário SBOM | **1–3 + 5 e 6**            | Grafo, vulnerabilidades transitivas e exportação; maior integração. |
| **2** | Monitoramento de mudanças de risco     | **1–3 + 4 e recorte do 7** | Um arquivo, versões fixadas e monitor local periódico.              |

**A entrega final é a base comum mais o escopo atribuído ao grupo.** Os recortes obrigatórios estão nos próprios desafios e delimitam o que será cobrado. As propostas mais amplas de resolvedor, daemon e integrações permanecem como aprofundamento opcional. Os números identificam os escopos.

O desafio **8 (fontes privadas)**, as seções de desempenho, segurança e integração e as demandas do outro grupo são opcionais e não substituem as atribuídas. Cada ferramenta deve funcionar sem depender da implementação do outro grupo.

**Na apresentação:** mostrem brevemente a base comum e concentrem a demonstração no diferencial, com um caso de sucesso, um caso de erro ou limite e as decisões tomadas. Separem o código fornecido do que foi desenvolvido e identifiquem os dados simulados.

## Desafios Fáceis

### Desafio 1: Adicionar Exibição de Severidade Codificada por Cores

**Obrigatório para os dois grupos.**

**O que construir:**
Melhorar a saída de vulnerabilidades para mostrar a severidade com cores de fundo, não apenas a cor do texto.

**Por que é útil:**
Ao escanear 50 pacotes com mais de 20 vulnerabilidades, problemas de nível CRITICAL devem saltar aos olhos. O fundo vermelho torna impossível ignorá-los.

**O que você aprenderá:**

- Códigos de escape ANSI para cores de fundo
- Formatação de strings com estilos mistos
- Design de experiência do usuário em interfaces de terminal

**Dicas:**

- Veja `internal/cli/output.go:228-248` onde `severityColorFn()` escolhe as cores do texto
- O pacote fatih/color suporta `color.BgRed` para cores de fundo
- Não se esqueça de lidar com o caso onde a variável de ambiente `NO_COLOR` está definida

**Teste se funciona:**
Execute `angela scan --file testdata/pyproject.toml` e verifique se as vulnerabilidades CRITICAL possuem fundos vermelhos, enquanto as vulnerabilidades LOW usam cores normais.

### Desafio 2: Mostrar Estatísticas de Hit do Cache

**Obrigatório para os dois grupos.**

**O que construir:**
Adicionar um subcomando `stats` que mostre as taxas de hit/miss do cache, o tamanho do cache e as entradas mais antigas/recentes.

**Por que é útil:**
Ajuda os usuários a entender se o cache está funcionando. Se a taxa de hit for <50%, talvez o TTL seja muito curto.

**O que você aprenderá:**

- Operações de sistema de arquivos (leitura de diretório, chamadas de sistema stat)
- Agregação de dados e estatísticas de resumo
- Formatação de tempo para saída legível por humanos

**Abordagem de implementação:**

1. **Adicionar comando** em `internal/cli/update.go`:

   ```go
   func newStatsCmd() *cobra.Command {
       return &cobra.Command{
           Use:   "stats",
           Short: "Show cache statistics",
           RunE: func(_ *cobra.Command, _ []string) error {
               return runStats()
           },
       }
   }
   ```

2. **Implementar runStats()** que:
   - Liste todos os arquivos `.json` em `~/.angela/cache/`
   - Analise cada um para obter o timestamp `cached_at`
   - Calcule: total de entradas, tamanho total no disco, distribuição de idade

3. **Formatar a saída** como:

   ```text
   Cache Statistics
   ────────────────────────────────────
   Total entries:     42
   Cache size:        1.2 MB
   Oldest entry:      7 days ago (requests.json)
   Newest entry:      5 minutes ago (flask.json)
   Average age:       2 days 4 hours
   ```

**Dicas:**

- Use `os.ReadDir()` para listar o diretório de cache
- `os.Stat()` fornece o tamanho do arquivo
- Analise `cached_at` com `time.Parse()` para calcular a idade
- O pacote `internal/ui/` possui auxiliares de cores para uma saída bonita

**Teste se funciona:**
Execute a angela algumas vezes com pacotes diferentes, então `angela stats` deve mostrar o aumento na contagem de entradas.

### Desafio 3: Implementar Modo de Saída --json

**Obrigatório para os dois grupos.**

**O que construir:**
Adicionar uma flag `--json` que exiba os resultados como JSON em vez da formatação bonita de terminal.

**Aplicação no mundo real:**
Pipelines de CI/CD precisam de saída legível por máquina. O GitHub Actions pode analisar JSON para criar anotações.

**O que você aprenderá:**

- Marshaling de JSON com estruturas personalizadas
- Manipulação de flags de linha de comando
- Adaptação de código legível por humanos para automação

**Abordagem de implementação:**

1. **Adicionar flag** aos comandos relevantes:

   ```go
   var jsonOutput bool
   cmd.Flags().BoolVar(&jsonOutput, "json", false, "output as JSON")
   ```

2. **Criar structs JSON** em `pkg/types/types.go`:

   ```go
   type JSONOutput struct {
       Updates         []UpdateResult      `json:"updates"`
       Vulnerabilities []VulnByPackage     `json:"vulnerabilities"`
       Summary         ScanResult          `json:"summary"`
   }

   type VulnByPackage struct {
       Package string          `json:"package"`
       Vulns   []Vulnerability `json:"vulnerabilities"`
   }
   ```

3. **Saída condicional** em `internal/cli/output.go`:

   ```go
   if jsonOutput {
       data, _ := json.MarshalIndent(result, "", "  ")
       fmt.Println(string(data))
   } else {
       PrintUpdates(result.Updates)
       PrintVulnerabilities(result.Vulnerabilities)
       PrintSummary(result.Summary, updated)
   }
   ```

**Crédito extra:**
Suportar `--json-compact` para saída em linha única (sem indentação) adequada para agregação de logs.

**Teste se funciona:**

```bash
angela scan --file testdata/pyproject.toml --json | jq '.vulnerabilities[].package'
```

Deve retornar os nomes dos pacotes como um array JSON.

## Desafios Intermediários

### Desafio 4: Adicionar Suporte a requirements.in

**Obrigatório — Grupo 2 (2 integrantes), junto com o recorte do desafio 7.**

**Recorte da entrega:** ler e atualizar `requirements.in`, preservando comentários e aproveitando o parser existente. Orientar a regeneração de arquivos produzidos pelo pip-tools após atualizar o `.in`. O monitor usa versões fixadas (`pacote==versão`); quando uma versão não estiver resolvida, informar análise incompleta em vez de presumir uma versão segura.

**Demonstração própria:** alterar uma dependência do `.in`, mostrar a preservação dos comentários e usar o arquivo no monitor do desafio 7. Não é necessário implementar um resolvedor de versões.

**O que construir:**
Estender a angela para lidar com arquivos requirements.in (usados pelo pip-tools para compilação de dependências).

**Aplicação no mundo real:**
O workflow do pip-tools usa `requirements.in` para dependências de alto nível e compila para `requirements.txt`. A angela deve atualizar o arquivo .in, e então os usuários executam `pip-compile` para regenerar o .txt.

**O que você aprenderá:**

- Suporte a múltiplos formatos de arquivo
- Detecção de tipo de arquivo
- Reuso de código entre formatos semelhantes

**Abordagem de implementação:**

1. **Detectar tipo de arquivo** em `internal/cli/update.go:395-401`:

   ```go
   func isRequirementsIn(path string) bool {
       return strings.HasSuffix(strings.ToLower(path), ".in")
   }
   ```

2. **Reutilizar o parser** - requirements.in usa a mesma sintaxe que requirements.txt:

   ```go
   func parseDeps(file string) ([]types.Dependency, error) {
       if isRequirementsTxt(file) || isRequirementsIn(file) {
           return requirements.ParseFile(file)
       }
       return pyproject.ParseFile(file)
   }
   ```

3. **Lidar com a atualização de forma diferente** - Após atualizar o requirements.in, sugerir a execução do pip-compile:

   ```go
   if updated && isRequirementsIn(file) {
       fmt.Printf("\n  %s %s\n",
           ui.HiYellow(ui.ArrowRight),
           ui.HiBlackItalic("Run 'pip-compile' to regenerate requirements.txt"))
   }
   ```

**Dicas:**

- requirements.in e requirements.txt são formatos idênticos
- A única diferença é que o pip-tools lê o .in e escreve o .txt
- A angela deve atualizar o .in, não o .txt (que é gerado automaticamente)

**Teste se funciona:**
Crie um `test.in` com `requests>=2.28.0`, execute `angela update --file test.in`, verifique se a versão foi atualizada e se o arquivo preservou os comentários.

### Desafio 5: Escanear Dependências Transitivas

**Obrigatório — Grupo 1 (3 integrantes), junto com o desafio 6.**

**Recorte da entrega:**

- Obter o grafo de **um projeto com versões já resolvidas**, por ambiente instalado, arquivo de resolução ou resolvedor existente. Não é necessário construir PubGrub nem um resolvedor geral.
- Distinguir dependências diretas e transitivas, percorrer pelo menos dois níveis, evitar repetição e tratar ciclos.
- Consultar vulnerabilidades de todos os componentes e mostrar o caminho até um componente transitivo afetado. Versão ausente ou falha de consulta deve aparecer como análise incompleta.
- Reutilizar o mesmo grafo na exportação do desafio 6. Testar ciclos, componentes repetidos e metadados ausentes.

**Demonstração própria:** mostrar `aplicação → A → B → C`, com versões fixadas e um aviso simulado em B ou C, ausente das dependências diretas da aplicação. Exibir o caminho até o risco e o inventário exportado. As propostas de resolução própria abaixo são aprofundamento opcional.

**O que construir:**
Em vez de apenas escanear pacotes no pyproject.toml, obtenha a árvore de dependências com versões resolvidas e escaneie seus componentes. O recorte acima permite usar um resolvedor existente; criar um resolvedor é uma extensão opcional.

**Por que isso é difícil:**
A resolução de dependências é complexa. Você precisa:

- Analisar especificadores de versão e encontrar versões compatíveis
- Lidar com requisitos conflitantes (pacote A precisa de requests>=2.0, pacote B precisa de requests<3.0)
- Respeitar marcadores de plataforma (algumas dependências apenas no Windows)
- Lidar com dependências circulares

**O que você aprenderá:**

- Algoritmos de resolução de dependências (PubGrub, usado pelo Poetry)
- Travessia de grafo e detecção de ciclos
- Problemas de satisfação de restrições

**Abordagem de implementação:**

1. **Fase de pesquisa**
   - Leia a PEP 508 (especificadores de dependência)
   - Estude o resolvedor do pip ou a implementação do Poetry
   - Entenda o algoritmo PubGrub (https://github.com/pubgrub-rs/pubgrub)

2. **Fase de design**
   - Decida: PubGrub completo ou um resolvedor BFS simplificado?
   - Para um projeto iniciante: BFS com "primeira versão compatível" é o suficiente
   - Considere o desempenho: o cache de metadados de versão é crítico

3. **Fase de implementação**
   - Comece com `func ResolveTree(deps []Dependency) ([]Dependency, error)`
   - Para cada dependência, busque suas dependências nos metadados do PyPI
   - Resolva recursivamente até que nenhum novo pacote seja encontrado
   - Remova duplicatas: se um pacote aparecer múltiplas vezes, escolha a versão compatível mais alta

4. **Fase de teste**
   - Teste com o flask (possui muitas dependências transitivas)
   - Verifique se dependências circulares não causam loops infinitos
   - Verifique se erros de requisitos conflitantes são exibidos claramente

**Armadilhas:**

- A Simple API do PyPI não inclui informações de dependência. Você precisa da API JSON: `https://pypi.org/pypi/{package}/json`
- A resolução de dependências é NP-difícil no caso geral. Simplificações são necessárias.
- Marcadores de ambiente (`platform_system == "Windows"`) precisam de avaliação

**Recursos:**

- PEP 508: https://peps.python.org/pep-0508/
- Poetry resolver: https://github.com/python-poetry/poetry-core
- Artigo PubGrub: https://medium.com/@nex3/pubgrub-2fb6470504f

### Desafio 6: Gerar SBOM (Software Bill of Materials)

**Obrigatório — Grupo 1 (3 integrantes), junto com o desafio 5.**

**Recorte da entrega:** gerar **um formato**, CycloneDX ou SPDX, com versão do padrão declarada, componentes, versões, identificadores e relações do grafo. Incluir licença e hash de um artefato identificado quando disponíveis; explicitar ausências sem inventar metadados. Validar contra o esquema da versão e do formato escolhidos.

**Demonstração própria:** exportar o grafo do desafio 5 e comprovar que a dependência transitiva afetada e suas relações aparecem no SBOM validado. Não são exigidos os dois formatos nem o suporte a `requirements.in` do outro grupo.

**O que construir:**
Adicionar o comando `angela sbom` que exporta um SBOM no formato CycloneDX ou SPDX.

**Por que isso é difícil:**
Formatos SBOM são verbosos e exigem dados que a angela não coleta atualmente (informações de licença, hashes de pacotes, relacionamentos entre componentes).

**O que você aprenderá:**

- Padrões SBOM (CycloneDX 1.5, SPDX 2.3)
- Segurança da cadeia de suprimentos de software
- Exportação de dados estruturados

**Mudanças de arquitetura necessárias:**

```text
┌─────────────────────┐
│  angela sbom        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐     ┌─────────────────────┐
│  Coletar Metadados  │────▶│   PyPI JSON API     │
│  - Licença          │     │   /pypi/{pkg}/json  │
│  - Autor            │     └─────────────────────┘
│  - Hashes           │
│  - Dependências     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Formatar como SBOM │
│  - CycloneDX XML    │
│  - SPDX JSON        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Saída para Arquivo │
└─────────────────────┘
```

**Etapas de implementação:**

1. **Adicionar buscador de metadados do PyPI** em `internal/pypi/metadata.go`:

   ```go
   type PackageMetadata struct {
       Name         string
       Version      string
       License      string
       Author       string
       HomePage     string
       SHA256Hash   string
       Dependencies []string
   }

   func (c *Client) FetchMetadata(ctx context.Context, name, version string) (*PackageMetadata, error) {
       url := fmt.Sprintf("https://pypi.org/pypi/%s/%s/json", name, version)
       // ... requisição HTTP, parse do JSON ...
   }
   ```

2. **Criar gerador de SBOM** em `internal/sbom/cyclonedx.go`:

   ```go
   func GenerateCycloneDX(deps []Dependency, metadata map[string]*PackageMetadata) ([]byte, error) {
       bom := CycloneDXBOM{
           BOMFormat:    "CycloneDX",
           SpecVersion:  "1.5",
           Version:      1,
           Components:   buildComponents(deps, metadata),
           Dependencies: buildDependencies(deps),
       }
       return xml.MarshalIndent(bom, "", "  ")
   }
   ```

3. **Adicionar comando** em `internal/cli/update.go`:

   ```go
   func newSBOMCmd() *cobra.Command {
       return &cobra.Command{
           Use:   "sbom",
           Short: "Generate Software Bill of Materials",
           RunE:  runSBOM,
       }
   }
   ```

**Critérios de sucesso:**
Seu SBOM deve:

- [ ] Incluir todas as dependências diretas
- [ ] Incluir licenças disponíveis e explicitar metadados ausentes
- [ ] Incluir hashes SHA256 de artefatos identificados quando disponíveis, sem inventar valores
- [ ] Vincular dependências (A depende de B)
- [ ] Validar contra o esquema da versão escolhida de CycloneDX ou SPDX

**Teste se funciona:**

```bash
angela sbom --file pyproject.toml --output sbom.xml
cyclonedx validate sbom.xml
```

Deve passar na validação.

## Desafios Avançados

### Desafio 7: Implementar Monitoramento Contínuo

**Obrigatório — Grupo 2 (2 integrantes), junto com o desafio 4.**

**Recorte da entrega para a dupla:**

- Implementar **um monitor em primeiro plano, com intervalo configurável**, para um arquivo `requirements.in` e dependências diretas com versões fixadas. Um ciclo por vez é suficiente.
- Reler o arquivo e consultar vulnerabilidades a cada ciclo. Detectar tanto mudança de dependência quanto aviso novo com arquivo inalterado.
- Persistir o último estado válido e comparar pacote, versão e identificador do aviso para registrar novidades e resoluções sem repetir alertas, inclusive após reinício.
- Em timeout, erro da fonte, versão não resolvida ou arquivo inválido, registrar análise incompleta e preservar o estado válido. Uma falha não significa que um aviso foi resolvido.
- Encerrar com segurança em interrupção. Atualizar dependências continua sendo uma ação explícita, separada do monitor.
- Testar com relógio e respostas controlados, sem esperas longas nem dependência de um aviso real surgir durante a apresentação.

**Demonstração própria:** mostrar estado inicial, aviso novo sem mudar o arquivo, repetição sem duplicar alerta e atualização para versão corrigida. Simular falha de consulta e reiniciar para comprovar preservação do estado. O foco é a mudança de risco ao longo do tempo.

**Limite do recorte:** serviço de sistema, execução em background, watcher de arquivos, webhook, nuvem, grafo e SBOM são opcionais. A arquitetura e as fases abaixo são referências para a versão completa, não exigências adicionais para a dupla.

**O que construir:**
Um monitor que verifica mudanças nas dependências e nos avisos de vulnerabilidade. Para a dupla, vale o loop periódico local descrito acima; o daemon em segundo plano é uma evolução opcional.

**Tempo estimado:**
20-30 horas

**Pré-requisitos:**
Concluir os Desafios 2-4 primeiro. Isso se baseia na saída JSON, estatísticas de cache e suporte a múltiplos formatos de arquivo.

**O que você aprenderá:**

- Observação de sistema de arquivos com fsnotify
- Processos daemon de longa duração
- Manipulação de sinais para desligamento gracioso
- Limitação de taxa (rate limiting) para evitar sobrecarregar o OSV.dev

**Planejando este recurso:**

Antes de codificar, pense sobre:

- Como o daemon inicia e para? (serviço systemd? Processo em segundo plano?)
- O que dispara um scan? (mudança no arquivo? Intervalo de tempo? Ambos?)
- Para onde vão os resultados? (Terminal? Arquivo de log? Webhook?)
- Como evitar loops infinitos se a angela modificar o arquivo que está observando?

**Arquitetura de alto nível:**

```text
┌─────────────────────┐
│   angela daemon     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   File Watcher      │  fsnotify no pyproject.toml
│   (debounce 5s)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Parse & Scan       │  Lê dependências, consulta OSV
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Notificar Mudanças  │  Log ou webhook em novas CVEs
└─────────────────────┘
```

**Fases de implementação:**

**Fase 1: Observação de Arquivos** (3-5 horas)

```go
watcher, err := fsnotify.NewWatcher()
defer watcher.Close()

err = watcher.Add("pyproject.toml")
if err != nil {
    log.Fatal(err)
}

for {
    select {
    case event := <-watcher.Events:
        if event.Op&fsnotify.Write == fsnotify.Write {
            log.Println("File modified:", event.Name)
            // Debounce: espera 5 segundos por mais mudanças
            debounce(5*time.Second, scanFile)
        }
    case err := <-watcher.Errors:
        log.Println("Error:", err)
    }
}
```

**Fase 2: Escaneamento em Segundo Plano** (8-12 horas)

- Execute scans sem bloquear o loop principal
- Limite de taxa: não escaneie mais de uma vez por minuto
- Armazene resultados anteriores para detectar _novas_ vulnerabilidades
- Armazene o estado em `~/.angela/daemon_state.json`

**Fase 3: Notificações** (4-6 horas)

- Registre novas CVEs em `~/.angela/daemon.log`
- Opcional: webhook para Slack/Discord
- Opcional: notificação de desktop via notify-send

**Fase 4: Manipulação de Sinais** (2-3 horas)

```go
sigChan := make(chan os.Signal, 1)
signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

go func() {
    <-sigChan
    log.Println("Shutting down gracefully...")
    // Cancela scans em andamento
    // Fecha o watcher
    // Escreve o estado no disco
    os.Exit(0)
}()
```

**Desafios conhecidos:**

1. **Debouncing de eventos de arquivo**
   - Problema: Editores de texto disparam múltiplos eventos de Write por salvamento
   - Dica: Use um timer que reseta a cada evento. Só escaneie após 5 segundos de silêncio.

2. **Detectando novas vulnerabilidades vs antigas**
   - Problema: Como saber se a CVE-2024-1234 é nova ou já estava lá?
   - Dica: Armazene os resultados do scan anterior em `daemon_state.json`. Compare o atual com o anterior.

3. **Gerenciamento de ciclo de vida do daemon**
   - Problema: Como o usuário inicia/para/reinicia o daemon?
   - Dica: `angela daemon start --background` faz um fork e sai. `angela daemon stop` envia SIGTERM para o arquivo PID.

**Critérios de sucesso:**
No recorte obrigatório da dupla, o monitor deve:

- [ ] Reler o requirements.in a cada intervalo e perceber mudanças nas dependências
- [ ] Detectar um novo aviso mesmo sem alteração no arquivo
- [ ] Registrar avisos novos e resolvidos sem duplicar alertas
- [ ] Encerrar com segurança em interrupção
- [ ] Reiniciar sem perder o estado válido
- [ ] Respeitar o intervalo configurado e executar apenas um ciclo por vez
- [ ] Preservar o estado válido em falhas e indicar análise incompleta

### Desafio 8: Adicionar Suporte a Banco de Dados de Vulnerabilidades Privado

**Opcional nesta entrega.** Não está atribuído a nenhum dos dois grupos.

**O que construir:**
Permitir que os usuários consultem bancos de dados de vulnerabilidades personalizados além do OSV.dev. Útil para empresas com avisos de segurança internos.

**Tempo estimado:**
15-25 horas

**Pré-requisitos:**
Você deve ter uma compreensão sólida do cliente OSV da angela e do design de interfaces.

**O que você aprenderá:**

- Arquitetura de plugins e interfaces
- Camadas de abstração de banco de dados
- Parsing de arquivos de configuração
- Design de API HTTP (se estiver construindo o servidor de banco de dados)

**Planejando este recurso:**

#### Decisão chave de design: definição da interface

```go
// pkg/vulnsource/source.go
type Source interface {
    // Name retorna um identificador único para esta fonte
    Name() string

    // ScanPackages consulta por vulnerabilidades
    ScanPackages(ctx context.Context, packages []Package) (map[string][]Vulnerability, error)

    // IsReachable verifica se a fonte está acessível
    IsReachable(ctx context.Context) error
}

// Implementação padrão
type OSVSource struct {
    client *osv.Client
}

func (s *OSVSource) ScanPackages(ctx context.Context, packages []Package) (map[string][]Vulnerability, error) {
    // Delega para o osv.Client existente
}
```

**Formato de configuração:**

```toml
[tool.angela]
# OSV.dev é sempre consultado
# Fontes adicionais:

[[tool.angela.vuln-sources]]
name = "company-internal"
url = "https://vulndb.company.com/api/v1"
api_key = "${COMPANY_VULNDB_KEY}"  # Lê de variável de ambiente
enabled = true

[[tool.angela.vuln-sources]]
name = "snyk"
url = "https://api.snyk.io/v1/test/pip"
api_key = "${SNYK_TOKEN}"
enabled = false  # Desativado
```

**Fases de implementação:**

**Fase 1: Definir Interface** (2-3 horas)

- Crie `pkg/vulnsource/source.go` com a interface Source
- Implemente o wrapper OSVSource em torno do osv.Client existente
- Escreva testes para conformidade da interface

**Fase 2: Parsing da Configuração** (3-5 horas)

```go
type VulnSourceConfig struct {
    Name    string `toml:"name"`
    URL     string `toml:"url"`
    APIKey  string `toml:"api_key"`
    Enabled bool   `toml:"enabled"`
}

func (c *Config) LoadVulnSources() ([]vulnsource.Source, error) {
    var sources []vulnsource.Source

    // Sempre inclui OSV
    sources = append(sources, vulnsource.NewOSVSource())

    for _, cfg := range c.VulnSources {
        if !cfg.Enabled {
            continue
        }

        // Expande variáveis de ambiente no api_key
        apiKey := os.ExpandEnv(cfg.APIKey)

        source, err := vulnsource.NewHTTPSource(cfg.Name, cfg.URL, apiKey)
        if err != nil {
            return nil, err
        }

        sources = append(sources, source)
    }

    return sources, nil
}
```

**Fase 3: Fonte HTTP Genérica** (5-8 horas)

```go
type HTTPSource struct {
    name   string
    url    string
    apiKey string
    client *http.Client
}

func (s *HTTPSource) ScanPackages(ctx context.Context, packages []Package) (map[string][]Vulnerability, error) {
    // Constrói requisição para API personalizada
    req, err := http.NewRequestWithContext(ctx, "POST", s.url+"/scan", body)
    req.Header.Set("Authorization", "Bearer "+s.apiKey)

    resp, err := s.client.Do(req)
    // ... parse da resposta ...

    // Normaliza o formato da resposta para coincidir com a struct Vulnerability da angela
    return normalizeVulns(resp), nil
}
```

**Fase 4: Mesclar Resultados** (3-4 horas)

```go
func scanAllSources(ctx context.Context, sources []Source, packages []Package) (map[string][]Vulnerability, error) {
    allVulns := make(map[string][]Vulnerability)
    var mu sync.Mutex

    g, ctx := errgroup.WithContext(ctx)

    for _, src := range sources {
        g.Go(func() error {
            vulns, err := src.ScanPackages(ctx, packages)
            if err != nil {
                log.Printf("Source %s failed: %v", src.Name(), err)
                return nil  // Não falha o scan inteiro
            }

            mu.Lock()
            defer mu.Unlock()

            // Mescla resultados, remove duplicatas por ID
            for pkg, vlist := range vulns {
                allVulns[pkg] = append(allVulns[pkg], vlist...)
            }

            return nil
        })
    }

    _ = g.Wait()

    // Remove duplicatas entre fontes
    for pkg := range allVulns {
        allVulns[pkg] = deduplicateVulns(allVulns[pkg])
    }

    return allVulns, nil
}
```

**Estratégia de teste:**

- Teste unitário: Implementação Mock de Source que retorna vulnerabilidades falsas
- Teste de integração: Subir servidor HTTP de teste que imita um banco de dados de vulnerabilidades personalizado
- Teste de ponta a ponta: Consultar OSV.dev real + servidor de teste, verificar se os resultados foram mesclados

**Critérios de sucesso:**

- [ ] Pode consultar múltiplas fontes de vulnerabilidade concorrentemente
- [ ] Resultados são deduplicados pelo ID da CVE
- [ ] Chaves de API carregadas de variáveis de ambiente
- [ ] Falha de uma fonte não bloqueia as outras
- [ ] Configuração valida (rejeita URLs malformadas, chaves de API ausentes)

## Desafios de Desempenho

### Desafio: Lidar com mais de 10.000 Pacotes

**O objetivo:**
Tornar a angela rápida o suficiente para escanear listas de dependências de monorepos com milhares de pacotes.

**Gargalo atual:**
O endpoint de lote do OSV.dev aceita no máximo 1000 pacotes por requisição. Para 10.000 pacotes, você precisa de 10 requisições. Cada uma leva de 2 a 5 segundos. Sequencial = 20-50 segundos no total.

**Abordagens de otimização:**

#### Abordagem 1: Requisições de Lote Concorrentes

```go
func (c *Client) ScanPackagesBatched(ctx context.Context, packages []PackageQuery) (map[string][]Vulnerability, error) {
    const batchSize = 1000
    batches := chunkPackages(packages, batchSize)

    var mu sync.Mutex
    allVulns := make(map[string][]Vulnerability)

    g, ctx := errgroup.WithContext(ctx)
    g.SetLimit(5)  // Máximo de 5 requisições de lote concorrentes

    for _, batch := range batches {
        g.Go(func() error {
            vulns, err := c.ScanPackages(ctx, batch)
            if err != nil {
                return err
            }

            mu.Lock()
            for pkg, vlist := range vulns {
                allVulns[pkg] = append(allVulns[pkg], vlist...)
            }
            mu.Unlock()

            return nil
        })
    }

    if err := g.Wait(); err != nil {
        return nil, err
    }

    return allVulns, nil
}
```

- Ganho: 5x mais rápido (5 lotes em paralelo)
- Tradeoff: Maior uso de memória, uso mais agressivo da API

### Abordagem 2: Cache Local do Banco de Dados de Vulnerabilidades

Baixar todo o banco de dados de vulnerabilidades do OSV.dev (é público) e consultar localmente:

```bash
wget https://osv-vulnerabilities.storage.googleapis.com/PyPI/all.zip
unzip all.zip -d ~/.angela/vulndb/
```

Então pesquise arquivos JSON localmente em vez de acessar a API:

```go
func (c *LocalDB) FindVulns(pkg, version string) ([]Vulnerability, error) {
    files, _ := filepath.Glob(c.dir + "/*.json")

    var vulns []Vulnerability
    for _, f := range files {
        vuln := parseVulnFile(f)
        if affects(vuln, pkg, version) {
            vulns = append(vulns, vuln)
        }
    }
    return vulns, nil
}
```

- Ganho: 100x mais rápido (sem rede), escala ilimitada
- Tradeoff: 500MB de espaço em disco, precisa de atualizações periódicas

**Faça o benchmark:**

```bash
# Antes da otimização
time angela scan --file huge-project.toml
# real    0m42.318s

# Após abordagem 1
time angela scan --file huge-project.toml
# real    0m8.942s

# Após abordagem 2
time angela scan --file huge-project.toml
# real    0m0.431s
```

Métricas alvo:

- 1.000 pacotes: <5 segundos
- 10.000 pacotes: <30 segundos (abordagem 1) ou <5 segundos (abordagem 2)

## Desafios de Segurança

### Desafio: Verificar Assinaturas de Pacotes

**O que implementar:**
Antes de confiar nos dados de versão do PyPI, verifique se eles estão assinados pela chave do PyPI.

**Modelo de ameaça:**
Isso protege contra:

- Ataques man-in-the-middle em requisições ao PyPI
- CDN comprometida ou envenenamento de DNS
- Proxy malicioso interceptando e modificando respostas

**Implementação:**

1. **Baixar a chave pública do PyPI** de https://pypi.org/simple/.well-known/
2. **Verificar a assinatura da resposta** usando PGP ou similar
3. **Rejeitar dados não assinados ou assinados incorretamente**

Este é um desafio profundo que exige compreensão de:

- Assinaturas PGP
- Cadeias de confiança e verificação de chaves
- Manipulação de dados binários em Go

O PyPI não assina atualmente as respostas da Simple API (até 2024), então você pode precisar implementar isso para um futuro hipotético onde eles o façam, ou projetar seu próprio esquema de assinatura para mirrors privados do PyPI.

### Desafio: Passar nos Padrões do OWASP Dependency-Check

**O objetivo:**
Tornar a angela compatível com os requisitos do OWASP Dependency-Check para ferramentas SCA.

**Lacunas atuais:**

- Sem scan de dependências transitivas
- Sem categorização CWE
- Sem relatório de pontuação CVSS
- Sem formato de arquivo de supressão

**Remediação:**

1. **Adicionar mapeamento CWE** - Dados do OSV incluem IDs CWE em alguns avisos. Extraia e exiba:

   ```text
   CVE-2023-32681 (CWE-113: Improper Neutralization of CRLF Sequences)
   ```

2. **Relatar pontuações CVSS** - Extraia do campo de severidade do OSV:

   ```text
   CVSS v3.1: 9.8 (CRITICAL)
   Vector: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
   ```

3. **Arquivo de supressão** - Suportar o formato XML do dependency-check:

   ```xml
   <suppressions>
     <suppress>
       <cve>CVE-2023-1234</cve>
       <reason>False positive - doesn't affect our use case</reason>
     </suppress>
   </suppressions>
   ```

4. **Gerar relatório HTML** - Coincidir com o formato de relatório do dependency-check para compatibilidade com ferramentas existentes.

## Misture e Combine

Combine recursos para projetos maiores:

### Ideia de Projeto 1: Analisador de Cadeia de Suprimentos Completo

- Combine o Desafio 5 (dependências transitivas) + Desafio 6 (geração de SBOM) + Desafio 8 (banco de dados de vulnerabilidades privado)
- Resultado: Scanner de dependências de nível empresarial que mapeia toda a cadeia de suprimentos, gera SBOMs e consulta bancos de dados de vulnerabilidades internos.

### Ideia de Projeto 2: Suíte de Integração CI/CD

- Combine o Desafio 3 (saída JSON) + Desafio 7 (modo daemon) + Desafio 4 (requirements.in)
- Resultado: Sistema de monitoramento contínuo que se integra com GitHub Actions, fornece dados estruturados para anotações e suporta todos os formatos de dependência Python.

## Desafios de Integração no Mundo Real

### Integrar com o GitHub Security Advisories

**O objetivo:**
Fazer a angela buscar dados de vulnerabilidade da API GraphQL do GitHub além do OSV.dev.

**O que você precisará:**

- Token de acesso pessoal do GitHub com escopo `security_events`
- Biblioteca de cliente GraphQL (ex: `github.com/shurcooL/graphql`)
- Compreensão do esquema de vulnerabilidades do GitHub

**Plano de implementação:**

1. **Configurar cliente GraphQL**:

   ```go
   import "github.com/shurcooL/graphql"

   client := graphql.NewClient(
       "https://api.github.com/graphql",
       oauth2Client,
   )
   ```

2. **Consultar por avisos**:

   ```go
   var query struct {
       SecurityAdvisories struct {
           Nodes []struct {
               GHSAID      string
               Severity    string
               Description string
               // ...
           }
       } `graphql:"securityAdvisories(ecosystem: PIP, first: 100)"`
   }
   ```

3. **Converter para o formato Vulnerability da angela**
4. **Mesclar com os resultados do OSV**

**Cuidado com:**

- Limites de taxa (5000 consultas/hora para requisições autenticadas)
- Paginação (GitHub retorna no máximo 100 resultados por consulta)
- Diferentes escalas de severidade (GitHub usa LOW/MODERATE/HIGH/CRITICAL, igual ao OSV)

### Implantar como Função Lambda

**O objetivo:**
Executar a angela como um AWS Lambda que escaneia repositórios em eventos de webhook.

**O que você aprenderá:**

- Arquitetura serverless
- Otimização de cold start
- Manipulação de eventos Lambda

**Etapas:**

1. **Conteinerizar a angela**:

   ```dockerfile
   FROM golang:1.24 AS build
   WORKDIR /app
   COPY . .
   RUN go build -o angela ./cmd/angela

   FROM public.ecr.aws/lambda/provided:al2
   COPY --from=build /app/angela /var/task/angela
   ENTRYPOINT ["/var/task/angela"]
   ```

2. **Lidar com eventos Lambda**:

   ```go
   func handler(ctx context.Context, event S3Event) error {
       // Baixa pyproject.toml do S3
       // Executa angela scan
       // Faz o upload dos resultados de volta para o S3
   }
   ```

3. **Implantar**:

   ```bash
   sam build
   sam deploy --guided
   ```

**Checklist de produção:**

- [ ] Camada de cache para respostas do PyPI (use ElastiCache ou S3)
- [ ] Tratamento de timeout (o máximo do Lambda é 15 minutos)
- [ ] Ajuste de memória (perfil com 512MB, 1024MB, 2048MB)
- [ ] Alertas de erro (alarmes CloudWatch)

## Ideias de Contribuição

Terminou um desafio? Compartilhe-o de volta:

1. **Faça um fork do repositório** em github.com/CarterPerez-dev/angela
2. **Implemente sua extensão** em uma branch de recurso (feature branch)
3. **Documente-a** - atualize a pasta learn/ com suas mudanças
4. **Envie um PR** com:
   - Implementação
   - Testes (mínimo de 80% de cobertura)
   - Documentação
   - Exemplo de uso

Boas extensões podem ser mescladas ao projeto principal.

## Desafie-se Ainda Mais

### Construa Algo Novo

Use os conceitos que você aprendeu aqui para construir:

**angela-watch** - Monitor de segurança de dependências em tempo real que abre issues no GitHub quando novas CVEs aparecem. Combina observação de arquivos, integração com API do GitHub e escaneamento de vulnerabilidades.

**angela-diff** - Compara duas branches/commits para ver quais dependências mudaram e qual o impacto de segurança disso. Útil para revisões de pull request.

**angela-policy** - Engine de política como código. Defina regras como "nenhuma dependência com vulnerabilidades CRITICAL" ou "todas as dependências devem ser atualizadas em até 30 dias após o lançamento". angela-policy impõe estas regras no CI/CD.

### Estude Implementações Reais

Compare sua implementação com ferramentas de produção:

**Dependabot** (https://github.com/dependabot/dependabot-core)

- Como eles lidam com dependências transitivas
- A estratégia de resolução de versão deles
- Baseado em Ruby, suporta mais de 20 ecossistemas

**pip-audit** (https://github.com/pypa/pip-audit)

- Usa OSV.dev como a angela
- Implementação em Python
- Integra-se com o resolvedor do pip

**Snyk** (código fechado, mas leia a documentação deles)

- Como eles priorizam vulnerabilidades
- Suas sugestões de correção e workflow de auto-PR
- Banco de dados proprietário vs agregação OSV

Leia o código deles, entenda seus trade-offs, roube suas boas ideias.

### Escreva Sobre Isso

Documente sua extensão:

**Post em blog**: "Eu Adicionei Escaneamento de Dependências Transitivas a um Scanner de Vulnerabilidades"

- O que você construiu
- Desafios técnicos que encontrou
- Benchmarks de desempenho antes/depois
- Trechos de código com explicações

**Tutorial**: "Construindo um Scanner de Dependências Python em Go"

- Guia passo a passo replicando a angela
- Explique cada componente
- Inclua exercícios

**Comparação**: "angela vs pip-audit vs Snyk"

- Matriz de recursos
- Comparação de desempenho
- Quando usar cada ferramenta

Ensinar os outros é a melhor maneira de verificar se você entendeu.

## Obtendo Ajuda

Travou em um desafio?

1. **Depure sistematicamente**
   - O que você esperava que acontecesse?
   - O que realmente aconteceu?
   - Qual é a menor mudança de código que reproduz o problema?

2. **Leia o código existente**
   - Como a angela lida com problemas semelhantes?
   - O cliente OSV faz requisições concorrentes - você pode adaptar esse padrão?

3. **Pesquise por problemas semelhantes**
   - StackOverflow: `[go] http client retry logic`
   - GitHub Issues: como outros projetos resolveram isso?

4. **Peça ajuda**
   - Abra uma Discussão no GitHub com:
     - O que você está tentando construir
     - O que você tentou até agora
     - Mensagens de erro específicas ou comportamento inesperado
     - Exemplo de código mínimo

Não apenas cole mensagens de erro. Explique seu entendimento do que _deveria_ acontecer e por que não está funcionando.

## Rastreador de Conclusão de Desafios

Acompanhe seu progresso. Para esta entrega, são obrigatórios apenas os itens de todos os grupos e os atribuídos ao seu grupo, nos recortes definidos acima:

- [ ] Desafio Fácil 1: Severidade Codificada por Cores — todos
- [ ] Desafio Fácil 2: Estatísticas de Cache — todos
- [ ] Desafio Fácil 3: Modo de Saída JSON — todos
- [ ] Desafio Intermediário 4: Suporte a requirements.in — Grupo 2
- [ ] Desafio Intermediário 5: Dependências Transitivas — Grupo 1
- [ ] Desafio Intermediário 6: Geração de SBOM — Grupo 1
- [ ] Desafio Avançado 7: Monitoramento Contínuo — Grupo 2, no recorte local
- [ ] Desafio Avançado 8: Banco de Dados de Vulnerabilidades Privado — opcional
- [ ] Desempenho: mais de 10.000 Pacotes — opcional
- [ ] Segurança: Verificação de Assinatura de Pacote — opcional

Completou todos eles? Você dominou o escaneamento de dependências. Hora de construir algo novo ou contribuir de volta para projetos de código aberto que precisam de melhores ferramentas de segurança.
