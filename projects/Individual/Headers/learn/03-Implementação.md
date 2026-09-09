# Passo a Passo da Implementação

Este arquivo percorre o código real em `http_headers_scanner.py` (e um pouco de `test_http_headers_scanner.py`) linha por linha. Ao final, você deverá entender cada parte do arquivo: o que ela faz, por que está lá e o que quebraria se você a removesse.

Este é o arquivo mais longo na pasta learn. Leia-o em partes. A ordem abaixo corresponde à ordem em que as coisas aparecem no código-fonte.

## 0. Convenções de leitura

Cada seção nomeia uma função, classe ou constante de `http_headers_scanner.py`. Abra o arquivo em seu editor ao lado e procure pelo nome. Os trechos de código neste guia são reais, copiados diretamente do arquivo, mas o arquivo também é curto o suficiente para que você possa percorrê-lo inteiro em algumas páginas.

## 1. A docstring do arquivo

O arquivo começa com uma longa string entre aspas triplas. Em Python, uma string no topo de um arquivo é chamada de **docstring do módulo**. É o lugar oficial para explicar do que se trata o arquivo.

```python
"""
©AngelaMos | 2026
Copyright (C) 2026 Murilo Miacci
http_headers_scanner.py

Scan a URL and grade its HTTP security headers A–F

When a browser asks a website for a page, the server sends back the
page itself PLUS a bunch of metadata called "HTTP response headers."
...
"""
```

Algumas coisas para observar:

- **As primeiras três linhas são o cabeçalho padrão de arquivo do projeto.** Cada arquivo no projeto começa desta forma: duas linhas de copyright e o nome do arquivo. A parte `©AngelaMos | 2026` é a marca do projeto, não algo que você veria normalmente em um tutorial genérico de Python.
- **O corpo é excepcionalmente longo para uma docstring.** A maioria dos arquivos tem um resumo de uma linha. Este é detalhado porque é um projeto de ensino. A docstring é a primeira coisa que qualquer leitor vê (`help(http_headers_scanner)` a imprime, IDEs a mostram ao passar o mouse), então a usamos para ensinar.
- **Ela termina com uma lista de "o que este arquivo expõe".** Esta é uma convenção real. Diz aos leitores o que eles podem importar do módulo sem precisar percorrer 600 linhas.

## 2. Importações

```python
import argparse
import re
import sys
from dataclasses import dataclass
from typing import Literal

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
```

A PEP 8 (guia de estilo do Python) recomenda que as importações sejam agrupadas em três seções separadas por linhas em branco:

1. **Biblioteca padrão**: coisas que vêm com o Python. Aqui: `argparse`, `re`, `sys`, `dataclasses`, `typing`.
2. **Terceiros**: coisas que você instalou com `uv` / `pip`. Aqui: `httpx`, `rich`.
3. **Local**: coisas deste mesmo projeto. Não temos nenhuma.

`re` é o módulo de expressões regulares da biblioteca padrão. Usamos `re.search(pattern, value, re.IGNORECASE)` dentro de `evaluate_header()` para verificar se o valor de um cabeçalho corresponde ao padrão exigido por uma regra. Regexes nos dão uma maneira de expressar "max-age deve ser um número inteiro positivo" em uma linha, em vez de termos que analisar a estrutura da diretiva HSTS por conta própria.

Cada módulo é importado com um comentário curto explicando para que o usamos. Iniciantes costumam perguntar "o que o `import` faz?". Resposta curta: ele diz ao Python "vá buscar este módulo e torne seus nomes disponíveis neste arquivo". `import argparse` torna `argparse.ArgumentParser` disponível. `from dataclasses import dataclass` torna o nome `dataclass` disponível para que possamos usar `@dataclass` diretamente sem escrever `@dataclasses.dataclass`.

## 3. Os tipos Severity e Status

```python
Severity = Literal["high", "medium", "low"]
Status = Literal["ok", "weak", "missing"]
```

Estes são **aliases de tipo**. Eles dão um nome amigável a um tipo mais complexo. Em qualquer lugar que você escrever `Severity` de agora em diante, o verificador de tipos lerá `Literal["high", "medium", "low"]`.

A razão pela qual o `Literal` existe: um `str` comum significa "qualquer string". Se anotássemos `severity: str`, então `severity = "hgih"` compilaria normalmente e só daria erro em tempo de execução quando algo tentasse buscá-lo. Com `severity: Severity`, o mypy se recusa a deixar `"hgih"` chegar perto do campo. O erro de digitação é capturado no momento da edição.

