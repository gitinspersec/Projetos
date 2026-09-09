"""
©AngelaMos | 2026
http_headers_scanner.py

Escaneia uma URL e classifica seus cabeçalhos de segurança HTTP de A a F

Quando um navegador solicita uma página a um site, o servidor envia a
própria página MAIS um monte de metadados chamados "cabeçalhos de resposta HTTP".
Alguns desses cabeçalhos são críticos para a segurança: eles dizem ao navegador
"converse comigo apenas via HTTPS", "não permita que outros sites me incorporem em
um iframe", "ignore suposições sobre tipos de arquivo" e muito mais

Se um site esquecer esses cabeçalhos, ataques reais se tornam mais fáceis:
clickjacking, MIME-sniffing, rebaixamentos de mixed-content, XSS que
caso contrário teriam sido impedidos por uma boa Content-Security-Policy.
Este script se conecta a uma URL, obtém os cabeçalhos e informa quais
estão ausentes ou são fracos

────────────────────────────────────────────────────────────────────
Os cabeçalhos que nos importam
────────────────────────────────────────────────────────────────────
  Strict-Transport-Security  força HTTPS para visitas posteriores
  Content-Security-Policy    controla quais scripts/styles podem carregar
  X-Content-Type-Options     desativa o MIME-sniffing
  X-Frame-Options            controla incorporação em iframe (clickjacking)
  Referrer-Policy            limita vazamento de Referer
  Permissions-Policy         desativa recursos do navegador que a página não
                             precisa (câmera, microfone, etc.)

Cada regra tem uma gravidade (alta / média / baixa). A pontuação é a
porcentagem de pontos ponderados que o site conquistou. A nota vem da
pontuação: 90+ A, 80+ B, 70+ C, 60+ D, caso contrário F. Isso espelha o
modelo usado pelo Mozilla Observatory

────────────────────────────────────────────────────────────────────
O que este script NÃO faz
────────────────────────────────────────────────────────────────────
  - Não rastreia o site, apenas a URL fornecida
  - Não analisa diretivas CSP complexas (apenas verifica a presença)
  - Não testa XSS real ou redirecionamentos abertos

Isso é fundamental: aprenda os cabeçalhos, depois evolua para ferramentas
maiores como Mozilla Observatory ou `securityheaders.com`

────────────────────────────────────────────────────────────────────
O que este arquivo expõe
────────────────────────────────────────────────────────────────────
  HeaderRule        — uma regra (nome do cabeçalho, gravidade, descrição, ...)
  HeaderFinding     — o resultado da avaliação de uma regra
  ScanReport        — relatório completo (url, status_code, descobertas, pontuação, nota)
  evaluate_header() — executa uma regra contra um conjunto de cabeçalhos
  scan()            — busca uma URL e executa todas as regras
  main()            — ponto de entrada da CLI usado por `headers <url>`
"""

# Biblioteca padrão: analisa flags de linha de comando como `--timeout 5` em
# um objeto organizado para não precisarmos fatiar `sys.argv` manualmente.
import argparse

# Biblioteca padrão: expressões regulares — usamos `re.search` para comparar
# valores de cabeçalhos com padrões de regras (ex.: `max-age\s*=\s*[1-9]` para
# HSTS, que deve rejeitar `max-age=0`).
import re

# Biblioteca padrão: acesso a internals do interpretador — usamos para
# escrever em stderr e encerrar o processo com um código de status específico.
import sys

# Biblioteca padrão: um decorator que transforma uma classe em um pequeno
# registro de dados imutável sem escrever boilerplate de `__init__`.
from dataclasses import dataclass

# Biblioteca padrão: uma dica de tipo que restringe um valor a um pequeno
# conjunto fixo de strings (aqui: níveis de gravidade como "good"/"warn"). Mypy
# captura erros de digitação.
from typing import Literal

# Terceiros (httpx): o cliente HTTP que realmente busca a URL.
# Substituição moderna para `requests` — suporta timeouts e HTTP/2.
import httpx

# Terceiros (rich): o printer que desenha saída colorida no terminal,
# com suporte total a Unicode e largura.
from rich.console import Console

