# angela - Scanner de Segurança de Dependências Python

## O Que É Isso

angela é uma ferramenta CLI que escaneia projetos Python em busca de dependências desatualizadas e vulnerabilidades de segurança conhecidas. Ela lê seu `pyproject.toml` ou `requirements.txt`, verifica no PyPI as versões mais recentes, consulta o OSV.dev em busca de CVEs e atualiza seu arquivo de dependências preservando todos os seus comentários e formatação.

## Por Que Isso Importa

Em dezembro de 2022, o pacote PyTorch no PyPI foi comprometido com uma dependência maliciosa (`torchtriton`) que exfiltrou variáveis de ambiente e credenciais da AWS. Usuários que executaram `pip install torch` durante uma janela de tempo específica instalaram malware sem saber. Isso aconteceu porque o PyPI permite que qualquer pessoa faça upload de pacotes, e ataques de dependency confusion são triviais de executar.

O incidente do ua-parser-js em 2021 mostrou outro vetor: um pacote legítimo com 8 milhões de downloads semanais foi sequestrado quando as credenciais do npm do mantenedor foram roubadas. O atacante publicou as versões 0.7.29, 0.8.0 e 1.0.0 contendo mineradores de criptomoedas e ladrões de senhas. Mais de 1.000 projetos foram infectados antes que o npm o removesse.

**Cenários do mundo real onde isso se aplica:**

- Seu projeto depende de `requests==2.28.0`, mas a versão 2.28.1 corrige a CVE-2023-32681 (uma vulnerabilidade de injeção de cabeçalho que permite que atacantes injetem cabeçalhos e cookies arbitrários)
- Você está rodando `django==3.2.0`, sem saber que versões anteriores à 3.2.19 são vulneráveis à CVE-2023-31047, permitindo injeção de SQL via nomes de arquivos manipulados
- Uma dependência transitiva três níveis abaixo possui uma RCE crítica, mas você nunca sequer olha para a saída do `pip list`

## O Que Você Aprenderá

Este projeto ensina como a resolução de dependências e o escaneamento de vulnerabilidades funcionam no nível do protocolo. Ao construí-lo você mesmo, você entenderá:

**Conceitos de Segurança:**

- Ataques à cadeia de suprimentos via dependency confusion, typosquatting e sequestro de pacotes (package takeover). Você aprenderá como os atacantes exploram o fato de que o `pip` instalará qualquer pacote com o nome correto, independentemente de quem o publicou.
- Bancos de dados de CVE e como o OSV.dev agrega dados de vulnerabilidade do GitHub Security Advisories, PyPA e do National Vulnerability Database em uma API consultável.
- Estratégias de resolução de versão, incluindo o parsing da PEP 440, que lida com épocas, pre-releases, post-releases e identificadores de versão local que o versionamento semântico não suporta.

**Habilidades Técnicas:**

- Design de cliente HTTP com concorrência limitada usando o pacote errgroup do Go. Você implementará pools de workers que evitam sobrecarregar APIs enquanto mantêm o paralelismo.
- Cache baseado em arquivos com ETags e expiração TTL, o mesmo padrão que CloudFlare e Varnish usam para cache de borda.
- Edição cirúrgica baseada em Regex para atualizar versões de dependências sem destruir comentários ou formatação, uma técnica também usada pelo Renovate e Dependabot.

**Ferramentas e Técnicas:**

- PyPI Simple API (PEP 691) para buscar metadados de pacotes. Este é o mesmo endpoint que o pip usa, então você está vendo exatamente o que o pip vê.
- Banco de dados de vulnerabilidades OSV.dev para consultas em lote de CVEs conhecidas em múltiplos ecossistemas.
- Parsing e manipulação de TOML em Go usando pelletier/go-toml, com padrões regex personalizados para preservar a formatação.

## Pré-requisitos

Antes de começar, você deve entender:

**Conhecimento necessário:**

- Fundamentos de Go, incluindo goroutines, channels e context. Você precisa saber o que `go func()` faz e por que `context.Context` é importante para cancelamento.
- APIs HTTP e padrões REST. Você chamará endpoints do PyPI e OSV.dev, analisará respostas JSON e lidará com limites de taxa (rate limits).
- Conceitos básicos de segurança, como o que é uma CVE, por que as versões das dependências importam e como as dependências transitivas criam riscos.

**Ferramentas necessárias:**

- Go 1.24+ - O projeto usa a sintaxe `for range N` do Go 1.24 e constantes `math.MinInt`.
- Task runner `just` (opcional) - O Justfile fornece atalhos para tarefas comuns como `just lint` e `just test`.
- Um projeto Python com dependências para testar, ou use o `testdata/pyproject.toml` fornecido.

**Útil, mas não obrigatório:**

- Experiência com ferramentas de empacotamento Python como pip, poetry ou uv. Entender como o `pyproject.toml` difere do `requirements.txt` ajuda.
- Conhecimento da PEP 440 (versionamento Python) e PEP 503 (normalização de nomes de pacotes). O projeto implementa ambos do zero.

## Início Rápido

Coloque o projeto para rodar localmente:

