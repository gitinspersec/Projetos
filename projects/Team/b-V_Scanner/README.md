# V_Scanner

![Team](https://img.shields.io/badge/Team-Red_Team-c62828)
![Mode](https://img.shields.io/badge/Mode-Team-555)
![Difficulty](https://img.shields.io/badge/Difficulty-N4_Avan%C3%A7ado-orange)
![Stack](https://img.shields.io/badge/Stack-Go-00ADD8)

> Atualizador de dependências Python e scanner de vulnerabilidades rápido escrito em Go.

> [!NOTE]
> **Sucessor de:** [`Headers`](../../Individual/b-Headers/README.md) — da inspeção de headers HTTP para a análise da cadeia de dependências (supply chain).

_Esta é uma visão geral rápida — teoria de segurança, arquitetura e orientações completas estão nos [módulos de aprendizado](#learn)._

## 🎯 Objective

Construir uma ferramenta em Go que escaneia dependências Python (`pyproject.toml` e `requirements.txt`) em busca de vulnerabilidades conhecidas (CVEs) via OSV.dev, e atualiza as dependências para versões seguras e estáveis.

## 🧠 Learning Outcomes

- O que é supply chain security e por que dependências são uma superfície de ataque
- Como funciona o OSV.dev e a consulta a vulnerabilidades conhecidas
- Parsing de versões PEP 440 e filtragem de pre-releases
- Consultas paralelas ao PyPI com cache local (ETag)
- Go: CLI, parsing de arquivos, concorrência, configuração TOML
- Atualização de arquivos preservando comentários e formatação

## � Caso tenha dificuldades com a base do projeto

> [!NOTE]
> Este projeto combina Go, análise de dependências e consulta a APIs. Se você travar na base, estes recursos práticos ajudam.

- [Learn Go in 1 Hour — freeCodeCamp.org](https://www.youtube.com/watch?v=YS4e4q9oBaU) — visão geral rápida de Go
- [Go CLI Tutorial — Tech With Tim](https://www.youtube.com/watch?v=ysEN5RaKOlA) — construção de ferramentas de linha de comando em Go
- [Supply Chain Security Overview — OWASP](https://www.youtube.com/watch?v=5D0GKaNkr4A) — introdução prática ao problema de segurança de dependências

## 🛠️ Scope

### Obrigatório

- Escanear `pyproject.toml` e `requirements.txt` em busca de CVEs via OSV.dev
- Atualizar todas as dependências Python para versões estáveis mais recentes
- Consultas paralelas ao PyPI com cache local de ETag
- Parsing completo de versões PEP 440 com filtragem de pre-releases
- Atualizações de arquivos que preservam comentários e formatação
- Configurável via `.angela.toml` ou `[tool.angela]` no `pyproject.toml`

### Mínimo viável (MVP)

- Escanear `requirements.txt` em busca de CVEs
- Exibir vulnerabilidades encontradas em texto simples

### Stretch

- Atualização automática de dependências
- Cache local de ETag para velocidade
- Configuração via TOML
- Integração com CI

## ✅ Definition of Done

- [ ] `angela scan` identifica CVEs em dependências Python
- [ ] `angela update` atualiza dependências preservando comentários
- [ ] Parsing PEP 440 correto com filtragem de pre-releases
- [ ] Consultas paralelas ao PyPI com cache funcionando
- [ ] Testes automatizados passam
- [ ] Completar pelo menos os Desafios Nível 1–3 listados em `learn/04-CHALLENGES.md` (ver `learn/04-CHALLENGES.md`)

## 🧪 Validation

```bash
go install github.com/CarterPerez-dev/angela/cmd/angela@latest
angela scan
```

Teste com os arquivos em `testdata/` (`pyproject.toml` e `requirements.txt`).

## 🎬 Demo

Execute o scanner em um projeto Python de exemplo e explique:

- Como o OSV.dev é consultado e quais vulnerabilidades são encontradas
- Como o parsing PEP 440 funciona e por que pre-releases são filtrados
- Como as atualizações preservam comentários e formatação
- Como o cache de ETag acelera consultas repetidas

## 👥 Suggested Team Breakdown

| Workstream  | Responsabilidade                                                 |
| ----------- | ---------------------------------------------------------------- |
| **CLI**     | Interface de linha de comando, flags, comandos                   |
| **Config**  | Parsing de `.angela.toml` e `[tool.angela]`                      |
| **PyPI**    | Consultas paralelas ao PyPI, cache de ETag                       |
| **OSV**     | Consulta a vulnerabilidades via OSV.dev                          |
| **Parsing** | Parsing de `pyproject.toml`, `requirements.txt`, versões PEP 440 |
| **Update**  | Atualização de arquivos preservando comentários e formatação     |
| **UI**      | Saída de terminal, tabelas, progresso                            |

> **Dica:** defina as interfaces entre módulos primeiro (ex: formato de dados de dependência) para permitir desenvolvimento paralelo.

## Milestones

| Milestone       | Prazo estimado | Entregável (referência `learn/`)                                                    |
| --------------- | -------------- | ----------------------------------------------------------------------------------- |
| M1 — Fundação   | Semana 1       | CLI, parsing de `requirements.txt`, estrutura de dados (ver `learn/00-OVERVIEW.md`) |
| M2 — OSV        | Semana 2       | Consulta a OSV.dev e exibição de vulnerabilidades (ver `learn/01-CONCEPTS.md`)      |
| M3 — PyPI       | Semana 3       | Consultas paralelas ao PyPI, cache de ETag (ver `learn/03-IMPLEMENTATION.md`)       |
| M4 — Update     | Semana 4       | Atualização de arquivos preservando formatação (ver `learn/03-IMPLEMENTATION.md`)   |
| M5 — Integração | Semana 5       | Configuração TOML, testes, demo (ver `learn/04-CHALLENGES.md`)                      |

## 🚀 Getting Started

```bash
go install github.com/CarterPerez-dev/angela/cmd/angela@latest
angela scan
```

> [!TIP]
> Este projeto usa o [`just`](https://github.com/casey/just) como executor de comandos. Digite `just` para ver todos os comandos disponíveis.
>
> Instalação: `curl -sSf https://just.systems/install.sh | bash -s -- --to ~/.local/bin`

## Comandos

| Comando              | Descrição                                                                 |
| -------------------- | ------------------------------------------------------------------------- |
| `angela init`        | Inicializa um novo arquivo de configuração `.angela.toml`                 |
| `angela update`      | Atualiza todas as dependências Python para versões estáveis mais recentes |
| `angela check`       | Visualiza atualizações disponíveis sem modificar os arquivos              |
| `angela scan`        | Escaneia dependências em busca de CVEs conhecidas via OSV.dev             |
| `angela cache clear` | Limpa o cache local de ETag e de versões                                  |

## 📚 Learning Resources

| Módulo                                           | Tópico                             |
| ------------------------------------------------ | ---------------------------------- |
| [00 - Visão Geral](learn/00-OVERVIEW.md)         | Pré-requisitos e início rápido     |
| [01 - Conceitos](learn/01-CONCEPTS.md)           | Supply chain, OSV.dev, PEP 440     |
| [02 - Arquitetura](learn/02-ARCHITECTURE.md)     | Design do sistema e fluxo de dados |
| [03 - Implementação](learn/03-IMPLEMENTATION.md) | Passo a passo do código            |
| [04 - Desafios](learn/04-CHALLENGES.md)          | Ideias de extensão e exercícios    |

## 🔗 Referências externas

- Tour of Go — https://go.dev/tour/
- OSV.dev docs — https://osv.dev/
- PEP 440 — https://peps.python.org/pep-0440/

## 🧭 Next Step

Após concluir `V_Scanner`, você terá completado o **Ramo B** (Web & Supply Chain). Este projeto faz a ponte para a frente **Blue Team** (perfil defensivo de supply chain). Avance para o [Purple Capstone](../../../PurpleTeam/README.md) ou explore projetos Blue.

> [!NOTE]
> **Não é obrigatório** avançar imediatamente para o próximo projeto. Você pode trabalhar em múltiplos projetos primários em paralelo, respeitando as janelas de entrega do calendário.

---

@CarterPerez-dev | Copyright (C) 2026 Murilo Miacci
