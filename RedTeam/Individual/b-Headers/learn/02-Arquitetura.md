# Arquitetura

Este arquivo explica como o código está organizado e o porquê. Ele é a ponte entre "eu entendo o que são cabeçalhos HTTP" (o arquivo anterior) e "eu consigo ler este código Python específico" (o próximo arquivo). Leia-o após os conceitos e antes da implementação.

Todo o scanner é composto por um arquivo Python mais um arquivo de teste. Menos de 700 linhas no total. Isso é pequeno o suficiente para você se perguntar por que estamos usando a palavra "arquitetura". A resposta: mesmo programas pequenos se beneficiam de serem divididos em partes, e a FORMA como são divididos importa. Um scanner de produção real crescerá para muitos arquivos. Aprender como é a divisão neste tamanho torna os maiores menos assustadores.

## 1. A visão geral

O scanner é um pipeline. Os dados fluem da esquerda para a direita através de quatro estágios:

```
   ┌────────┐  URL  ┌──────────┐  bytes   ┌────────────┐  findings  ┌──────────┐
   │  User  │ ────▶ │  scan()  │ ──────▶  │ evaluate_  │ ────────▶  │  render  │
   │  CLI   │       │  fetches │          │  header()  │            │  report  │
   └────────┘       └──────────┘  loop    │   ×6       │            └──────────┘
                                          └────────────┘
```

1. **Camada CLI.** O usuário digita `headers https://example.com`. O `argparse` transforma isso em um objeto Python normal com `args.url` e `args.timeout`.
2. **Camada de rede (`scan()`).** Faz uma requisição HTTPS, segue redirecionamentos, retorna os cabeçalhos brutos como um dict.
3. **Camada de avaliação (`evaluate_header()`).** Função pura. Recebe uma regra e os cabeçalhos da resposta, retorna um resultado (finding). Chamada uma vez por regra. Sem rede. Sem impressão.
4. **Camada de renderização (`_render_report()`).** Recebe o relatório, imprime uma tabela colorida, o painel de notas e as recomendações.

A razão pela qual ele é estruturado desta forma: cada estágio é testável de forma independente. Podemos passar para `evaluate_header()` um dict falso de cabeçalhos e verificar o resultado, sem nunca tocar na internet. Podemos construir um `ScanReport` falso e verificar a pontuação e a nota, sem executar `scan()` de forma alguma.

Se qualquer um desses estágios estivesse misturado (por exemplo, se `scan()` imprimisse diretamente sua saída e a matemática vivesse dentro da lógica de impressão), testar significaria subir um servidor web real ou falso toda vez. Separá-los é a razão pela qual você pode escrever 20 testes que rodam em menos de um segundo.

## 2. Os quatro formatos de dados principais

Usamos **dataclasses** para nossos dados. Uma dataclass é apenas uma classe onde o Python escreve o boilerplate para você. Em vez disso:

```python
class HeaderRule:
    def __init__(self, header, severity, description, recommendation, must_match=None):
        self.header = header
        self.severity = severity
        self.description = description
        self.recommendation = recommendation
        self.must_match = must_match
```

Você escreve isto:

```python
@dataclass(frozen=True, slots=True)
class HeaderRule:
    header: str
    severity: Severity
    description: str
    recommendation: str
    must_match: str | None = None
```

O decorador `@dataclass` no topo lê as declarações de campos e gera o `__init__` para você. Ele também gera igualdade (`==`), uma representação de string e algumas outras coisas úteis.

Duas flags que valem a pena entender:

- **`frozen=True`** torna a dataclass **imutável**. Depois de criar um `HeaderRule`, você não pode fazer `rule.severity = "low"`. Tentar modificar um campo gera um erro. Isso é bom para tipos "value object" onde você quer garantias de que nenhuma outra parte do código possa alterá-los sem você saber.
- **`slots=True`** torna as instâncias **menores na memória**. Sem slots, cada objeto Python carrega um dicionário oculto para seus atributos, o que é flexível, mas usa mais memória. Com slots, os atributos vão para slots fixos, sem dict. Para um tipo de registro com um conjunto conhecido de campos, isso é pura vantagem. Não custa nada.

Temos quatro formatos no total:

### 2.1 `HeaderRule`: "o que estamos procurando"

