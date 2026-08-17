# 🗺️ Mapa Curricular — Insper Sec Projects

> Documento transversal que define a progressão, os ramos temáticos, os níveis de dificuldade e a relação entre os projetos do repositório.

---

## 1. Filosofia

O repositório é uma **trilha educacional**, não um inventário de ferramentas. Cada projeto tem um papel pedagógico claro: ensinar um conjunto de conceitos, exigir um esforço previsível e preparar o membro para o próximo passo.

A progressão geral continua sendo organizada em **semestres e frentes**, mas o **semestre atual (2026/2)** tem uma composição específica: o **Blue Team** é composto por membros mais antigos, o **Red Team** reúne os membros que estão entrando e o **Purple Team** ainda não está ativo neste período.

A estrutura didática geral é:

- **Red Team:** onboarding, fundamentos, observação, mapeamento e exploração em contexto autorizado.
- **Blue Team:** mesma trilha-base do Red Team, com revisão e aprofundamento aplicado em prática.
- **Purple Team:** integração ofensiva/defensiva, a ser estruturada em uma etapa futura.

Dentro de cada semestre, a progressão **não é linear**. O currículo é organizado em **ramos temáticos paralelos**, cada um com sua própria cadeia de projetos (Individual → Team).

---

## 2. Frentes (Teams) e Semestres

|  Frente atual   |   Perfil do grupo    | Situação neste semestre | Papel pedagógico                                                     |
| :-------------: | :------------------: | :---------------------: | -------------------------------------------------------------------- |
|  **Red Team**   |   membros entrando   |          ativa          | onboarding, base técnica e exploração em contexto autorizado         |
|  **Blue Team**  | membros mais antigos |          ativa          | mesma trilha-base do Red Team, com revisão e aprofundamento aplicado |
| **Purple Team** |      integração      |     ainda não ativo     | será estruturado mais para frente                                    |

> **Modelo do semestre atual:** o projeto **Individual** representa uma entrega intermediária, e o projeto **Team** representa a entrega final do semestre. Neste ciclo, o **Blue Team e o Red Team compartilham o mesmo catálogo de 8 projetos**, com o **team misto** entre os grupos e a mesma janela de trabalho.

> **Calendário do semestre atual:**
>
> - **Red Team / Blue Team (individuais):** 09/09 a 07/10
> - **Blue Team / Red Team (mesmo catálogo):** 20/08 a 08/10 para revisão e aprofundamento
> - **Team (comum a ambos):** 14/10 a 02/12

---

## 3. Níveis de Dificuldade

A dificuldade é **sempre explícita e separada do domínio/tema**. As letras A/B/C/D nos nomes de pasta indicam **ramo temático**, não dificuldade.

São **5 níveis de dificuldade**, de N1 a N5:

| Nível | Rótulo        | Descrição                                                     |
| ----- | ------------- | ------------------------------------------------------------- |
| N1    | Iniciante     | Fundamentos, escopo contido, sem barreira de tooling          |
| N2    | Básico        | Primeiros conceitos aplicados, tooling simples                |
| N3    | Intermediário | Engenharia aplicada, exige domínio de conceitos e ferramentas |
| N4    | Avançado      | Projeto complexo, exige maturidade técnica e integração       |
| N5    | Especialista  | Projeto de alto nível, exige domínio profundo e arquitetura   |

---

## 4. Ramos Temáticos (Red Team — 1º Semestre)

Os projetos Red são organizados em **quatro ramos temáticos paralelos**:

| Ramo  | Tema                   | Individual     | Team           | Dificuldade (Ind → Team) |
| ----- | ---------------------- | -------------- | -------------- | ------------------------ |
| **A** | Cryptography & Hashing | `Hash_ID`      | `Hash_Cracker` | N1 → N4                  |
| **B** | Web & Supply Chain     | `Headers`      | `V_Scanner`    | N2 → N4                  |
| **C** | Network Security       | `Port_Scanner` | `Net_Analyzer` | N3 → N5                  |
| **D** | Secrets & Detection    | `Pass_Vault`   | `Secrets`      | N4 → N5                  |

