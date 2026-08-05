# Desafios de Extensão

Você leu o código e entende o que ele faz. É hora de torná-lo seu.

Estes desafios estão ordenados aproximadamente por dificuldade. Os primeiros são mudanças de 30 minutos. Os últimos são projetos de fim de semana que alteram significativamente o funcionamento do scanner. Nenhum deles tem a "resposta certa" escondida nesta pasta. Tente-os, erre, acerte e aprenda algo.

Se você ficar travado, a fonte da verdade é sempre o código. Releia `evaluate_header()`, `scan()` e `_render_report()`. O scanner inteiro cabe em uma tela.

## Desafios de aquecimento

### 1. Adicione um sétimo cabeçalho para verificar

**Objetivo:** Estender `RULES` com mais um cabeçalho de segurança. Escolha um destes:

- **`Cross-Origin-Opener-Policy`** (COOP): impede que a página sofra interação de outras origens via window.opener. Valor recomendado: `same-origin`.
- **`Cross-Origin-Embedder-Policy`** (COEP): controla quais recursos de origem cruzada podem ser carregados. Valor recomendado: `require-corp`.
- **`Cross-Origin-Resource-Policy`** (CORP): controla quem pode incorporar este recurso. Valor recomendado: `same-origin`.

**Por que é útil.** Estes três cabeçalhos juntos (COOP, COEP, CORP) são a forma moderna de isolar uma página de ataques de origem cruzada como o Spectre. Sites reais de alta segurança configuram os três.

**Dicas.**

- Adicione um `HeaderRule(...)` a `RULES`. Escolha uma severidade. Decida se você precisa de um padrão `must_match` (uma palavra simples como `"same-origin"` funciona como uma verificação de substring; use uma regex mais rica se "o valor deve ser exatamente uma de N opções" for importante).
- Os totais de pontuação mudarão. Seus testes existentes que afirmam pontuações exatas podem quebrar. Atualize esses testes ou escreva-os em termos de porcentagens.
- Teste contra um site real. `https://web.dev` é um bom site para verificar.

**Concluído quando.** `just test` passar e `just run -- https://web.dev` mostrar seu novo cabeçalho na tabela.

### 2. Adicione uma flag `--json` para saída legível por máquina

**Objetivo.** Fazer o scanner emitir um blob JSON quando o usuário passar `--json`, em vez da tabela colorida.

**Por que é útil.** Sistemas de CI e dashboards precisam de saída estruturada. Uma tabela amigável para o terminal é ótima para humanos, JSON é ótimo para todo o resto.

**Dicas.**

- Adicione uma flag booleana `--json` ao `_build_argument_parser()` usando `action="store_true"`.
- No `main()`, após o retorno de `scan()`, crie um desvio baseado em `args.json`. Se for True, use o módulo `json` da biblioteca padrão para gerar um dict com os campos do relatório. Se for False, chame o `_render_report()` existente.
- `HeaderFinding` não é diretamente serializável para JSON porque contém um `HeaderRule` aninhado. Você pode achatá-lo manualmente ou usar `dataclasses.asdict()`, que converte uma árvore de dataclasses congeladas em dicts aninhados.

**Concluído quando.** `just run -- https://example.com --json | jq '.score'` imprimir apenas o número da pontuação.

### 3. Adicione uma flag `--verbose` que imprime os cabeçalhos brutos da resposta

**Objetivo.** Flag opcional que, quando configurada, imprime cada cabeçalho que o servidor retornou (incluindo os que não são de segurança) acima da tabela.

**Por que é útil.** Ao depurar "por que o scanner diz que meu HSTS é fraco", você quer ver o valor bruto que o servidor enviou.

**Dicas.**

- Adicione a flag da mesma forma que o `--json`.
- A função `scan()` armazena apenas os resultados (findings), não a resposta bruta. Você precisará passar os cabeçalhos brutos através do `ScanReport` (adicione um novo campo) ou fazer com que `scan()` retorne uma tupla.
- Imprima os cabeçalhos brutos em `_render_report` quando uma flag verbose for passada. A assinatura do renderizador precisará ser atualizada.

**Concluído quando.** `just run -- https://example.com --verbose` mostrar todos os cabeçalhos do servidor acima da tabela de resultados.

## Desafios intermediários

### 4. Escaneie múltiplas URLs em uma única execução

**Objetivo.** Permitir que o usuário passe várias URLs e obtenha um relatório por URL. Bônus: uma tabela de resumo ao final.

**Por que é útil.** Ao auditar os sites de uma empresa, você não quer executar o scanner uma vez por URL. Execute-o uma vez sobre a lista inteira.