Uma regra é uma coisa-a-ser-verificada. Nome do cabeçalho, severidade, descrição (para humanos), uma recomendação (o que configurar se estiver ausente) e um regex opcional `must_match` (para cabeçalhos como `X-Content-Type-Options` onde o _valor_ tem que estar correto, não apenas presente — uma palavra simples como `"nosniff"` funciona como uma verificação de substring, enquanto um padrão mais rico como `r"max-age\s*=\s*[1-9]"` rejeita valores de HSTS que se desativam).

Esta é a regra que o scanner percorre. Toda a lista de regras vive em uma constante de nível de módulo chamada `RULES`. Adicionar uma nova verificação de cabeçalho significa anexar a essa lista. O restante do código é genérico.

### 2.2 `HeaderFinding`: "o que encontramos"

Um resultado (finding) é o resultado da execução de uma regra contra a resposta do servidor. Ele carrega:

- A regra de onde veio (para que o renderizador possa mostrar a severidade, recomendação, etc., sem fazer uma segunda busca).
- Um `status`: `ok`, `weak` ou `missing`.
- O `actual_value` que o servidor enviou (ou `None` se o cabeçalho estiver ausente).
- Uma `note` curta legível por humanos descrevendo o que aconteceu ("Presente", "Presente e contém `nosniff`", "Cabeçalho `X` não está configurado", etc.).

Os resultados também são congelados (frozen). Uma vez que avaliamos uma regra, o resultado não muda. Isso torna o relatório seguro para ser passado para múltiplas funções sem se preocupar que uma delas o altere.

### 2.3 `ScanReport`: "o resultado completo"

Um relatório envolve tudo de um scan. A URL original (o que o usuário digitou), a URL final (após redirecionamentos), o código de status HTTP e a lista de resultados (um por regra).

A parte interessante: `score` e `grade` são **propriedades computadas**, não campos armazenados. São funções decoradas com `@property` que olham para os resultados em tempo real. Isso significa:

- Não precisamos lembrar de recalculá-los quando os resultados mudam (eles não podem mudar, o relatório está congelado, mas o princípio permanece).
- Um teste pode construir um relatório com um conjunto sintético de resultados e perguntar imediatamente `report.score`, sem necessidade de encanamento extra.

### 2.4 Os tipos `Severity` e `Status`

Estes são **tipos Literal**:

```python
Severity = Literal["high", "medium", "low"]
Status = Literal["ok", "weak", "missing"]
```

Um tipo `Literal` diz ao verificador de tipos "isso é uma string, mas só pode ser um destes valores exatos". Por que se preocupar? Dois motivos:

1. **Proteção contra erros de digitação.** Se você escrever `severity = "hgih"` em algum lugar, o mypy detecta antes mesmo de você rodar o código. Sem `Literal`, o tipo seria apenas `str` e qualquer erro de digitação passaria.
2. **Documentação.** Apenas olhando para a assinatura do tipo você conhece os valores legais. Você não precisa fazer um grep no código para descobrir.

Poderíamos ter usado um `Enum`. O guia de estilo do Carter prefere `Literal` para pequenos conjuntos fixos porque mantém os valores como strings simples (fáceis de imprimir, fáceis de registrar em log, fáceis de usar como chaves de dicionário).

## 3. Separação de camadas: a barreira de I/O

A decisão arquitetural mais importante neste projeto é a **barreira entre o código que toca a rede e o código que não toca**. Vamos rastreá-la.

```
┌─────────────────────────────────────────────────────────────────────┐
│  A CAMADA DE I/O                                                    │
│  - scan()                       (chama httpx.get, acessa a rede)    │
│  - main()                       (lê sys.argv, chama scan)           │
│  - _render_report()             (escreve no terminal)               │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                │  passa um dict[str, str] ou um ScanReport
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  A CAMADA PURA                                                      │
│  - evaluate_header(rule, headers) -> HeaderFinding                  │
│  - ScanReport.score property                                        │
│  - ScanReport.grade property                                        │
│  - lista RULES, dict SEVERITY_POINTS                                │
└─────────────────────────────────────────────────────────────────────┘
```

Tudo na **camada pura**:

- Recebe entradas.
- Retorna saídas.
- Não toca na rede. Não toca no sistema de arquivos. Não imprime nada.

