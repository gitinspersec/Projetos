# Conceitos de Segurança Fundamentais

Este documento explica os conceitos de segurança que você encontrará ao construir o Portia. Estes não são apenas definições. Vamos nos aprofundar em por que eles importam e como eles realmente funcionam em sistemas de produção.

## Secret Sprawl (Dispersão de Segredos)

### O Que É

Secret sprawl é a disseminação descontrolada de credenciais, chaves de API, tokens e outros valores sensíveis em código-fonte, arquivos de configuração, pipelines de CI/CD, logs de chat e documentação. Uma vez que um segredo entra em um repositório git, ele existe em cada clone para sempre, mesmo que o arquivo seja deletado posteriormente.

### Por Que Isso Importa

O GitHub relatou em 2023 que detectou mais de 12,8 milhões de novos segredos vazados em repositórios públicos naquele ano. Esse número cobre apenas os segredos que eles escaneiam ativamente. O número real é significativamente maior.

**Uber, Novembro de 2016**
Dois engenheiros enviaram chaves de acesso AWS para um repositório privado no GitHub. Seis meses depois, atacantes que tiveram acesso a esse repositório usaram as chaves para acessar um bucket S3 contendo 57 milhões de registros de passageiros e motoristas (nomes, endereços de e-mail, números de telefone, números de carteira de habilitação). A Uber pagou aos atacantes US$ 100.000 para deletar os dados e manter silêncio, e depois pagou US$ 148 milhões em um acordo com os procuradores-gerais de todos os 50 estados dos EUA. As chaves correspondiam exatamente ao padrão de prefixo `AKIA` que a regra `aws-access-key-id` do Portia detecta (`internal/rules/builtin.go`).

**Samsung, Março de 2022**
O grupo Lapsus$ exfiltrou 190GB de código-fonte da Samsung de servidores Git internos. Dentro do código: credenciais hardcoded para a plataforma SmartThings da Samsung, chaves privadas de assinatura e código-fonte para bootloaders e TrustZone. A superfície de ataque existia porque os segredos estavam embutidos diretamente no código da aplicação, em vez de serem injetados em tempo de execução.

**Twitter, Janeiro de 2023**
Um pesquisador descobriu que os aplicativos móveis do Twitter continham chaves de API embutidas que podiam ser extraídas através de engenharia reversa. O Twitter reconheceu o problema e rotacionou as chaves, mas o incidente destacou um problema fundamental: aplicativos móveis enviam código compilado para milhões de dispositivos, e quaisquer segredos nesse código são extraíveis.

### Como Funciona

Segredos acabam no código através de três caminhos principais:

**Atalhos de desenvolvimento**: Um desenvolvedor precisa de uma chave de API para testar um recurso. Ele a cola em um arquivo de configuração, faz o commit e planeja movê-la para variáveis de ambiente mais tarde. Ele nunca o faz. A chave permanece no histórico do git para sempre. Mesmo deletar o arquivo e fazer o commit da deleção não ajuda, porque `git log --all --full-history` ainda a mostra.

**Copiar e colar da documentação**: Provedores de nuvem frequentemente mostram comandos de exemplo com chaves de exemplo como `AKIAIOSFODNN7EXAMPLE`. Desenvolvedores substituem o exemplo por sua chave real, esquecem de reverter e fazem o commit do arquivo.

**Configuração de CI/CD**: Segredos são definidos como variáveis de ambiente em pipelines de CI (GitHub Actions, CircleCI, Jenkins). Quando um desenvolvedor copia um arquivo de workflow ou exporta uma config de pipeline, esses valores acabam em arquivos sob controle de versão. A violação da CircleCI em janeiro de 2023 aconteceu em parte porque segredos de clientes foram armazenados como variáveis de ambiente em texto simples acessíveis aos jobs de CI.

### Estratégias de Defesa

O Portia implementa o escaneamento de pre-commit, que captura segredos antes que eles entrem no histórico do git. Mas o escaneamento é apenas uma camada:

1.  **Hooks de pre-commit** - Execute o Portia em arquivos em staging antes de cada commit.
2.  **Escaneamento de pipeline de CI** - Execute o Portia em cada pull request como uma verificação obrigatória.
3.  **Integração com Vault** - Use HashiCorp Vault, AWS Secrets Manager ou ferramentas similares para injetar segredos em tempo de execução.
4.  **Variáveis de ambiente** - Mantenha segredos totalmente fora do código. Referencie `${API_KEY}` em vez de colar a chave.
5.  **Rotação** - Assuma que segredos vazarão. Rotacione-os regularmente para que chaves vazadas expirem rapidamente.