> **Nota sobre o Ramo B:** `V_Scanner` é um scanner de **dependências Python / supply chain** (Go, OSV.dev, PyPI), não um scanner de vulnerabilidades web genérico. Ele faz a ponte entre o tema web (`Headers`) e a frente defensiva (Blue Team).

---

## 5. Grafo de Progressão

```mermaid
flowchart TD
    F[Onboarding: Git + terminal + programação básica]

    F --> H1[Hash_ID · N1]
    F --> W1[Headers · N2]
    F --> N1[Port_Scanner · N3]
    F --> C1[Pass_Vault · N4]

    H1 --> H2[Hash_Cracker · N4]
    W1 --> V1[V_Scanner · N4]
    N1 --> N2[Net_Analyzer · N5]
    C1 --> S1[Secrets · N5]

    H2 & V1 & N2 & S1 --> R[Red Team — Competências do 1º Semestre]

    R --> B[Blue Team — 2º Semestre]
```

> Todos os 8 projetos consolidados pertencem ao **Red Team** (1º semestre). O Blue Team (2º semestre) e o Purple Team (3º+ semestre) são fases posteriores da trilha.

---

## 6. Planejamento Acadêmico (não consolidado)

Os nomes abaixo aparecem como **planejamento didático**, mas **não fazem parte do catálogo ativo do semestre**. O conteúdo consolidado e executado no repositório continua sendo o mesmo conjunto de 8 projetos da trilha-base do Red Team.

### Planejamento não consolidado

- `Canary_Token_Generator` — geração de tokens canário para detecção de acesso não autorizado
- `Metadata_Scrubber_Tool` — remoção de metadados sensíveis de arquivos
- `Systemd_Persist_Scan` — detecção de persistência via systemd
- `DLP_Scanner` — prevenção de vazamento de dados
- `Docker_Security_Audit` — auditoria de segurança de containers
- `Honeypot_Network` — rede de honeypots para detecção de intrusão
- `SBOM_Generator&Vulnerability` — geração de SBOM e análise de vulnerabilidades

> [!NOTE]
> Esses itens não substituem o catálogo em execução do semestre. O modelo atual é: **Blue Team e Red Team seguem os mesmos 8 projetos consolidados**.

---

## 7. Purple Team (3º+ Semestre)

Em construção. 🏗️

---

## 8. Resumo de Dificuldade por Projeto

| Projeto        | Modo       | Dificuldade   | Nível |
| -------------- | ---------- | ------------- | ----- |
| `Hash_ID`      | Individual | Iniciante     | N1    |
| `Headers`      | Individual | Básico        | N2    |
| `Port_Scanner` | Individual | Intermediário | N3    |
| `Pass_Vault`   | Individual | Avançado      | N4    |
| `Hash_Cracker` | Team       | Avançado      | N4    |
| `V_Scanner`    | Team       | Avançado      | N4    |
| `Net_Analyzer` | Team       | Especialista  | N5    |
| `Secrets`      | Team       | Especialista  | N5    |

---

## 9. Onboarding

1. Leia o [`README.md`](../README.md) raiz.
2. Leia a [`trilha de projetos unificada`](../projects/README.md) para explorar os ramos temáticos.
3. Comece pelo projeto **Individual** do ramo escolhido em [`projects/Individual/`](../projects/Individual/).
4. Siga para o projeto **Team** do mesmo ramo em [`projects/Team/`](../projects/Team/) (entrega final do semestre).
5. Ao final do semestre, avance para o **Blue Team** (2º semestre) — projetos em [`projects/Individual/`](../projects/Individual/) e [`projects/Team/`](../projects/Team/).
6. No 3º+ semestre, participe do **Purple Team**.
