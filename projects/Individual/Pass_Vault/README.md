# Pass Vault

![Mode](https://img.shields.io/badge/Mode-Individual-402)
![Difficulty](https://img.shields.io/badge/Difficulty-N4_Avan%C3%A7ado-orange)
![Stack](https://img.shields.io/badge/Stack-Python-3776AB)

> Gerenciador de senhas de linha de comando criptografado — derivação de chave Argon2id, criptografia autenticada AES-256-GCM, escritas atômicas e duráveis, bloqueio de arquivo consultivo (advisory file locking). Uma senha mestra protege cada credencial que você confia a ele.

_Esta é uma visão geral rápida — teoria de segurança, arquitetura e orientações completas estão nos [/learn](./learn/00-Introdução.md)._

> [!NOTE]
> O projeto assume que não há experiência prévia com Python, mas avança mais rápido. O código-fonte é fortemente comentado como auxílio didático, a pasta `learn/` explica cada ideia criptográfica do zero, e cada recurso do Python é introduzido quando aparece pela primeira vez.

## 🎯 Objective

Construir um gerenciador de senhas de linha de comando que armazena credenciais em um arquivo criptografado, protegido por uma senha mestra, com derivação de chave Argon2id, criptografia autenticada AES-256-GCM e escritas atômicas e duráveis.

## 🧠 Learning Outcomes

- O que é criptografia, KDFs, Argon2id, salts, AES-GCM, nonces
- Modelagem de ameaça: o que o projeto protege e o que não protege
- Derivação de chave a partir de senha (Argon2id)
- Criptografia autenticada (AES-256-GCM) — confidencialidade + integridade
- Escritas atômicas e duráveis (tmp → fsync → rename → fsync)
- Bloqueio de arquivo consultivo (fcntl) para concorrência
- Geração de senhas criptograficamente seguras (`secrets`, nunca `random`)

## � Caso tenha dificuldades com a base do projeto

> [!NOTE]
> Este projeto ensina criptografia aplicada e práticas de I/O nos módulos `learn/`. Se você tiver dúvidas sobre os fundamentos, estes recursos ajudam.

- [Python Cryptography Tutorial — freeCodeCamp.org](https://youtu.be/kb_scuDUHls?si=uNTS1JHybxxd_bqF) — uso prático de bibliotecas de criptografia em Python
- [Password Storage Tier List](https://youtu.be/qgpsIBLvrGY?si=bXGNiS0lraiaP7ZZ) — entenda por que Argon2 é usado para senhas
- [Key Exchange (Diffie-Hellman) - Computerphile](https://youtu.be/NmM9HA2MQGI?si=2S0oPa6cRwxg99q4) — visão geral de criptografia aplicada

## 🛠️ Scope

### MVP

- Concluir os **Desafios de Nível 1 (1–4)** em `learn/04-Desafios.md`: `search`, `count`, timestamp de último uso e ocultação de senha com `--show`.
- Manter o vault criptografado, os comandos básicos (`init`, `add`, `get`, `list`) e as garantias de senha mestra, escrita atômica, permissões e concorrência que formam a base do projeto.
- Demonstrar cada desafio com testes automatizados e uma execução da CLI.

### Stretch

- **Nível 2 (5–8):** export/import seguro, pontuação de força, cópia para a área de transferência e verificação opcional no `init`.

### Conquer

- **Nível 3 (9–12):** TOTP, atualização transparente do custo do KDF, backups versionados com restauração e UI web local.
- **Nível 4 (13–15):** auditoria do modelo de ameaça de um gerenciador real, leitor do formato de vault em outra linguagem e modelagem de uma fraqueza deliberada.

## ✅ Definition of Done

- [ ] `just test` passa (mais de 60 testes cobrindo criptografia, vault e gerador)
- [ ] `just lint` passa (ruff + mypy + pylint)
- [ ] `pv init`, `pv add`, `pv get`, `pv list` funcionam corretamente
- [ ] Vault criptografado com AES-256-GCM e Argon2id
- [ ] Escritas atômicas e bloqueio de arquivo funcionando

## 🧪 Validation

```bash
just test       # executa o pytest (mais de 60 testes)
just test-cov   # testes + relatório de cobertura
just lint       # ruff + mypy + pylint
just run -- init
just run -- add github
just run -- get github
```

> [!IMPORTANT]
> O `pv` **nunca** aceita a senha mestra como flag de CLI. Senhas passadas como flags vazam para o histórico do shell e listagens de processos.

## 🎬 Demo

Execute o fluxo completo e explique:

- Como a senha mestra é derivada em chave (Argon2id)
- Como o AES-256-GCM protege confidencialidade e integridade
- Como as escritas atômicas evitam corrupção em caso de queda de energia
- Como o bloqueio de arquivo serializa invocações concorrentes

## 🚀 Getting Started

```bash
./install.sh
just run -- init
just run -- add github
just run -- get github
```

> [!TIP]
> Este projeto usa o [`just`](https://github.com/casey/just) como executor de comandos. Digite `just` para ver todas as receitas disponíveis.
>
> Instalação: `curl -sSf https://just.systems/install.sh | bash -s -- --to ~/.local/bin`

## Comandos

| Comando              | O que faz                                                       |
| -------------------- | --------------------------------------------------------------- |
| `pv init`            | Cria um novo vault vazio. Solicita a senha mestra duas vezes.   |
| `pv add <name>`      | Adiciona uma entrada. `--generate` / `-g` para senha aleatória. |
| `pv get <name>`      | Mostra todos os campos de uma entrada em um painel colorido.    |
| `pv list`            | Imprime o nome de cada entrada como uma tabela.                 |
| `pv delete <name>`   | Remove uma entrada pelo nome.                                   |
| `pv gen [length]`    | Gera uma senha aleatória forte. Não requer vault.               |
| `pv change-password` | Rotaciona a senha mestra — re-criptografa todo o vault.         |

## Garantias Criptográficas

| Preocupação                           | Mitigação                                                              |
| ------------------------------------- | ---------------------------------------------------------------------- |
| Arquivo do vault roubado              | Argon2id com 64 MiB / 3 passagens / 4 threads (~0.5s por tentativa)    |
| Arquivo do vault adulterado           | Tag de autenticação AES-GCM recusa a descriptografia                   |
| Queda de energia durante o salvamento | Escrita atômica: tmp → fsync → `os.replace` → fsync do diretório pai   |
| Dois processos `pv` em disputa        | `fcntl.LOCK_EX` consultivo em arquivo `.lock` lateral                  |
| Saída aleatória previsível            | Módulo `secrets` em todos os lugares                                   |
| Parâmetros KDF obsoletos              | Parâmetros armazenados no arquivo; `change-password` pode atualizá-los |

## 📚 Learning Resources

| Módulo                                          | Tópico                                                                  |
| ----------------------------------------------- | ----------------------------------------------------------------------- |
| [00 - Introdução](learn/00-Introdução.md)       | Início rápido, pré-requisitos, layout do projeto                        |
| [01 - Conceitos](learn/01-Conceitos.md)         | O que é criptografia, KDFs, Argon2id, salts, AES-GCM, modelo de ameaça  |
| [02 - Arquitetura](learn/02-Arquitetura.md)     | Layout de cinco arquivos, formato em disco, pipeline de escrita atômica |
| [03 - Implementação](learn/03-Implementação.md) | Passo a passo linha por linha de cada arquivo fonte                     |
| [04 - Desafios](learn/04-Desafios.md)           | Quinze ideias de extensão em quatro níveis                              |

## 🔗 Referências externas

- Crypto 101 — https://www.crypto101.io/
- Argon2 (spec) — https://github.com/P-H-C/phc-winner-argon2
- Practical Cryptography for Developers — https://cryptobook.nakov.com/

## 🧭 Next Step

Após concluir `Pass_Vault`, avance para o projeto em equipe do mesmo ramo: [`Secrets`](../../Team/Secrets/README.md) — detecção de segredos expostos em bases de código e repositórios git.

> [!NOTE]
> **Não é obrigatório** avançar imediatamente para o próximo projeto. Você pode trabalhar em múltiplos projetos primários em paralelo, respeitando as janelas de entrega do calendário.

---

@CarterPerez-dev | Copyright (C) 2026 Murilo Miacci
