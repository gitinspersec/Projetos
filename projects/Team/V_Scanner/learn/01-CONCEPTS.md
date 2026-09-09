# Conceitos de Segurança Fundamentais

Este documento explica os conceitos de segurança que você encontrará ao construir a angela. Estes não são apenas definições. Vamos nos aprofundar em por que eles importam e como eles realmente funcionam em sistemas de produção.

## Ataques à Cadeia de Suprimentos (Supply Chain Attacks)

### O Que É

Um ataque à cadeia de suprimentos visa as dependências das quais seu código depende, em vez do seu próprio código. Um atacante compromete um pacote que você importa, e esse código malicioso é executado com os mesmos privilégios da sua aplicação. O ataque é bem-sucedido porque os desenvolvedores confiam em suas dependências sem auditá-las.

### Por Que Isso Importa

A violação da SolarWinds em 2020 comprometeu mais de 18.000 organizações, incluindo Microsoft, Intel e a maior parte do governo federal dos EUA. Os atacantes não hackearam a SolarWinds diretamente. Eles injetaram código malicioso no processo de build do software Orion, e cada cliente que atualizou o Orion instalou um backdoor. O código estava assinado com o certificado da SolarWinds, por isso parecia legítimo.

No ecossistema Python, o ataque à cadeia de suprimentos do PyTorch em 2022 funcionou da mesma maneira. Alguém fez o upload de um pacote malicioso chamado `torchtriton` para o PyPI. O pacote legítimo `torch` depende do `triton`, mas o resolvedor de dependências do pip aceitará o `torchtriton` se ele tiver um número de versão superior. Usuários que executaram `pip install torch` durante uma janela específica receberam o pacote malicioso, que roubou credenciais da AWS e chaves SSH.

### Como Funciona

Ataques à cadeia de suprimentos exploram três vetores principais:

**Dependency confusion**: Fazer o upload de um pacote malicioso para um registro público com o mesmo nome de um pacote interno. Se o pip verificar o PyPI antes do seu índice privado, ele baixará a versão maliciosa pública. Isso aconteceu com a Apple, Microsoft e Netflix em 2021, quando o pesquisador Alex Birsan fez o upload de pacotes que coincidiam com seus nomes internos.

**Typosquatting**: Registrar pacotes com nomes semelhantes aos populares (`requsts` em vez de `requests`). Desenvolvedores cometem erros de digitação, o pip instala o pacote errado, fim de jogo. Em 2017, alguém fez o upload de `python3-dateutil` para o PyPI. O pacote real é `python-dateutil`. O falso teve 2.000 downloads antes da remoção.

**Package takeover**: Comprometer a conta de um mantenedor ou explorar pacotes abandonados. O incidente do `ua-parser-js` (8 milhões de downloads semanais) aconteceu quando alguém roubou as credenciais do npm do mantenedor. O pacote `event-stream` foi entregue a um novo "mantenedor" que publicou código com backdoor visando carteiras de criptomoedas.

### Ataques Comuns

1. **Código malicioso no setup.py** - Pacotes Python executam código arbitrário durante a instalação. Um `setup.py` malicioso pode roubar credenciais antes mesmo do pacote ser importado.

2. **Dependências com backdoor** - O pacote malicioso em si pode estar limpo, mas ele depende de algo malicioso. Dependências transitivas criam uma superfície de ataque profunda.

3. **Bypasses de fixação de versão** - Você fixa `requests==2.28.0`, mas o pip ainda pode instalar `requests[security]==2.28.0`, que possui dependências diferentes. A sintaxe de extras cria uma rota de escape.

### Estratégias de Defesa

angela implementa várias defesas:

- **Fixação de versão com restrições >=** - `requests>=2.28.0` significa "pelo menos esta versão", fornecendo patches de segurança enquanto evita downgrades. É isso que o `internal/pyproject/parser.go:88-97` extrai.

- **Escaneamento de vulnerabilidades** - Consulta o OSV.dev em busca de CVEs conhecidas em sua árvore de dependências. angela faz isso em `internal/osv/client.go:40-65`, agrupando requisições para evitar sobrecarregar a API.

- **Verificação de assinatura** - Não implementado na angela (projeto iniciante), mas ferramentas de produção verificam os checksums dos pacotes contra um hash conhecido como bom. O PyPI fornece hashes SHA256 para cada lançamento.