Isso é mais disciplina do que a maioria dos códigos Python para iniciantes que você verá online. É uma escolha deliberada para um projeto de ensino: queremos que você absorva o hábito cedo.

## 4. Dataclass `HeaderRule`

```python
@dataclass(frozen=True, slots=True)
class HeaderRule:
    header: str
    severity: Severity
    description: str
    recommendation: str
    must_match: str | None = None
```

Uma dataclass é uma classe comum que tem as partes chatas (construtor, igualdade, representação de string) escritas para você pelo decorador `@dataclass`. Cobrimos as flags `frozen` e `slots` em `02-ARCHITECTURE.md`. A versão curta: `frozen` impede que qualquer pessoa modifique os campos após a construção, `slots` torna as instâncias menores na memória.

Os campos:

- **`header`**: o nome do cabeçalho HTTP que estamos procurando. Armazenado com a grafia canônica (ex: `"Strict-Transport-Security"`), mas comparado de forma insensível a maiúsculas no momento da busca.
- **`severity`**: define a pontuação. `"high"` = 30 pontos, `"medium"` = 15, `"low"` = 5.
- **`description`**: uma frase explicando o cabeçalho. Atualmente usada para documentação; poderíamos também renderizá-la na tabela.
- **`recommendation`**: o que adicionar para corrigir um cabeçalho ausente ou fraco. Exibido na seção "Recommendations" na parte inferior da saída.
- **`must_match`**: opcional. Um padrão regex que o valor deve corresponder (insensível a maiúsculas) para ser considerado `ok`. Para HSTS, o padrão é `r"max-age\s*=\s*[1-9]"` (rejeita `max-age=0`); para `X-Content-Type-Options`, é `"nosniff"` (uma palavra simples funciona como uma correspondência de substring sob `re.search`). Se for `None`, a presença por si só é suficiente.

O `= None` final em `must_match` é seu **valor padrão**. Significa que você pode construir um `HeaderRule` sem especificá-lo. Apenas campos com valores padrão podem ser omitidos no momento da construção.

## 5. A tabela `RULES`

```python
RULES: list[HeaderRule] = [
    HeaderRule(
        header="Strict-Transport-Security",
        severity="high",
        ...
        must_match=r"max-age\s*=\s*[1-9]",
    ),
    HeaderRule(
        header="Content-Security-Policy",
        severity="high",
        ...
    ),
    ...
]
```

Esta é a **única fonte de verdade** para quais cabeçalhos verificamos. O padrão de lista de dataclasses é um dos mais úteis em Python: cada entrada é estruturada, imutável e fácil de adicionar.

Um detalhe do padrão: usamos **argumentos nomeados** (keyword arguments) para cada campo, não posicionais. Escrevemos `HeaderRule(header="...", severity="...", ...)`, não `HeaderRule("...", "...", ...)`. Por quê? Duas razões:

1. **Legibilidade.** Quando alguém lê o código, vê `severity="high"` e sabe exatamente o que o segundo valor significa. O posicional `("Strict-Transport-Security", "high", ...)` obriga a contar os campos.
2. **Segurança na refatoração.** Se você adicionar um novo campo depois (digamos `references: list[str]`), chamadas posicionais podem colocar o novo valor no lugar errado. Chamadas nomeadas são inequívocas.

Por que esta lista está no nível do módulo e não dentro de uma função? Porque ela nunca muda. Construí-la uma vez no momento da importação é mais barato do que reconstruí-la em cada scan. Ela também é acessível para a suíte de testes (`from http_headers_scanner import RULES`).

## 6. Mapeamento `SEVERITY_POINTS`

```python
SEVERITY_POINTS: dict[Severity, int] = {
    "high": 30,
    "medium": 15,
    "low": 5,
}
```

Um dicionário mapeando cada severidade para seu valor em pontos. Observe a anotação de tipo: `dict[Severity, int]`. Isso diz ao verificador de tipos "as chaves devem ser `"high"` / `"medium"` / `"low"`, os valores devem ser inteiros". Se você tentasse adicionar `"critical": 50` a este dicionário, o mypy recusaria: `"critical"` não está no tipo Literal `Severity`.

Por que um dicionário e não uma função com três declarações if? Porque são dados, não lógica. Código orientado a dados é mais fácil de estender (adicione outra severidade, edite uma linha) e mais fácil de testar (você pode afirmar os valores exatos de pontos).

## 7. Dataclass `HeaderFinding`

```python
@dataclass(frozen=True, slots=True)
class HeaderFinding:
    rule: HeaderRule
    status: Status
    actual_value: str | None
    note: str
```

Um resultado (finding) é o resultado da avaliação de uma regra contra uma resposta. Ele carrega:

- **`rule`**: a regra que foi avaliada. Armazenar a regra inteira dentro do resultado (em vez de apenas seu nome) significa que o renderizador nunca precisa fazer uma segunda busca para saber a severidade ou recomendação.
- **`status`**: um entre `"ok"`, `"weak"`, `"missing"`. O tipo Literal captura erros de digitação.
- **`actual_value`**: o que o servidor realmente enviou. `None` se o cabeçalho estiver ausente.
- **`note`**: uma string curta amigável para humanos. Exibida na tabela.

Por que `actual_value` é do tipo `str | None`? Porque o campo genuinamente às vezes é uma string e às vezes nada. `None` é a maneira do Python dizer "sem valor". O tipo `str | None` torna isso explícito. Em qualquer lugar que você usar `finding.actual_value`, o verificador de tipos força você a lidar com o caso None ou afirmar que ele não pode ser None.

A sintaxe `|` (ex: `str | None`) é a forma moderna (Python 3.10+). A forma antiga era `Optional[str]` do módulo `typing`. Ambas funcionam; a nova sintaxe é mais curta.

## 8. Dataclass `ScanReport` com propriedades computadas

```python
@dataclass(frozen=True, slots=True)
class ScanReport:
    url: str
    final_url: str
    status_code: int
    findings: list[HeaderFinding]

    @property
    def score(self) -> int:
        ...

    @property
    def grade(self) -> str:
        ...
```

Um relatório tem quatro campos armazenados mais duas propriedades computadas.

### 8.1 Por que `final_url` é separado de `url`

`url` é o que o usuário digitou. `final_url` é onde ele terminou após os redirecionamentos. Eles são frequentemente os mesmos. Eles são diferentes quando, por exemplo, `http://example.com/` redireciona para `https://example.com/`. Rastreamos ambos porque:

- O usuário quer ver a URL que digitou reconhecida na saída.
- A nota realmente pertence à URL final (o destino redirecionado é o que o navegador realmente mostra).

### 8.2 A propriedade `score`

```python
@property
def score(self) -> int:
    total = sum(SEVERITY_POINTS[r.severity] for r in RULES)
    if total == 0:
        return 0

    earned = 0.0
    for finding in self.findings:
        full = SEVERITY_POINTS[finding.rule.severity]
        if finding.status == "ok":
            earned += full
        elif finding.status == "weak":
            earned += full / 2

    return int((earned / total) * 100 + 0.5)
```

Passo a passo:

1. **`@property`** na linha acima transforma o método em algo que você acessa sem parênteses. `report.score`, não `report.score()`. Parece um campo, computado sob demanda.
2. **`total = sum(SEVERITY_POINTS[r.severity] for r in RULES)`** calcula o total de pontos alcançáveis percorrendo as regras. A expressão dentro de `sum(...)` é uma **expressão geradora**: ela produz um número por regra (o valor de pontos para a severidade daquela regra), então o sum os soma. Com as regras atuais de 2-altas, 2-médias, 2-baixas, total = 100.
3. **`if total == 0: return 0`** é uma proteção. Se alguém deletasse a tabela de regras em tempo de execução, caso contrário, dividiríamos por zero. Retornar zero é uma resposta segura.
4. **O loop principal** percorre cada resultado. Para cada um, busca o valor total de pontos para a severidade de sua regra. Se o status for `ok`, adiciona os pontos totais. Se for `weak`, adiciona metade. Se for `missing`, não adiciona nada (não há ramificação explícita; a variável permanece inalterada).
5. **`int((earned / total) * 100 + 0.5)`** é a pontuação final. O `+ 0.5` seguido de `int(...)` é um arredondamento manual para cima. Usamos isso porque o `round()` nativo do Python usa arredondamento bancário (arredonda o meio para o par mais próximo), o que mapearia `round(0.5)` para `0` e `round(2.5)` para `2`. Matematicamente defensável (cancela o viés em uma amostra grande), mas surpreendente no limite de `.5`, onde uma pontuação deve sempre arredondar para cima. `int(x + 0.5)` é o formato que todos esperam.

### 8.3 A propriedade `grade`

```python
@property
def grade(self) -> str:
    score = self.score
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"
```

Observe que cada ramificação retorna (`return`) diretamente, portanto não há `elif`s nem um `else` final. Este é um idioma comum chamado **retorno antecipado** (early return). A função é lida de cima para baixo: assim que uma condição coincide, você terminou. Isso também evita o "código em flecha" onde cada ramificação é mais indentada que a anterior.