# Terceiros (rich): desenha uma caixa com borda ao redor do conteúdo — usamos
# para o banner de resumo no topo do relatório.
from rich.panel import Panel

# Terceiros (rich): constrói a tabela ASCII colorida que lista cada
# descoberta de cabeçalho com sua gravidade.
from rich.table import Table

# =============================================================================
# Tipo de gravidade — três valores válidos
# =============================================================================
# Literal["high", "medium", "low"] é uma dica de tipo que diz "esta string
# só PODE ser um destes três valores." Mypy capturará erros de digitação como
# "hgih" em tempo de edição. Escolhemos Literal em vez de Enum porque o guia
# de estilo de Carter prefere Literals para pequenos conjuntos fixos

Severity = Literal["high", "medium", "low"]
Status = Literal["ok", "weak", "missing"]


# =============================================================================
# HeaderRule — uma regra que avaliamos contra a resposta
# =============================================================================


@dataclass(frozen=True, slots=True)
class HeaderRule:
    """
    Uma única verificação de cabeçalho de segurança

    `frozen=True` torna o dataclass imutável — uma vez criado, seus
    campos não podem ser alterados. `slots=True` torna as instâncias leves
    em memória. Juntas, essas duas flags criam um "objeto valor" limpo

    Campos
    ------
    header
        O nome do cabeçalho HTTP a ser procurado (case-insensitive)
    severity
        O quão importante é o cabeçalho. Define o valor em pontos abaixo
    description
        Uma frase explicando o que o cabeçalho faz. Mostrado na saída
    recommendation
        Correção concreta que o usuário deve aplicar se o cabeçalho estiver ausente
    must_match
        Padrão regex opcional (case-insensitive) que o valor DEVE corresponder.
        Use uma palavra simples para correspondência de substring (ex.: ``nosniff``), ou uma
        regex real para verificações mais rigorosas. Exemplo: ``max-age\\s*=\\s*[1-9]``
        requer que ``max-age`` seja um inteiro positivo, o que rejeita o
        ativamente prejudicial ``max-age=0``. Se definido e o valor
        não corresponder, relatamos `weak` em vez de `ok`
    """

    header: str
    severity: Severity
    description: str
    recommendation: str
    must_match: str | None = None


# =============================================================================
# Tabela de regras — fonte única de verdade do que verificamos
# =============================================================================
# Adicionar um cabeçalho a esta lista é a única alteração necessária para
# estender o scanner. A lógica de verificação é genérica — ela percorre esta
# lista em tempo de execução e aplica cada regra da mesma forma

RULES: list[HeaderRule] = [
    HeaderRule(
        header="Strict-Transport-Security",
        severity="high",
        description=(
            "Diz ao navegador para CONECTAR APENAS via HTTPS pelos "
            "próximos N segundos, derrotando ataques de stripping SSL"
        ),
        recommendation=(
            "Adicione: Strict-Transport-Security: max-age=31536000; includeSubDomains"
        ),
        # Requer que max-age seja um inteiro positivo — `max-age=0`
        # desativa ativamente o HSTS, portanto devemos rejeitá-lo. A regex
        # aceita espaços em branco ao redor de `=` para tolerar `max-age = 60`.
        must_match=r"max-age\s*=\s*[1-9]",
    ),
    HeaderRule(
        header="Content-Security-Policy",
        severity="high",
        description=(
            "Controla quais scripts, estilos, frames e conexões "
            "o navegador pode carregar — a defesa mais forte contra XSS"
        ),
        recommendation=(
            "Adicione uma Content-Security-Policy que não permita "
            "'unsafe-inline' e limite as fontes a origens confiáveis"
        ),
    ),
    HeaderRule(
        header="X-Content-Type-Options",
        severity="medium",
        description=(
            "Impede que navegadores adivinhem o Content-Type "
            "e tratem um arquivo .txt como HTML — derrota o MIME-sniffing"
        ),
        recommendation="Adicione: X-Content-Type-Options: nosniff",
        # O valor deve ser literalmente `nosniff`; qualquer outra coisa está errada.
        # `re.search("nosniff", ...)` é uma correspondência de substring aqui — sem
        # caracteres regex especiais no padrão.
        must_match="nosniff",
    ),
    HeaderRule(
        header="X-Frame-Options",
        severity="medium",
        description=(
            "Impede que outro site incorpore esta página em um "
            "iframe, derrotando ataques de clickjacking"
        ),
        recommendation=(
            "Adicione: X-Frame-Options: DENY (ou use "
            "Content-Security-Policy: frame-ancestors 'none')"
        ),
    ),
    HeaderRule(
        header="Referrer-Policy",
        severity="low",
        description=(
            "Limita quanto da URL atual vaza para outros sites "
            "quando o usuário clica em um link externo"
        ),
        recommendation=("Adicione: Referrer-Policy: strict-origin-when-cross-origin"),
    ),
    HeaderRule(
        header="Permissions-Policy",
        severity="low",
        description=(
            "Desativa recursos do navegador que a página não usa "
            "(câmera, microfone, geolocalização, pagamentos, etc.)"
        ),
        recommendation=(
            "Adicione: Permissions-Policy: camera=(), microphone=(), geolocation=()"
        ),
    ),
]


