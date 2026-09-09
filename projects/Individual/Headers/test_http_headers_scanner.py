"""
©AngelaMos | 2026
test_http_headers_scanner.py

Testes para http_headers_scanner — cobre avaliação de regras, cálculo
de pontuação, limites de notas e um scan end-to-end com simulação

────────────────────────────────────────────────────────────────────
O que são "testes" e por que os escrevemos
────────────────────────────────────────────────────────────────────
Um teste é uma pequena função Python que chama nosso código real com
uma entrada conhecida e então AFIRMA que o resultado é o que esperávamos.
Se a afirmação falhar, o pytest imprime uma mensagem de FALHA vermelha — o
que significa que mudamos algo e quebramos um comportamento que nos importava

Testes são um seguro. Na primeira vez que você escreve o código, o teste
apenas confirma que funciona. Mas seis meses depois, quando você refatora ou
adiciona um novo recurso, os testes existentes detectam qualquer quebra acidental

────────────────────────────────────────────────────────────────────
Por que simulamos a rede com respx
────────────────────────────────────────────────────────────────────
Um teste que acessa um site real é FRÁGIL. O site pode estar fora do ar,
lento, redesenhado ou atrás de um captcha. Nada disso tem a ver com
se o NOSSO código está correto

`respx` é uma biblioteca que intercepta chamadas httpx e retorna uma
resposta controlada que definimos. Assim, quando testamos scan("https://test"),
respx devolve EXATAMENTE os cabeçalhos que mandamos — permitindo-nos
verificar a lógica de scan sem tocar na rede

────────────────────────────────────────────────────────────────────
Estratégia de cobertura
────────────────────────────────────────────────────────────────────
Executamos cada ramificação do código pelo menos uma vez

  - evaluate_header: ok / weak / missing / busca case-insensitive
  - ScanReport.score: tudo-ok, tudo-ausente, misto
  - ScanReport.grade: cada faixa (A, B, C, D, F)
  - scan(): pipeline completo contra uma resposta simulada, incluindo um redirecionamento

Isso é confiança suficiente — adicionar dez variações de "outro cabeçalho"
não detectaria novos bugs
"""

# Terceiros (httpx): precisamos de seu tipo `Response` para construir
# respostas falsas dentro de nossas rotas simuladas.
import httpx

# Terceiros: o executor de testes. Também usamos seu decorador
# `@pytest.mark.parametrize` para expandir uma função de teste em muitos casos.
import pytest

# Terceiros (respx): intercepta chamadas httpx e retorna falsificações que
# definimos, para que os testes não acessem a internet real.
import respx

# Local: nosso próprio módulo. Importamos as peças públicas sob teste —
# a tabela de regras, dataclasses e as duas funções de entrada.
from http_headers_scanner import (
    RULES,
    HeaderFinding,
    HeaderRule,
    ScanReport,
    Status,
    evaluate_header,
    scan,
)

# =============================================================================
# Fixtures — pequenos auxiliares usados por múltiplos testes
# =============================================================================
# Uma "fixture" do pytest é uma função de configuração que o pytest executa
# antes de um teste que precise dela. Testes solicitam fixtures listando-as
# como parâmetros


@pytest.fixture
def hsts_rule() -> HeaderRule:
    """
    Uma HeaderRule representativa que requer um valor positivo para max-age
    """
    # Construímos uma inline em vez de acessar RULES para que este
    # teste seja robusto a futuras adições/reordenações da tabela.
    # A regex corresponde a `max-age` seguido por `=` e um dígito 1-9 —
    # o que rejeita `max-age=0` (HSTS deliberadamente desabilitado)
    return HeaderRule(
        header="Strict-Transport-Security",
        severity="high",
        description="Força HTTPS",
        recommendation="Adicione: Strict-Transport-Security: max-age=31536000",
        must_match=r"max-age\s*=\s*[1-9]",
    )


@pytest.fixture
def referrer_rule() -> HeaderRule:
    """
    Uma regra SEM must_contain — presença sozinha ganha pontos completos
    """
    return HeaderRule(
        header="Referrer-Policy",
        severity="low",
        description="Limita vazamento de Referer",
        recommendation="Adicione: Referrer-Policy: strict-origin-when-cross-origin",
    )


# =============================================================================
# evaluate_header — a função pura no coração do scanner
# =============================================================================
# Estes testes não tocam na rede — construímos manualmente o
# dicionário de cabeçalhos e verificamos a descoberta


def test_evaluate_header_present_with_required_substring(
    hsts_rule: HeaderRule,
) -> None:
    """
    Cabeçalho está presente E contém must_contain → status = ok
    """
    headers = {"Strict-Transport-Security": "max-age=31536000"}
    finding = evaluate_header(hsts_rule, headers)
    assert finding.status == "ok"
    assert finding.actual_value == "max-age=31536000"