Observe também que **chamamos `self.score` uma vez**, armazenamos o resultado e depois o comparamos cinco vezes. Se escrevêssemos `if self.score >= 90:` etc., a propriedade seria executada novamente a cada vez. Para uma função de pontuação minúscula não importaria, mas o hábito de fazer cache de buscas repetidas e caras vale a pena ser formado cedo.

## 9. `evaluate_header()`: o coração do scanner

Esta é a **função pura** no centro de tudo. Sem rede. Sem impressões. Apenas regra mais cabeçalhos entram, resultado sai.

```python
def evaluate_header(
    rule: HeaderRule,
    response_headers: dict[str, str],
) -> HeaderFinding:
    target = rule.header.lower()

    actual_value: str | None = None
    for name, value in response_headers.items():
        if name.lower() == target:
            actual_value = value
            break

    if actual_value is None:
        return HeaderFinding(
            rule=rule,
            status="missing",
            actual_value=None,
            note=f"Header `{rule.header}` is not set",
        )

    if rule.must_match is None:
        return HeaderFinding(
            rule=rule,
            status="ok",
            actual_value=actual_value,
            note="Present",
        )

    if re.search(rule.must_match, actual_value, re.IGNORECASE):
        return HeaderFinding(
            rule=rule,
            status="ok",
            actual_value=actual_value,
            note=f"Present and matches `{rule.must_match}`",
        )

    return HeaderFinding(
        rule=rule,
        status="weak",
        actual_value=actual_value,
        note=(
            f"Present but does not match `{rule.must_match}` "
            f"(got `{actual_value}`)"
        ),
    )
```

Três ramificações, em ordem:

1. **Ausente.** Percorremos os cabeçalhos da resposta, convertemos cada nome para minúsculas e comparamos com o alvo em minúsculas. Se nunca encontrarmos uma correspondência, `actual_value` permanece `None` e retornamos um resultado `missing`.
2. **Presente, sem verificação de must_match.** Se a regra não exigir um padrão específico, a presença por si só é suficiente. Retorna `ok`.
3. **Presente, com verificação de must_match.** Se a regra tiver um `must_match`, executa `re.search(pattern, value, re.IGNORECASE)`. Uma palavra simples como `"nosniff"` funciona como uma verificação de substring; um padrão mais rico como `r"max-age\s*=\s*[1-9]"` impõe uma condição real (HSTS deve ser definido como um inteiro positivo, não o ativamente prejudicial `max-age=0`). Se o padrão coincidir, `ok`. Se não, `weak`.

Algumas coisas que valem a pena destacar:

**A busca insensível a maiúsculas.** Os nomes dos cabeçalhos HTTP são insensíveis a maiúsculas conforme a RFC 7230. Diferentes servidores os retornam com diferentes grafias. Alguns retornam `Strict-Transport-Security`, outros `strict-transport-security`, alguns até `STRICT-TRANSPORT-SECURITY` (raro, mas legal). Converter ambos os lados para minúsculas é a maneira portátil mais simples de lidar com isso.

Poderíamos ter usado um dicionário insensível a maiúsculas (o httpx retorna um), mas a função deve aceitar um dicionário comum para fins de teste. Na prática, `scan()` já converte os cabeçalhos da resposta para um `dict[str, str]` comum antes de chamar `evaluate_header`, então esta função nunca vê um objeto `httpx.Headers` diretamente — mas o contrato é "qualquer `dict[str, str]` funciona", o que torna as entradas de teste construídas manualmente triviais.

**Por que usamos `break` para sair do loop cedo.** Uma vez que encontramos o cabeçalho, temos o que precisamos. Continuar o loop desperdiçaria CPU.

**As f-strings em `note`.** Uma f-string é uma string com espaços reservados `{expressão}` que são preenchidos em tempo de execução. `f"Header `{rule.header}` is not set"` torna-se `Header `Strict-Transport-Security` is not set` se o cabeçalho da regra for HSTS. As crases ao redor do nome do cabeçalho fazem com que ele pareça monoespaçado se o renderizador for compatível com markdown, e geralmente ajudam a visualização.

**Sem ramificações else.** Cada ramificação retorna. Uma vez que você retorna, a função termina. Não há necessidade de escrever `elif` ou `else`. Este é o mesmo padrão de retorno antecipado da propriedade `grade`.

## 10. `scan()`: a chamada de rede