# =============================================================================
# Gravidade → pontos. Define a pontuação final
# =============================================================================
# Cada cabeçalho presente e correto ganha seus pontos completos; presença
# fraca ganha metade dos pontos; ausente ganha zero. Total alcançável = soma
# de todos os pontos das regras. A pontuação é (ganho / total) * 100, arredondado

SEVERITY_POINTS: dict[Severity, int] = {
    "high": 30,
    "medium": 15,
    "low": 5,
}


# =============================================================================
# HeaderFinding — o resultado da avaliação de uma regra
# =============================================================================


@dataclass(frozen=True, slots=True)
class HeaderFinding:
    """
    Resultado da execução de uma HeaderRule contra os cabeçalhos de resposta

    Campos
    ------
    rule
        A regra que avaliamos. Carregá-la dentro da descoberta significa
        que o renderizador nunca precisa procurar a regra novamente
    status
        "ok"      — cabeçalho está presente e (se aplicável) o valor
                    corresponde a must_match
        "weak"    — cabeçalho está presente mas o valor está errado
        "missing" — cabeçalho não está na resposta
    actual_value
        O que o servidor realmente enviou para este cabeçalho, ou None
        quando o cabeçalho estava completamente ausente
    note
        Breve explicação legível por humanos. Mostrada na tabela ao lado
        da coluna de status
    """

    rule: HeaderRule
    status: Status
    actual_value: str | None
    note: str


# =============================================================================
# ScanReport — o resultado completo retornado por scan()
# =============================================================================


@dataclass(frozen=True, slots=True)
class ScanReport:
    """
    Um resultado de scan completo para uma URL

    As propriedades `score` e `grade` são calculadas sob demanda a partir
    das descobertas, portanto sempre refletem o que a tabela de regras
    era no momento do scan
    """

    url: str
    final_url: str
    status_code: int
    findings: list[HeaderFinding]

    @property
    def score(self) -> int:
        """
        Retorna uma pontuação de 0 a 100 refletindo as descobertas ponderadas

        Fórmula
        -------
            ganho = pontos completos para cada "ok"
                  + metade dos pontos para cada "weak"
                  + zero para cada "missing"
            pontuacao = arredondar(ganho / total * 100)
        """
        total = sum(SEVERITY_POINTS[r.severity] for r in RULES)
        # Proteção contra tabela de regras vazia — só importaria se
        # alguém excluísse RULES durante testes. Mantém o código total
        if total == 0:
            return 0

        earned = 0.0
        for finding in self.findings:
            full = SEVERITY_POINTS[finding.rule.severity]
            if finding.status == "ok":
                earned += full
            elif finding.status == "weak":
                earned += full / 2
            # "missing" ganha 0 — nenhum branch else necessário

        # Arredondamento para cima via int(x + 0.5) evita o arredondamento
        # bancário do Python, que mapearia round(0.5) -> 0 e round(2.5) -> 2
        # — surpreendente para uma pontuação que sempre deve arredondar para
        # cima no limite .5
        return int((earned / total) * 100 + 0.5)

    @property
    def grade(self) -> str:
        """
        Mapeia a pontuação para uma nota A–F
        """
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


