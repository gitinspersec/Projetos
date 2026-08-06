# Arquitetura

Este arquivo é o mapa. Ao final, você deverá ser capaz de desenhar o projeto de memória: qual arquivo contém o quê, como as camadas dependem umas das outras, o que o arquivo no disco realmente contém e o fluxo passo a passo de cada comando CLI.

## Tabela de conteúdos

1. [O layout de cinco arquivos (e por quê)](#1-o-layout-de-cinco-arquivos-e-por-quê)
2. [Direção de dependência — quem importa quem](#2-direção-de-dependência--quem-importa-quem)
3. [O formato do arquivo de vault no disco](#3-o-formato-do-arquivo-de-vault-no-disco)
4. [Fluxo: `pv init`](#4-fluxo-pv-init)
5. [Fluxo: `pv add`](#5-fluxo-pv-add)
6. [Fluxo: `pv get` e `pv list`](#6-fluxo-pv-get-e-pv-list)
7. [Fluxo: `pv change-password`](#7-fluxo-pv-change-password)
8. [Fluxo: `pv gen` (sem vault)](#8-fluxo-pv-gen-sem-vault)
9. [Escritas atômicas + duráveis + seguras para concorrência, detalhadas](#9-escritas-atômicas--duráveis--seguras-para-concorrência-detalhadas)
10. [Ciclo de vida de um `UnlockedVault`](#10-ciclo-de-vida-de-um-unlockedvault)

---

## 1. O layout de cinco arquivos (e por quê)

```
src/password_manager/
├── __init__.py        entrada do pacote — reexporta a API pública
├── __main__.py        permite que `python -m password_manager` funcione
├── constants.py       cada número mágico e string fixa
├── crypto.py          primitivas Argon2id + AES-256-GCM
├── generator.py       geração de senhas criptograficamente segura
├── vault.py           formato de arquivo, escritas atômicas, bloqueio, CRUD de entradas
└── main.py            comandos CLI (Typer): init, add, get, list, …
```

Comparado ao `hash-identifier` (um arquivo, 680 linhas), este projeto está dividido em cinco arquivos fonte (~1.400 linhas no total). A divisão não é decorativa — cada arquivo tem um motivo estrito para existir:

| Arquivo        | Fala com              | Não fala com                   | Trabalho                                                                     |
| -------------- | --------------------- | ------------------------------ | ---------------------------------------------------------------------------- |
| `constants.py` | Nada                  | Qualquer coisa                 | Fonte única de verdade para números, strings e parâmetros ajustáveis         |
| `crypto.py`    | Apenas `constants`    | Sistema de arquivos, rede, CLI | Criptografia pura. Bytes entram, bytes saem. Sem E/S.                        |
| `generator.py` | Apenas `constants`    | Sistema de arquivos, rede, CLI | Geração de senhas aleatórias. Função pura, sem E/S.                          |
| `vault.py`     | `crypto`, `constants` | O terminal, linha de comando   | Formato de arquivo, escritas atômicas, bloqueio de arquivo, CRUD de entradas |
| `main.py`      | Todos os itens acima  | —                              | Camada de cola entre o teclado do usuário e o resto do código                |

**Por que esses limites importam:**

- O arquivo de criptografia não chama _nenhuma função de E/S_. Sem leituras de arquivo, sem `print`, sem `input`. Isso significa que é trivial de testar (basta chamar `encrypt(b"ola", key)`) e impossível introduzir um bug do tipo "deixe-me apenas imprimir a chave para depuração" na camada errada.
- O arquivo do vault não sabe nada sobre o terminal. Ele lança exceções tipadas (`VaultNotFoundError`, `WrongPasswordError`, etc.). A camada CLI as captura e as transforma em mensagens de erro coloridas. Uma futura GUI ou frontend web poderia ser construída sobre o `vault.py` sem alterar nada nele.
- O arquivo CLI não sabe nada sobre criptografia. Ele chama `UnlockedVault.create(...)` e `vault.add_entry(...)` e `vault.save()`. Se trocarmos o Argon2id por algo mais novo no próximo ano, o `main.py` não muda.

Isso é chamado de **arquitetura em camadas**. As camadas inferiores não importam das camadas superiores. A criptografia está na base; a CLI está no topo.

---

## 2. Direção de dependência — quem importa quem

```
                    ┌─────────────────────┐
                    │      main.py        │   a CLI (Typer + Rich)
                    │  (comandos, cola)   │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
        ┌───────────────┐  ┌──────────┐  ┌────────────┐
        │  vault.py     │  │ crypto   │  │ generator  │
        │  (formato     │  │   .py    │  │   .py      │
        │   de arquivo) │  │          │  │            │
        └───────┬───────┘  └────┬─────┘  └─────┬──────┘
                │               │              │
                └───────┬───────┴──────┬───────┘
                        │              │
                        ▼              ▼
                  ┌───────────────────────┐
                  │     constants.py      │   sem imports do nosso código
                  │ (números + strings)   │
                  └───────────────────────┘
```

**As setas apontam na direção dos imports.** `main.py` importa de `vault.py`, `crypto.py`, `generator.py` e `constants.py`. `vault.py` importa de `crypto.py` e `constants.py`. Nada importa de volta no sentido contrário. Sem ciclos.

Se você vir uma seta apontando para o lado errado (ex: `crypto.py` importando de `vault.py`), isso é um "code smell" — geralmente significa que uma parte da lógica foi parar na camada errada. O compilador/linter não vai te impedir, mas o design começará a apodrecer.

---

## 3. O formato do arquivo de vault no disco

O vault é um único arquivo JSON. Por padrão, ele vive em `~/.password-vault/vault.json` com permissões de arquivo `0600` (apenas o proprietário).

Aqui está como o arquivo se parece _aproximadamente_ (os campos base64 estão abreviados):

```json
{
  "version": 1,
  "kdf": {
    "name": "argon2id",
    "salt": "X3lkR1d2hcKLwk0PXfQpPg==",
    "time_cost": 3,
    "memory_cost": 65536,
    "parallelism": 4
  },
  "cipher": {
    "name": "aes-256-gcm",
    "nonce": "8tNTPwoq8uTXkpKt",
    "ciphertext": "Yk7eEVTSfA9wL...<muito mais base64>...kw=="
  }
}
```

Duas camadas de JSON vivem aqui, e isso é importante:

**Camada externa (o envelope):** JSON simples contendo os metadados necessários para _descriptografar_ a camada interna. Qualquer pessoa que roube o arquivo pode ler isso — ele informa qual KDF e cifra foram usados, o salt, o nonce. Nada disso é secreto; a segurança criptográfica depende da _chave_, não de esconder o algoritmo.

**Camada interna (o ciphertext):** quando descriptografado, este é _outro_ documento JSON — um dicionário de entradas de credenciais:

```json
{
  "github": {
    "username": "alice",
    "password": "hunter2-but-better",
    "url": "https://github.com",
    "notes": "",
    "created_at": "2026-05-13T14:22:10+00:00",
    "updated_at": "2026-05-13T14:22:10+00:00"
  },
  "email": {
    "username": "alice@example.com",
    "password": "another-secret",
    "url": "",
    "notes": "personal Fastmail",
    "created_at": "2026-05-13T14:30:01+00:00",
    "updated_at": "2026-05-14T09:11:42+00:00"
  }
}
```

Portanto: **envelope JSON envolvendo um JSON criptografado.** Comum, inspecionável, portátil. O comum é bom em segurança — menos coisas personalizadas para errar.

**Por que JSON especificamente?**

- Inspecionável por humanos. Você pode dar um `cat vault.json` e pelo menos confirmar a estrutura. Útil para depuração.
- Trivialmente portátil. Toda linguagem tem um parser JSON. Se você quisesse escrever um leitor para este formato em Rust ou Go, teria ele funcionando em uma hora.
- Compatível com versões futuras. O campo `"version": 1` permite que versões futuras saibam como ler os vaults de hoje — e nos permite recusar a leitura de vaults de uma versão _futura_ que ainda não entendemos.

**Por que base64?**

O JSON não tem como representar bytes brutos. A correção padrão é o base64: uma maneira de escrever qualquer dado binário como uma string de caracteres ASCII imprimíveis (`A-Z`, `a-z`, `0-9`, `+`, `/`, `=`). Ele infla os dados em ~33%, mas nos permite trafegar bytes através do JSON de forma limpa. Salts, nonces e ciphertexts são todos armazenados codificados em base64.

---

## 4. Fluxo: `pv init`

Isso cria um vault vazio novinho em folha. Acompanhe o que acontece passo a passo:

```
usuário digita: `pv init`
   │
   ▼
┌─────────────────────────────────────────────────┐
│ main.init()                                     │
│  - analisa flag --vault (ou env, ou path padrão)│
│  - verifica existência: recusa se vault.json já │
│    existir                                      │
│  - solicita senha mestra (duas vezes, confirma) │
│  - valida: não vazia, >= 8 chars, coincidente   │
└─────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────┐
│ UnlockedVault.create(path, master)              │
│  - gera salt novo de 16 bytes (secrets)         │
│  - deriva chave de 32 bytes de master + salt    │
│    via Argon2id (~0.5s em laptop moderno)       │
│  - constrói dicionário de entradas vazio        │
│  - chama self.save()                            │
└─────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────┐
│ vault.save()                                    │
│  - serializa entradas (vazio {}) para JSON      │
│  - gera nonce novo de 12 bytes (secrets)        │
│  - criptografa JSON interno com AES-256-GCM     │
│  - constrói envelope JSON externo               │
│  - escrita atômica em vault.json.tmp            │
│  - fsync dos dados                              │
│  - os.replace sobre vault.json                  │
│  - fsync do diretório pai                       │
└─────────────────────────────────────────────────┘
   │
   ▼
   `Vault criado em ~/.password-vault/vault.json`
```

Duas coisas principais a notar:

1. **O salt é gerado uma vez, no momento do `create()`, e nunca muda durante a vida do vault.** Mesmo depois que o `change-password` re-criptografa tudo sob uma nova chave, o salt em si é regenerado apenas porque a senha mudou — para uma determinada senha, o salt é estável.
2. **O nonce é gerado em _cada salvamento_, nunca reutilizado.** O caminho mais lento (Argon2id) acontece uma vez por sessão; o segundo caminho mais lento (criptografia AES-GCM) acontece em cada salvamento e usa um nonce novo a cada vez.

---

## 5. Fluxo: `pv add`

Isso desbloqueia o vault, adiciona uma entrada e o salva de volta. O custo do Argon2id é pago _uma vez_ no desbloqueio, então o `add` e o `save` são ambos rápidos.

```
usuário digita: `pv add github`
   │
   ▼
┌─────────────────────────────────────────────────┐
│ main.add()                                      │
│  - solicita senha mestra                        │
└─────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────┐
│ UnlockedVault.unlock(path, master)              │
│  - lê vault.json do disco                       │
│  - analisa envelope JSON                        │
│  - valida versão + nomes de algoritmos          │
│  - valida parâmetros Argon2 (limites mínimos)   │
│  - extrai salt, params KDF, nonce, ciphertext   │
│  - derive_key(master, salt, params)  ← lento    │
│  - descriptografa AES-256-GCM(cipher, nonce, key)│
│      ↓ se tag de aut. falhar: raise             │
│        WrongPasswordError → CLI sai com msg     │
│  - analisa JSON interno → dicionário entradas   │
│  - retorna UnlockedVault(path, salt, params,    │
│                          key, entries)          │
└─────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────┐
│ corpo do main.add(), dentro do bloco `with`     │
│  - solicita usuário (visível)                   │
│  - se --generate: generate_password(length)     │
│    senão: getpass para senha (oculta)           │
│  - solicita url, notas (opcional)               │
│  - constrói Entry(user, pass, url, notas,       │
│                   created_at=now, updated_at=now)│
│  - vault.add_entry(name, entry, force=...)      │
│      ↓ se nome existe e não force:              │
│        EntryAlreadyExistsError → CLI sai        │
│      ↓ se nome é vazio ou tem espaços:          │
│        ValueError → CLI sai                      │
│  - vault.save() (atômico, durável, bloqueado)   │
└─────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────┐
│ fim do bloco `with` → vault.__exit__()          │
│  - vault.entries = {}                           │
│  - vault.key = bytes(32) (preenchido com zeros) │
│ (limpeza de melhor esforço; bytes Python são    │
│  imutáveis, mas removemos as referências no mín)│
└─────────────────────────────────────────────────┘
   │
   ▼
   `Entrada adicionada: github`
```

Observe os **dois modos de falha após a descriptografia**:

- "Senha incorreta" recebe uma mensagem de erro.
- "Arquivo do vault está corrompido" recebe a _mesma_ mensagem de erro ("Senha mestra incorreta (ou arquivo de vault está corrompido)").

Isso é proposital. A falha de autenticação GCM significa uma de três coisas e não podemos dizer qual: senha errada, arquivo adulterado, arquivo corrompido. Do ponto de vista do usuário, elas são indistinguíveis, e _expor_ a diferença ajuda um atacante (que saberia se sua tentativa foi "quase certa" vs "chave definitivamente errada"). Nós as colapsamos em uma única mensagem honesta.

---

## 6. Fluxo: `pv get` e `pv list`

Ambos seguem o mesmo padrão: desbloquear, ler, renderizar, fechar. O vault é desbloqueado apenas o tempo suficiente para pegar os dados e é descartado imediatamente após a renderização.

```
pv get github
   │
   ├─► solicita senha mestra
   │
   ├─► UnlockedVault.unlock(...)      (lento uma vez, Argon2id)
   │
   ├─► entry = vault.get_entry("github")
   │         ↓ se não encontrado:
   │           EntryNotFoundError → CLI sai com 1
   │
   ├─► console.print(rich.Panel(...))    ← painel colorido
   │
   └─► fim do `with` → limpa chave + entradas
```

```
pv list
   │
   ├─► solicita senha mestra
   │
   ├─► UnlockedVault.unlock(...)
   │
   ├─► names = vault.names()         (ordenados alfabeticamente)
   │
   ├─► se não houver nomes: imprime msg "vault está vazio"
   │
   ├─► constrói uma rich.Table com uma linha por entrada
   │      colunas: nome, usuário, atualizado_em
   │      (senhas NÃO são mostradas no `list`)
   │
   ├─► console.print(table)
   │
   └─► fim do `with` → limpa chave + entradas
```

O `list` mostra nomes de usuário e horários de atualização, mas **não as senhas**. O usuário tem que pedir explicitamente por uma senha com `get <nome>`. Essa é uma pequena fricção que reduz a chance de vazar um conjunto inteiro de credenciais para qualquer pessoa que esteja observando seu terminal.

---

## 7. Fluxo: `pv change-password`

Este é o comando criptograficamente mais interessante. Ele rotaciona a senha mestra ao:

1. Desbloquear o vault com a senha _antiga_ (custo total do Argon2id).
2. Gerar um _salt novo_ e derivar uma _chave nova_ a partir da _nova_ senha.
3. Salvar o vault — o `save()` criptografará as entradas existentes sob a nova chave, com um nonce novo.

```
pv change-password
   │
   ├─► solicita: "Senha mestra atual: "
   │
   ├─► UnlockedVault.unlock(path, senha_atual)
   │     ↓ se errada: WrongPasswordError → sai com 1
   │
   ├─► solicita: "Nova senha mestra: " (duas vezes, confirma)
   │     ↓ valida: não vazia, >= 8 chars, coincidente
   │
   ├─► vault.change_master_password(nova_senha)
   │     - novo_salt = secrets.token_bytes(16)
   │     - nova_chave = derive_key(nova, novo_salt, defaults)
   │     - self.salt = novo_salt
   │     - self.kdf_parameters = defaults()
   │     - self.key = nova_chave
   │     (apenas altera o estado em memória — disco intocado)
   │
   ├─► vault.save()
   │     - serializa o MESMO dicionário de entradas (preservado)
   │     - gera um NOVO nonce
   │     - criptografa sob a NOVA chave
   │     - escrita atômica substitui o arquivo antigo
   │
   └─► "Senha mestra alterada. Vault re-criptografado em <path>"
```

**Por que isso é interessante:** o arquivo do vault armazena os parâmetros KDF e o salt ao lado do ciphertext. É _exatamente_ por isso que esta operação é possível. Se os parâmetros KDF vivessem apenas no código, então "alterar minha senha" não teria como também "atualizar meus parâmetros Argon2 dos padrões do ano passado para os deste ano". Colocá-los no arquivo torna o caminho de atualização possível. O argumento `kdf_parameters` em `change_master_password` é o gancho para isso.

**Segurança contra falhas:** se o processo morrer entre a alteração do estado em memória e a conclusão do salvamento atômico, o _arquivo no disco_ ainda terá o salt antigo e o ciphertext antigo — totalmente legíveis com a senha antiga. A nova chave só "vence" depois que o `os.replace` é concluído. Esta é a razão fundamental pela qual as escritas atômicas importam para gerenciadores de senhas: uma rotação mal sucedida nunca deve te deixar bloqueado.

---

## 8. Fluxo: `pv gen` (sem vault)

O comando mais simples. Não toca no vault de forma alguma. Não solicita a senha mestra. Apenas gera uma senha aleatória forte e a imprime.

```
pv gen 32
   │
   ▼
generate_password(length=32,
                  use_lowercase=True,
                  use_uppercase=True,
                  use_digits=True,
                  use_symbols=True)
   │
   ├─► comprimento >= MIN (8)?
   ├─► pelo menos um pool ativado?
   ├─► comprimento >= número de pools ativados?
   │      (precisa caber um char de cada)
   │
   ├─► obrigatorios = [secrets.choice(pool) for pool in pools]
   │      um char garantido de cada pool ativado
   │
   ├─► preenchimento = [secrets.choice(combinado) for _ in range(length - len(obrigatorios))]
   │
   ├─► caracteres = obrigatorios + preenchimento
   │
   ├─► _secure_shuffle(caracteres)
   │      Fisher-Yates com secrets.randbelow
   │      (NÃO random.shuffle — previsível)
   │
   └─► retorna "".join(caracteres)
```

A saída vai para o stdout via `print()` simples (não o console rich), por isso é amigável para pipes:

```bash
pv gen 32 | pbcopy
PASSWORD=$(pv gen 32)
```

Este é o único comando que usa `print` em vez de `console.print`. O motivo é exatamente o piping: não queremos os códigos de escape de cor do rich dentro da senha que é enviada para o `pbcopy`.

---

## 9. Escritas atômicas + duráveis + seguras para concorrência, detalhadas

O método `save()` faz mais trabalho do que você imagina. A versão "apenas escreva o arquivo" disso seria uma linha; a nossa tem algumas dezenas. Aqui está o porquê de cada peça estar lá.

### O que pode dar errado com a abordagem ingênua

```python
# NÃO FAÇA ISSO
path.write_bytes(envelope_bytes)
```

Isso tem três problemas, todos os quais já vimos acontecer em sistemas reais:

1. **Crash no meio da escrita → arquivo corrompido.** Se o processo morrer após escrever 4096 bytes de um arquivo de 6000 bytes, o arquivo estará escrito pela metade. Na próxima vez que o usuário tentar desbloquear, a análise do JSON falhará e ele pensará que seu vault foi destruído.
2. **Queda de energia → arquivo de 0 bytes (ou pior).** Mesmo que o processo seja concluído, os bytes vivem no cache de página do kernel. O SO os escreverá no disco _eventualmente_, mas uma queda de energia entre a escrita e a gravação no disco significa que o arquivo parece existir, mas não contém nada.
3. **Duas instâncias do `pv` em disputa.** O usuário executa `pv add github` em um terminal e `pv add email` em outro simultaneamente. Ambos desbloqueiam o vault (lento), ambos adicionam sua entrada, ambos salvam. Aquele que salvar por _segundo_ perde a entrada do outro — silenciosamente. Sem erro.

### Como corrigimos cada um

```
        ┌──────────────────────────────────────────────┐
        │ 1. adquire flock consultivo em vault.json.lock│
        │    (sistemas POSIX — Windows pula isso)      │
        └──────────────────┬───────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────────────┐
        │ 2. os.open(vault.json.tmp, …, mode=0600)     │
        │    arquivo criado ilegível para outros desde │
        │    a primeiríssima syscall (sem disputa chmod)│
        └──────────────────┬───────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────────────┐
        │ 3. os.write(fd, envelope_bytes)              │
        └──────────────────┬───────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────────────┐
        │ 4. os.fsync(fd)                              │
        │    força cache de página do kernel → disco.  │
        │    sem isso, "nós escrevemos" é uma história │
        │    que o cache conta; uma queda de energia a │
        │    apaga.                                    │
        └──────────────────┬───────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────────────┐
        │ 5. os.close(fd)                              │
        └──────────────────┬───────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────────────┐
        │ 6. os.replace(vault.json.tmp, vault.json)    │
        │    renomeação atômica. após este instante,   │
        │    leitores veem OU o arquivo antigo OU o    │
        │    novo. nunca metade de nenhum deles.       │
        └──────────────────┬───────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────────────┐
        │ 7. fsync do diretório pai (POSIX)            │
        │    para que a renomeação sobreviva à queda   │
        │    de energia. sem isso, um crash do SO logo │
        │    após a renomeação pode reverter a entrada.│
        └──────────────────┬───────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────────────┐
        │ 8. libera o bloqueio consultivo              │
        └──────────────────────────────────────────────┘
```

Cada etapa tapa um buraco:

| Etapa | Tapa                                                 |
| ----- | ---------------------------------------------------- |
| 1, 8  | Dois processos `pv` em disputa                       |
| 2     | Janela curta onde o arquivo tmp é legível por todos  |
| 4     | "Queda de energia logo após a escrita" perde dados   |
| 6     | "Crash no meio da escrita" corrompe o arquivo ativo  |
| 7     | "Queda de energia logo após renomear" reverte a ação |

O bloqueio consultivo (advisory lock) é interessante: ele não é imposto pelo SO, apenas pelo código que opta por ele. Um processo que ignora o `flock` ainda pode escrever no arquivo. Mas _cada_ `save()` em nosso código opta por ele, então duas invocações do `pv` não podem disputar entre si. Um editor externo (vim, `sed`) não bloqueia, mas um usuário editando o arquivo do vault manualmente já saiu do contrato da ferramenta.

O Windows não possui `fcntl.flock` ou `fsync` de diretório, então pulamos ambos lá. O NTFS nos dá o `os.replace` atômico de qualquer maneira. O compromisso é: no Windows perdemos a serialização entre processos (caso extremo raro para uma ferramenta de usuário único) e perdemos a garantia absoluta de durabilidade do diretório (o journaling do NTFS cobre a maioria dos casos).

---

## 10. Ciclo de vida de um `UnlockedVault`

Um `UnlockedVault` é um objeto Python que contém:

- O caminho para o arquivo do vault no disco.
- O salt de 16 bytes.
- Os parâmetros Argon2 que foram usados.
- A chave AES de 32 bytes (sensível!).
- As entradas descriptografadas (também sensíveis! contêm senhas em texto simples).

Manter a chave na memória significa que as operações subsequentes (adicionar, obter, excluir, salvar) não precisam derivá-la novamente — caso contrário, pagariam o custo do Argon2 em cada salvamento. Mas também significa que queremos um sinal claro de "terminei com isso".

A instrução `with` do Python (um "context manager") é exatamente esse sinal:

```python
with UnlockedVault.unlock(path, master) as vault:
    vault.add_entry("github", entry)
    vault.save()
# neste ponto, vault.__exit__ foi chamado
# vault.entries agora é {}
# vault.key agora é b"\x00" * 32
```

O `__enter__` roda quando o bloco começa. O `__exit__` roda quando o bloco termina — _seja normalmente ou por exceção_. Portanto, mesmo que o `vault.save()` lance um erro, a limpeza ainda acontece.

A limpeza em si (`vault.close()`) substitui o dicionário de entradas por `{}` e a chave por 32 bytes zero. Este é um esforço de **melhor tentativa**. Os objetos `bytes` do Python são imutáveis, então os bytes da chave original podem ainda viver na memória até que o garbage collector rode. Uma limpeza real ao liberar memória no Python exigiria truques de `bytearray` mais `ctypes` que este projeto de ensino evita deliberadamente — a disciplina de "descartar segredos explicitamente quando terminar" é o hábito mais importante.

```
       ┌────────────────────────────────────────────┐
       │  UnlockedVault.unlock(path, master)        │
       │  ─ lento: Argon2id deriva chave 32-byte    │
       │  ─ AES-GCM descriptografa o ciphertext     │
       │  ─ retorna instância: { path, salt, params,│
       │                       key, entries }       │
       └────────────────────────────────────────────┘
                              │
                              ▼
       ┌────────────────────────────────────────────┐
       │  __enter__ → retorna self                  │
       └────────────────────────────────────────────┘
                              │
                              ▼
       ┌────────────────────────────────────────────┐
       │  corpo do bloco `with`                     │
       │  ─ get_entry, add_entry, delete_entry      │
       │  ─ save() (rápido: chave já na memória,    │
       │            apenas AES-GCM + escrita atôm)  │
       └────────────────────────────────────────────┘
                              │
                              ▼
       ┌────────────────────────────────────────────┐
       │  __exit__ → close()                        │
       │  ─ self.entries = {}                       │
       │  ─ self.key = b"\x00" * 32                 │
       │  (limpeza de melhor esforço; bytes Python  │
       │   são imutáveis, o GC pode ter cópias)     │
       └────────────────────────────────────────────┘
```

Este é o mesmo padrão que o `open()` do Python usa (`with open("x.txt") as f:`). O vault é apenas um recurso mais sensível à segurança do que um manipulador de arquivo.

---

## Para onde ir em seguida

Agora você tem a estrutura do projeto na sua cabeça: qual arquivo faz o quê, como o arquivo no disco se parece, o que cada comando faz passo a passo.

O **[03-Implementação.md](./03-Implementação.md)** percorre cada arquivo fonte linha por linha. Abra o `crypto.py`, `vault.py` e `main.py` em uma segunda janela e acompanhe a leitura.