Tudo na **camada de I/O**:

- Fala com o mundo externo.
- Eventualmente passa seus resultados para a camada pura.

Por que isso importa: a camada pura é **trivialmente testável**. Você constrói as entradas manualmente, você verifica as saídas. Não é necessário fazer mocking. A camada de I/O é mais difícil de testar (você tem que simular a rede ou o terminal), mas também é a parte menor. A maioria dos bugs em um scanner está na matemática, não na chamada ao httpx. Colocar a matemática em uma função pura significa que você testa a matemática com confiança e o código de rede com apenas alguns testes de fumaça (smoke tests).

Isso às vezes é chamado de **núcleo funcional, casca imperativa** (functional core, imperative shell). Termo cunhado por Gary Bernhardt. Mesma ideia: mantenha a parte que decide o que fazer pura, empurre a parte que realmente faz para as bordas.

## 4. O fluxo de dados, de ponta a ponta

Vamos rastrear um scan do terminal até a saída. O usuário digita:

```
$ just run -- https://github.com
```

```
1. SHELL → main()
   ─────────────────────────────────────────────────────
   `just run` chama `uv run headers https://github.com`.
   `uv run` ativa o venv, executa `headers` que está
   declarado no pyproject.toml como o ponto de entrada que
   mapeia para http_headers_scanner:main.
   sys.argv agora é ["headers", "https://github.com"].

2. main() → _build_argument_parser()
   ─────────────────────────────────────────────────────
   Construímos um parser argparse, adicionamos o argumento `url`
   e a opção `--timeout`, então chamamos parse_args().
   Resultado: args.url = "https://github.com", args.timeout = 10.0

3. main() → scan(url, timeout)
   ─────────────────────────────────────────────────────
   scan() chama httpx.get() com follow_redirects=True
   e um User-Agent customizado. httpx faz o DNS, abre uma
   conexão TCP, negocia o TLS, envia a requisição GET,
   lê a resposta, segue quaisquer redirecionamentos. Retorna um
   objeto Response.

4. scan() → response_headers (um dict[str, str])
   ─────────────────────────────────────────────────────
   Convertemos o objeto Headers do httpx para um dict simples.
   Este é o momento de "sair do mundo de I/O, entrar no mundo
   puro". Após este ponto, nada sabe ou se importa com o httpx.

5. scan() → [evaluate_header(rule, headers) for rule in RULES]
   ─────────────────────────────────────────────────────
   Uma list comprehension. Executa evaluate_header() uma vez para
   cada uma das seis regras. Cada chamada é pura: ela busca
   o cabeçalho no dict (insensível a maiúsculas), verifica
   must_match (via re.search, insensível a maiúsculas) se configurado,
   retorna um HeaderFinding.

6. scan() → ScanReport
   ─────────────────────────────────────────────────────
   Agrupa a URL, URL final, código de status e resultados
   em um ScanReport congelado. scan() está concluído.

7. main() → _render_report(report, console)
   ─────────────────────────────────────────────────────
   O renderizador constrói uma Table do rich, adiciona uma linha por
   resultado, imprime-a. Então constrói o Panel da nota,
   imprime-o. Então itera sobre os resultados que não são ok e
   imprime suas recomendações.

8. main() → código de saída
   ─────────────────────────────────────────────────────
   Olha para report.grade. A ou B → retorna 0 (sucesso).
   C ou D → retorna 1 (aviso). F ou erro de rede → 2.
   sys.exit(main()) envia o código para o shell.