# =============================================================================
# Avaliação de cabeçalho — função pura, sem I/O
# =============================================================================
# Separar isso de scan() torna-o trivialmente testável: passe uma
# regra e um dicionário de cabeçalhos, receba uma descoberta. Sem rede necessária


def evaluate_header(
    rule: HeaderRule,
    response_headers: dict[str, str],
) -> HeaderFinding:
    """
    Aplica uma única HeaderRule a um conjunto de cabeçalhos de resposta

    Os nomes de cabeçalhos HTTP são case-insensitive conforme RFC 7230 — `HSTS` e
    `hsts` e `Hsts` são o mesmo cabeçalho. Normalizamos ambos os lados
    para minúsculas antes de comparar
    """
    target = rule.header.lower()

    # Percorre os cabeçalhos de resposta manualmente em vez de construir um
    # dicionário case-insensitive. A entrada é sempre um dict simples aqui —
    # scan() converte o objeto Headers do httpx antes de nos chamar, então
    # os testes podem passar qualquer dict[str, str] sem cerimônia
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
            note=f"Cabeçalho `{rule.header}` não está definido",
        )

    # Se a regra não tem verificação must_match, a presença é suficiente
    if rule.must_match is None:
        return HeaderFinding(
            rule=rule,
            status="ok",
            actual_value=actual_value,
            note="Presente",
        )

    # Caso contrário, verifica se o valor corresponde ao padrão exigido.
    # re.search encontra o padrão em qualquer lugar da string — para uma
    # palavra simples como `nosniff` isso se comporta como verificação de substring;
    # para uma regex real como `max-age\s*=\s*[1-9]` aplica uma condição
    # mais rica (inteiro positivo após `max-age=`)
    if re.search(rule.must_match, actual_value, re.IGNORECASE):
        return HeaderFinding(
            rule=rule,
            status="ok",
            actual_value=actual_value,
            note=f"Presente e corresponde a `{rule.must_match}`",
        )

    return HeaderFinding(
        rule=rule,
        status="weak",
        actual_value=actual_value,
        note=(
            f"Presente mas não corresponde a `{rule.must_match}` "
            f"(recebido `{actual_value}`)"
        ),
    )


# =============================================================================
# scan() — busca a URL e aplica todas as regras
# =============================================================================


# Um User-Agent educado e identificável. Alguns servidores bloqueiam
# requisições com o UA padrão do httpx ou sem UA algum
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
    """
    Busca `url` uma vez e classifica seus cabeçalhos de resposta

    Parâmetros
    ----------
    url
        URL completa incluindo o esquema. Nomes de host simples como
        "example.com" NÃO são suportados porque não podemos adivinhar
        se o usuário queria http ou https
    timeout
        Segundos antes de desistirmos de um servidor lento. Padrão 10
    user_agent
        Enviado como o cabeçalho User-Agent. Alguns sites servem respostas
        diferentes para bots; o padrão nos identifica honestamente

    Retorna
    -------
    ScanReport
        Contendo as descobertas, código de status e URL final após
        quaisquer redirecionamentos

    Levanta
    ------
    httpx.RequestError
        Em falha de DNS, recusa de conexão, timeout, etc. A CLI
        captura estas para imprimir uma mensagem de erro limpa
    """
    # follow_redirects=True significa que http://example.com → https://example.com
    # é seguido automaticamente. Classificamos a URL FINAL, não a primeira,
    # porque é a que os usuários realmente veem
    response = httpx.get(
        url,
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": user_agent},
    )

    # O objeto Headers do httpx se comporta como um dict para nossos propósitos.
    # dict(response.headers) nos dá um dict[str, str] comum
    response_headers = dict(response.headers)

    # Executa cada regra contra a resposta. List comprehension é
    # mais limpo que um loop for com .append() aqui
    findings = [evaluate_header(rule, response_headers) for rule in RULES]

    return ScanReport(
        url=url,
        final_url=str(response.url),
        status_code=response.status_code,
        findings=findings,
    )


# =============================================================================
# Renderização da CLI — mantém a lógica de exibição fora da camada de dados
# =============================================================================