## Entropia de Shannon

### O Que É

A entropia de Shannon (nomeada em homenagem a Claude Shannon, o pai da teoria da informação) mede a aleatoriedade de uma string. Ela responde à pergunta: "Quão surpreso eu ficaria com cada caractere?". Um texto em inglês tem baixa entropia (você pode prever a próxima letra). Uma chave de API como `xK9mP2vL5nQ8jR3t` tem alta entropia (cada caractere é imprevisível).

A fórmula: `H = -Σ p(x) * log₂(p(x))`

Onde `p(x)` é a frequência de cada caractere dividida pelo comprimento da string.

### Por Que Isso Importa

Regex sozinho não é suficiente para detectar todos os segredos. Algumas regras correspondem a padrões estruturais (prefixo `AKIA` para chaves AWS, prefixo `ghp_` para tokens GitHub). Mas muitos segredos não possuem um prefixo estrutural. Uma senha como `xK9mP2vL5nQ8jR3t` parece caracteres aleatórios, e essa aleatoriedade em si é o sinal.

Textos legíveis por humanos (nomes de variáveis, comentários, URLs) têm entropia em torno de 2.5-3.5 bits por caractere. Segredos gerados aleatoriamente tipicamente têm entropia acima de 4.0. Ao computar a entropia e comparar com um limite (threshold), o Portia pode sinalizar strings de alta aleatoriedade que não correspondem a nenhum padrão regex específico.

### Como Funciona

A implementação em `internal/rules/entropy.go` funciona em três etapas:

**Etapa 1: Detecção de charset** - Determina se a string se parece com hex (`0-9a-f`), base64 (`A-Za-z0-9+/=`) ou alfanumérico geral. Isso importa porque o limite de entropia difere: uma string hex precisa de uma entropia menor para ser suspeita (já que hex só tem 16 caracteres possíveis), enquanto strings alfanuméricas precisam de uma entropia maior.

**Etapa 2: Contagem de frequência de caracteres** - Conta quantas vezes cada caractere aparece. Para `aabbcc`, as frequências são: `a=2, b=2, c=2`. Cada caractere tem probabilidade 2/6 = 0.333.

**Etapa 3: Cálculo de entropia** - Para cada caractere único, computa `-p * log₂(p)` e os soma. Para `aabbcc`: `-0.333 * log₂(0.333) * 3 caracteres únicos = 1.585 bits`. Para uma string aleatória de 20 caracteres com todos os caracteres únicos: `-0.05 * log₂(0.05) * 20 = 4.322 bits`.

**Limites usados no Portia:**

- Strings Hex (charset `0-9a-f`): mínimo de 3.0 bits
- Strings Base64 (charset `A-Za-z0-9+/=`): mínimo de 4.0 bits
- Strings Alfanuméricas: mínimo de 3.5 bits

Esses limites são configurados por regra em `internal/rules/builtin.go`. Regras como `generic-password` e `generic-secret` usam limites de entropia para filtrar falsos positivos de baixa aleatoriedade como `password = "admin"`.

### Armadilhas Comuns

**Baixa entropia não significa segurança.** A string `aaaaaaaaAAAAAAAA` tem baixa entropia, mas ainda pode ser uma chave de API válida para um sistema mal projetado. A entropia é um sinal, não o único sinal.

**O charset importa.** Uma string hex `deadbeef` tem baixa entropia absoluta, mas pode ser suspeita em um contexto hexadecimal. A função `DetectCharset` do Portia (`internal/rules/entropy.go`) ajusta os limites baseada no conjunto de caracteres.

## Detecção Baseada em Expressões Regulares

### O Que É

A maioria dos provedores de nuvem e serviços usa formatos estruturados para suas credenciais. Chaves de acesso AWS sempre começam com `AKIA`, `ABIA`, `ACCA` ou `ASIA` seguidas por 16 caracteres alfanuméricos maiúsculos. PATs do GitHub começam com `ghp_` seguidos por 36 caracteres alfanuméricos. Chaves live do Stripe começam com `sk_live_`. Esses padrões são específicos o suficiente para corresponderem a expressões regulares, mantendo taxas de falsos positivos muito baixas.