```python
DEFAULT_USER_AGENT: str = (
    "http-headers-scanner/1.0 "
    "(+https://github.com/CarterPerez-dev/Cybersecurity-Projects)"
)


def scan(
    url: str,
    *,
    timeout: float = 10.0,
    user_agent: str = DEFAULT_USER_AGENT,
) -> ScanReport:
    response = httpx.get(
        url,
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": user_agent},
    )

    response_headers = dict(response.headers)
    findings = [evaluate_header(rule, response_headers) for rule in RULES]

    return ScanReport(
        url=url,
        final_url=str(response.url),
        status_code=response.status_code,
        findings=findings,
    )
```

### 10.1 O User-Agent

A string User-Agent identifica quem está fazendo a requisição. Navegadores enviam coisas como `Mozilla/5.0 (X11; Linux x86_64) ...`. Nosso scanner envia `http-headers-scanner/1.0 (+https://...)`. Isso é educado por duas razões:

- Operadores de servidor que leem seus logs de acesso podem saber quem os está acessando e verificar a página do nosso projeto se quiserem saber o porquê.
- Alguns sites bloqueiam o UA padrão do httpx. Um UA personalizado tem mais chances de obter uma resposta real.

### 10.2 O `*,` na assinatura

```python
def scan(
    url: str,
    *,
    timeout: float = 10.0,
    user_agent: str = DEFAULT_USER_AGENT,
) -> ScanReport:
```

O `*,` entre `url` e `timeout` força os chamadores a passar `timeout` e `user_agent` por nome. Você não pode chamar `scan("https://example.com", 5.0)`. Você deve chamar `scan("https://example.com", timeout=5.0)`.

Por que forçar isso? Porque `5.0` não significa obviamente "cinco segundos de timeout" quando você lê o local da chamada. `timeout=5.0` significa. Argumentos apenas nomeados tornam os locais de chamada mais legíveis e seguros para refatoração. O custo é exatamente um caractere extra (`timeout=`) ao chamar a função.

### 10.3 `follow_redirects=True`

Quando o servidor diz "esta URL mudou, tente esta outra", seguimos o redirecionamento automaticamente. Muitos sites redirecionam `http://` para `https://` ou `www.` para o domínio puro. O usuário digitou uma URL, mas seu navegador terminaria em uma diferente. Queremos avaliar aquela que o navegador realmente veria.

### 10.4 A passagem para a camada pura

```python
response_headers = dict(response.headers)
findings = [evaluate_header(rule, response_headers) for rule in RULES]
```

Estas duas linhas são a passagem "saia do mundo de I/O, entre no mundo puro" de que falamos no arquivo de arquitetura. `dict(response.headers)` converte o objeto Headers do httpx em um dicionário comum. A compreensão de lista na linha seguinte executa `evaluate_header()` para cada regra.

Uma **compreensão de lista** (list comprehension) é um atalho para "criar uma lista executando uma expressão sobre cada item em uma fonte". O loop for equivalente seria:

```python
findings = []
for rule in RULES:
    findings.append(evaluate_header(rule, response_headers))
```

Mesmo resultado, mais linhas. A compreensão é preferida quando o corpo é uma única expressão.

## 11. Renderização

```python
STATUS_COLORS: dict[Status, str] = {
    "ok": "green",
    "weak": "yellow",
    "missing": "red",
}

GRADE_COLORS: dict[str, str] = {
    "A": "bright_green",
    "B": "green",
    "C": "yellow",
    "D": "red",
    "F": "bright_red",
}


def _render_report(report: ScanReport, console: Console) -> None:
    table = Table(...)
    table.add_column(...)
    ...
    for finding in report.findings:
        status_color = STATUS_COLORS[finding.status]
        table.add_row(...)
    console.print(table)

    if report.final_url.startswith("http://"):
        console.print(
            "[yellow]Note:[/yellow] this response was served over plain "
            "HTTP. Browsers IGNORE HSTS over HTTP, ..."
        )

    grade_color = GRADE_COLORS[report.grade]
    panel = Panel(...)
    console.print(panel)

    actionable = [f for f in report.findings if f.status != "ok"]
    if actionable:
        console.print("\n[bold]Recommendations:[/bold]")
        for finding in actionable:
            console.print(...)
```

O renderizador usa o **rich**, uma biblioteca de terceiros para saídas bonitas no terminal. Os padrões:

- **Um objeto `Table`** com colunas. Você adiciona linhas uma de cada vez. `console.print(table)` a desenha como uma tabela com bordas Unicode.
- **`[green]algo[/green]`** é a sintaxe de marcação do rich. É aproximadamente como HTML para cores de terminal. `[bold cyan]Result[/bold cyan]` renderizaria "Result" em ciano negrito.
- **`Panel(...)`** envolve o conteúdo em uma caixa com bordas.