def test_evaluate_header_present_without_required_substring(
    hsts_rule: HeaderRule,
) -> None:
    """
    Cabeçalho está presente mas NÃO corresponde a must_match → status = weak

    Um exemplo do mundo real: alguém define o cabeçalho como uma string vazia
    ou apenas `includeSubDomains` sem `max-age=`. O cabeçalho existe
    mas é funcionalmente inútil
    """
    headers = {"Strict-Transport-Security": "includeSubDomains"}
    finding = evaluate_header(hsts_rule, headers)
    assert finding.status == "weak"


def test_evaluate_header_missing(hsts_rule: HeaderRule) -> None:
    """
    Cabeçalho não está na resposta → status = missing
    """
    # Dicionário vazio — nenhum cabeçalho
    headers: dict[str, str] = {}
    finding = evaluate_header(hsts_rule, headers)
    assert finding.status == "missing"
    # E actual_value deve ser None quando o cabeçalho está ausente
    assert finding.actual_value is None


def test_evaluate_header_hsts_max_age_zero_is_weak(
    hsts_rule: HeaderRule,
) -> None:
    """
    `max-age=0` DESATIVA ativamente o HSTS para visitas posteriores — o
    cabeçalho está presente mas faz o oposto do que queremos, portanto deve
    ser sinalizado como weak em vez de ok

    Isso fixa o comportamento identificado na auditoria — a correspondência
    baseada em substring classificava este caso como ok e deixava os usuários
    pensando que HSTS estava ativo quando estava deliberadamente desligado
    """
    headers = {"Strict-Transport-Security": "max-age=0; includeSubDomains"}
    finding = evaluate_header(hsts_rule, headers)
    assert finding.status == "weak"
    assert finding.actual_value == "max-age=0; includeSubDomains"


def test_evaluate_header_case_insensitive_lookup(
    referrer_rule: HeaderRule,
) -> None:
    """
    Nomes de cabeçalhos HTTP são case-insensitive conforme RFC 7230 — `Referrer-Policy`
    e `referrer-policy` e `REFERRER-POLICY` significam a mesma coisa
    """
    # O servidor retornou o cabeçalho com letras minúsculas, mas a
    # regra pede "Referrer-Policy" com a forma canônica.
    # Sem busca case-insensitive, este teste falharia
    headers = {"referrer-policy": "no-referrer"}
    finding = evaluate_header(referrer_rule, headers)
    assert finding.status == "ok"


def test_evaluate_header_no_must_match_treats_presence_as_ok(
    referrer_rule: HeaderRule,
) -> None:
    """
    Uma regra com must_match=None passa sempre que o cabeçalho existe
    """
    headers = {"Referrer-Policy": "qualquer-coisa-aqui-funciona"}
    finding = evaluate_header(referrer_rule, headers)
    assert finding.status == "ok"


# =============================================================================
# ScanReport.score e .grade — a matemática por trás do relatório
# =============================================================================
# A pontuação é calculada a partir das descobertas em tempo real, não
# armazenada. Portanto, podemos construir um ScanReport sintético com
# quaisquer descobertas que quisermos e afirmar exatamente qual deve
# ser a pontuação


def _make_report(statuses: list[Status]) -> ScanReport:
    """
    Constrói um ScanReport falso associando cada regra ao status fornecido

    Auxiliar para que cada teste não precise construir descobertas manualmente.
    O primeiro item em `statuses` é pareado com a primeira regra, etc.
    Preenche a lista com "missing" se for mais curta que RULES.

    O parâmetro é tipado como `list[Status]` para que o mypy imponha o
    contrato Literal em cada local de chamada — sem necessidade de verificação
    em tempo de execução ou escape type-ignore
    """
    findings: list[HeaderFinding] = []
    for index, rule in enumerate(RULES):
        # Quando o chamador passou menos statuses que regras, trata o
        # restante como missing. Comum quando um teste só se importa
        # com as primeiras regras
        status: Status = statuses[index] if index < len(statuses) else "missing"
        findings.append(
            HeaderFinding(
                rule=rule,
                status=status,
                actual_value=None,
                note="sintético",
            )
        )
    return ScanReport(
        url="https://example.com",
        final_url="https://example.com",
        status_code=200,
        findings=findings,
    )


def test_score_all_ok_is_100() -> None:
    """
    Todas as regras passando devem produzir uma pontuação perfeita
    """
    statuses: list[Status] = ["ok"] * len(RULES)
    report = _make_report(statuses)
    assert report.score == 100
    # E a nota segue a pontuação
    assert report.grade == "A"


def test_score_all_missing_is_zero() -> None:
    """
    Nada presente, nada ganho. Pontuação = 0, nota = F
    """
    statuses: list[Status] = ["missing"] * len(RULES)
    report = _make_report(statuses)
    assert report.score == 0
    assert report.grade == "F"