# Como cada status / gravidade deve ser colorido no terminal
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
    """
    Imprime o relatório do scan como uma tabela rich mais um painel de nota
    """
    # A tabela de cabeçalhos — uma linha por regra
    table = Table(
        title=(f"Cabeçalhos para {report.final_url} (HTTP {report.status_code})"),
        title_style="bold cyan",
        show_lines=False,
    )
    table.add_column("cabeçalho", style="bold white", no_wrap=True)
    table.add_column("status", no_wrap=True)
    table.add_column("gravidade", no_wrap=True)
    table.add_column("observação", style="dim")

    for finding in report.findings:
        status_color = STATUS_COLORS[finding.status]
        table.add_row(
            finding.rule.header,
            f"[{status_color}]{finding.status}[/{status_color}]",
            finding.rule.severity,
            finding.note,
        )
    console.print(table)

    # Navegadores IGNORAM HSTS recebido via HTTP puro conforme RFC 6797 §8.1
    # — se a resposta final foi servida via http://, qualquer nota HSTS
    # acima é enganosa. Avisa para o usuário não sair com uma
    # falsa sensação de segurança
    if report.final_url.startswith("http://"):
        console.print(
            "[yellow]Nota:[/yellow] esta resposta foi servida via HTTP "
            "puro. Navegadores IGNORAM HSTS via HTTP, portanto qualquer "
            "nota HSTS acima é enganosa até que o site force HTTPS"
        )

    # O painel de nota — grande, colorido, chamativo
    grade_color = GRADE_COLORS[report.grade]
    panel = Panel(
        f"[bold {grade_color}]Nota: {report.grade}[/bold {grade_color}]\n"
        f"Pontuação: {report.score} / 100",
        title="Resultado",
        border_style=grade_color,
    )
    console.print(panel)

    # Imprime recomendações para quaisquer descobertas não-ok, para que o
    # usuário tenha uma lista de ações — o que adicionar ou corrigir
    actionable = [f for f in report.findings if f.status != "ok"]
    if actionable:
        console.print("\n[bold]Recomendações:[/bold]")
        for finding in actionable:
            console.print(
                f"  • [yellow]{finding.rule.header}[/yellow] "
                f"— {finding.rule.recommendation}"
            )


# =============================================================================
# Infraestrutura do argparse — separada para que testes possam chamá-la diretamente
# =============================================================================


def _build_argument_parser() -> argparse.ArgumentParser:
    """
    Constrói o parser argparse usado por main()
    """
    parser = argparse.ArgumentParser(
        prog="headers",
        description=(
            "Escaneia uma URL por cabeçalhos de segurança HTTP e classifica o resultado A–F."
        ),
    )
    parser.add_argument(
        "url",
        help="URL completa para escanear (deve incluir http:// ou https://).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Segundos para esperar antes de desistir da requisição (padrão: 10).",
    )
    return parser


# =============================================================================
# main() — códigos de saída têm significado
# =============================================================================
# 0 → nota A ou B (sinal verde para CI)
# 1 → nota C ou D (aviso mas não falha por padrão)
# 2 → nota F ou erro de rede (falha ruidosamente)


def main() -> int:
    """
    Ponto de entrada da CLI — retorna um código de saída refletindo o resultado do scan
    """
    parser = _build_argument_parser()
    args = parser.parse_args()
    console = Console()

    # Captura erros de rede aqui para o usuário ver uma mensagem limpa
    # em vez de um traceback cru. Deixamos a própria mensagem do httpx
    # passar após nosso prefixo — o erro subjacente geralmente tem
    # detalhes úteis (falha de DNS, conexão recusada, etc.)
    try:
        report = scan(args.url, timeout=args.timeout)
    except httpx.RequestError as exc:
        console.print(f"[red]Falha na requisição:[/red] {type(exc).__name__}: {exc}")
        return 2

    _render_report(report, console)

    if report.grade in ("A", "B"):
        return 0
    if report.grade in ("C", "D"):
        return 1
    return 2


# Guarda padrão "se invocado diretamente como script" — permite que o arquivo
# seja importado por testes sem executar main()
if __name__ == "__main__":
    sys.exit(main())