### Por Que Isso Importa

A detecção baseada em prefixo funciona porque os provedores de nuvem projetam intencionalmente seus formatos de chave para serem identificáveis. A AWS usa o prefixo `AKIA` especificamente para que ferramentas possam detectar chaves vazadas. O GitHub mudou seu formato de token de strings hex aleatórias para tokens com prefixo (`ghp_`, `gho_`, `ghs_`, `ghr_`) em 2021 para permitir exatamente esse tipo de escaneamento.

### Como Funciona

Cada regra em `internal/rules/builtin.go` possui quatro componentes que trabalham juntos:

**Keywords** - Correspondência rápida de strings para eliminar ~95% dos chunks antes da regex. Se um chunk não contém a keyword `AKIA`, não há sentido em rodar a regex de chave AWS contra ele. Esta é uma otimização de desempenho. Veja a função `MatchKeywords` em `internal/rules/registry.go`.

**Pattern** - A regex real. Para chaves AWS: `\b((?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16})\b`. As fronteiras de palavra `\b` evitam a correspondência de substrings de tokens mais longos. O grupo de captura `(...)` extrai apenas a parte do segredo.

**SecretGroup** - Qual grupo de captura da regex contém o valor do segredo. O grupo 0 é a correspondência inteira; o grupo 1 é o primeiro grupo entre parênteses. A maioria das regras usa o grupo 1 para extrair a chave sem o contexto ao redor.

**Allowlist** - Padrões por regra que suprimem falsos positivos conhecidos. Chaves AWS possuem uma allowlist para `AKIAIOSFODNN7EXAMPLE` (a chave de exemplo da documentação da AWS).

### 150 Regras Organizadas por Provedor

As regras integradas do Portia cobrem:

- **Provedores de nuvem**: AWS (3), GCP (3), Azure (3), Alibaba Cloud (1), IBM Cloud (1), Cloudflare (2)
- **Controle de versão**: GitHub (6), GitLab (3), Bitbucket (1)
- **Pagamento**: Stripe (4), Square (2), Razorpay (1), Braintree (1), Coinbase (1)
- **Comunicação**: Slack (4), Twilio (3), SendGrid (1), Discord (3), Telegram (1), Microsoft Teams (1), Intercom (1)
- **E-mail**: Mailchimp (1), Mailgun (1), Resend (1), Brevo (1), Postmark (1)
- **Infraestrutura**: Heroku (1), DigitalOcean (3), Supabase (2), Confluent (1), Fly.io (1), Render (1), Vercel (1), Netlify (1), PlanetScale (3), Neon (1), Upstash (1), Turso (1)
- **Hospedagem/VPS**: Hetzner (1), Linode (1), Vultr (1)
- **IA/ML**: OpenAI (2), Anthropic (1), HuggingFace (1), Replicate (1), Groq (1), Perplexity (1)
- **CI/CD**: CircleCI (1), Buildkite (1), GitHub Actions (1)
- **Gerenciamento de segredos**: Vault (1), Doppler (2), 1Password (1)
- **Criptográfico**: Chaves SSH/PGP/PKCS8 (6), JWT (1), Age (1)
- **Registros de pacotes**: NPM (1), PyPI (1), RubyGems (1), Docker Hub (1)
- **Genérico**: senha (1), segredo (1), api-key (1), token (1)
- **Strings de conexão**: PostgreSQL (1), MySQL (1), MongoDB (1), Redis (1), Firebase URL (1), Cloudinary (1)
- **Monitoramento/Observabilidade**: Datadog (1), New Relic (1), Grafana (2), Sentry (1), PostHog (1), Axiom (1), Dynatrace (1), Honeycomb (1), Elastic (1), Segment (1), Rollbar (1), Mixpanel (1), Amplitude (1)
- **Ferramentas de desenvolvedor**: Figma (1), Linear (1), Postman (1), Algolia (1), Contentful (1), Snyk (1), SonarQube (1), Freshdesk (1), Zendesk (1)
- **Outros**: Terraform (1), Shopify (4), Okta (1), LaunchDarkly (2), Infracost (1), Prefect (1), Pulumi (1), Databricks (1), HubSpot (1), PagerDuty (1), Atlassian (1), Facebook (1), Twitter (1), Firebase FCM (1), Mapbox (2), Doppler CLI (1)

## Redução de Falsos Positivos

### O Que É