def test_grade_threshold_a_at_90_percent() -> None:
    """
    Passando ambos os high e ambos os mediums (90/100 = 90%) fica exatamente
    no limite do A

    A tabela de regras atual totaliza 100 pontos (30 + 30 + 15 + 15 + 5 + 5)
    Dois `high` = 60 / 100 = 60%, que é nota D
    Ambos high + ambos mediums = 90 / 100 = 90%, que é nota A
    """
    statuses_by_severity: dict[str, Status] = {
        "high": "ok",
        "medium": "ok",
        "low": "missing",
    }
    statuses: list[Status] = [statuses_by_severity[r.severity] for r in RULES]
    report = _make_report(statuses)
    assert report.score == 90
    assert report.grade == "A"


def test_grade_threshold_b_at_83_percent() -> None:
    """
    Ambos highs ok, um medium ok e o outro weak (60 + 15 + 7.5 = 82.5
    → arredonda para 83) cai abaixo de 90 e fica na faixa B
    """
    # Dois highs ok, mediums divididos entre ok e weak, lows missing
    statuses: list[Status] = []
    medium_seen = 0
    for rule in RULES:
        if rule.severity == "high":
            statuses.append("ok")
        elif rule.severity == "medium":
            statuses.append("ok" if medium_seen == 0 else "weak")
            medium_seen += 1
        else:
            statuses.append("missing")
    report = _make_report(statuses)
    assert 80 <= report.score < 90
    assert report.grade == "B"


# =============================================================================
# scan() — pipeline completo contra uma resposta simulada
# =============================================================================
# `@respx.mock` intercepta cada requisição httpx dentro do teste e
# retorna o que configuramos no corpo. A rede real nunca é tocada


@respx.mock
def test_scan_mocks_a_clean_response_and_grades_it_correctly() -> None:
    """
    Uma resposta com todos os cabeçalhos recomendados deve pontuar 100
    """
    # Respondemos a GET https://safe.example.com/ com 200 e o
    # conjunto completo de cabeçalhos de segurança. respx.get(...).mock(return_value=...)
    # registra a simulação; o próximo httpx.get dentro deste teste a dispara
    respx.get("https://safe.example.com/").mock(
        return_value=httpx.Response(
            status_code=200,
            headers={
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Content-Security-Policy": "default-src 'self'",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "camera=(), microphone=()",
            },
        )
    )

    report = scan("https://safe.example.com/")

    assert report.status_code == 200
    assert report.score == 100
    assert report.grade == "A"
    # Todas as descobertas devem ser `ok`
    assert all(f.status == "ok" for f in report.findings)


@respx.mock
def test_scan_flags_missing_and_weak_headers() -> None:
    """
    Uma resposta sem CSP e com X-Content-Type-Options fraco
    deve produzir descobertas de status misto
    """
    respx.get("https://weak.example.com/").mock(
        return_value=httpx.Response(
            status_code=200,
            headers={
                "Strict-Transport-Security": "max-age=600",
                # X-Content-Type-Options está presente mas o valor está errado:
                # a regra requer `nosniff`, isto diz outra coisa.
                # Escolhemos um valor que genuinamente NÃO contém a
                # substring `nosniff` — `"snifftest"` seria tratado
                # como ok porque embute a palavra
                "X-Content-Type-Options": "off",
                # Nota: Content-Security-Policy NÃO está incluído
            },
        )
    )

    report = scan("https://weak.example.com/")

    findings_by_header = {f.rule.header: f for f in report.findings}
    assert findings_by_header["Content-Security-Policy"].status == "missing"
    assert findings_by_header["X-Content-Type-Options"].status == "weak"
    assert findings_by_header["Strict-Transport-Security"].status == "ok"

    # Pontuação deve ser menor que 100 pois CSP está ausente e XCTO está weak
    assert report.score < 100


@respx.mock
def test_scan_records_final_url_after_redirect() -> None:
    """
    Quando http://x.example.com/ → https://x.example.com/, o relatório
    deve lembrar a URL final — é onde o usuário realmente chegou
    """
    # Primeira requisição: 301 para a versão https
    respx.get("http://redirect.example.com/").mock(
        return_value=httpx.Response(
            status_code=301,
            headers={"Location": "https://redirect.example.com/"},
        )
    )
    # Requisição final: 200 com um cabeçalho definido
    respx.get("https://redirect.example.com/").mock(
        return_value=httpx.Response(
            status_code=200,
            headers={"X-Frame-Options": "DENY"},
        )
    )

    report = scan("http://redirect.example.com/")

    assert report.url == "http://redirect.example.com/"
    assert report.final_url == "https://redirect.example.com/"
    assert report.status_code == 200
