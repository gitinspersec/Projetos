# Desafios de Extensão

Estes desafios estendem o Portia além de suas capacidades atuais. Cada um ensina uma habilidade diferente. Eles estão ordenados aproximadamente por dificuldade e baseiam-se na base de código existente sem exigir grandes refatorações.

## Desafio 1: Integração com Hook de Pre-commit

**Dificuldade:** Fácil | **Tempo:** 1-2 horas | **Ensina:** Git hooks, shell scripting, workflow de desenvolvedor

Escreva um script que instale o Portia como um Git pre-commit hook. Quando um desenvolvedor executar `git commit`, o hook deve:

1.  Compilar o Portia (ou usar um binário pré-compilado)
2.  Executar `portia git --staged` para escanear apenas os arquivos em staging
3.  Se segredos forem encontrados, imprimir as descobertas e abortar o commit
4.  Se nenhum segredo for encontrado, permitir que o commit prossiga

**Ponto de partida:** Crie um `scripts/install-hook.sh` que escreva um pre-commit hook em `.git/hooks/pre-commit`. O script do hook deve chamar `portia git --staged --format terminal` e verificar o código de saída.

**Dicas:**

- Git hooks devem ser executáveis (`chmod +x`)
- O hook deve sair com 0 para permitir o commit, e diferente de zero para abortar
- Você precisará adicionar suporte a códigos de saída na CLI do Portia (atualmente ele sempre sai com 0). Adicione a flag `--exit-code` que retorna o código de saída 1 quando segredos são encontrados. Modifique `executeScan` em `internal/cli/scan.go` para chamar `os.Exit(1)` quando existirem descobertas e a flag estiver definida.
- Considere adicionar uma flag `--quiet` que suprima o banner e o spinner para uso em hooks