```

O ponto principal a notar: os passos 5 e 6 são puros. Se você quiser escrever um teste que exercite a lógica de pontuação e resultados, você pula o passo 3 inteiramente e chama `evaluate_header()` diretamente com entradas construídas manualmente. É exatamente isso que o `test_http_headers_scanner.py` faz.

## 5. Por que cada função tem o tamanho que tem

Uma pergunta comum para iniciantes: como saber quando dividir um pedaço de código em uma nova função?

Uma regra prática útil: **uma tarefa por função**. Se você consegue descrever o que uma função faz em uma frase sem usar "e", ela provavelmente está no tamanho certo. Se você tiver que dizer "isso busca a URL E analisa os cabeçalhos E avalia-os E imprime a tabela", ela é grande demais.

Olhe para nossas funções através dessa lente:

- **`evaluate_header()`**: "Aplica uma regra a um conjunto de cabeçalhos e retorna um resultado." Uma tarefa.
- **`scan()`**: "Busca uma URL e retorna um relatório." Uma tarefa. Ela também chama `evaluate_header()` internamente, mas isso é delegação, não uma segunda tarefa.
- **`_render_report()`**: "Imprime de forma formatada um relatório no terminal." Uma tarefa.
- **`_build_argument_parser()`**: "Constrói o parser argparse." Uma tarefa. Vale a pena separar para que os testes possam chamá-lo sem disparar o main().
- **`main()`**: "Cola os outros pedaços e escolhe um código de saída." Uma tarefa: orquestração.

O prefixo de sublinhado em `_render_report` e `_build_argument_parser` é uma convenção do Python que significa "isso é privado, não faz parte da API pública". Outros códigos no mesmo arquivo ainda podem chamá-los, mas qualquer pessoa importando o módulo deve considerá-los internos.

## 6. A única fonte de verdade: a lista `RULES`

Observe que `RULES` é definida uma vez, no topo do arquivo, como uma lista de objetos `HeaderRule`. As funções de pontuação, a função de avaliação e o renderizador percorrem essa lista em tempo de execução. Nenhum deles tem conhecimento fixo (hardcoded) de quais cabeçalhos existem.

O que isso nos garante: **adicionar um sétimo cabeçalho para verificar é uma mudança de uma linha**. Anexe um `HeaderRule` à lista. O scanner o reconhece automaticamente. A suíte de testes o reconhece automaticamente (o auxiliar de relatório sintético usa `RULES` diretamente). Nenhum código no `scan()`, na renderização ou na pontuação precisa mudar.

Isso é o que as pessoas querem dizer quando falam em código "orientado a dados" (data driven). O comportamento é determinado pelos dados (a tabela de regras), não por lógica fixa por caso. É também um dos padrões mais fáceis de reconhecer quando você começa a procurá-lo.

O mesmo padrão, com os mesmos benefícios, aparece em scanners de produção reais:

- Nuclei (um scanner de vulnerabilidades) lê templates YAML que se parecem muito com o nosso HeaderRule, apenas maiores.
- Plugins do ESLint são majoritariamente tabelas de regras.
- Scripts NSE do Nmap são arquivos de regras individuais em um diretório.

## 7. Por que usamos httpx, não requests

`requests` é a famosa biblioteca HTTP do Python. `httpx` é a mais nova. Elas possuem APIs muito semelhantes. Escolhemos o httpx porque:

- **Dicas de tipo de primeira classe.** O mypy entende o httpx nativamente. O requests ainda exige stubs `types-requests`.
- **Suporte a HTTP/2.** Sites mais novos falam HTTP/2 por padrão. O requests é apenas HTTP/1.1.
- **Pronto para async.** O httpx tem uma API síncrona (o que usamos) e uma API assíncrona para quando você evoluir.
- **Manutenção ativa.** O requests está em modo de manutenção. O httpx é onde o novo desenvolvimento acontece.

Para este projeto, usamos apenas a API síncrona. A API assíncrona nos permitiria escanear muitas URLs em paralelo, o que é um ótimo desafio de extensão em `04-Desafios.md`.

## 8. Por que usamos respx para testes

Quando você escreve um teste que chama `scan("https://example.com")`, você tem um problema: o teste agora depende de o example.com estar acessível, rápido e retornando cabeçalhos previsíveis. Nada disso é garantido. O teste seria **flaky** (às vezes passa, às vezes falha, por razões não relacionadas ao seu código).

O `respx` resolve isso interceptando cada chamada httpx dentro de um teste e retornando o que você configurar. Esquematicamente:

```
   Código de Teste       respx (interceptador)       A internet real
   ─────────             ───────────────────         ─────────────────
   respx.get(URL).mock(   intercepta httpx.get,
       return_value=...   nunca envia um pacote,
   )                      devolve o objeto fake
   scan(URL)         ───▶ Response               ──╳  nunca alcançada