O renderizador é intencionalmente separado de `scan()` e `evaluate_header()`. O código puro não sabe nem se importa com cores. Se algum dia quisermos um modo de saída JSON para CI, adicionamos um segundo renderizador (`_render_json(report)`) e mantemos todo o outro código inalterado.

A linha `actionable = [f for f in report.findings if f.status != "ok"]` é outra compreensão: cria uma lista de cada resultado cujo status não seja `ok`. Estes são aqueles para os quais temos recomendações. Se a lista estiver vazia (pontuação perfeita), pulamos a seção inteira.

**O aviso de HTTP.** Logo após a tabela, verificamos `report.final_url.startswith("http://")`. Conforme a RFC 6797 §8.1, os navegadores DEVEM IGNORAR o cabeçalho `Strict-Transport-Security` quando ele chega via HTTP comum — apenas o HSTS recebido via HTTPS conta. Portanto, se um usuário apontar o scanner para `http://example.com` e o servidor retornar HSTS, esse HSTS ganha crédito total em nossa avaliação, embora nenhum navegador real o honre. A nota amarela torna a ressalva visível no único lugar que importa: o relatório voltado para o usuário. Não alteramos a lógica de avaliação — uma regra, um resultado — mas o usuário vê uma linha honesta de "esta nota é enganosa até que o site imponha HTTPS" logo ao lado da pontuação.

## 12. O encanamento do argparse

```python
def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="headers",
        description="Scan a URL for HTTP security headers and grade the result A–F.",
    )
    parser.add_argument(
        "url",
        help="Full URL to scan (must include http:// or https://).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Seconds to wait before giving up on the request (default: 10).",
    )
    return parser
```

**argparse** é o analisador de argumentos de linha de comando da biblioteca padrão. Você declara o que seu programa aceita, o argparse cuida do resto: análise, conversão de tipo, geração de saída `--help`, rejeição de entradas ruins.

Dois argumentos declarados:

- **`url`**: posicional (sem prefixo `--`). Obrigatório. Se o usuário não o fornecer, o argparse gera um erro e imprime o uso automaticamente.
- **`--timeout`**: opcional. O padrão é `10.0`. `type=float` diz ao argparse para converter a string `"5"` no float `5.0`.

A função é intencionalmente separada de `main()` para que os testes possam construir o analisador e chamar `parse_args([...])` em uma lista sintética, sem ter que mexer com `sys.argv`.

## 13. `main()`: orquestração

```python
def main() -> int:
    parser = _build_argument_parser()
    args = parser.parse_args()
    console = Console()

    try:
        report = scan(args.url, timeout=args.timeout)
    except httpx.RequestError as exc:
        console.print(f"[red]Request failed:[/red] {type(exc).__name__}: {exc}")
        return 2

    _render_report(report, console)

    if report.grade in ("A", "B"):
        return 0
    if report.grade in ("C", "D"):
        return 1
    return 2
```

Esta função é pequena de propósito. Seu trabalho é ser a cola. Passos:

1. Constrói o analisador argparse. `parse_args()` sem argumento lê `sys.argv` implicitamente.
2. Cria um `Console` (objeto principal do rich para impressão).
3. Tenta escanear. Se um `httpx.RequestError` (o pai de todo erro relacionado à rede) for lançado, imprime uma mensagem limpa e retorna o código de saída 2.
4. Renderiza o relatório.
5. Escolhe um código de saída baseado na nota.

O `try / except` aqui é o **único** lugar onde capturamos erros de rede. Deixamos que eles se propaguem de `httpx.get()` através de `scan()` até `main()`. O motivo: funções de nível inferior não podem saber o que fazer com erros. A CLI sabe o que fazer (mostrar ao usuário, sair). A CLI é a camada correta para capturar.

`type(exc).__name__` é "o nome da classe da exceção como uma string". Para um timeout de conexão, seria `ConnectTimeout`. Para falha de DNS, `ConnectError`. Incluir isso na saída dá ao usuário uma pista sobre o que deu errado sem despejar um traceback completo.

## 14. O ponto de entrada do script

```python
if __name__ == "__main__":
    sys.exit(main())
```

Este padrão aparece em todo script Python. Significa "se este arquivo foi invocado diretamente (não importado como um módulo), execute o main".

Quando você executa `python http_headers_scanner.py`, o Python define uma variável especial `__name__` como `"__main__"`. Quando algum outro código faz `import http_headers_scanner`, `__name__` é definido como `"http_headers_scanner"`.

Portanto, `if __name__ == "__main__":` significa "apenas quando estiver rodando como um script, não quando estiver sendo importado". Os testes importam o arquivo, então eles precisam que o `main()` NÃO seja executado automaticamente.