A melhor defesa é **reduzir a contagem de dependências**. Cada pacote que você importa é um vetor potencial na cadeia de suprimentos. A própria angela possui apenas 5 dependências diretas (fatih/color, pelletier/go-toml, spf13/cobra, golang.org/x/sync).

## Bancos de Dados de CVE

### O Que É

CVE (Common Vulnerabilities and Exposures) é um formato padronizado para documentar bugs de segurança. Cada vulnerabilidade recebe um ID único como `CVE-2023-32681`. A MITRE Corporation mantém o sistema CVE, mas múltiplas organizações contribuem com dados: GitHub Security Advisories, o National Vulnerability Database do NIST, bancos de dados específicos de fornecedores.

OSV.dev (Open Source Vulnerabilities) agrega todos esses em uma única API consultável. Ele cobre PyPI, npm, Maven, Go e mais. Em vez de consultar 10 bancos de dados diferentes, angela consulta o OSV uma única vez.

### Por Que Isso Importa

Em 14 de abril de 2023, a CVE-2023-32681 foi publicada para a biblioteca `requests`. Versões anteriores à 2.31.0 permitem que atacantes injetem cabeçalhos arbitrários via caracteres `\r\n` no cabeçalho Proxy-Authorization. Isso ignora restrições de proxy e pode vazar cookies sensíveis.

Se você estiver rodando `requests==2.28.0`, você está vulnerável. Mas como você saberia sobre a CVE-2023-32681? Você teria que assinar o GitHub Security Advisories, monitorar os anúncios do PyPI, verificar o NIST NVD regularmente e cruzar tudo com suas dependências. O OSV.dev automatiza isso.

### Como Funciona

O OSV.dev fornece um endpoint de consulta em lote que aceita múltiplos pares de pacote+versão:

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

A resposta inclui todas as vulnerabilidades conhecidas para aquelas versões exatas:

```json
{
  "results": [
    {
      "vulns": [
        { "id": "GHSA-j8r2-6x86-q33q", "modified": "2023-05-22T20:30:00Z" }
      ]
    },
    {
      "vulns": [{ "id": "CVE-2023-31047", "modified": "2023-05-03T12:00:00Z" }]
    }
  ]
}
```

angela então busca os detalhes completos para cada ID de vulnerabilidade para obter o resumo, a severidade e a versão corrigida. Este processo de duas etapas (consulta em lote + buscas individuais) está em `internal/osv/client.go:40-95`.

### Armadilhas Comuns

**Erro 1: Verificar apenas dependências diretas**

```go
// Ruim: apenas escaneia pacotes explicitamente no pyproject.toml
for _, dep := range directDeps {
    checkVulns(dep)
}

// Bom: precisaria resolver toda a árvore de dependências
// (angela não faz isso - é uma limitação de projeto iniciante)
```

Dependências transitivas são onde a maioria das CVEs se esconde. `requests` depende de `urllib3`, que depende de `certifi`. Uma vulnerabilidade no `certifi` afeta seu app mesmo que você nunca o tenha importado diretamente. O escaneamento completo da cadeia de suprimentos requer a construção do grafo de dependências completo, o que a angela não faz (veja 04-CHALLENGES.md para saber como adicionar isso).

**Erro 2: Confiar cegamente no campo de severidade**

O OSV às vezes não possui dados de severidade, relata "UNKNOWN" ou usa sistemas de pontuação diferentes (CVSS v3 vs v4 vs escala interna do GitHub). angela extrai a severidade em `internal/osv/client.go:245-270`:

```go
func extractSeverity(v *osvVuln) string {
    for _, s := range v.Severity {
        if s.Type != "CVSS_V3" && s.Type != "CVSS_V4" {
            continue  // Pula pontuação não padrão
        }
        if score, err := strconv.ParseFloat(s.Score, 64); err == nil {
            return classifyScore(score)  // Mapeia 0-10 para nomes de severidade
        }
    }
    // Fallback para database_specific.severity ou "UNKNOWN"
}
```

Sempre tenha um fallback. Alguns avisos do GitHub usam rótulos qualitativos ("MODERATE") em vez de pontuações CVSS numéricas.

**Erro 3: Não remover duplicatas de aliases CVE/GHSA**

A mesma vulnerabilidade recebe múltiplos IDs:

