# Headers

![Mode](https://img.shields.io/badge/Mode-Individual-402)
![Difficulty](https://img.shields.io/badge/Difficulty-N2_B%C3%A1sico-green)
![Stack](https://img.shields.io/badge/Stack-Python-3776AB)

> Faz uma única requisição a uma URL e avalia seus cabeçalhos de segurança HTTP com uma nota de A a F usando o mesmo modelo de rubrica ponderada do Mozilla Observatory.

_Esta é uma visão geral rápida. A teoria de segurança, a arquitetura e os tutoriais completos estão nos [/learn](./learn/00-Introdução.md)._

> [!NOTE]
> Este projeto foi desenvolvido para alguém que nunca escreveu Python antes. O código-fonte é amplamente comentado como auxílio didático, a pasta `learn/` explica todos os conceitos do zero e toda a ferramenta está contida em um único arquivo legível.

## 🎯 Objective

Construir uma ferramenta de linha de comando que faz uma requisição HTTP a uma URL, avalia seis cabeçalhos de segurança críticos e atribui uma nota de A a F usando uma rubrica ponderada.

## 🧠 Learning Outcomes

- O que é HTTP e o que são headers de segurança
- Os seis cabeçalhos críticos e os ataques que eles previnem (SSL stripping, XSS, clickjacking, MIME sniffing, vazamento via referer)
- Como usar `httpx` para fazer requisições HTTP
- Fundamentos de Python: dataclasses, I/O fence (núcleo funcional / casca imperativa)
- Como estruturar um pipeline de decisão em etapas

## � Caso tenha dificuldades com a base do projeto

> [!NOTE]
> Este projeto ensina Python e HTTP nos módulos `learn/`. Se você tiver dúvidas básicas, estes recursos práticos ajudam.

- [Curso em Vídeo — Python para Iniciantes](https://www.cursoemvideo.com/course/curso-python-3/) — vídeo-aula passo a passo
- [HTTP Security Headers Crash Course — Traversy Media](https://youtu.be/iYM2zFP3Zn0?si=cB1VHRk9zNEdBTtF) — visão prática do que cada header faz
- [MDN Web Docs: HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP) — referência oficial de headers e métodos

## 🛠️ Scope

### MVP

- Concluir os **Desafios 1–3 (aquecimento)** em `learn/04-Desafios.md`: adicionar um sétimo cabeçalho, criar a saída `--json` e adicionar a flag `--verbose`.
- Preservar no fluxo principal a requisição HTTPS, a avaliação dos cabeçalhos, a pontuação/nota e os códigos de saída já definidos pelo projeto.
- Demonstrar cada desafio com testes automatizados e uma execução da CLI.

### Stretch

- **Desafios 4–7 (intermediários):** múltiplas URLs, limite mínimo de nota, cache em disco e aviso sobre redirecionamento HTTP/HTTPS.

### Conquer

- **Desafios 8–11 (avançados):** escaneamento assíncrono, análise estática de CSP, monitoramento contínuo e comparação entre User-Agents.
- **Desafio 12 (especialista):** transformar o scanner em um serviço com API REST, incluindo validação contra SSRF, rate limiting, logs e deploy.
- **Outras direções:** modo para daltônicos, importação de HAR, diff contra baseline e modo `--strict`.

## ✅ Definition of Done

- [ ] `just test` passa (11 testes, rede simulada com respx)
- [ ] `just lint` passa (ruff + mypy --strict + pylint)
- [ ] `just run -- <url>` retorna nota e pontuação corretas
- [ ] Códigos de saída corretos para diferentes notas

## 🧪 Validation

```bash
just test       # executa o pytest (rede simulada, offline)
just lint       # ruff + mypy --strict + pylint
just run -- https://example.com
# Nota: B, Pontuação: 85 / 100
```

Teste com as [URLs de demonstração](#urls-de-demonstração) abaixo.

## 🎬 Demo

Execute o scanner em URLs conhecidas e explique:

- Como cada cabeçalho é avaliado e pontuado
- Por que alguns sites recebem nota A e outros B/C/F
- O que as recomendações sugerem para melhorar a nota

## 🚀 Getting Started

```
bash
sudo apt update
wget -qO- https://astral.sh/uv/install.sh | sh
uv venv --python 3.14
source .venv/bin/activate
./install.sh
just run -- https://example.com
```

> [!TIP]
> Este projeto utiliza o [`just`](https://github.com/casey/just) como executor de comandos. Digite `just` para ver todos os comandos disponíveis.
>
> Instalação: `curl -sSf https://just.systems/install.sh | bash -s -- --to ~/.local/bin`

## URLs de Demonstração

| URL                   | Nota esperada | Motivo                                              |
| --------------------- | ------------- | --------------------------------------------------- |
| `https://github.com`  | A             | CSP abrangente, HSTS com `includeSubDomains`        |
| `https://web.dev`     | A             | Conjunto moderno completo de cabeçalhos             |
| `https://mozilla.org` | A             | A Mozilla pratica o que o Observatory recomenda     |
| `https://example.com` | B / C         | Possui HSTS, mas não possui CSP, Permissions-Policy |
| `http://neverssl.com` | F             | Serve propositalmente apenas HTTP puro              |

> [!IMPORTANT]
> Sempre inclua o esquema `http://` ou `https://`. O scanner rejeita nomes de host sem esquema.

## Os Cabeçalhos Avaliados

| Header                      | Severidade | O que impede                                            |
| --------------------------- | ---------- | ------------------------------------------------------- |
| `Strict-Transport-Security` | alta       | SSL stripping em redes Wi-Fi públicas                   |
| `Content-Security-Policy`   | alta       | XSS por meio de tags `<script>` injetadas               |
| `X-Content-Type-Options`    | média      | MIME sniffing de arquivos enviados                      |
| `X-Frame-Options`           | média      | Clickjacking por meio de iframes ocultos                |
| `Referrer-Policy`           | baixa      | Vazamento de tokens secretos pelo Referer               |
| `Permissions-Policy`        | baixa      | Scripts de terceiros abusando de câmera, microfone etc. |

## Códigos de Saída

| Nota              | Código de saída | Significado                          |
| ----------------- | --------------- | ------------------------------------ |
| A, B              | `0`             | Sinal verde, nenhuma ação necessária |
| C, D              | `1`             | Vale a pena investigar               |
| F ou erro de rede | `2`             | Falha crítica, deve ser corrigida    |

## 📚 Learning Resources

| Módulo                                          | Tópico                                                    |
| ----------------------------------------------- | --------------------------------------------------------- |
| [00 - Introdução](learn/00-Introdução.md)       | Início rápido, pré-requisitos, saída esperada             |
| [01 - Conceitos](learn/01-Conceitos.md)         | O que é HTTP, o que é um header, ataques reais por header |
| [02 - Arquitetura](learn/02-Arquitetura.md)     | Pipeline de quatro etapas, dataclasses, I/O fence         |
| [03 - Implementação](learn/03-Implementação.md) | Explicação função por função                              |
| [04 - Desafios](learn/04-Desafios.md)           | Doze ideias de extensão                                   |

## 🔗 Referências externas

- MDN HTTP — https://developer.mozilla.org/en-US/docs/Web/HTTP
- OWASP Cheat Sheet: Secure Headers — https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html
- HTTP Security Headers (Mozilla Observatory docs) — https://observatory.mozilla.org/

## 🧭 Next Step

Após concluir `Headers`, avance para o projeto em equipe do mesmo ramo: [`V_Scanner`](../../Team/V_Scanner/README.md) — scanner de dependências Python em busca de vulnerabilidades (supply chain).

> [!NOTE]
> **Não é obrigatório** avançar imediatamente para o próximo projeto. Você pode trabalhar em múltiplos projetos primários em paralelo, respeitando as janelas de entrega do calendário.

---

@CarterPerez-dev | Copyright (C) 2026 Murilo Miacci
