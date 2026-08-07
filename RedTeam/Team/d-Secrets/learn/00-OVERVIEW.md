# Portia - Scanner de Segredos para Bases de Código

## O Que É Isso

Portia é uma ferramenta CLI em Go que escaneia diretórios de código-fonte e o histórico do git em busca de segredos vazados: chaves de API, senhas, tokens, chaves privadas, strings de conexão. Ela utiliza 150 regras de detecção, análise de entropia de Shannon, um filtro de falsos positivos de 5 camadas e verificação opcional de vazamentos no Have I Been Pwned. Os arquivos são divididos em chunks de 50 linhas e processados através de um worker pool concorrente limitado, com resultados reportados no terminal ou nos formatos JSON ou SARIF.

O nome vem da personagem Portia de _O Mercador de Veneza_, de Shakespeare, que é quem expõe o que está escondido no contrato. Esta ferramenta faz o mesmo pela sua base de código.

## Por Que Isso Importa

Segredos hardcoded em código-fonte são um dos erros de segurança mais comuns e prejudiciais no desenvolvimento de software. Isso não é teórico. Aqui estão três incidentes que mostram exatamente por que isso importa:

**Uber, 2016 - Chaves AWS Hardcoded no GitHub**
Dois engenheiros da Uber enviaram chaves de acesso AWS para um repositório privado no GitHub. Atacantes que ganharam acesso a esse repositório usaram as chaves para acessar um bucket S3 contendo informações pessoais de 57 milhões de passageiros e motoristas. A Uber pagou US$ 148 milhões em acordos. As chaves ficaram no repositório por meses antes da violação. Uma ferramenta como a Portia, escaneando em cada commit, teria sinalizado padrões `AKIA...` imediatamente usando a regra `aws-access-key-id` definida em `internal/rules/builtin.go:22-31`. A regex `\b((?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16})\b` captura exatamente este formato.

**CircleCI, Janeiro de 2023 - Segredos na Configuração de CI**
Um atacante comprometeu o laptop de um engenheiro da CircleCI e usou o cookie de sessão para acessar sistemas internos. Eles então extraíram segredos de clientes que estavam armazenados como variáveis de ambiente em pipelines de CI/CD. O comunicado (CCI-2023-001) instou todos os clientes a rotacionar cada segredo armazenado na CircleCI. O problema raiz: os segredos foram configurados como valores em texto simples nas configurações de CI, em vez de serem buscados em vaults em tempo de execução. Se esses arquivos de configuração tivessem sido escaneados antes do deployment, o problema teria sido detectado. As regras genéricas da Portia para atribuições de `password`, `secret`, `token` e `api_key` visam exatamente este padrão.

**Codecov, Abril de 2021 - Ataque à Cadeia de Suprimentos via Tokens Exfiltrados**
Atacantes modificaram o script de upload em bash da Codecov para exfiltrar variáveis de ambiente de ambientes de CI. Cada empresa que utilizava o uploader em bash da Codecov vazou quaisquer tokens e chaves presentes em seu ambiente de CI, incluindo credenciais do GitHub, AWS e serviços internos. O script modificado rodou por dois meses antes da detecção. Entre as empresas afetadas: Twitch, HashiCorp, Confluent. Portia detecta tokens para GitHub (`ghp_`, `gho_`, `ghs_`), HashiCorp Vault (`hvs.`, `hvb.`, `hvr.`) e muitos outros provedores, todos definidos em `internal/rules/builtin.go`.

O ponto em comum: segredos parados em código ou configurações onde ferramentas automatizadas poderiam tê-los capturado. É isso que este projeto constrói.

## O Que Você Aprenderá

Construir este projeto ensina tanto conceitos de segurança quanto padrões reais de engenharia em Go.

**Conceitos de Segurança:**