- CVE-2023-32681 (ID da MITRE)
- GHSA-j8r2-6x86-q33q (ID do GitHub)
- PYSEC-2023-80 (ID da PyPA)

O OSV retorna os três. Se você os contar ingenuamente, relatará "3 vulnerabilidades" quando na verdade é um único problema com três nomes. angela remove duplicatas em `internal/osv/client.go:141-149`:

```go
func isDuplicate(v *osvVuln, seen map[string]bool) bool {
    if seen[v.ID] {
        return true
    }
    for _, alias := range v.Aliases {
        if seen[alias] {
            return true  // Já vimos esta vuln sob um ID diferente
        }
    }
    return false
}
```

## Resolução de Versão PEP 440

### O Que É

A PEP 440 define como as versões de pacotes Python são estruturadas e comparadas. **Não** é versionamento semântico (semver). Versões Python suportam épocas, pre-releases (alpha/beta/rc), post-releases, dev releases e identificadores de versão local. A gramática completa é:

```
[epoch!]release[.pre-release][.post-release][.dev-release][+local]
```

Exemplos reais:

- `2!1.0` - Época 2, lançamento 1.0 (vence todas as versões de época 0 ou 1)
- `1.0a1` - Pre-release Alpha
- `1.0.post3` - Post-release (estável, apenas uma correção menor)
- `1.0.dev5` - Snapshot de desenvolvimento
- `1.0+ubuntu2` - Rótulo de versão local

### Por Que Isso Importa

Se você ordenar versões como strings, você errará:

```
"1.0a1" > "1.0"   # ERRADO: "a" > "" em ASCII
"1.10.0" < "1.9.0"  # ERRADO: comparação de string não é numérica
```

O Pip usa a comparação PEP 440 para determinar a "versão mais recente". Se a angela ordenar incorretamente, ela pode atualizar usuários para um pre-release instável ou pular patches de segurança importantes.

Em março de 2023, alguém fez o upload de `certifi==2023.03.07a1` para o PyPI (um pre-release acidental). Ferramentas que não implementaram a PEP 440 corretamente tentaram atualizar usuários da estável `2023.02.23` para a pre-release `2023.03.07a1`, quebrando builds.

### Como Funciona

O parser PEP 440 da angela em `internal/pypi/version.go:60-112` usa uma única regex compilada para extrair todos os componentes:

```
(?i)^v?
(?:(\d+)!)?                          # epoch
(\d+(?:\.\d+)*)                      # release segments
(?:[-_.]?(alpha|a|beta|b|rc)[-_.]?(\d*))?  # pre-release
(?:[-_.]?(post|rev|r)[-_.]?(\d*)|-(\d+))?  # post-release
(?:[-_.]?(dev)[-_.]?(\d*))?          # dev release
(?:\+([a-z0-9]...))?$                # local version
```

A função de comparação implementa as regras de ordenação da PEP 440:

```
1.0.dev1 < 1.0a1 < 1.0b1 < 1.0rc1 < 1.0 < 1.0.post1
```

Isso é feito usando valores sentinela (`math.MinInt` e `math.MaxInt`) em `internal/pypi/version.go:146-174`:

```go
func preKey(v Version) (int, int) {
    hasPre := v.PreKind != ""
    hasDev := v.Dev >= 0
    hasPost := v.Post >= 0

    switch {
    case !hasPre && !hasPost && hasDev:
        return math.MinInt, math.MinInt  // Dev-only ordena primeiro
    case hasPre:
        return preKindRank(v.PreKind), v.PreNum  // a=0, b=1, rc=2
    default:
        return math.MaxInt, math.MaxInt  // Lançamentos finais ordenam por último
    }
}
```

### Ataques Comuns

A resolução de versão PEP 440 não possui "ataques" per se, mas existem comportamentos exploráveis:

1. **Confusão de pre-release** - Um atacante faz o upload de `malicious-package==2.0a1`. Se um usuário tem `malicious-package>=1.0` em suas dependências e seu resolvedor não filtra pre-releases, ele recebe a versão alpha.

2. **Bumping de época** - Épocas sobrepõem tudo o mais. `1!1.0` vence `9999.0.0` porque época 1 > época 0. Isso é destinado a renomeações de pacotes de emergência, mas um ator malicioso poderia abusar disso.

3. **Rótulos de versão local** - `1.0+evil` não aparece no PyPI (versões locais não podem ser enviadas), mas se o índice privado de alguém o servir, ele ordena após `1.0` e pode ser instalado.

