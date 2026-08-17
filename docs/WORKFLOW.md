# 🧭 Guia Central de Workflow — Sec_Projects

> Documento transversal de referência operacional. Este guia explica **como agir em todo o workflow do repositório**: comandos, passo a passo, estrutura, entregas de projeto e validação.

---

## 1. Visão Geral do Repositório

O `Sec_Projects` é uma **trilha educacional** de cibersegurança, organizada em **três semestres**:

|     Frente      | Semestre | Cor |    Foco    | Papel pedagógico                                                    |
| :-------------: | :------: | :-: | :--------: | ------------------------------------------------------------------- |
|  **Red Team**   |    1º    | 🔴  |  Ofensivo  | Observar, mapear, testar e explorar sistemas em contexto autorizado |
|  **Blue Team**  |    2º    | 🔵  | Defensivo  | Observar, detectar, investigar, responder e endurecer sistemas      |
| **Purple Team** |   3º+    | 💜  | Integração | Executar Red → detectar Blue → refletir e melhorar a trilha         |

> **Modelo semestral:** dentro de cada semestre, o projeto **Individual** representa uma **entrega intermediária**, e o projeto **Team** representa a **entrega final do semestre**, com apresentação à Insper Sec.

Cada projeto tem um **README** (contrato educacional) e uma pasta **`learn/`** (teoria, arquitetura e implementação).

---

## 2. Estrutura de Pastas

```text
Sec_Projects/
├── README.md                    # Landing page raiz
├── CONTRIBUTING.md              # Guia de contribuição
├── LICENSE
├── docs/
│   ├── CURRICULUM.md            # Mapa curricular (progressão, ramos, dificuldades)
│   ├── WORKFLOW.md              # Este guia — workflow central
│   └── DEMO_GUIDE.md            # Guia de demo/apresentação
├── projects/
│   ├── README.md                # Landing page unificada de projetos
│   ├── Individual/              # Projetos individuais (Red/Blue/Purple)
│   └── Team/                    # Projetos em equipe (Red/Blue/Purple)
└── submissions/
    ├── README.md                # Instruções de entrega
    ├── Individual/              # Entregas individuais por aluno
    └── Team/                    # Entregas de equipe
```

### Convenção de nomes de pasta

- **`a-`**, **`b-`**, **`c-`**, **`d-`** = **ramo temático** (domínio), **não** dificuldade.
  - A: Cryptography & Hashing
  - B: Web & Supply Chain
  - C: Network Security
  - D: Secrets & Detection
- A **dificuldade** é sempre explícita no README (badge `Difficulty`), separada do tema.
- Os projetos estão organizados fisicamente por tipo (`Individual/` ou `Team/`), não por frente (Red/Blue/Purple).
- A frente é metadados/documentação, não uma pasta de primeiro nível.

---

## 3. Estrutura de um Projeto

Cada projeto segue este layout padrão:

```text
projeto/
├── README.md          # Contrato educacional (segue padroes do CONTRIBUTING.md)
├── DEMO.md            # Roteiro de demonstração (se aplicável)
├── install.sh         # Script de instalação (padrão)
├── justfile           # Executor de comandos (just)
├── pyproject.toml     # Python (uv) | CMakeLists.txt (C++) | go.mod (Go)
├── assets/            # Imagens, capturas, gifs
├── learn/             # Módulos de teoria (00..04)
├── src/ ou internal/  # Código-fonte
└── tests/ ou testdata/ # Testes e dados de teste
```

---

## 4. Comandos Padrão

### Executor de comandos: `just`