- **Secret sprawl e por que ele acontece** - Por que desenvolvedores continuam inserindo credenciais hardcoded apesar de saberem dos riscos, e as soluções sistêmicas (variáveis de ambiente, integrações com vault, hooks de pre-commit)
- **Entropia de Shannon para detecção de anomalias** - Usando a teoria da informação para distinguir chaves de API aleatórias de texto normal em inglês. A matemática está em `internal/rules/entropy.go`.
- **k-Anonymity** - O protocolo de Troy Hunt para verificar se um segredo aparece em bancos de dados de vazamentos sem revelar o segredo em si. Implementação em `internal/hibp/client.go`.
- **Redução de falsos positivos** - Por que o escaneamento ingênuo por regex produz milhares de resultados inúteis, e a abordagem de filtragem em 5 camadas que torna a saída realmente útil. Veja `internal/engine/filter.go`.
- **SARIF para integração com CI** - O formato padrão da indústria que o GitHub, Azure DevOps e outras plataformas de CI consomem para mostrar descobertas de segurança inline em pull requests.

**Habilidades Técnicas (específicas de Go):**

- **Pipelines concorrentes com errgroup** - Worker pools limitados usando `golang.org/x/sync/errgroup` com comunicação baseada em canais. O pipeline completo está em `internal/engine/pipeline.go`.
- **Framework CLI Cobra** - Construção de uma CLI de múltiplos comandos com flags persistentes, suporte a arquivo de configuração e subcomandos. Comando raiz em `internal/cli/root.go`.
- **Biblioteca go-git** - Travessia programática do histórico do git, caminhada por commits, leitura de blobs e escaneamento de arquivos em staging sem depender do binário `git`. Veja `internal/source/git.go`.
- **Padrão Circuit breaker** - Usando `gobreaker` para prevenir falhas em cascata quando APIs externas (HIBP) estão fora do ar. Configurado em `internal/hibp/client.go`.
- **Caching LRU** - Cache em memória limitado com `hashicorp/golang-lru` para evitar chamadas de API redundantes. Veja `internal/hibp/client.go`.
- **Configuração TOML** - Resolução de configuração em camadas com flags de CLI > arquivo de configuração > padrões. Suporta tanto `.portia.toml` quanto `pyproject.toml` (tabela `[tool.portia]`). Veja `internal/config/config.go` e `internal/cli/root.go`.

**Ferramentas e Técnicas:**

- **Criação de Regex para segurança** - Escrever padrões que correspondam a formatos reais de credenciais (prefixos de chaves AWS, formatos de token do GitHub, padrões de chaves Stripe) enquanto evita falsos positivos
- **just task runner** - Usando `Justfile` como uma alternativa aos Makefiles para workflows de build, test e lint
- **golangci-lint** - Configuração de análise estática em `.golangci.yml` para garantir a qualidade do código

## Pré-requisitos

**Conhecimento necessário:**

- **Básico de Go** - Você precisa entender goroutines, canais, interfaces e structs. O pipeline utiliza todos esses recursos intensamente. Se `go func()` ou `chan types.Chunk` parecer estranho, complete o Go Tour primeiro.
- **Expressões Regulares** - O engine de detecção é construído sobre regex. Você deve conhecer grupos de captura, quantificadores, classes de caracteres e grupos de não-captura. As regras em `internal/rules/builtin.go` usam todos esses recursos.
- **Fundamentos de Git** - Você deve entender commits, branches, staging e blobs. O scanner de git percorre essas estruturas programaticamente.

**Ferramentas necessárias:**

- **Go 1.22+** - Utiliza `range` sobre inteiros (ex: `for range p.workers` em `internal/engine/pipeline.go:53`), o que requer Go 1.22
- **just** - Task runner. Instale com `cargo install just` ou através do seu gerenciador de pacotes
- **git** - Para os recursos de escaneamento de histórico do git

**Útil, mas não obrigatório:**

- **Teoria da Informação** - Entender entropia ajuda, mas o documento de conceitos explica isso do zero
- **Especificação SARIF** - O padrão OASIS para resultados de análise estática. Você pode ler a saída sem conhecer a especificação.

## Instalação