`sys.exit(main())` chama o main e então passa seu valor de retorno (0, 1 ou 2) para o sistema operacional como o código de saída.

## 15. Passo a passo do arquivo de teste

Os testes vivem em `test_http_headers_scanner.py`. Não passaremos por cada linha, mas aqui estão os padrões principais.

### 15.1 Fixtures

```python
@pytest.fixture
def hsts_rule() -> HeaderRule:
    return HeaderRule(
        header="Strict-Transport-Security",
        severity="high",
        ...
        must_match=r"max-age\s*=\s*[1-9]",
    )
```

Uma **fixture** é a maneira do pytest dizer "antes deste teste rodar, configure esta coisa para ele". Qualquer função de teste que tenha um parâmetro chamado `hsts_rule` receberá o que quer que esta fixture retorne. O Pytest faz a correspondência pelo nome.

Usamos fixtures para que a regra seja construída em um só lugar. Se o formato de `HeaderRule` mudar (novo campo adicionado), atualizamos a fixture, não cinco testes diferentes.

### 15.2 Os testes de função pura

```python
def test_evaluate_header_present_with_required_substring(
    hsts_rule: HeaderRule,
) -> None:
    headers = {"Strict-Transport-Security": "max-age=31536000"}
    finding = evaluate_header(hsts_rule, headers)
    assert finding.status == "ok"
    assert finding.actual_value == "max-age=31536000"
```

Cada teste segue o padrão **arrange-act-assert** (organizar-agir-afirmar):

1. **Arrange.** Constrói a entrada. Aqui: um dicionário minúsculo de cabeçalhos.
2. **Act.** Chama a função sob teste.
3. **Assert.** Verifica se o resultado é o que esperávamos.

`assert` é o "isso deve ser verdadeiro ou falhe o teste" do Python. Se `finding.status != "ok"`, o pytest lança um AssertionError e imprime qual era o valor real.

Como `evaluate_header` é pura, estes testes são extremamente simples. Sem mocking, sem configuração além da fixture, sem limpeza (teardown).

### 15.3 Os testes de pontuação e nota

O auxiliar `_make_report` constrói um `ScanReport` sintético emparelhando cada regra com um status. Então o teste pergunta por `report.score` e `report.grade` e afirma que eles são o que esperávamos.

Este é o benefício de tornar `score` e `grade` propriedades de `ScanReport`: podemos testá-los sem executar `scan()`. Apenas construímos as entradas manualmente.

### 15.4 Os testes de scan com mock do respx

```python
@respx.mock
def test_scan_mocks_a_clean_response_and_grades_it_correctly() -> None:
    respx.get("https://safe.example.com/").mock(
        return_value=httpx.Response(
            status_code=200,
            headers={
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                ...
            },
        )
    )

    report = scan("https://safe.example.com/")

    assert report.status_code == 200
    assert report.score == 100
```

O decorador `@respx.mock` acima da função diz ao respx: "durante este teste, intercepte cada chamada httpx e use as rotas que eu configurar abaixo".

`respx.get("https://safe.example.com/").mock(return_value=httpx.Response(...))` diz "quando algo fizer um HTTP GET para essa URL, entregue esta resposta pronta, não vá realmente para a internet".

Então `scan("https://safe.example.com/")` faz o seu trabalho. O httpx tenta buscar a URL; o respx intercepta; a resposta falsa volta; o resto do código nunca percebe a diferença. Fazemos as afirmações sobre a pontuação.

O teste de redirecionamento (`test_scan_records_final_url_after_redirect`) configura duas rotas mockadas: a primeira retorna um 301 para a segunda, a segunda retorna 200. O scanner segue o redirecionamento e afirmamos que `report.final_url` reflete onde terminamos.

## 16. Ferramental: lint, type-check, format

O projeto vem com quatro ferramentas de qualidade configuradas através do `just`:

```
just lint    # executa ruff, depois pylint, depois mypy
just format  # executa yapf no local
just test    # executa pytest
just fix     # executa ruff com --fix (corrige automaticamente o que puder)
```

O que cada ferramenta faz:

- **ruff** é um linter Python rápido. Captura uma longa lista de problemas de estilo e correção. Substituto moderno para o flake8.
- **pylint** é um linter mais lento e opinativo. Captura problemas diferentes do ruff. Executamos ambos porque suas verificações se complementam.
- **mypy** é o verificador estático de tipos. Ele lê as anotações de tipo e verifica cada chamada contra elas. Captura erros de digitação como `severity = "hgih"` e muitos outros bugs no momento da edição.
- **yapf** é o formatador de código. Ele reescreve o arquivo para corresponder a um estilo configurado (limite de colunas, indentação, etc.). Significa que o projeto tem um visual único e consistente, independentemente de quem escreveu cada linha.
- **pytest** é o executor de testes. Descobre arquivos que começam com `test_`, executa cada função neles cujo nome comece com `test_`, relata sucessos e falhas.

