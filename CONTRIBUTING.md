# 🤝 Contribuindo para o Sec_Projects

> Guia de contribuição para o repositório educacional do **Insper Sec**.

Obrigado por querer contribuir! Este repositório é uma trilha educacional, e toda contribuição deve manter a consistência pedagógica e documental.

---

## 📋 Antes de Contribuir

1. Leia o [`README.md`](./README.md) raiz para entender o mapa geral.
2. Leia o [`docs/CURRICULUM.md`](./docs/CURRICULUM.md) para entender a progressão e os ramos.
3. Leia a seção [Padrões de README](#-padrões-de-readme) abaixo — todo README deve seguir estas convenções.
4. Leia o [`docs/WORKFLOW.md`](./docs/WORKFLOW.md) para entender o workflow operacional.

---

## 🧭 Tipos de Contribuição

### 1. Novo Projeto

- Escolha uma frente (Red/Blue/Purple) e um ramo temático (A/B/C/D).
- Crie a pasta seguindo a convenção: `projects/<Modo>/letra-Nome_Projeto/`.
  - `<Modo>` é `Individual` ou `Team`
  - A frente (Red/Blue/Purple) é **metadados**, não parte do caminho
  - O exemplo: `projects/Individual/a-Hash_ID/` ou `projects/Team/b-V_Scanner/`
- Crie o README seguindo os [Padrões de README](#-padrões-de-readme).
- Crie a pasta `learn/` com os módulos 00–04.
- Adicione o projeto ao mapa curricular (`docs/CURRICULUM.md`) e à landing page unificada (`projects/README.md`).

### 2. Melhoria de Projeto Existente

- Leia o README do projeto para entender o contrato educacional.
- Siga o escopo (Obrigatório/MVP/Stretch) definido.
- Mantenha a consistência com os [Padrões de README](#-padrões-de-readme).

### 3. Correção de Documentação

- Corrija links quebrados, erros de markdown ou inconsistências.
- Garanta que o README reflita a implementação real.

### 4. Correção de Código

- Siga as convenções da stack do projeto (Python/uv, C++/CMake, Go).
- Adicione/atualize testes.
- Garanta que `just test` e `just lint` passem.

---

## 🚀 Fluxo de Trabalho

### 1. Crie uma branch

```bash
git checkout -b blackboxai/<sua-mudanca>
```

### 2. Faça as mudanças

- Siga as convenções documentais e de código.
- Atualize a documentação afetada.

### 3. Valide

- **Markdown:** rode `markdownlint` e `lychee` (ou o CI fará isso).
- **Código:** rode `just test` e `just lint` na pasta do projeto.

### 4. Commit

```bash
git add .
git commit -m "tipo: descrição clara da mudança"
```

Tipos de commit: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.

### 5. Push e Pull Request

```bash
git push origin blackboxai/<sua-mudanca>
```

Abra um PR descrevendo:

- O que foi feito;
- Por que foi feito;
- Como validar.

---

## 📄 Padrões de README

Todo README de projeto deve seguir estas convenções. Este é o **contrato educacional** padrão do repositório.

### Estrutura obrigatória

```
markdown
# Nome do Projeto

[Badges de metadata]

> Uma frase dizendo exatamente o que será construído.

## 🎯 Objective
## 🧠 Learning Outcomes
## 📋 Prerequisites
## 🛠️ Scope
## ✅ Definition of Done
## 🧪 Validation
## 🎬 Demo
## 🚀 Getting Started
## 📚 Learning Resources
## 🧭 Next Step
```

Para projetos **Team**, incluir também:

```markdown
## 👥 Suggested Team Breakdown

## Milestones
```

### Badges de metadata (topo)

Use badges apenas para metadata de alto valor:

```
markdown
![Team](https://img.shields.io/badge/Team-Red_Team-c62828)
![Mode](https://img.shields.io/badge/Mode-Individual-555)
![Difficulty](https://img.shields.io/badge/Difficulty-N3_Intermedi%C3%A1rio-yellow)
![Stack](https://img.shields.io/badge/Stack-Python-3776AB)
```

| Campo      | Valores possíveis                                                                 |
| ---------- | --------------------------------------------------------------------------------- |
| Team       | `Red_Team`, `Blue_Team`, `Purple_Team`                                            |
| Mode       | `Individual`, `Team`                                                              |
| Difficulty | `N1_Iniciante`, `N2_Básico`, `N3_Intermediário`, `N4_Avançado`, `N5_Especialista` |
| Stack      | Linguagem principal (ex: `Python`, `C++`, `Go`)                                   |

### Níveis de dificuldade

| Nível | Rótulo        | Cor do badge | Descrição                                                     |
| ----- | ------------- | ------------ | ------------------------------------------------------------- |
| N1    | Iniciante     | brightgreen  | Fundamentos, escopo contido, sem barreira de tooling          |
| N2    | Básico        | green        | Primeiros conceitos aplicados, tooling simples                |
| N3    | Intermediário | yellow       | Engenharia aplicada, exige domínio de conceitos e ferramentas |
| N4    | Avançado      | orange       | Projeto complexo, exige maturidade técnica e integração       |
| N5    | Especialista  | red          | Projeto de alto nível, exige domínio profundo e arquitetura   |

### Semântica de emoji (estável)

| Emoji | Significado                       |
| ----- | --------------------------------- |
| 🎯    | Objetivo / escopo                 |
| 🧠    | Aprendizado                       |
| 🛠️    | Stack / implementação             |
| 🧪    | Validação                         |
| ✅    | Conclusão / Definition of Done    |
| 📚    | Recursos / aprendizado            |
| ⚠️    | Atenção / aviso                   |
| 👥    | Colaboração / divisão de trabalho |

> Não use emoji decorativo sem função. Cada emoji deve ter semântica estável e consistente entre projetos.

### Convenções de nomenclatura

- **Dificuldade** é sempre explícita e separada do domínio/tema, usando os 5 níveis (N1–N5).
- **A/B/C/D** nos nomes de pasta indicam **ramo temático**, não dificuldade.
- Projetos **Team** sempre incluem `Suggested Team Breakdown` e `Milestones`.
- Links internos devem ser relativos e funcionais.

### Referências externas

Cada README de projeto deve incluir uma seção **🔗 Referências externas** apontando para fontes de aprendizado das tecnologias usadas (ex: C++ → learncpp.com, Go → tour.golang.org, Python → python.org/tutorial). Isso garante que um membro sem experiência prévia tenha um ponto de partida claro.

### O que estudar antes

Cada README de projeto deve incluir, na seção Prerequisites, uma subseção **📖 O que estudar antes** recomendando fontes externas para o estudo prévio da stack. Seja transparente: a maioria das linguagens **são ensinadas** nos projetos, mas um estudo básico prévio evita frustração.

---

## ✅ Checklist de Qualidade

Antes de abrir um PR, verifique:

- [ ] README segue os [Padrões de README](#-padrões-de-readme)
- [ ] Badges de metadata no topo (Team, Mode, Difficulty, Stack)
- [ ] Escopo dividido em Obrigatório / MVP / Stretch
- [ ] Definition of Done objetivo e verificável
- [ ] Validação com comandos e critérios observáveis
- [ ] Links para `learn/` funcionais
- [ ] Next Step definido
- [ ] Emojis com semântica estável
- [ ] Projetos Team com divisão de trabalho e milestones
- [ ] Links internos funcionais
- [ ] Markdown válido (sem erros de lint)
- [ ] Código passa em `just test` e `just lint`

---

## ⚠️ Aviso Legal

> Todos os projetos deste repositório devem ser executados somente em ambientes próprios ou explicitamente autorizados. O uso indevido das ferramentas aqui desenvolvidas é de responsabilidade exclusiva do usuário.

---

## 📚 Referências

- [Mapa curricular](./docs/CURRICULUM.md)
- [Padrões de README](#-padrões-de-readme)
- [Guia de workflow](./docs/WORKFLOW.md)
- [Guia de demo](./docs/DEMO_GUIDE.md)