**Dicas.**

- Altere o argumento `url` do argparse para aceitar `nargs="+"` (um ou mais). `args.url` torna-se uma lista de strings.
- Faça um loop sobre as URLs no `main()`. Chame `scan()` para cada uma, renderize cada relatório e colete-os.
- Para o resumo, adicione uma pequena tabela final com uma linha por URL: URL, pontuação, nota.
- O código de saída torna-se interessante. Provavelmente a pior nota entre todas as URLs.

**Casos de borda.**

- Uma URL falha (erro de rede), mas outras têm sucesso. Você ainda sai com o código 2?
- Duas URLs retornam a mesma URL final (após redirecionamentos). Remover duplicatas ou mostrar ambas?

### 5. Adicione uma flag de limite no estilo `--allow-warnings`

**Objetivo.** Permitir que o usuário diga "estou ok com a nota C, saia com erro apenas se a nota for D ou inferior".

**Por que é útil.** Integrações de CI. Diferentes equipes têm diferentes barras de aceitação.

**Dicas.**

- Adicione `--min-grade` recebendo um valor de `{"A", "B", "C", "D", "F"}`. O padrão deve ser `"C"` (o comportamento atual, aproximadamente).
- No `main()`, compare `report.grade` com o limite e escolha o código de saída adequadamente.
- As notas têm uma ordem natural. Você pode compará-las com um pequeno auxiliar que mapeia cada uma para um inteiro.

**Concluído quando.** `just run -- https://example.com --min-grade C` sair com 0 se o site obteve C ou melhor, e sair com 1 caso contrário.

### 6. Cache de resultados em disco

**Objetivo.** Quando o usuário escanear a mesma URL novamente dentro da última hora, retorne o resultado em cache em vez de acessar a rede.

**Por que é útil.** Quando você está iterando no renderizador ou na pontuação, você não quer sobrecarregar um site real em cada execução de teste.

**Dicas.**

- Armazene os relatórios em cache em `~/.cache/http-headers-scanner/`.
- Nome do arquivo a partir de um hash da URL (`hashlib.sha256(url.encode()).hexdigest()`).
- Use `dataclasses.asdict(report)` para converter em JSON e `json.dump()` para escrever.
- Inclua um timestamp no arquivo de cache. Ignore o cache quando ele for mais antigo que uma hora.
- Adicione uma flag `--no-cache` para ignorar o cache.

**Parte difícil.** `HeaderFinding` contém um `HeaderRule`. Quando você carrega do cache, precisa reconstruir essas regras a partir do JSON. Ou, de forma mais simples, armazene apenas as partes que lhe interessam e reconstrua o formato do relatório do zero.

### 7. Detectar e avisar sobre HTTP/HTTPS mistos

**Objetivo.** Se o usuário passar uma URL `http://` e o servidor redirecionar para `https://`, mencione isso com destaque na saída.

**Por que é útil.** Muitos sites impõem HTTPS via redirecionamento, mas a própria cadeia de redirecionamento não é criptografada no primeiro salto e pode ser removida por atacantes (é contra isso que o HSTS protege). Saber se um redirecionamento aconteceu é um sinal útil.

**Dicas.**

- Após `scan()`, compare `report.url` (o que o usuário digitou) com `report.final_url` (onde ele terminou).
- Se o usuário digitou `http://...` e a URL final é `https://...`, imprima uma nota de uma linha: "Nota: esta URL foi atualizada de HTTP para HTTPS via redirecionamento. Sem HSTS, a primeira requisição é vulnerável a interceptação."
- Melhor ainda, deduza pontos se o HSTS estiver ausente E o usuário entrou via http.

## Desafios avançados

### 8. Torne-o assíncrono para escanear muitos sites em paralelo

**Objetivo.** Use `httpx.AsyncClient` mais `asyncio.gather` para que o escaneamento de 50 URLs leve aproximadamente o tempo de um escaneamento, não de 50.

**Por que é útil.** Auditorias reais cobrem muitos hosts. O escaneamento sequencial é o gargalo.

**Dicas.**

- Adicione um `async def scan_async(url, ...)` ao lado de `scan()`. Use `async with httpx.AsyncClient() as client:` e `client.get(...)`.
- No `main()`, construa um `asyncio.gather()` sobre uma lista de chamadas `scan_async`.
- Limite de concorrência: não dispare contra 5000 URLs de uma vez. Use `asyncio.Semaphore(20)` para limitar o paralelismo.
- As funções puras (`evaluate_header`, `score`, `grade`) não mudam. Esse é o benefício de separar a lógica pura do I/O.