Em um fluxo de trabalho real, você configuraria um **pre-commit hook** que executa `just lint` e `just test` antes de cada commit, para que código quebrado nunca seja commitado. Não fizemos isso neste projeto para manter o nível de fundamentos minimalista, mas estendê-lo é um dos desafios.

## 17. O pyproject.toml

`pyproject.toml` é o arquivo de metadados de projeto Python moderno. Ele substitui o antigo combo `setup.py` + `setup.cfg`. Vale a pena dar uma olhada, mesmo que você não o edite no dia a dia.

Seções principais:

- **`[project]`**: nome, versão, descrição, requisito de versão do Python, dependências.
- **`[project.optional-dependencies]`**: dependências de desenvolvimento (pytest, mypy, etc.) que os usuários finais não precisam.
- **`[project.scripts]`**: declara o script de linha de comando `headers`. É por isso que `uv run headers` funciona: ele sabe invocar `http_headers_scanner:main`.
- **`[tool.ruff]`, `[tool.mypy]`, `[tool.pylint.*]`, `[tool.pytest.ini_options]`**: configuração para cada ferramenta. Centralizar a configuração em um arquivo é conveniente.

## 18. Armadilhas comuns ao estender

Algumas coisas que atrapalharam as pessoas ao adicionar novas regras ou recursos:

**Esquecer de atualizar o total da pontuação nos testes.** Atualmente, `RULES` são seis regras totalizando 100 pontos. Se você adicionar uma sétima, o cálculo da pontuação ainda funciona (ele soma o que estiver na lista), mas testes que fixaram a pontuação esperada (ex: "a pontuação deve ser 50 quando metade estiver ausente") podem quebrar. Correção: escreva testes em termos de porcentagens, não contagens absolutas de pontos.

**Adicionar uma regra cuja análise de valor não seja trivial.** Nosso campo `must_match` é uma regex única. Isso é suficiente para "começa com `nosniff`" ou "max-age é um inteiro positivo", mas alguns cabeçalhos reais precisam de uma análise muito mais complexa (CSP, por exemplo, tem sua própria gramática de diretivas, expressões de fonte e nonces). Se sua nova regra precisar de análise estruturada, faça a análise em `evaluate_header()` baseada no nome do cabeçalho da regra, ou estenda `HeaderRule` com um novo campo como `value_validator: Callable[[str], bool] | None`.

**Esquecer a comparação insensível a maiúsculas.** Novo código que fizer `if "X-Frame-Options" in response.headers` perderá servidores que retornam `x-frame-options`. Sempre use minúsculas em ambos os lados para comparação de nomes de cabeçalho.

**Tentar escanear múltiplas URLs sem async.** A API síncrona bloqueia uma URL por vez. Escanear 100 URLs em sequência é lento. Se você quiser concorrência, mude para `httpx.AsyncClient` e use `asyncio.gather`. O arquivo de desafios tem um esboço disso.

## 19. Dicas de depuração

Quando algo der errado:

**Execute com `-v` para saída detalhada do pytest.**

```
uv run pytest -v
```

Mostra o nome de cada teste enquanto ele roda. Mais fácil de identificar qual falhou.

**Use a flag `--pdb` para um depurador interativo.**

```
uv run pytest --pdb
```

Entra no depurador do Python no primeiro teste que falhar. Digite `l` para ver o código ao redor da falha, `p nome_da_variavel` para inspecionar, `c` para continuar.

**Imprima os cabeçalhos reais quando o scanner der resultados errados.**
Edite `scan()` para imprimir `response_headers` antes do loop. Execute o scanner contra um site conhecido. Compare o que você vê com o que as ferramentas de desenvolvedor do seu navegador dizem. Diferentes User-Agents às vezes recebem respostas diferentes.

**Use `curl -I` como uma verificação de sanidade.**

```
curl -I https://example.com
```

A flag `-I` busca apenas os cabeçalhos. Se os cabeçalhos que você vê lá não coincidirem com o que o scanner relata, algo está errado com a requisição que o scanner está fazendo.

## 20. Próximo

Leia **[04-Desafios.md](./04-Desafios.md)** para ideias de como estender o scanner. Escolha uma que lhe interesse, tente implementá-la e veja como a arquitetura se comporta quando você a pressiona.