Três maneiras de instalar o Portia:

**Opção 1: Script de instalação** (não requer Go)

```bash
curl -fsSL https://raw.githubusercontent.com/CarterPerez-dev/portia/main/install.sh | bash
```

Isso baixa um binário pré-compilado para sua plataforma (Linux/macOS, amd64/arm64). Se nenhum binário estiver disponível, ele recorre à compilação a partir do código-fonte com Go.

**Opção 2: Go install**

```bash
go install github.com/CarterPerez-dev/portia/cmd/portia@latest
```

Requer Go 1.24+. O binário é colocado em seu `$GOPATH/bin` (ou `$GOBIN`).

**Opção 3: Construir a partir do código-fonte**

```bash
cd RedTeam/Team/d-Secrets/
go build -o portia ./cmd/portia
```

Este é o caminho que você usará ao trabalhar neste projeto e fazer alterações no código.

## Início Rápido

Coloque o projeto para rodar:

```bash
cd RedTeam/Team/d-Secrets/

./portia scan ./testdata/fixtures

./portia scan --format json ./testdata/fixtures

./portia scan --hibp ./testdata/fixtures

./portia git --depth 10 .

./portia git --staged .
```

Saída esperada nos fixtures de teste: saída colorida no terminal mostrando segredos detectados com níveis de severidade, IDs de regras, caminhos de arquivos, números de linhas, pontuações de entropia e valores de segredos mascarados.

Para inicializar um arquivo de configuração:

```bash
./portia init
```

Isso cria o arquivo `.portia.toml` com as configurações padrão. Edite-o para desativar regras, definir exclusões ou ativar a verificação HIBP por padrão.

Para projetos Python, você pode usar o `pyproject.toml` em vez disso:

```bash
./portia pyproject
```

Isso cria um `pyproject.toml` com uma seção `[tool.portia]`. Portia lê automaticamente do `pyproject.toml` quando nenhum `.portia.toml` é encontrado.

## Estrutura do Projeto

```
secrets-scanner/
├── cmd/portia/main.go           # Ponto de entrada, chama cli.Execute()
├── internal/
│   ├── cli/                     # Comandos Cobra
│   │   ├── root.go              # Comando raiz, definições de flags, init de config
│   │   ├── scan.go              # `portia scan` - escaneamento de diretório
│   │   ├── git.go               # `portia git` - escaneamento de histórico git
│   │   ├── init.go              # `portia init` + `portia pyproject` - cria arquivos de config
│   │   └── config.go            # `portia config` - mostra a config atual
│   ├── config/
│   │   └── config.go            # Carregador de config TOML, padrões, caminhos de busca
│   ├── engine/
│   │   ├── detector.go          # Aplica regras aos chunks, validação de entropia
│   │   ├── filter.go            # Stopwords, placeholders, templates, allowlists
│   │   └── pipeline.go          # Worker pool errgroup, deduplicação
│   ├── hibp/
│   │   └── client.go            # Cliente de API k-anonymity, cache LRU, circuit breaker
│   ├── reporter/
│   │   ├── reporter.go          # Interface de reporter e factory
│   │   ├── terminal.go          # Saída colorida no terminal com mascaramento
│   │   ├── json.go              # Formato de saída JSON
│   │   └── sarif.go             # Saída SARIF v2.1.0 para integração com CI
│   ├── rules/
│   │   ├── builtin.go           # 150 regras de detecção cobrindo AWS, GitHub, etc.
│   │   ├── entropy.go           # Calculadora de entropia de Shannon e detecção de charset
│   │   └── registry.go          # Armazenamento de regras, keyword matching, allowlists globais
│   ├── source/
│   │   ├── source.go            # Definição da interface Source
│   │   ├── directory.go         # Walker de sistema de arquivos com chunking de 50 linhas
│   │   └── git.go               # Scanner de histórico git usando go-git
│   └── ui/                      # Cores, spinner, banner, símbolos
├── pkg/types/types.go           # Tipos principais: Finding, Chunk, Rule, Severity
├── testdata/fixtures/            # Segredos de teste para testes de integração
├── Justfile                      # Task runner
└── .golangci.yml                 # Configuração do linter
```

