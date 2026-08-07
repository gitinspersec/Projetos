# 🔵 Blue Team — 2º Semestre

> [!NOTE]
> Esta frente reúne os projetos defensivos do Insper Sec para o **2º semestre**.

Se o Red Team procura entender como sistemas podem ser observados, testados e explorados em contexto autorizado, o Blue Team olha para o outro lado da mesma moeda: como detectar, proteger, monitorar e responder.

A proposta aqui é desenvolver a visão de quem cuida da saúde do sistema. Isso inclui análise de eventos, identificação de comportamento suspeito, prevenção, monitoramento, investigação e resposta a incidentes. Em vez de focar em "como atacar", o foco aqui é "como perceber, conter e corrigir".

> **Modelo semestral:** dentro do 2º semestre, o projeto **Individual** representa uma **entrega intermediária**, e o projeto **Team** representa a **entrega final do semestre**, com apresentação à Insper Sec.

## 🔵 Filosofia do Blue Team

O Blue Team **não copia a estrutura do Red Team**. Seu papel pedagógico é:

- **Observar** — coletar e interpretar eventos, tráfego e comportamento de sistemas;
- **Detectar** — identificar sinais de atividade suspeita ou comprometimento;
- **Investigar** — entender o que aconteceu, como e por quê;
- **Responder** — conter, erradicar e recuperar;
- **Endurecer** — reduzir a superfície de ataque e melhorar a postura defensiva.

Isso favorece projetos como:

- detecção de tráfego suspeito;
- monitoramento de host;
- integridade de dependências;
- proteção de segredos;
- contenção de comportamento malicioso.

## Estrutura das trilhas

A estrutura segue a mesma lógica geral dos projetos do Red Team:

- o projeto **Individual** introduz um problema central da trilha;
- o projeto **Team** amplia esse problema em direção a algo mais próximo da realidade operacional.

### Individual

| Projeto                  | Tema          | Descrição                                                        |
| ------------------------ | ------------- | ---------------------------------------------------------------- |
| `Canary_Token_Generator` | Detecção      | Geração de tokens canário para detecção de acesso não autorizado |
| `Metadata_Scrubber_Tool` | Endurecimento | Remoção de metadados sensíveis de arquivos                       |
| `Systemd_Persist_Scan`   | Detecção      | Detecção de persistência maliciosa via systemd                   |
| `V_Scanner`              | Supply chain  | Scanner de dependências Python (ponte com Red, perfil defensivo) |

### Team

| Projeto                        | Tema          | Descrição                                              |
| ------------------------------ | ------------- | ------------------------------------------------------ |
| `DLP_Scanner`                  | Prevenção     | Prevenção de vazamento de dados (Data Loss Prevention) |
| `Docker_Security_Audit`        | Endurecimento | Auditoria de segurança de containers Docker            |
| `Honeypot_Network`             | Detecção      | Rede de honeypots para detecção e análise de intrusão  |
| `SBOM_Generator&Vulnerability` | Supply chain  | Geração de SBOM e análise de vulnerabilidades          |

> [!NOTE]
> Os projetos Blue estão **em construção**. As pastas existem, mas ainda não contêm implementação ou documentação detalhada. Estes READMEs serão criados conforme os projetos forem implementados.

## O que você vai encontrar aqui

Cada projeto Blue deve ter sua própria documentação detalhada, explicando:

- qual problema defensivo ela aborda;
- por que esse problema é importante;
- como o projeto individual constrói a base;
- como o projeto em equipe expande essa base;
- quais conceitos técnicos aparecem no caminho;
- e o que o aluno deve ser capaz de entender ao final.

## Modelo de trilha

Quando uma trilha for adicionada, ela pode seguir este formato:

```markdown
## Trilha X — Nome da Trilha

> [!NOTE]
> Frase curta resumindo o foco da trilha.

Texto introdutório explicando o tema, o problema de segurança tratado e a progressão entre os dois projetos.

### `Projeto_Individual`

Descrição breve do projeto individual, com foco nos fundamentos.

### `Projeto_Team`

Descrição breve do projeto em equipe, destacando a evolução da trilha.
```

> [!TIP]
> Consulte o [mapa curricular completo](../docs/CURRICULUM.md) e os [padrões de README](../CONTRIBUTING.md#-padrões-de-readme) para as convenções padrão.