```bash
# Clone e navegue
cd projects/Team/b-V_Scanner

# Instale as dependências
go mod download

# Execute contra os dados de teste
just dev-scan

# Ou execute diretamente
go run ./cmd/angela scan --file testdata/pyproject.toml
```

Saída esperada: angela mostrará que pacotes como `django>=3.2,<4.0` e `requests>=2.28.0` estão desatualizados, e então listará quaisquer vulnerabilidades conhecidas com seus níveis de severidade (CRITICAL, HIGH, MODERATE, LOW) e versões corrigidas.

Para realmente atualizar um arquivo:

```bash
# Verifique o que mudaria (dry run)
go run ./cmd/angela check --file testdata/pyproject.toml

# Atualize o arquivo
go run ./cmd/angela update --file testdata/pyproject.toml

# Atualize E escaneie por vulnerabilidades
go run ./cmd/angela update --vulns --file testdata/pyproject.toml
```

## Estrutura do Projeto

```
simple-vulnerability-scanner/
├── cmd/
│   └── angela/
│       └── main.go              # Ponto de entrada, chama cli.Execute()
├── internal/
│   ├── cli/                     # Comandos Cobra e formatação de saída
│   │   ├── update.go            # Lógica principal do comando
│   │   └── output.go            # UI de terminal com cores
│   ├── pypi/                    # Cliente PyPI Simple API
│   │   ├── client.go            # Cliente HTTP com cache
│   │   ├── cache.go             # Cache baseado em arquivo com suporte a ETag
│   │   └── version.go           # Parser de versão PEP 440
│   ├── osv/                     # Scanner de vulnerabilidades OSV.dev
│   │   └── client.go            # Consultas de vulnerabilidade em lote
│   ├── pyproject/               # Parser/writer de pyproject.toml
│   │   ├── parser.go            # Extrai dependências do TOML
│   │   └── writer.go            # Atualiza versões preservando comentários
│   ├── requirements/            # Parser/writer de requirements.txt
│   ├── config/                  # Carregador de configuração da angela
│   └── ui/                      # Cores de terminal e spinners
├── pkg/types/                   # Definições de tipos compartilhados
├── testdata/                    # Arquivos de exemplo para testes
├── Justfile                     # Atalhos do task runner
└── .golangci.yml               # Configuração do linter
```

## Próximos Passos

1. **Entenda os conceitos** - Leia [01-CONCEPTS.md](./01-CONCEPTS.md) para aprender sobre segurança da cadeia de suprimentos, bancos de dados de CVE e resolução de versão.
2. **Estude a arquitetura** - Leia [02-ARCHITECTURE.md](./02-ARCHITECTURE.md) para ver como o cache do PyPI, requisições concorrentes e o escaneamento de vulnerabilidades se encaixam.
3. **Percorra o código** - Leia [03-IMPLEMENTATION.md](./03-IMPLEMENTATION.md) para explicações linha por linha do parser PEP 440, sistema de cache e atualizações de arquivos baseadas em regex.
4. **Estenda o projeto** - Leia [04-CHALLENGES.md](./04-CHALLENGES.md) para ideias como adicionar geração de SBOM, escaneamento de dependências transitivas ou fontes de vulnerabilidade personalizadas.

## Problemas Comuns

**"Package not found on PyPI"**

```
Error: package "my-package" not found on PyPI
```

Solução: Verifique a grafia do nome do pacote. O PyPI normaliza nomes (sublinhados tornam-se hífens), então `my_package` e `my-package` são o mesmo. O pacote também pode ser escrito de forma diferente do que você pensa (ex: `Pillow`, não `PIL`).

**"Rate limit exceeded" ao escanear muitos pacotes**
Solução: A PyPI Simple API possui limites de taxa (aproximadamente 10 requisições/segundo). angela define como padrão 10 workers concorrentes (`internal/pypi/client.go:17`). Se você atingir os limites, reduza o `DefaultMaxWorkers`. O cache ajuda a evitar requisições repetidas.

**O cache mostra dados obsoletos**
Solução: Limpe o cache com `angela cache clear` ou delete manualmente `~/.angela/cache/`. O TTL padrão é de 1 hora (`internal/pypi/cache.go:11`). Para desenvolvimento, você pode querer diminuir este valor.

**"Invalid TOML syntax" após atualização**
Isso nunca deveria acontecer (o atualizador valida antes de escrever), mas se acontecer: o padrão regex em `internal/pyproject/writer.go:90-99` pode ter correspondido a algo que não deveria. Abra um issue com o conteúdo original do pyproject.toml.

## Projetos Relacionados

Se você achou isso interessante, confira:

- **api-rate-limiter** - Constrói a limitação de taxa HTTP que o PyPI e o OSV.dev usam para prevenir abusos.
- **package-vulnerability-db** - Mostra como construir sua própria alternativa ao OSV.dev com fontes de vulnerabilidade personalizadas.
- **dependency-graph-analyzer** - Estende este projeto para mapear dependências transitivas e encontrar riscos na cadeia de suprimentos mais profundamente na árvore.