### Estratégias de Defesa

Abordagem da angela:

- **Filtrar pre-releases por padrão** - `internal/pypi/version.go:208-220` possui `LatestStable()` que pula qualquer coisa com `PreKind != ""` ou `Dev >= 0`.

- **Opt-in explícito de pre-release** - A flag `--include-prerelease` permite que usuários obtenham deliberadamente versões alpha/beta ao testar.

- **Consciência de época** - O parser lida com épocas corretamente. Se você vir `2!1.0`, angela não assumirá incorretamente que `1.0` é mais recente.

A chave é nunca assumir que as versões são simples major.minor.patch. Pacotes Python no mundo real usam a gramática completa da PEP 440, e se o seu parser não lidar com isso, você tomará decisões ruins.

## Como Estes Conceitos se Relacionam

Ataques à cadeia de suprimentos visam o processo de resolução de dependências. Um atacante explora a confusão de versão (PEP 440) para fazer o pip instalar um pacote malicioso. Bancos de dados de CVE detectam vulnerabilidades conhecidas após o fato, mas não conseguem capturar zero-days ou backdoors intencionais. Você precisa de ambos: fixação de versão para controlar o que é instalado e escaneamento de vulnerabilidades para saber quando uma versão instalada está comprometida.

```
┌─────────────────┐
│  pyproject.toml │  ← Suas dependências
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Parsing Versão  │  ← PEP 440 determina a "mais recente"
│  (PEP 440)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Banco Dados CVE │  ← Verifica se a "mais recente" é vulnerável
│  (OSV.dev)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Avaliação Risco │  ← Devemos atualizar? Pular? Ignorar?
└─────────────────┘
```

Todos os três trabalham juntos. Perca um e você terá pontos cegos.

## Padrões e Frameworks da Indústria

### OWASP Top 10

Este projeto aborda:

- **A06:2021 - Componentes Vulneráveis e Desatualizados** - angela escaneia por CVEs conhecidas e pacotes desatualizados. Este é o risco #6 mais crítico para aplicações web da OWASP. A violação da Equifax em 2017 (143 milhões de registros roubados) aconteceu porque eles rodavam uma versão desatualizada do Apache Struts com uma vulnerabilidade RCE conhecida.

- **A08:2021 - Falhas de Integridade de Software e Dados** - Ataques à cadeia de suprimentos como dependency confusion caem aqui. angela ajuda mostrando exatamente quais versões você está rodando, mas não verifica assinaturas de pacotes (isso exigiria verificar as chaves PGP do PyPI).

### MITRE ATT&CK

Técnicas relevantes:

- **T1195.001 - Compromise Software Dependencies** - Os ataques SolarWinds e PyTorch usaram isso. Atacantes injetam código malicioso em um pacote que seu processo de build baixa. angela detecta comprometimentos conhecidos via OSV.dev, mas não consegue capturar zero-days.

- **T1195.002 - Compromise Software Supply Chain** - Mais amplo que apenas dependências. Inclui comprometer servidores de build, certificados de assinatura e infraestrutura de distribuição. angela aborda a parte das dependências.

### CWE

Enumerações de fraquezas comuns cobertas:

- **CWE-1104** - Uso de Componentes de Terceiros Não Mantidos. Se você está rodando `django==2.2`, você está em uma versão que chegou ao fim da vida (EOL) em abril de 2022. angela sinaliza isso mostrando as atualizações disponíveis.

- **CWE-829** - Inclusão de Funcionalidade de Esfera de Controle Não Confiável. Cada `pip install` do PyPI confia no código desse pacote. angela não resolve isso (você precisaria de revisão de código ou sandboxing), mas pelo menos informa em quem você está confiando.

## Exemplos do Mundo Real

### Estudo de Caso 1: Violação da Equifax (2017)

**O que aconteceu**: A Equifax rodava o Apache Struts com uma vulnerabilidade RCE conhecida (CVE-2017-5638, publicada em março de 2017). Atacantes a exploraram em maio de 2017, roubando 143 milhões de números de Seguro Social, datas de nascimento e endereços.

**Como o ataque funcionou**: A vulnerabilidade estava no parser de upload de arquivos do Struts. Um atacante enviou um cabeçalho `Content-Type` manipulado que disparou a execução remota de código. A Equifax teve **dois meses** entre a publicação da CVE e a violação para aplicar o patch.