```

Um teste usando respx é rápido (sem rede), determinístico (a resposta falsa é exatamente o que você configurou) e amigável para uso offline. O custo é que você deve ser cuidadoso: o `respx` intercepta apenas o httpx, então um scan que usasse `requests` internamente ignoraria silenciosamente o mock.

## 9. Filosofia de tratamento de erros

Duas camadas de tratamento de erros.

No `scan()`, nós **deixamos os erros se propagarem**. Se o DNS falhar, se o host recusar a conexão, se a requisição expirar (timeout), o httpx lança uma exceção. Nós não a capturamos. O trabalho da função é buscar e avaliar, não decidir o que fazer quando a busca falha.

No `main()`, nós **capturamos `httpx.RequestError` uma vez** e o transformamos em uma mensagem limpa mais o código de saída 2. O usuário não precisa ver um traceback Python de 30 linhas para "não foi possível conectar". Ele precisa ver "a requisição falhou".

Este é um padrão que vale a pena internalizar: **o código da biblioteca deixa os erros borbulharem, o código da CLI os traduz em uma saída amigável para o usuário.** O autor da biblioteca não sabe em que contexto a biblioteca está sendo chamada, então não deve fingir que sabe como tratar os erros. O autor da CLI sabe exatamente em que contexto a chamada está sendo feita (um usuário digitou um comando), então pode apresentar os erros apropriadamente.

## 10. Códigos de saída que significam algo

A maioria das CLIs retorna código de saída 0 para sucesso e 1 para qualquer tipo de falha. Nosso scanner usa três:

```
0 → nota A ou B   (CI: verde, nenhuma ação necessária)
1 → nota C ou D   (CI: amarelo, vale a pena investigar)
2 → nota F ou erro de rede  (CI: vermelho, deve corrigir)
```

Isso é útil quando você integra o scanner no CI. Um pipeline pode executar:

```
just run -- https://meu-site-implantado.com
if [ $? -gt 1 ]; then exit 1; fi   # falha o build apenas em F ou erro
```

Você pode decidir por si mesmo qual limite conta como "falha no build". O ponto é que o scanner te dá a informação para decidir. Um código de saída binário de sucesso/falha descarta muitos detalhes.

## 11. O que NÃO pertence a esta arquitetura

Para um projeto de fundamentos, deliberadamente deixamos coisas de fora:

- **Sem async.** Uma única URL não precisa disso. A API síncrona é mais fácil de ler.
- **Sem subcomandos.** Nada de `headers scan`, `headers explain`, `headers config`. Apenas uma tarefa, execute-a.
- **Sem arquivo de configuração.** Todas as configurações vêm de flags da CLI. Nada de `~/.config/headers.toml`. Adicione um se você o estender.
- **Sem banco de dados.** Cada execução é independente. Sem histórico. Adicione um se quiser tendências ao longo do tempo (o arquivo de desafios tem detalhes).
- **Sem sistema de plugins.** A tabela de regras é apenas uma lista. Para "estender" o scanner, você edita a lista.

Essas são todas coisas que um scanner mais maduro teria, e cada uma delas é uma ótima ideia de extensão. Nenhuma delas pertence a um projeto cujo objetivo é "ser a menor coisa possível que ensina a ideia central".

## 12. Referência dos arquivos principais

Um mapa rápido do projeto:

| Caminho                        | O que contém                                                                                         |
| ------------------------------ | ---------------------------------------------------------------------------------------------------- |
| `http_headers_scanner.py`      | Todo o scanner. Regras, avaliação, scan, CLI.                                                        |
| `test_http_headers_scanner.py` | Todos os testes. Usa pytest e respx.                                                                 |
| `pyproject.toml`               | Metadados do projeto, dependências, configurações de ferramentas (ruff, mypy, pylint, yapf, pytest). |
| `uv.lock`                      | Versões exatas de cada dependência transitiva. Builds reproduzíveis.                                 |
| `justfile`                     | Comandos de atalho: `just test`, `just lint`, `just run`.                                            |
| `install.sh`                   | Instalador de um passo para novos clones.                                                            |
| `learn/`                       | A documentação que você está lendo.                                                                  |

## Próximo

Siga para **[03-Implementação.md](./03-Implementação.md)** para o passo a passo linha por linha, ou pule para **[04-Desafios.md](./04-Desafios.md)** para ideias de extensão.