## Comandos de Desenvolvimento

Este projeto utiliza o [`just`](https://github.com/casey/just) como executor de comandos. Execute `just` sem argumentos para ver todos os comandos disponíveis.

| Comando           | Descrição                                               |
| ----------------- | ------------------------------------------------------- |
| `just lint`       | Executa o golangci-lint                                 |
| `just lint-fix`   | Executa o golangci-lint com auto-fix                    |
| `just format`     | Formata o código via golangci-lint                      |
| `just vet`        | Executa o `go vet`                                      |
| `just tidy`       | Executa o `go mod tidy`                                 |
| `just test`       | Executa todos os testes com detector de race            |
| `just test-v`     | Executa os testes com saída detalhada                   |
| `just cover`      | Executa os testes com resumo de cobertura               |
| `just cover-html` | Gera relatório de cobertura em HTML                     |
| `just ci`         | Executa lint + test (verificação completa de CI)        |
| `just check`      | Executa lint + vet                                      |
| `just run <args>` | Executa o portia com argumentos (ex: `just run scan .`) |
| `just dev-scan`   | Escaneia o diretório testdata                           |
| `just dev-git`    | Escaneia o histórico git do repositório atual           |
| `just dev-json`   | Escaneia o testdata com saída JSON                      |
| `just dev-sarif`  | Escaneia o testdata com saída SARIF                     |
| `just dev-rules`  | Lista todas as regras de detecção                       |
| `just build`      | Build de produção para `bin/portia`                     |
| `just install`    | `go install` para `$GOPATH/bin`                         |
| `just info`       | Mostra informações do projeto/Go/SO                     |
| `just clean`      | Remove artefatos de build                               |

## Próximos Passos

Siga os documentos na ordem:

1. **01-CONCEPTS.md** - Conceitos de segurança: secret sprawl, entropia de Shannon, detecção baseada em regex, filtragem de falsos positivos, k-anonymity, SARIF
2. **02-ARCHITECTURE.md** - Design do sistema: arquitetura de pipeline, modelo de concorrência, fluxo de dados, interações de componentes
3. **03-IMPLEMENTATION.md** - Passo a passo do código: cada arquivo chave explicado com referências de linha
4. **04-CHALLENGES.md** - Extensões: hooks de pre-commit, regras personalizadas, escaneamento incremental, GitHub Actions

## Problemas Comuns

**"Nenhum segredo detectado" em código real:**
Seu código pode estar limpo. Tente escanear `testdata/fixtures/` primeiro para confirmar que a ferramenta funciona. Se estiver escaneando código real, verifique se você não está excluindo caminhos demais. Use `--verbose` para ver quais arquivos estão sendo escaneados.

**O escaneamento de Git está lento:**
Use `--depth` para limitar quantos commits serão escaneados. `--depth 100` escaneia os últimos 100 commits em vez de todo o histórico. Para uma verificação rápida, use `--staged` para escanear apenas as alterações em staging.

**Muitos falsos positivos:**
Edite o `.portia.toml` para adicionar caminhos ou valores à allowlist. Você também pode desativar regras específicas com `rules.disable = ["generic-password"]`. O sistema de filtros (stopwords, placeholders, templates) lida com a maioria dos casos, mas padrões específicos do projeto podem precisar de allowlisting customizado.

**A verificação HIBP falha:**
A API do HIBP possui limites de taxa. O circuit breaker em `internal/hibp/client.go` abrirá após 5 falhas consecutivas, prevenindo novas requisições por 60 segundos. Isso é por design. Se a API estiver consistentemente indisponível, o scan ainda será concluído sem os dados de violação.

**Erros de build com a versão do Go:**
Este projeto utiliza a sintaxe `for range p.workers`, que requer Go 1.22+. Verifique sua versão com `go version`.