**Quais defesas falharam**: A Equifax não possuía escaneamento automatizado de vulnerabilidades. Eles dependiam de auditorias de segurança manuais, que não detectaram a versão desatualizada do Struts. Mesmo após o início da violação, levaram **seis semanas** para detectá-la.

**Como isso poderia ter sido evitado**: O escaneamento automatizado (o que a angela faz) teria sinalizado a CVE-2017-5638 imediatamente. Se a Equifax tivesse uma política de "aplicar patches em CVEs críticas em 72 horas", a violação não teria acontecido.

### Estudo de Caso 2: Backdoor no event-stream (2018)

**O que aconteceu**: Um pacote npm popular chamado `event-stream` (2 milhões de downloads/semana) foi entregue a um novo mantenedor que imediatamente publicou uma versão com backdoor. O código malicioso visava carteiras de criptomoedas, roubando chaves privadas de Bitcoin.

**Como o ataque funcionou**: O mantenedor original estava sobrecarregado e aceitou a oferta de um voluntário para assumir o projeto. O novo "mantenedor" adicionou uma dependência ao `flatmap-stream@0.1.1`, que continha código ofuscado que verificava se a aplicação era a Copay (uma carteira Bitcoin). Se sim, ele exfiltrava as chaves da carteira.

**Quais defesas falharam**: O pacote não possuía escaneamento contínuo de vulnerabilidades. Desenvolvedores confiaram na conta do mantenedor sem verificar a identidade. O npm não sinalizou a adição suspeita de dependência.

**Como isso poderia ter sido evitado**: A revisão de dependências (qual versão tínhamos na semana passada vs esta semana?) teria detectado a adição repentina do `flatmap-stream`. angela não faz monitoramento contínuo (ainda), mas [04-CHALLENGES.md](./04-CHALLENGES.md) tem ideias para adicioná-lo.

## Testando Seu Entendimento

Antes de passar para a arquitetura, certifique-se de que você consegue responder:

1. Você vê uma dependência de pacote `requests>=2.28.0`. Quais vulnerabilidades isso poderia perder em comparação com `requests==2.31.0`? (Dica: qualquer coisa entre 2.28.0 e 2.31.0)

2. Um novo pacote `requests-security==3.0.0` aparece no PyPI. Seu app importa `requests`. Você deve se preocupar? (Dica: sim. Ataque de dependency confusion via typosquatting)

3. O OSV retorna CVE-2023-1234, GHSA-abcd-efgh e PYSEC-2023-001 para o mesmo pacote. Quantas vulnerabilidades distintas são estas? (Dica: uma vulnerabilidade, três IDs)

Se estas perguntas parecerem confusas, releia as seções relevantes. A implementação fará mais sentido quando estes fundamentos estiverem claros.

## Leitura Adicional

**Essencial:**

- [PEP 440 - Version Identification](https://peps.python.org/pep-0440/) - A especificação completa para strings de versão Python. angela implementa as partes principais.
- [Documentação da API OSV.dev](https://osv.dev/docs/) - Como consultar o banco de dados de vulnerabilidades. angela usa o endpoint de lote (batch).

**Aprofundamentos:**

- [Backstabber's Knife Collection](https://arxiv.org/abs/2005.09535) - Artigo acadêmico analisando pacotes maliciosos no PyPI. Encontrou 174 pacotes maliciosos usando typosquatting.
- [Dependency Confusion: When Are Your npm Packages Vulnerable?](https://medium.com/@alex.birsan/dependency-confusion-4a5d60fec610) - O relato de Alex Birsan sobre o ataque que atingiu Apple, Microsoft e outras.

**Contexto histórico:**

- [The Internet Worm (1988)](https://spaf.cerias.purdue.edu/tech-reps/823.pdf) - O worm de Robert Morris explorou um buffer overflow no `fingerd`. Primeiro grande ataque no estilo cadeia de suprimentos usando serviços de sistema confiáveis.
- [Reflections on Trusting Trust](https://www.cs.cmu.edu/~rdriley/487/papers/Thompson_1984_ReflectionsonTrustingTrust.pdf) - Palestra do Prêmio Turing de 1984 de Ken Thompson sobre backdoors em compiladores. Relevante para entender por que você não pode confiar totalmente em código upstream.