Todos os projetos usam [`just`](https://github.com/casey/just) como executor de comandos.

```bash
just            # lista todos os comandos disponíveis
```

### Projetos Python (Hash_ID, Headers, Pass_Vault, Net_Analyzer/python)

```bash
# Instalação (na pasta do projeto)
./install.sh                # instala uv, just e dependências

# Ambiente virtual
uv venv --python 3.14
source .venv/bin/activate

# Comandos comuns
just test       # executa pytest
just lint       # ruff + mypy --strict + pylint
just format     # yapf
just run -- <args>  # executa a ferramenta
```

### Projetos C++ (Port_Scanner, Hash_Cracker, Net_Analyzer/cpp)

```bash
# Compilação com CMake
mkdir build && cd build
cmake ..
make

# Comandos comuns
just run -- <args>   # executa a ferramenta
```

### Projetos Go (V_Scanner, Secrets)

```bash
# Instalação
go install github.com/<repo>/cmd/<tool>@latest

# Comandos comuns
just run -- <args>   # executa a ferramenta
```

---

## 5. Workflow de Entrega de um Projeto

Cada projeto é entregue seguindo este fluxo:

### 5.1 Antes de começar

1. Leia o [`README.md`](../README.md) raiz para entender o mapa geral.
2. Leia [`projects/README.md`](../projects/README.md) para explorar os ramos e projetos.
3. Escolha um ramo temático (A/B/C/D) e um projeto.
4. Leia o **README do projeto** em [`projects/Individual/`](../projects/Individual/) ou [`projects/Team/`](../projects/Team/) — é o contrato educacional.
5. Leia os módulos **`learn/`** em ordem (00 → 04).

### 5.2 Durante o desenvolvimento

1. Siga o **Scope** do README:
   - **Obrigatório** — o que deve existir ao final.
   - **Mínimo viável (MVP)** — o menor entregável que satisfaz o objetivo.
   - **Stretch** — extensões opcionais.
2. Use `just` para testar, lintar e formatar.
3. Valide o projeto com os comandos da seção **Validation**.

### 5.3 Critérios de conclusão (Definition of Done)

Todo projeto é considerado concluído quando:

- [ ] O escopo **obrigatório** está implementado
- [ ] Todos os testes automatizados passam (`just test`)
- [ ] O lint passa (`just lint`)
- [ ] A validação da seção `Validation` do README foi executada com sucesso
- [ ] A demo foi executada e documentada (ver [`docs/DEMO_GUIDE.md`](./DEMO_GUIDE.md))

### 5.4 Entrega final

1. Execute a **demo** (ver [`docs/DEMO_GUIDE.md`](./DEMO_GUIDE.md)).
2. Documente o que foi feito, decisões técnicas e dificuldades.
3. Crie a entrega dentro de `submissions/` usando o modelo de [`submissions/README.md`](../submissions/README.md).
4. Siga o **Next Step** do README para avançar.

---

## 5.5 Workflow Git e Pull Request (passo a passo)

> [!NOTE]
> Se você nunca usou Git para abrir um PR, siga **exatamente** estes comandos. Cada um é explicado.

### 1. Verifique o estado do repositório

```bash
# Entra na pasta do repositório (se ainda não estiver nela)
cd Sec_Projects

# Mostra a branch atual e arquivos modificados
git status
```

### 2. Atualize o repositório antes de começar

```bash
# Baixa as alterações mais recentes do remoto
git pull origin main
```

### 3. Crie uma branch para o seu trabalho

```bash
# Cria e já entra na branch. Use um nome descritivo.
git switch -c nome-da-branch
```

### 4. Faça as mudanças nos arquivos

Edite os arquivos normalmente (READMEs, código, etc.). Depois, verifique o que mudou:

```bash
git status
```

### 5. Adicione os arquivos ao "stage"

```bash
# Adiciona TODOS os arquivos modificados
git add .

# OU adicione arquivos específicos
git add projects/Individual/a-Hash_ID/README.md
```

### 6. Crie um commit com mensagem clara

```bash
git commit -m "docs: atualiza README do Hash_ID"
```

> **Convenção de mensagens:** use `feat:` para nova funcionalidade, `fix:` para correção, `docs:` para documentação, `refactor:` para refatoração, `test:` para testes.

### 7. Envie a branch para o GitHub

```bash
git push origin nome-da-branch
```

### 8. Abra um Pull Request (PR)

1. Acesse o repositório no GitHub.
2. Clique em **"Compare & pull request"** (aparece após o push).
3. Certifique-se de que a entrega esteja na pasta `submissions/<Modo>/<NomeDoAlunoOuEquipe>/<NomeDoProjeto>/`.
4. Descreva:
   - **O que foi feito** — resumo das mudanças;
   - **Por que foi feito** — motivação;
   - **Como validar** — comandos de teste/validação e local da entrega;
5. Clique em **"Create pull request"**.

### 9. Após o PR ser aprovado e mesclado

```bash
# Volta para a branch principal
git checkout main

# Atualiza com as mudanças mescladas
git pull origin main
```

> [!NOTE]
> O avaliador responsável deve receber a entrega formatada em `submissions/` e com o `README.md` de entrega preenchido.

> [!TIP]
> Se tiver conflitos no PR, o GitHub indica. Para resolver, atualize sua branch:

```bash
git checkout nome-da-branch
git pull origin main
# Resolva os conflitos nos arquivos indicados
git add .
git commit -m "fix: resolve conflitos"
git push origin nome-da-branch
```

---

## 6. Projetos Individual vs Team

### Projetos Individual

- Foco em **fundamentos** e **autonomia**.
- Escopo contido, sem divisão de trabalho.
- O membro deve completar sozinho.

### Projetos Team

- Foco em **integração** e **engenharia**.
- Exigem divisão de trabalho (ver seção `Suggested Team Breakdown` no README).
- Exigem **milestones** (ver seção `Milestones` no README).
- A integração entre submódulos é parte do aprendizado.

**Workflow Team recomendado:**

1. **Kickoff** — leiam o README juntos, definam papéis e milestones.
2. **Paralelo** — cada membro trabalha em um workstream (usando a divisão sugerida).
3. **Integração** — unifiquem os submódulos, resolvam conflitos.
4. **Teste** — validem o conjunto completo.
5. **Demo** — apresentem o resultado integrado.

---

## 7. Ferramentas e Convenções

| Ferramenta         | Uso                                            |
| ------------------ | ---------------------------------------------- |
| `just`             | Executor de comandos (test, lint, run, format) |
| `uv`               | Gerenciador de pacotes Python                  |
| `pytest`           | Testes Python                                  |
| `ruff/mypy/pylint` | Lint e type-check Python                       |
| `yapf`             | Formatação Python                              |
| `CMake`            | Build system C++                               |
| `go`               | Toolchain Go                                   |
| `markdownlint`     | Lint de Markdown (CI)                          |
| `lychee`           | Verificação de links (CI)                      |

### Convenções documentais

- Todos os READMEs seguem os [padrões de README](../CONTRIBUTING.md#-padrões-de-readme).
- Emojis têm semântica estável (🎯 objetivo, 🧠 aprendizado, 🛠️ stack, 🧪 validação, ✅ conclusão, 📚 recursos, ⚠️ atenção, 👥 colaboração).
- Links internos são relativos e funcionais.
- A/B/C/D = ramo temático, não dificuldade.

---

## 8. Validação por Stack

| Stack  | Validação típica                                        |
| ------ | ------------------------------------------------------- |
| Python | `just test` (pytest), `just lint`, `just run -- <args>` |
| C++    | Compilação CMake sem erros, `just run -- <args>`        |
| Go     | `go test ./...`, `go vet ./...`, `just run -- <args>`   |
| Geral  | Executar a ferramenta e verificar saída esperada        |

---

## 9. CI / Integração Contínua

O repositório usa GitHub Actions para manter a documentação viva:

- **`.github/workflows/docs-check.yml`** — roda `markdownlint` e `lychee` (link check) em todos os `*.md`.

Ao criar ou editar READMEs, garanta:

- Markdown válido (sem erros de lint).
- Links internos funcionais.
- Badges e seções conforme o template.

---

## 10. Contribuição

Para contribuir com novos projetos, correções ou melhorias, siga [`CONTRIBUTING.md`](../CONTRIBUTING.md).

---

## 11. Referências Rápidas

| Documento                                                  | Conteúdo                                 |
| ---------------------------------------------------------- | ---------------------------------------- |
| [`CURRICULUM.md`](./CURRICULUM.md)                         | Progressão, ramos, dificuldades, esforço |
| [Padrões de README](../CONTRIBUTING.md#-padrões-de-readme) | Convenções e contrato educacional padrão |
| [`DEMO_GUIDE.md`](./DEMO_GUIDE.md)                         | Guia de demo/apresentação                |
| [`CONTRIBUTING.md`](../CONTRIBUTING.md)                    | Guia de contribuição                     |

---

Este guia é o **ponto central de consulta** para qualquer dúvida operacional sobre o repositório. Se algo não estiver claro, consulte os documentos vinculados antes de perguntar.