Um scanner de regex ingênuo produz centenas ou milhares de falsos positivos: valores de placeholder, variáveis de template, fixtures de teste, chaves de exemplo de documentação. Se a saída for ruidosa, os desenvolvedores a ignoram. A redução de falsos positivos é o conjunto de técnicas que tornam a saída do scanner confiável o suficiente para se agir sobre ela.

### Por Que Isso Importa

O relatório State of Secrets Sprawl de 2023 da GitGuardian descobriu que equipes que usam scanners de segredos com altas taxas de falsos positivos tiveram uma taxa de remediação 40% menor do que equipes com scanners de baixa taxa de falsos positivos. O ruído mata a ação. Se cada segunda descoberta for um falso positivo, os desenvolvedores param de ler as descobertas.

### Como Funciona

O Portia usa uma cadeia de filtros de 5 camadas em `internal/engine/filter.go` e `internal/engine/detector.go`:

**Camada 1: Pré-filtragem de keywords** (`internal/rules/registry.go` MatchKeywords)
Antes de rodar qualquer regex, verifica se o chunk contém keywords relevantes para qualquer regra. Um arquivo cheio de HTML sem nenhuma instância de `password`, `secret`, `key`, `token` ou qualquer prefixo específico de provedor não corresponderá a nenhuma regra. Isso elimina ~95% dos chunks imediatamente e é uma pura otimização de desempenho.

**Camada 2: Validação estrutural** (`internal/engine/detector.go` extractSecret)
Após a correspondência da regex, extrai o segredo usando o grupo de captura. Se o grupo de captura estiver vazio ou a correspondência for apenas espaço em branco, descarta-a. Isso lida com casos de borda onde uma regex corresponde à sintaxe ao redor, mas não captura nada significativo.

**Camada 3: Detecção de placeholder** (`internal/engine/filter.go` IsPlaceholder)
Verifica o valor do segredo contra padrões de placeholder conhecidos: `example`, `test`, `dummy`, `fake`, `placeholder`, `YOUR_API_KEY`, `xxxx...`, `****...`, `${VARIABLE}`, `{{TEMPLATE}}`, `TODO`, `CHANGEME`, `REPLACE_ME`. Estes são definidos em `internal/rules/registry.go` GlobalValueAllowlist.

**Camada 4: Detecção de template** (`internal/engine/filter.go` IsTemplated)
Verifica se o segredo é uma variável de template: `${ENV_VAR}`, `{{handlebars}}`, `os.getenv(...)`, `process.env.X`, `System.getenv(...)`, `ENV[...]`. Estes não são segredos reais; são referências a segredos armazenados em outro lugar.

**Camada 5: Filtragem de stopwords** (`internal/engine/filter.go` IsStopword)
Verifica se o segredo, quando dividido em delimitadores (`_`, `-`, `.`, `/`), contém palavras comuns de programação como `function`, `controller`, `database`, `config`, etc. A lista de stopwords em `internal/engine/filter.go` possui mais de 700 palavras. Isso captura falsos positivos como `module_controller_factory` que a regex poderia identificar como um token genérico.

**Camada 6: Allowlisting de caminhos** (`internal/rules/registry.go` GlobalPathAllowlist)
Pula arquivos que são conhecidos por conterem dados não sensíveis: `go.mod`, `go.sum`, `package-lock.json`, `yarn.lock`, arquivos `.min.js`, `node_modules/`, `vendor/`, formatos binários.

### Armadilha Comum

O maior erro na redução de falsos positivos: ser agressivo demais. Se você filtrar resultados demais, perderá segredos reais. A abordagem do Portia é conservadora por padrão. Cada camada de filtro visa uma classe específica de falsos positivos com alta precisão. A lista de stopwords só corresponde a partes divididas por delimitadores (não substrings) para evitar a filtragem de segredos reais que por acaso contenham palavras comuns como substrings.

## HIBP k-Anonymity

### O Que É

Have I Been Pwned (HIBP) é o banco de dados de Troy Hunt com bilhões de senhas e credenciais de violações de dados conhecidas. O Portia pode verificar se um segredo detectado aparece em qualquer violação conhecida. Mas enviar o segredo para uma API externa derrotaria o propósito. O k-Anonymity resolve isso: você envia apenas 5 caracteres do hash SHA-1 do segredo, e o servidor retorna todos os hashes que compartilham esse prefixo. Você verifica localmente se o seu hash completo aparece nos resultados.