**Cuidado com.** Alguns sites limitam a taxa (rate-limit) de escaneamentos agressivos. O User-Agent padrão nos identifica; respeite quaisquer cabeçalhos `Retry-After` se eles retornarem.

### 9. Adicione um analisador estático para o valor do CSP

**Objetivo.** Atualmente, apenas verificamos se o `Content-Security-Policy` está presente. Construa um sub-analisador que olhe dentro do valor do CSP e relate problemas específicos:

- Contém `'unsafe-inline'` no `script-src`? Fraqueza grave, perda de pontos.
- Contém um domínio curinga (`*`) no `script-src`? O mesmo.
- Ausência de `default-src`? Vale a pena notar.

**Por que é útil.** Um CSP que permite `'unsafe-inline'` mal pode ser considerado um CSP. Scanners reais (Mozilla Observatory) fazem essa análise. O seu também pode fazer.

**Dicas.**

- Adicione uma nova dataclass `CSPAnalysis` com campos como `has_unsafe_inline: bool`, `wildcard_origins: list[str]`, etc.
- Adicione uma função pura `parse_csp(value: str) -> CSPAnalysis`. Gramática do CSP: diretivas são separadas por ponto e vírgula; cada diretiva é `nome fonte1 fonte2 ...`.
- Faça com que o status `weak` da regra CSP leve em conta o resultado da análise. O `evaluate_header` base precisará de uma saída de escape para regras que possuem um validador personalizado.

**Parte difícil.** O CSP é genuinamente complexo. A especificação oficial está em `w3.org/TR/CSP3`. Comece analisando apenas o `script-src`; ignore o resto.

### 10. Construa um monitor contínuo

**Objetivo.** Execute o scanner contra uma lista de URLs a cada 24 horas e alerte quando a nota de um site cair.

**Por que é útil.** Configurações sofrem desvios (drift). Um site que tinha nota A seis meses atrás pode cair para B porque alguém desativou o HSTS para depurar algo e esqueceu de reativá-lo. Você vai querer saber disso.

**Dicas.**

- Necessita de armazenamento persistente. O começo mais fácil: um banco de dados SQLite com as colunas `(url, run_at, score, grade)`. A biblioteca padrão possui `sqlite3`, então não há nova dependência.
- Um script separado lê uma lista de URLs (uma URL por linha, em um arquivo), executa o scanner e grava os resultados.
- Compare a nota de hoje com a nota anterior mais recente por URL. Se hoje estiver pior, emita um alerta (imprima no stdout, envie um e-mail, envie uma mensagem no Slack, você escolhe).
- Uma entrada no `cron` ou um timer do systemd dispara o script uma vez por dia.

**Cuidado com.** Redes são instáveis. Um timeout em um dia não é necessariamente uma queda de nota. Você provavelmente vai querer uma regra de "duas falhas seguidas" antes de alertar.

### 11. Comparação baseada em navegador: escaneie a mesma URL com três User-Agents diferentes

**Objetivo.** Sites às vezes servem cabeçalhos diferentes para bots em comparação com navegadores reais. Adicione um modo `--compare-uas` que escaneie a mesma URL com o UA padrão do scanner, com um UA do Chrome e com um UA do Googlebot, e então mostre uma comparação lado a lado dos cabeçalhos.

**Por que é útil.** Um site pode servir um CSP rigoroso para usuários reais, mas um CSP frouxo para bots, ou vice-versa. Saber disso é uma evidência real de uma configuração incorreta.

**Dicas.**

- A função `scan()` já recebe um argumento `user_agent`. Execute-a três vezes com três valores diferentes.
- Um UA real do Chrome se parece com: `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36`.
- O UA do Googlebot é `Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)`.
- A camada de renderização precisa de um modo de "comparação em três colunas". Uma Table do rich com as colunas "Default", "Chrome", "Googlebot" e uma linha por cabeçalho.

## Desafio especialista

### 12. Torne-o um serviço com uma API REST

**Objetivo.** Envolva o scanner em um pequeno servidor HTTP. Faça um POST de uma URL e receba de volta um relatório JSON.

**Por que é útil.** Outros serviços em um pipeline de segurança podem chamar o seu. Além disso, é a maneira natural de tornar o scanner acessível a partir de um frontend.

**Tempo estimado.** Um fim de semana se você nunca usou FastAPI antes, algumas horas se já usou.

**Pré-requisitos.** Alguma exposição a frameworks web ajudaria.

**Esboço da arquitetura.**

