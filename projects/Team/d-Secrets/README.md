# Secrets

![Team](https://img.shields.io/badge/Team-Red_Team-c62828)
![Mode](https://img.shields.io/badge/Mode-Team-555)
![Difficulty](https://img.shields.io/badge/Difficulty-N5_Especialista-red)
![Stack](https://img.shields.io/badge/Stack-Go-00ADD8)

> Scanner de segredos para bases de código e repositórios git, escrito em Go.

> [!NOTE]
> **Sucessor de:** [`Pass_Vault`](../../Individual/d-Pass_Vault/README.md) — do armazenamento seguro de segredos para a **detecção de segredos expostos**.

_Esta é uma visão geral rápida. Teoria de segurança, arquitetura e orientações completas estão nos [módulos de aprendizado](#learn)._

## 🎯 Objective

Construir um scanner que detecta segredos expostos (chaves, tokens, senhas, strings de conexão) em bases de código e histórico de repositórios git, com alta precisão e baixa taxa de falsos positivos.

## 🧠 Learning Outcomes

- O que é secret sprawl e por que segredos vazam para repositórios
- Detecção de segredos por regras, padrões e entropia de Shannon
- Verificação de vazamento via HIBP (k-anonimato — segredos nunca saem da máquina)
- Varredura de histórico git (branches, profundidade, intervalos de datas)
- Defesa contra falsos positivos em 5 camadas
- Go: pipeline concorrente, pools de workers, parsing de TOML

## � Caso tenha dificuldades com a base do projeto

> [!NOTE]
> Este projeto exige compreensão de detecção de segredos e análise de git. Se você travar na base, estes recursos ajudam a recuperar o fluxo.

- [Secret Scanning Explained — Google Cloud](https://www.youtube.com/watch?v=2Z2EMDgkX0k) — por que secret scanning importa
- [Git History and Secrets — freeCodeCamp.org](https://www.youtube.com/watch?v=UOc6-7Zl4cw) — varredura de repositórios e histórico
- [How Have I Been Pwned works — Troy Hunt](https://www.youtube.com/watch?v=n7Xc-4IwJ58) — introdução a k-anonimato e vazamentos

## 🛠️ Scope

### Obrigatório

- 150 regras de detecção (AWS, GitHub, GitLab, GCP, Azure, Slack, Stripe, Twilio, SendGrid, chaves SSH/PGP, senhas, strings de conexão, JWTs e mais)
- Análise de entropia de Shannon para strings de alta aleatoriedade
- Verificação de vazamento HIBP via protocolo de k-anonimato
- Varredura de diretórios e histórico completo do git
- Saída em tabelas coloridas, JSON ou SARIF v2.1.0
- Defesa contra falsos positivos em 5 camadas

### Mínimo viável (MVP)

- Detectar segredos por regras em um diretório
- Exibir resultados em texto simples

### Stretch

- Verificação HIBP via k-anonimato
- Varredura completa do histórico git
- Saída SARIF v2.1.0
- Pipeline concorrente com pools de workers limitados

## ✅ Definition of Done

- [ ] `portia scan .` detecta segredos em um diretório de teste
- [ ] `portia git <repo>` detecta segredos no histórico git
- [ ] Regras de detecção cobrindo os principais provedores
- [ ] Saída em terminal, JSON ou SARIF
- [ ] Baixa taxa de falsos positivos (validação com testdata)
- [ ] Completar pelo menos os Desafios Nível 1–3 listados em `learn/04-CHALLENGES.md` (ver `learn/04-CHALLENGES.md`)

## 🧪 Validation

```
bash
portia scan .
portia git <repo>
portia config rules
```

Teste com os arquivos em `testdata/`.

## 🎬 Demo

Execute o scanner em um repositório de exemplo e explique:

- Como as regras de detecção funcionam
- Como a entropia de Shannon identifica strings de alta aleatoriedade
- Como a verificação HIBP protege a privacidade (k-anonimato)
- Como a defesa contra falsos positivos funciona em 5 camadas

## 👥 Suggested Team Breakdown

| Workstream     | Responsabilidade                                                                         |
| -------------- | ---------------------------------------------------------------------------------------- |
| **Rules**      | Regras de detecção por provedor (AWS, GitHub, GCP, etc.)                                 |
| **Entropy**    | Análise de entropia de Shannon                                                           |
| **HIBP**       | Verificação de vazamento via protocolo de k-anonimato                                    |
| **Git**        | Varredura de histórico git (branches, profundidade, datas)                               |
| **FP Defense** | Defesa contra falsos positivos (pré-filtro, validação estrutural, stopwords, allowlists) |
| **Output**     | Saída em terminal, JSON, SARIF                                                           |
| **Pipeline**   | Pipeline concorrente com pools de workers                                                |

> **Dica:** as regras de detecção são naturalmente paralelizáveis — cada membro pode assumir um conjunto de provedores.

## Milestones

| Milestone       | Prazo estimado | Entregável (referência `learn/`)                                                       |
| --------------- | -------------- | -------------------------------------------------------------------------------------- |
| M1 — Fundação   | Semana 1       | CLI, estrutura de dados, varredura de diretório (ver `learn/00-OVERVIEW.md`)           |
| M2 — Regras     | Semana 2       | Regras de detecção para provedores principais (ver `learn/03-IMPLEMENTATION.md`)       |
| M3 — Entropy    | Semana 3       | Análise de entropia, defesa contra falsos positivos (ver `learn/03-IMPLEMENTATION.md`) |
| M4 — Git/HIBP   | Semana 4       | Varredura de histórico git, verificação HIBP (ver `learn/03-IMPLEMENTATION.md`)        |
| M5 — Integração | Semana 5       | Saída JSON/SARIF, pipeline concorrente, testes, demo (ver `learn/04-CHALLENGES.md`)    |

## 🚀 Getting Started

```
bash
curl -fsSL https://raw.githubusercontent.com/CarterPerez-dev/portia/main/install.sh | bash
```

Ou com Go:

```
bash
go install github.com/CarterPerez-dev/portia/cmd/portia@latest
portia scan .
```

> [!TIP]
> Este projeto usa [`just`](https://github.com/casey/just) como executor de comandos. Digite `just` para ver todos os comandos disponíveis.
>
> Instalação: `curl -sSf https://just.systems/install.sh | bash -s -- --to ~/.local/bin`

## Comandos

| Comando                 | Descrição                                                |
| ----------------------- | -------------------------------------------------------- |
| `portia scan [caminho]` | Escaneia um diretório em busca de segredos               |
| `portia git [repo]`     | Escaneia o histórico do git em busca de segredos         |
| `portia init`           | Inicializa a configuração `.portia.toml`                 |
| `portia pyproject`      | Cria `pyproject.toml` com a configuração `[tool.portia]` |
| `portia config rules`   | Lista todas as 150 regras de detecção                    |
| `portia config show`    | Mostra a configuração ativa                              |

**Flags:** `--format` (terminal/json/sarif), `--verbose`, `--no-color`, `--exclude`, `--max-size`, `--hibp`, `--config`

**Flags do Git:** `--branch`, `--since`, `--depth`, `--staged`

## 📚 Learning Resources

| Módulo                                           | Tópico                                                 |
| ------------------------------------------------ | ------------------------------------------------------ |
| [00 - Visão Geral](learn/00-OVERVIEW.md)         | Pré-requisitos e início rápido                         |
| [01 - Conceitos](learn/01-CONCEPTS.md)           | Secret sprawl, entropia, bancos de dados de vazamentos |
| [02 - Arquitetura](learn/02-ARCHITECTURE.md)     | Design do sistema e fluxo de dados                     |
| [03 - Implementação](learn/03-IMPLEMENTATION.md) | Passo a passo do código                                |
| [04 - Desafios](learn/04-CHALLENGES.md)          | Ideias de extensão e exercícios                        |

## 🔗 Referências externas

- HIBP API / k-anonimato — https://haveibeenpwned.com/API/v3
- GitGuardian / TruffleHog guides — https://www.gitguardian.com/
- Secret scanning research — artigos e guias indicados nos módulos `learn/`

## 🧭 Next Step

Após concluir `Secrets`, você terá completado o **Ramo D** (Secrets & Detection). Este projeto tem forte componente defensivo (detecção de exposição) e faz a ponte para a frente **Blue Team**. Avance para the [Purple Capstone](../../../PurpleTeam/README.md) ou explore projetos Blue.

> [!NOTE]
> **Não é obrigatório** avançar imediatamente para o próximo projeto. Você pode trabalhar em múltiplos projetos primários em paralelo, respeitando as janelas de entrega do calendário.

---

@CarterPerez-dev | Copyright (C) 2026 Murilo Miacci