### Por Que Isso Importa

Se o Portia encontra `password = "P@ssw0rd123"` no seu código, saber que ele aparece em 47.000 violações conhecidas adiciona urgência. Uma senha única, gerada aleatoriamente, que não foi violada é menos urgente do que uma senha comumente usada que está em todas as wordlists de credential stuffing.

O dump da violação Collection #1 de 2019 continha 773 milhões de endereços de e-mail únicos e 21 milhões de senhas únicas. O vazamento RockYou2021 continha 8,4 bilhões de senhas. Se o seu segredo detectado aparece nesses conjuntos de dados, os atacantes já o possuem.

### Como Funciona

Implementação em `internal/hibp/client.go`:

1.  **Hash SHA-1**: Computa `SHA-1(segredo)`. Para "P@ssw0rd123": `a94a8fe5ccb19ba61c4c0873d391e987982fbbd3`
2.  **Extração de prefixo**: Pega os primeiros 5 caracteres hex: `a94a8`
3.  **Consulta à API**: `GET https://api.pwnedpasswords.com/range/a94a8`
4.  **Resposta**: A API retorna ~500-800 sufixos de hash com contagens de ocorrência.
5.  **Correspondência local**: Verifica se os 35 caracteres restantes do seu hash aparecem na resposta.

A API nunca vê o hash completo, portanto não pode determinar qual senha você está verificando. Esta é a garantia do k-anonymity.

**Cache LRU** (`internal/hibp/client.go`): Os resultados são armazenados em um cache LRU de 10.000 entradas. Se o mesmo prefixo já foi consultado antes, o resultado em cache é retornado. Isso evita chamadas de API redundantes ao escanear grandes bases de código com segredos semelhantes.

**Circuit breaker** (`internal/hibp/client.go`): Usando a biblioteca gobreaker da Sony, o cliente rastreia falhas na API. Após 5 erros consecutivos, o circuito abre e as requisições são rejeitadas imediatamente por 60 segundos. Isso evita falhas em cascata se a API do HIBP estiver fora do ar ou limitada por taxa.

### Armadilha Comum

O HIBP foi projetado para senhas, não para chaves de API. Uma chave de acesso AWS vazada não aparecerá em bancos de dados de violação de senhas. A verificação HIBP é mais útil para descobertas do tipo senha (as regras `generic-password` e `generic-secret`) e menos útil para tokens específicos de provedores. O Portia apenas envia descobertas de password e generic-secret para o HIBP, pulando tokens específicos de provedores inteiramente.

## Formato de Saída SARIF

### O Que É

SARIF (Static Analysis Results Interchange Format) é um padrão OASIS (versão 2.1.0) para expressar a saída de ferramentas de análise estática. É um formato baseado em JSON que o GitHub, Azure DevOps, GitLab e outras plataformas de CI podem consumir para exibir descobertas inline em pull requests.

### Por Que Isso Importa

Sem o SARIF, integrar um scanner ao CI requer uma lógica de parsing personalizada para o formato de saída de cada ferramenta. Com o SARIF, você produz um arquivo JSON e todas as principais plataformas de CI sabem como exibi-lo. O GitHub Code Scanning, por exemplo, aceita uploads de SARIF e mostra as descobertas como anotações no diff do PR.

### Como Funciona

O reporter SARIF do Portia em `internal/reporter/sarif.go` produz um documento compatível com a v2.1.0:

```json
{
  "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
  "version": "2.1.0",
  "runs": [{
    "tool": {
      "driver": {
        "name": "portia",
        "rules": [...]
      }
    },
    "results": [...]
  }]
}
```

Cada descoberta mapeia para um `result` SARIF com:

- `ruleId` - O ID da regra do Portia (ex: `aws-access-key-id`)
- `level` - Mapeado da severidade do Portia (CRITICAL/HIGH = `error`, MEDIUM = `warning`, LOW = `note`)
- `message` - A descrição da descoberta
- `locations` - Caminho do arquivo e número da linha
- `properties` - Metadados específicos do Portia (entropia, status HIBP, segredo mascarado)

Para fazer o upload para o GitHub Code Scanning:

```bash
portia scan --format sarif . > results.sarif
gh api repos/{owner}/{repo}/code-scanning/sarifs \
  -f sarif=@results.sarif \
  -f commit_sha=$(git rev-parse HEAD)
```