**Bônus:** Faça-o funcionar com o framework `pre-commit` (https://pre-commit.com) criando um arquivo `.pre-commit-hooks.yaml` na raiz do repositório.

## Desafio 2: Carregador de Regras Customizadas em YAML

**Dificuldade:** Média | **Tempo:** 2-3 horas | **Ensina:** Parsing de YAML/TOML, validação de regras, extensibilidade de configuração

Adicione suporte para regras de detecção definidas pelo usuário em um arquivo YAML ou TOML. Os usuários devem ser capazes de criar um arquivo `.portia/rules.yml`:

```yaml
rules:
  - id: "internal-api-key"
    description: "Internal API key format"
    severity: HIGH
    keywords: ["ikey_"]
    pattern: "ikey_[a-zA-Z0-9]{32}"
    secret_group: 0
    entropy: 3.5
```

**Ponto de partida:** Crie `internal/rules/custom.go` com uma função `LoadCustomRules(path string) ([]*types.Rule, error)`. Chame esta função em `scan.go` após registrar as regras integradas (builtins).

**Dicas:**

- Use `gopkg.in/yaml.v3` para o parsing de YAML
- Valide o padrão regex chamando `regexp.Compile` e retornando um erro claro se falhar
- Valide a severidade contra os valores permitidos
- Verifique se há IDs de regras duplicados contra o registro existente
- Considere suportar `allowlist` no formato YAML com padrões de caminho e valor

**Atenção:** Palavras-chave (keywords) são críticas para o desempenho. Se uma regra customizada não tiver keywords, ela rodará sua regex contra cada chunk. Exija pelo menos uma keyword ou avise o usuário que keywords vazias tornarão o processo lento.

## Desafio 3: Escaneamento Incremental com Cache

**Dificuldade:** Média | **Tempo:** 2-3 horas | **Ensina:** Hashing, cache baseado em arquivo, otimização de desempenho

Adicione um arquivo `.portia-cache/scan.json` que armazene hashes SHA-256 de arquivos escaneados anteriormente. Em escaneamentos subsequentes, pule os arquivos cujo hash não tenha mudado.

**Ponto de partida:** Crie `internal/cache/scan.go` com:

- `type ScanCache struct` contendo um mapa do caminho relativo do arquivo para o hash do arquivo
- `Load(path) (*ScanCache, error)` e `Save(path) error` para persistência
- `IsChanged(relPath string, content []byte) bool` que computa o SHA-256 e compara

**Dicas:**

- Armazene o cache em `.portia-cache/scan.json` no diretório escaneado
- Use `crypto/sha256` para o hashing
- O cache deve incluir a contagem de regras como metadado. Se as regras mudarem (nova regra adicionada), invalide todo o cache.
- Adicione uma flag `--no-cache` para forçar um escaneamento completo
- Adicione a invalidação do cache em `internal/cli/scan.go` antes de criar a source
- Considere adicionar a versão do Portia aos metadados do cache para que atualizações de versão invalidem o cache

**Impacto no desempenho:** Em uma base de código de 10.000 arquivos onde apenas 50 mudaram, isso reduz o tempo de escaneamento em ~99,5%.

## Desafio 4: Integração com Git Blame

**Dificuldade:** Média | **Tempo:** 3-4 horas | **Ensina:** API de git blame, atribuição, saída enriquecida

Após detectar um segredo, execute o `git blame` no arquivo para determinar quem fez o commit e quando. Adicione esta informação à descoberta.

**Ponto de partida:** A struct `types.Finding` já possui os campos `Author` e `CommitDate`, mas eles são preenchidos apenas durante escaneamentos de histórico git. Para escaneamentos de diretório, esses campos ficam vazios.

**Dicas:**

- Use a função `git.Blame` do go-git: `blame, err := git.BlameCommit(commit, path)`
- O resultado do blame fornece o SHA do commit, autor e data para cada linha
- Corresponda o `LineNumber` da descoberta com o resultado do blame para obter a atribuição
- Isso deve ser opcional (flag `--blame`), pois adiciona overhead
- Para arquivos fora de um repositório git, pule o blame silenciosamente
- Adicione os dados de blame aos três formatos de reporter (terminal, JSON, SARIF)

**Atenção:** O `git.Blame` exige percorrer todo o histórico de commits do arquivo. Em repositórios grandes, isso pode ser lento. Considere fazer o cache dos resultados do blame por arquivo.

## Desafio 5: Escaneamento de Múltiplos Repositórios

**Dificuldade:** Média | **Tempo:** 3-4 horas | **Ensina:** Gerenciamento de configuração, E/S concorrente, agregação

Adicione um comando `portia scan-all` que leia um arquivo de configuração listando múltiplos repositórios e escaneie todos eles, produzindo um relatório unificado.

```toml
[[repos]]
path = "/home/dev/api-server"
excludes = ["vendor/"]

[[repos]]
path = "/home/dev/frontend"
excludes = ["node_modules/", "dist/"]

[[repos]]
url = "https://github.com/org/service.git"
branch = "main"
depth = 50
```

**Ponto de partida:** Crie `internal/cli/scanall.go` com um novo comando cobra.

**Dicas:**

- Analise o arquivo de configuração com `pelletier/go-toml`
- Para entradas de `url`, clone para um diretório temporário usando `git.PlainClone`
- Execute o escaneamento de cada repositório concorrentemente usando um errgroup
- Prefixar o `FilePath` de cada descoberta com o nome/caminho do repositório para desambiguação
- Considere uma flag `--parallel N` para controlar a concorrência
- Limpe os diretórios temporários clonados ao sair (use `defer`)

## Desafio 6: GitHub Action

**Dificuldade:** Difícil | **Tempo:** 4-6 horas | **Ensina:** GitHub Actions, Docker, integração SARIF, CI/CD

Construa uma GitHub Action que execute o Portia em pull requests e faça o upload dos resultados para o GitHub Code Scanning.

**Ponto de partida:** Crie `.github/action/action.yml` e um Dockerfile.

**Estrutura:**

```
.github/action/
├── action.yml        # Metadados da Action
├── Dockerfile        # Build do Portia em um container
└── entrypoint.sh     # Executa o Portia e faz o upload do SARIF
```

**Dicas:**

- O `action.yml` deve aceitar entradas: `path` (padrão `.`), `format` (padrão `sarif`), `exclude` (opcional), `hibp` (padrão false)
- O Dockerfile deve ser um build multi-estágio: compile o Portia em uma imagem Go, copie o binário para uma imagem de runtime leve
- O `entrypoint.sh` executa `portia scan --format sarif $INPUT_PATH > results.sarif`, e então faz o upload usando `gh api repos/{owner}/{repo}/code-scanning/sarifs`
- Use `github.sha` para o SHA do commit no upload do SARIF
- A Action deve falhar (exit 1) se descobertas CRITICAL ou HIGH forem detectadas

**Teste:** Crie um `.github/workflows/test-action.yml` que teste a action contra o `testdata/fixtures/`.

## Desafio 7: Sugestões de Rotação de Segredos

**Dificuldade:** Difícil | **Tempo:** 4-6 horas | **Ensina:** APIs de provedores, orientação para remediação, saída estruturada

Após detectar um segredo vazado, forneça instruções específicas de rotação para cada provedor.

**Ponto de partida:** Crie `internal/remediation/remediation.go` com um mapa do ID da regra para as etapas de remediação.

**Exemplo de saída:**

```
CRITICAL  aws-access-key-id  config.py:1

  Etapas de rotação:
  1. Vá para o Console AWS IAM → Usuários → Credenciais de segurança
  2. Crie uma nova chave de acesso
  3. Atualize todos os serviços que usam a chave antiga
  4. Desative a chave antiga (não a delete ainda)
  5. Após 24-48 horas sem problemas, delete a chave antiga
  6. Execute: aws sts get-caller-identity (para verificar se a nova chave funciona)

  Documentação: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html
```

**Dicas:**

- Crie uma struct `Remediation` com `Steps []string`, `DocURL string`, `CLICommand string`
- Mapeie IDs de regras para remediações: `aws-access-key-id` → rotação AWS IAM, `github-pat-classic` → rotação de configurações do GitHub, `stripe-live-secret` → rotação do dashboard do Stripe
- Adicione uma flag `--remediate` à CLI
- Para o reporter de terminal, imprima as etapas de remediação indentadas sob cada descoberta
- Para JSON/SARIF, inclua a remediação nas propriedades

## Desafio 8: Correspondência de Keywords com Aho-Corasick

**Dificuldade:** Difícil | **Tempo:** 3-4 horas | **Ensina:** Estruturas de dados Trie, algoritmos de correspondência de strings, desempenho

Substitua o escaneamento linear de keywords em `MatchKeywords` por um autômato Aho-Corasick para correspondência O(n) contra todas as keywords simultaneamente.

**Abordagem atual** (`internal/rules/registry.go` MatchKeywords):
Para cada regra, para cada keyword, chama `strings.Contains`. Isso é O(regras * keywords * comprimento_do_conteúdo).

**Melhor abordagem:**
Construa uma trie a partir de todas as keywords no momento da inicialização do registro. No momento do escaneamento, passe o conteúdo pelo autômato uma única vez. O autômato reporta quais keywords corresponderam, e você mapeia essas keywords de volta para as regras.

**Ponto de partida:** Use `github.com/cloudflare/ahocorasick` ou implemente o seu próprio.

**Dicas:**

- Construa o autômato em `Registry.Register` ou em um método `Finalize()` chamado após todas as regras serem registradas
- O autômato deve ser insensível a maiúsculas (converta todas as keywords e o conteúdo para minúsculas)
- Mapeie cada keyword de volta para sua(s) regra(s) usando um índice reverso
- Faça o benchmark antes e depois: `go test -bench=BenchmarkMatchKeywords -benchmem`
- A melhoria será mais perceptível em arquivos grandes com muitas regras. Em arquivos pequenos com poucas regras, o overhead de construir o autômato pode torná-lo mais lento.

**Melhoria esperada:** Em um arquivo de 500 linhas com 150 regras tendo em média 2 keywords cada, a abordagem atual faz ~300 chamadas `strings.Contains`. O Aho-Corasick faz uma única passagem pelo conteúdo. Para bases de código grandes com milhares de arquivos, isso faz diferença.

## Dicas Gerais

- **Escreva os testes primeiro.** Cada desafio deve começar com um teste que falha. Os padrões de teste existentes em `internal/engine/detector_test.go` e `internal/engine/integration_test.go` são bons templates.
- **Mantenha as alterações isoladas.** Cada desafio deve ser implementável sem modificar a lógica central de detecção. Use interfaces e composição para estender em vez de modificar.
- **Faça benchmarks ao alegar ganhos de desempenho.** Os benchmarks `testing.B` do Go são simples de escrever. Se você afirmar que algo é mais rápido, prove com números.
- **Verifique o Justfile.** Execute `just ci` antes de considerar qualquer desafio concluído. Todos os testes existentes ainda devem passar.