```
┌─────────────────────────────────────────────────────┐
│ App FastAPI                                         │
│                                                     │
│  POST /scan { "url": "..." }                        │
│       └──▶ async scan_async(url) ────▶ ScanReport   │
│       ◀── { "url": ..., "grade": ..., findings: ... }│
│                                                     │
│  GET /healthz                                       │
│       └──▶ {"ok": true}                             │
└─────────────────────────────────────────────────────┘
```

**Passos.**

1. **Adicione fastapi e uvicorn às dependências.** `uv add fastapi uvicorn[standard]`.
2. **Crie um novo arquivo `server.py`** que importe `scan_async` do seu scanner assincronizado.
3. **Defina um modelo Pydantic** para o corpo da requisição (`class ScanRequest(BaseModel): url: HttpUrl`).
4. **Defina um modelo de resposta** que reflita o `ScanReport` para serialização. `HttpUrl` valida URLs na fronteira da API.
5. **Adicione a rota.** `@app.post("/scan", response_model=ScanResponse)` e então `async def scan_endpoint(req: ScanRequest)`.
6. **Adicione um endpoint healthz** para que monitores externos possam confirmar que o serviço está ativo.
7. **Adicione limitação de taxa (rate limiting).** Caso contrário, as pessoas usarão seu serviço para escanear terceiros. O projeto avançado `api-rate-limiter` neste repositório é uma boa referência.

**Checklist de produção.**

- [ ] Validação: rejeite IPs internos (`127.0.0.1`, `10.0.0.0/8`, etc.) para prevenir SSRF.
- [ ] Timeouts: cada scan tem um limite rígido para que um alvo lento não prenda os workers.
- [ ] Logging: cada requisição é registrada com `url`, `grade`, `duration_ms`.
- [ ] CORS: decida quais origens podem chamar sua API.
- [ ] Deploy: Dockerfile que executa o uvicorn, variável de ambiente para a porta.

**Objetivo ambicioso.** Construa um pequeno frontend de página única (HTML puro + JS, sem necessidade de framework) que permita ao usuário colar uma URL e ver o relatório. Agora você tem um produto real.

## Outras direções

Algumas ideias menores se nenhuma das anteriores lhe interessar:

- **Modo para daltônicos.** Substitua as cores verde/amarelo/vermelho por verde/amarelo/vermelho mais formas distintas (✓, ⚠, ✗) para que a tabela seja legível para usuários daltônicos.
- **Importação de arquivo HAR.** Em vez de escanear uma URL ao vivo, leia os cabeçalhos de um arquivo `.har` (HTTP Archive, o que os navegadores exportam das ferramentas de desenvolvedor). Permite escanear respostas que você capturou anteriormente.
- **Mostrar diff contra uma linha de base conhecida.** Salve um "relatório de referência" para uma URL. No próximo scan, mostre apenas as mudanças ("HSTS ficou mais fraco", "X-Frame-Options desapareceu").
- **Adicione um modo `--strict`** que baixe a barra: deduza pontos mesmo para problemas menores (ex: `max-age` menor que seis meses, ausência de `includeSubDomains`).

## O que fazer quando estiver travado

A estratégia que funciona todas as vezes:

1. **Reduza.** Isole o problema. Comente tudo, exceto a menor parte que ainda se comporta mal.
2. **Imprima.** Quando `evaluate_header` não retornar o que você esperava, imprima as entradas e as saídas. Não adivinhe como elas se parecem. Olhe.
3. **Leia o teste.** Se um teste está falhando, o teste está lhe dizendo exatamente o que ele esperava. Leia a afirmação (assertion). Leia as entradas. Compare com a saída real.
4. **Compare com o que estava bom.** Use `git diff` para ver o que mudou desde a última vez que os testes passaram. O bug está nas suas alterações em 99% das vezes.

Se depois de tudo isso você ainda precisar de ajuda, a aba GitHub Discussions no repositório é o lugar certo. Traga:

- O que você tentou.
- O que você esperava.
- O que realmente aconteceu (o erro completo, se houver).
- O menor exemplo reprodutível que mostre o problema.

"Não funciona" não é informação suficiente para ajudar. Os quatro pontos acima são.

&nbsp;

## Fim

<p align="center">
  <img src="../assets/cat.gif" width="300" alt="Cat">
</p>

Agora você chegou ao final de seu projeto. Se conseguiu realizar a maioria dos desafios, saiba que estará pronto para o que virá em seguida. **Parabéns!**

Minha recomendação agora é que você _se arrisque em mais um projeto disponível_, mas no seu tempo. Aliás, esse é o ponto mais forte de qualquer currículo ao lado das experiências: **os projetos**. Então, sem medo, quanto mais fizer, melhor.
