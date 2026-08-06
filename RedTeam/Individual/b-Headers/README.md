```ruby
██╗  ██╗███████╗ █████╗ ██████╗ ███████╗██████╗ ███████╗
██║  ██║██╔════╝██╔══██╗██╔══██╗██╔════╝██╔══██╗██╔════╝
███████║█████╗  ███████║██║  ██║█████╗  ██████╔╝███████╗
██╔══██║██╔══╝  ██╔══██║██║  ██║██╔══╝  ██╔══██╗╚════██║
██║  ██║███████╗██║  ██║██████╔╝███████╗██║  ██║███████║
╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝╚══════╝
```

[![Python 3.14](https://img.shields.io/badge/Python-3.14-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![HTTP Client](https://img.shields.io/badge/httpx-0.28+-1f5582?style=flat)](https://www.python-httpx.org/)

> Faz uma única requisição a uma URL e avalia seus cabeçalhos de segurança HTTP com uma nota de A a F usando o mesmo modelo de rubrica ponderada do Mozilla Observatory.

_Esta é uma visão geral rápida. A teoria de segurança, a arquitetura e os tutoriais completos estão nos [módulos de aprendizado](#learn)._

> [!NOTE]
> Este projeto foi desenvolvido para alguém que nunca escreveu Python antes. O código-fonte é amplamente comentado como auxílio didático, a pasta `learn/` explica todos os conceitos do zero e toda a ferramenta está contida em um único arquivo legível.

## O Que Ele Faz

- Realiza uma única requisição HTTPS educada para a URL fornecida e inspeciona os cabeçalhos da resposta
- Avalia seis cabeçalhos críticos de segurança com uma rubrica ponderada (alta = 30 pts, média = 15 pts, baixa = 5 pts)
- Exibe cada resultado como `ok`, `weak` ou `missing`, acompanhado de uma explicação em uma linha do motivo
- Calcula uma pontuação de 0 a 100 e a converte em uma nota de A a F (90+ = A, 80+ = B, etc.)
- Detecta valores sutilmente incorretos, como `Strict-Transport-Security: max-age=0` (cabeçalho presente, porém desativado ativamente), marcando-os como `weak`, e não `ok`
- Segue redirecionamentos e avalia a URL **final**, aquela em que o navegador realmente terminaria
- Exibe uma tabela colorida usando Rich, um painel com a nota e uma lista de recomendações para cada resultado diferente de `ok`
- Retorna códigos de saída significativos: `0` para A/B, `1` para C/D e `2` para F ou erro de rede, úteis em pipelines de CI

## Os Cabeçalhos Avaliados

| Header                      | Severidade | O que impede                                                          |
| --------------------------- | ---------- | --------------------------------------------------------------------- |
| `Strict-Transport-Security` | alta       | SSL stripping em redes Wi-Fi públicas                                 |
| `Content-Security-Policy`   | alta       | XSS por meio de tags `<script>` injetadas                             |
| `X-Content-Type-Options`    | média      | MIME sniffing de arquivos enviados                                    |
| `X-Frame-Options`           | média      | Clickjacking por meio de iframes ocultos                              |
| `Referrer-Policy`           | baixa      | Vazamento de tokens secretos pelo cabeçalho Referer                   |
| `Permissions-Policy`        | baixa      | Scripts de terceiros comprometidos abusando de câmera, microfone etc. |

Cada cabeçalho está associado a uma classe real de ataque, com histórico de exploração. O módulo [`01-Conceitos.md`](learn/01-Conceitos.md) explica cada um deles usando exemplos concretos de ataques.

## Início Rápido

```bash
sudo apt update
wget -qO- https://astral.sh/uv/install.sh | sh
uv venv --python 3.14
source .venv/bin/activate
./install.sh
just run -- https://example.com
# Nota: B, Pontuação: 85 / 100  (example.com não possui CSP nem Permissions-Policy)
```

> [!TIP]
> Este projeto utiliza o [`just`](https://github.com/casey/just) como executor de comandos. Digite `just` para ver todos os comandos disponíveis.
>
> Instalação: `curl -sSf https://just.systems/install.sh | bash -s -- --to ~/.local/bin`

## URLs de Demonstração

Experimente estas URLs. Cada uma demonstra um caminho de avaliação diferente:

| URL                   | Nota esperada | Motivo                                                                                           |
| --------------------- | ------------- | ------------------------------------------------------------------------------------------------ |
| `https://github.com`  | A             | CSP abrangente, HSTS com `includeSubDomains` e praticamente todos os cabeçalhos configurados     |
| `https://web.dev`     | A             | Site de documentação para desenvolvedores do Google, com conjunto moderno completo de cabeçalhos |
| `https://mozilla.org` | A             | A Mozilla pratica aquilo que o Observatory recomenda                                             |
| `https://example.com` | B / C         | Possui HSTS, mas não possui CSP, Permissions-Policy e outros cabeçalhos                          |
| `http://neverssl.com` | F             | Serve propositalmente apenas HTTP puro, sem qualquer cabeçalho de segurança                      |

```bash
just run -- https://github.com
just run -- https://example.com
just run -- https://web.dev --timeout 5
just run -- http://neverssl.com
```

> [!IMPORTANT]
> Sempre inclua o esquema `http://` ou `https://`. O scanner rejeita nomes de host sem esquema, como `github.com`, porque não consegue adivinhar qual deles você pretendia usar, e adivinhar incorretamente é justamente o problema de SSL stripping que o HSTS existe para impedir.

## Exemplo de Saída

```
                  Headers for https://github.com/ (HTTP 200)
┌─────────────────────────────┬─────────┬──────────┬─────────────────────────┐
│ header                      │ status  │ severity │ note                    │
├─────────────────────────────┼─────────┼──────────┼─────────────────────────┤
│ Strict-Transport-Security   │ ok      │ high     │ Present and contains... │
│ Content-Security-Policy     │ ok      │ high     │ Present                 │
│ X-Content-Type-Options      │ ok      │ medium   │ Present and contains... │
│ X-Frame-Options             │ ok      │ medium   │ Present                 │
│ Referrer-Policy             │ ok      │ low      │ Present                 │
│ Permissions-Policy          │ missing │ low      │ Header ... is not set   │
└─────────────────────────────┴─────────┴──────────┴─────────────────────────┘
╭─ Result ───────────────────╮
│ Grade: A                   │
│ Score: 95 / 100            │
╰────────────────────────────╯
```

Em seguida, é exibido um bloco `Recommendations:` para cada resultado diferente de `ok`, contendo exatamente o valor do cabeçalho que deve ser adicionado.

## Códigos de Saída

O scanner retorna códigos de saída compatíveis com shell para que você possa integrá-lo a pipelines de CI:

| Nota              | Código de saída | Significado                                                             |
| ----------------- | --------------- | ----------------------------------------------------------------------- |
| A, B              | `0`             | Sinal verde, nenhuma ação necessária                                    |
| C, D              | `1`             | Vale a pena investigar; muitas vezes é aceitável dependendo do contexto |
| F ou erro de rede | `2`             | Falha crítica, deve ser corrigida                                       |

```bash
just run -- https://my-deployed-site.com
if [ $? -gt 1 ]; then exit 1; fi   # falha na build apenas em caso de F ou erro
```

## Ferramentas

```bash
just            # lista os comandos disponíveis
just test       # executa o pytest (11 testes, executa em menos de um segundo, rede simulada com respx)
just lint       # ruff + mypy --strict + pylint
just format     # yapf
just run -- <url>  # escaneia uma URL
```

## Requisitos

- **Python 3.13+**, o script de instalação fará essa verificação.
- [`uv`](https://github.com/astral-sh/uv), gerenciador moderno de pacotes Python (instalado automaticamente por `./install.sh`).
- [`just`](https://github.com/casey/just), executor de comandos (instalado automaticamente por `./install.sh`).
- Uma conexão ativa com a internet durante a execução (o scanner realiza uma requisição HTTPS real por análise, mas a suíte de testes simula a rede com `respx` e executa totalmente offline).

Nenhum compilador ou biblioteca de sistema é necessário. O projeto consiste em um único arquivo Python mais os testes.

## Learn

Este projeto inclui materiais de aprendizado passo a passo que cobrem teoria de segurança, arquitetura e implementação, escritos para alguém que nunca teve contato com Python.

| Module                                          | Tópico                                                                                                                                                                  |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [00 - Introdução](learn/00-Introdução.md)       | Início rápido, pré-requisitos, saída esperada e problemas comuns na primeira execução                                                                                   |
| [01 - Conceitos](learn/01-Conceitos.md)         | O que é HTTP, o que é um header e cada cabeçalho de segurança com o ataque real que ele impede (SSL stripping, clickjacking, MIME sniffing, XSS, vazamento via referer) |
| [02 - Arquitetura](learn/02-Arquitetura.md)     | Pipeline de quatro etapas, dataclasses como objetos de valor e o padrão I/O fence (núcleo funcional / casca imperativa)                                                 |
| [03 - Implementação](learn/03-Implementação.md) | Explicação função por função, cada recurso de Python explicado quando aparece pela primeira vez, além de padrões de teste e ferramentas                                 |
| [04 - Desafios](learn/04-Desafios.md)           | Doze ideias de extensão, desde "adicionar uma sétima regra de cabeçalho" até "empacotar a ferramenta em um serviço FastAPI com rate limiting"                           |

## Contexto do Mundo Real

Este scanner é uma versão em escala didática de ferramentas que realizam a mesma tarefa em escala de produção:

- **[Mozilla Observatory](https://observatory.mozilla.org/)**, a versão canônica. Utiliza a mesma abordagem de rubrica ponderada, porém com análise mais profunda de CSP, verificação de cookies e avaliação da configuração TLS.
- **[securityheaders.com](https://securityheaders.com)**, interface mais simples, mesma ideia.
- **[nmap http-security-headers script](https://nmap.org/nsedoc/scripts/http-security-headers.html)**, voltado para fluxos de trabalho em linha de comando.

Depois que você entender como este scanner toma suas decisões, essas ferramentas deixarão de parecer mágicas e passarão a ser compreensíveis. O módulo [04-Desafios.md](learn/04-Desafios.md) apresenta ideias para evoluir este projeto em direção ao que o Observatory faz.

---

@CarterPerez-dev | Copyright (C) 2026 Murilo Miacci
