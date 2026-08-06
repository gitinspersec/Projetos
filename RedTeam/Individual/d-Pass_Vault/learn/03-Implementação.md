# Passo a passo da implementação

Abra os arquivos fonte em outra janela e acompanhe. Passaremos por eles na ordem de dependência: a base da pirâmide primeiro, o topo por último. A ordem é:

1. [`constants.py`](#1-constantspy--fonte-única-de-verdade)
2. [`crypto.py`](#2-cryptopy--argon2id--aes-256-gcm)
3. [`generator.py`](#3-generatorpy--senhas-aleatórias-seguras)
4. [`vault.py`](#4-vaultpy--formato-de-arquivo-escritas-atômicas-bloqueio)
5. [`main.py`](#5-mainpy--a-cli)
6. [`__init__.py` e `__main__.py`](#6-__init__py-e-__main__py)
7. [Os testes](#7-os-testes)

Cada recurso do Python será explicado quando aparecer pela primeira vez. Se você já o conhece, leia por cima; se não, a explicação estará logo ali.

---

## 1. `constants.py` — fonte única de verdade

Abra [`src/password_manager/constants.py`](../src/password_manager/constants.py).

### Por que este arquivo existe

No primeiro projeto Python de um iniciante, números e strings costumam ficar espalhados: `length = 16`, `salt = os.urandom(16)`, `if memory > 65536:`. Seis meses depois, ninguém lembra por que 16, e alterá-lo exige caçar em cinco arquivos diferentes.

Colocar cada "número mágico" em um único arquivo com um nome e um comentário transforma o resto do código em uma prosa autodocumentada. Em vez de `os.urandom(16)`, escrevemos `secrets.token_bytes(SALT_LENGTH_BYTES)` — e o leitor consegue ver imediatamente o que o 16 significa aqui.

### Topo do arquivo: imports

```python
from pathlib import Path
from typing import Final
```

- **`pathlib.Path`** é o tipo de caminho de sistema de arquivos orientado a objetos do Python. Em vez de `os.path.join("dir", "file.json")`, você escreve `Path("dir") / "file.json"`. O operador `/` é sobrecarregado para caminhos. É mais seguro porque não envolve escape ou citação de strings manual.
- **`typing.Final`** é um type hint que marca uma variável como "nunca me reatribua". É verificado pelo **mypy** (o verificador de tipos), não pelo Python em si. Se você escrever `X: Final[int] = 5` e depois tentar `X = 6`, o mypy apontará o erro. O runtime do Python não o fará — Final é uma documentação que o linter entende.

### Parâmetros Argon2id

```python
ARGON2_TIME_COST: Final[int] = 3
ARGON2_MEMORY_KIB: Final[int] = 65536  # 64 MiB
ARGON2_PARALLELISM: Final[int] = 4
SALT_LENGTH_BYTES: Final[int] = 16
```

Os três parâmetros ajustáveis explicados em [01-Conceitos.md](./01-Conceitos.md). O bloco de comentários acima deles detalha o _porquê_ de cada valor ser o que é, incluindo a divergência deliberada da recomendação da OWASP de `parallelism=1`, que é voltada para servidores.

Abaixo deles estão três "mínimos":

```python
ARGON2_TIME_COST_MIN: Final[int] = 1
ARGON2_PARALLELISM_MIN: Final[int] = 1
ARGON2_MEMORY_KIB_PER_LANE_MIN: Final[int] = 8
```

Estes não são botões de ajuste — são os limites algorítmicos abaixo dos quais o próprio Argon2 se recusa a rodar. Nós os usamos no `vault.py` para validar parâmetros carregados do disco, para que um arquivo de vault corrompido ou editado manualmente não nos faça chamar o Argon2 com `time_cost=0` e travar nas profundezas da biblioteca com um erro confuso.

### Parâmetros AES-256-GCM

```python
KEY_LENGTH_BYTES: Final[int] = 32   # AES-256 requer 32 bytes
NONCE_LENGTH_BYTES: Final[int] = 12 # Tamanho de nonce recomendado para GCM
```

O tamanho da chave diz "queremos AES-256, não AES-128". O tamanho do nonce é a recomendação para GCM do [NIST SP 800-38D](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf). Não altere nenhum dos dois.

### Formato do arquivo de vault

O grande bloco de comentários desenha o formato em disco. Em seguida, os nomes das chaves JSON vivem como constantes:

```python
VAULT_KEY_VERSION: Final[str] = "version"
VAULT_KEY_KDF: Final[str] = "kdf"
VAULT_KEY_CIPHER: Final[str] = "cipher"

KDF_KEY_NAME: Final[str] = "name"
KDF_KEY_SALT: Final[str] = "salt"
# ... etc
```

Isso parece excesso de engenharia para um projeto iniciante, mas tem um benefício real: se você algum dia renomear um campo, altera apenas uma vez aqui, e o linter imediatamente informa cada local que precisa de atualização. Compare isso com `"version"` escrito inline em cinco arquivos diferentes — um erro de digitação (`"verison"`) poderia quebrar as coisas silenciosamente em tempo de execução.

As constantes de caminho de arquivo usam `pathlib`:

```python
DEFAULT_VAULT_DIRECTORY: Final[Path] = Path.home() / ".password-vault"
DEFAULT_VAULT_FILENAME: Final[str] = "vault.json"
DEFAULT_VAULT_PATH: Final[Path] = (
    DEFAULT_VAULT_DIRECTORY / DEFAULT_VAULT_FILENAME
)
```

`Path.home()` resolve no **momento da importação**, não no momento da chamada. Ele retorna `/home/seunome` no Linux, `/Users/seunome` no macOS, `C:\Users\seunome` no Windows. É por isso que isso funciona em todos os SOs sem ramificações `if os.name == "windows"`.

### Modo do arquivo

```python
VAULT_FILE_MODE: Final[int] = 0o600
```

`0o600` é a sintaxe do Python para o número octal 600. Em permissões de arquivo Unix, isso significa: o proprietário pode ler e escrever, ninguém mais pode fazer nada. O prefixo `0o` diz ao Python "interprete estes dígitos como octal". (Apenas `600` seria seiscentos em decimal — errado). Passamos isso para o `os.open` para que o arquivo seja criado ilegível para outros usuários desde a primeiríssima chamada de sistema.

### Padrões do gerador de senhas

```python
DEFAULT_GENERATED_PASSWORD_LENGTH: Final[int] = 24
MINIMUM_GENERATED_PASSWORD_LENGTH: Final[int] = 8
MINIMUM_MASTER_PASSWORD_LENGTH: Final[int] = 8

LOWERCASE_LETTERS: Final[str] = "abcdefghijklmnopqrstuvwxyz"
UPPERCASE_LETTERS: Final[str] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIGITS: Final[str] = "0123456789"
SAFE_SYMBOLS: Final[str] = "!@#$%^&*()-_=+[]{};:,.<>/?"
```

O pool de símbolos exclui deliberadamente alguns caracteres:

- **Aspas** (`'`, `"`, `` ` ``) — confundem o copiar e colar em shells.
- **Barra invertida** (`\`) — metacaractere de shell, strings com aspas duplas o interpretam.
- **Espaço** — parece invisível quando exibido.

Esta é uma escolha de UX. Se você quiser aleatoriedade pura com cada caractere ASCII imprimível, você os colocaria de volta.

### Strings de prompts e mensagens da CLI

O resto do arquivo é o texto voltado para o usuário:

```python
PROMPT_MASTER_PASSWORD: Final[str] = "Master password: "
MSG_VAULT_CREATED: Final[str] = "Vault created at {path}"
MSG_ENTRY_ADDED: Final[str] = "Added entry: {name}"
```

Os `{path}` e `{name}` são espaços reservados para o `.format()`. Colocá-los aqui significa que:

1. Você pode ajustar o vocabulário em um só lugar sem caçar no `main.py`.
2. Se você algum dia quiser internacionalizar a ferramenta (versão em espanhol, etc.), você distribuiria um `constants.py` diferente por idioma.

---

## 2. `crypto.py` — Argon2id + AES-256-GCM

Abra [`src/password_manager/crypto.py`](../src/password_manager/crypto.py).

Esta é a camada mais baixa do projeto. Bytes entram, bytes saem. Sem E/S de arquivo. Sem declarações `print`. Criptografia pura envolvida em funções Python amigáveis.

### Importações

```python
import secrets
from dataclasses import dataclass

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from password_manager.constants import (
    ARGON2_MEMORY_KIB,
    ARGON2_PARALLELISM,
    ARGON2_TIME_COST,
    KEY_LENGTH_BYTES,
    NONCE_LENGTH_BYTES,
    SALT_LENGTH_BYTES,
)
```

Três grupos, linhas em branco entre eles. Esta é a convenção padrão do Python ([PEP 8](https://peps.python.org/pep-0008/#imports)):

1. **Biblioteca padrão** (vem com o Python): `secrets`, `dataclasses`.
2. **Terceiros** (instalados via PyPI): `argon2-cffi`, `cryptography`.
3. **Local** (nosso próprio código): `password_manager.constants`.

`hazmat` em `cryptography.hazmat.primitives.ciphers.aead` é abreviação de "hazardous materials" (materiais perigosos) — a biblioteca usa este namespace para primitivas que exigem cuidado para serem usadas corretamente. O AES-GCM vive aqui porque a reutilização de nonce é uma armadilha perigosa. A biblioteca está sendo honesta sobre isso.

### Exceções personalizadas

```python
class CryptoError(Exception):
    """Classe base para cada erro de criptografia que lançamos."""

class WrongPasswordError(CryptoError):
    """Lançada quando a descriptografia falha."""
```

Duas classes, uma herdando da outra. O corpo é apenas uma docstring — isso é Python válido; uma classe precisa de _algo_ em seu corpo, e uma docstring conta.

**Por que exceções personalizadas em vez de apenas `raise Exception`?** Porque quem chama precisa ser capaz de tratar erros diferentes de formas diferentes:

```python
try:
    vault = UnlockedVault.unlock(path, password)
except WrongPasswordError:
    print("Tente novamente")
except VaultNotFoundError:
    print("Execute `pv init` primeiro")
```

Se lançássemos apenas `Exception` para tudo, quem chama teria que comparar as mensagens de exceção como strings — frágil e feio. Tipos personalizados tornam a API autodocumentada.

### `@dataclass(frozen=True, slots=True)`

```python
@dataclass(frozen=True, slots=True)
class KdfParameters:
    time_cost: int
    memory_cost: int
    parallelism: int

    @classmethod
    def defaults(cls) -> "KdfParameters":
        return cls(
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_KIB,
            parallelism=ARGON2_PARALLELISM,
        )
```

Uma **dataclass** é uma classe com métodos `__init__`, `__repr__` e `__eq__` gerados automaticamente a partir dos campos que você declara. Sem ela, você escreveria:

```python
class KdfParameters:
    def __init__(self, time_cost, memory_cost, parallelism):
        self.time_cost = time_cost
        self.memory_cost = memory_cost
        self.parallelism = parallelism

    def __eq__(self, other):
        return (self.time_cost == other.time_cost
                and self.memory_cost == other.memory_cost
                and self.parallelism == other.parallelism)

    def __repr__(self):
        return f"KdfParameters({self.time_cost}, {self.memory_cost}, ...)"
```

O decorador `@dataclass` escreve tudo isso para você. Os campos com anotações de tipo sob o corpo da classe tornam-se os argumentos do construtor.

As duas flags:

- **`frozen=True`** — as instâncias são imutáveis. Após `params = KdfParameters(3, 65536, 4)`, você não pode fazer `params.time_cost = 5`. Tentar fará com que uma exceção seja lançada. Útil quando você quer que um valor seja passado como um número ou string — ninguém adiante no código pode modificá-lo secretamente.
- **`slots=True`** — economiza memória ao pular o `__dict__` por instância. É uma otimização menor. O maior benefício é que impede a adição acidental de atributos: `params.typo = 5` lança `AttributeError` em vez de criar silenciosamente um erro de digitação.

**`@classmethod`**: um método cujo primeiro argumento é a própria _classe_, não uma instância. Convencionalmente nomeado como `cls`. Usado aqui para criar um construtor com um nome mais amigável: `KdfParameters.defaults()` em vez de `KdfParameters(3, 65536, 4)`.

### `generate_salt` e `generate_nonce`

```python
def generate_salt() -> bytes:
    return secrets.token_bytes(SALT_LENGTH_BYTES)

def generate_nonce() -> bytes:
    return secrets.token_bytes(NONCE_LENGTH_BYTES)
```

Ambas são funções de uma linha. O trabalho _não_ é o corpo da função — o trabalho é o nome. Ao ter `generate_salt` e `generate_nonce` como funções nomeadas, o código que as chama é autodocumentado:

```python
nonce = generate_nonce()    # todos sabem para que serve isso
salt = generate_salt()
```

vs.

```python
nonce = secrets.token_bytes(12)   # o que é o 12? ah, deve ser um nonce
salt = secrets.token_bytes(16)    # o que é o 16?
```

As funções nomeadas também mantêm os _tamanhos_ de salt e nonce invisíveis para o resto do código — apenas `crypto.py` os conhece.

### `derive_key` — o passo lento

```python
def derive_key(
    master_password: str,
    salt: bytes,
    parameters: KdfParameters | None = None,
) -> bytes:
    if not master_password:
        raise ValueError("master_password must not be empty")

    if parameters is None:
        parameters = KdfParameters.defaults()

    password_bytes = master_password.encode("utf-8")

    return hash_secret_raw(
        secret=password_bytes,
        salt=salt,
        time_cost=parameters.time_cost,
        memory_cost=parameters.memory_cost,
        parallelism=parameters.parallelism,
        hash_len=KEY_LENGTH_BYTES,
        type=Type.ID,
    )
```

Algumas coisas notáveis:

- **`KdfParameters | None = None`** — a sintaxe de type hint para "ou um `KdfParameters` ou `None`". O `|` é a forma mais curta do Python 3.10+ para `Optional[KdfParameters]` ou `Union[KdfParameters, None]`. O `= None` faz com que o argumento assuma `None` por padrão quando omitido.
- **Verificação de senha vazia primeiro.** Se o usuário (ou um chamador com bug) passar `""`, recusamos imediatamente. O Argon2 rodaria alegremente, mas a chave resultante seria "a chave derivada de nenhum segredo + um salt público" — qualquer um que roube o arquivo pode derivá-la novamente.
- **A verificação `is None`** para `parameters`. Poderíamos escrever `parameters: KdfParameters = KdfParameters.defaults()` como um argumento padrão, mas o Python avalia argumentos padrão **uma única vez, no momento da definição da função**. Para um `KdfParameters` imutável isso até estaria ok, mas o padrão de "usar `None` como padrão e então substituir dentro da função" é o hábito geral mais seguro — porque se o padrão algum dia se tornar mutável (como uma lista), o bug de um-padrão-compartilhado-entre-chamadas aconteceria.
- **`.encode("utf-8")`** — strings no Python vivem como code points Unicode. Funções criptográficas exigem bytes brutos. UTF-8 é a codificação universalmente correta para texto Unicode. Sempre a especifique explicitamente; nunca confie no padrão da plataforma.
- **`Type.ID`** escolhe especificamente o Argon2id — não o Argon2d ou Argon2i. Veja [01-Conceitos.md §6](./01-Conceitos.md#6-argon2id-especificamente-e-por-quê).
- **Argumentos nomeados em todo lugar.** `secret=password_bytes`, não apenas `password_bytes`. Esta é uma escolha de design de API com foco em segurança: argumentos posicionais para uma função com sete parâmetros são um erro de digitação esperando para acontecer. Nomeá-los no local da chamada torna os erros evidentes.

### `encrypt` e `decrypt`

```python
def encrypt(plaintext: bytes, key: bytes) -> tuple[bytes, bytes]:
    cipher = AESGCM(key)
    nonce = generate_nonce()
    ciphertext = cipher.encrypt(
        nonce=nonce,
        data=plaintext,
        associated_data=None,
    )
    return nonce, ciphertext
```

Três coisas:

1. **`AESGCM(key)`** constrói um objeto de cifra vinculado à chave. A biblioteca valida o tamanho da chave — deve ser 16, 24 ou 32 bytes. Uma chave de tamanho errado lança um erro imediatamente.
2. **Nonce novo em cada chamada.** A linha `generate_nonce()` é a linha mais crítica para a segurança em todo o arquivo. Reutilizar um nonce com a mesma chave é catastrófico (veja [01-Conceitos.md §10](./01-Conceitos.md#10-nonces-a-coisa-mais-perigosa-nesta-base-de-código)).
3. **`associated_data=None`.** O AES-GCM tem um parâmetro opcional de "dados associados": dados que são autenticados (evidência de adulteração), mas não criptografados. Útil para cabeçalhos de pacotes — você quer que o destinatário detecte modificações no cabeçalho, mas o cabeçalho em si é público. Não temos tais dados, então passamos `None`.

O tipo de retorno `tuple[bytes, bytes]` significa "dois objetos bytes retornados juntos". Quem chama desempacota como `nonce, ciphertext = encrypt(data, key)`.

```python
def decrypt(ciphertext: bytes, nonce: bytes, key: bytes) -> bytes:
    cipher = AESGCM(key)
    try:
        return cipher.decrypt(
            nonce=nonce,
            data=ciphertext,
            associated_data=None,
        )
    except InvalidTag as exc:
        raise WrongPasswordError(
            "Decryption failed: wrong master password or corrupted vault"
        ) from exc
```

`InvalidTag` é o sinal da biblioteca de criptografia de que a tag de autenticação não coincidiu — chave errada, nonce errado ou ciphertext modificado. Nós a capturamos e a relançamos como nossa própria `WrongPasswordError`. Quem chama não precisa saber que `cryptography.exceptions` existe.

**`raise WrongPasswordError(...) from exc`** — a parte `from exc` preserva o traceback da exceção original no atributo `__cause__` da nova exceção. Se algo explodir inesperadamente, a saída de depuração ainda mostrará a causa subjacente `InvalidTag`. É uma boa prática quando você está traduzindo um tipo de exceção em outro.

---

## 3. `generator.py` — senhas aleatórias seguras

Abra [`src/password_manager/generator.py`](../src/password_manager/generator.py).

Este arquivo é mais curto que o `crypto.py` e mais fácil de raciocinar. Duas funções públicas que valem a pena acompanhar com cuidado.

### `generate_password`

```python
def generate_password(
    length: int = DEFAULT_GENERATED_PASSWORD_LENGTH,
    *,
    use_lowercase: bool = True,
    use_uppercase: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
) -> str:
```

O **`*`** na assinatura é um recurso do Python chamado **argumentos apenas nomeados** (keyword-only arguments). Após o `*`, cada argumento deve ser passado pelo nome. Isso:

```python
generate_password(20, use_symbols=False)    # OK
generate_password(20, True, True, True, False)  # ERRO
```

Isso força os locais de chamada a serem legíveis. `generate_password(20, True, True, True, False)` é impossível de entender de relance — você teria que contar os booleanos. `generate_password(20, use_symbols=False)` é autodocumentado.

### Validando as entradas

```python
if length < MINIMUM_GENERATED_PASSWORD_LENGTH:
    raise PasswordTooShortError(...)

enabled_pools = {
    "lower": LOWERCASE_LETTERS if use_lowercase else "",
    "upper": UPPERCASE_LETTERS if use_uppercase else "",
    "digit": DIGITS if use_digits else "",
    "symbol": SAFE_SYMBOLS if use_symbols else "",
}
enabled_pools = {k: v for k, v in enabled_pools.items() if v}
```

O `if use_lowercase else ""` é uma **expressão condicional** (às vezes chamada de ternário). `<a> if <cond> else <b>` avalia para `<a>` quando `<cond>` é verdadeiro, caso contrário `<b>`.

A segunda linha é uma **dict comprehension** (compreensão de dicionário): `{k: v for k, v in algo.items() if condicao}` constrói um novo dicionário a partir de itens filtrados. É o equivalente para dicionários de `[x for x in lista if cond]` (uma list comprehension). Resultado: mantemos apenas os pools cuja flag era True (porque strings vazias são falsas no Python).

```python
if not enabled_pools:
    raise ValueError("At least one character pool must be enabled")

if length < len(enabled_pools):
    raise PasswordTooShortError(
        f"length={length} is too small to include one character "
        f"from each of {len(enabled_pools)} enabled pools"
    )
```

Se todos os pools foram desativados, recusamos. Se o usuário quer uma senha mais curta do que o número de pools que ele ativou, também recusamos (não conseguiríamos encaixar um de cada).

### A geração real

```python
alphabet = "".join(enabled_pools.values())

required = [secrets.choice(pool) for pool in enabled_pools.values()]
fill_count = length - len(required)
fill = [secrets.choice(alphabet) for _ in range(fill_count)]

chars = required + fill
_secure_shuffle(chars)

return "".join(chars)
```

Três passos:

1. **Caracteres obrigatórios.** Para cada pool ativado, escolhemos um caractere. Isso garante que a senha final contenha pelo menos um de cada tipo — importante para sites que impõem regras de "deve conter um dígito", embora a amostragem aleatória sem essa garantia seja _tecnicamente_ aceitável.
2. **Preencher o resto.** Escolhemos mais `length - len(required)` caracteres do alfabeto combinado.
3. **Embaralhar.** Sem o embaralhamento, os caracteres obrigatórios estariam sempre nas posições 0..N-1 — o que é um padrão previsível e uma fraqueza, por menor que seja.

**`secrets.choice(pool)`** é a versão segura de `random.choice(pool)`. Escolhe um elemento uniformemente de forma aleatória.

**`for _ in range(fill_count)`** — o sublinhado é uma convenção do Python que significa "eu preciso de uma variável de loop, mas não vou usar seu valor". O mesmo que o identificador em branco do Go.

### `_secure_shuffle`

```python
def _secure_shuffle(items: list[str]) -> None:
    for i in range(len(items) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        items[i], items[j] = items[j], items[i]
```

Isso implementa o **embaralhamento Fisher-Yates** (também chamado de embaralhamento Knuth). Ele produz uma permutação uniformemente aleatória se a fonte aleatória for uniforme.

Por que não `random.shuffle()`? Porque o `random.shuffle()` usa o Mersenne Twister, que é previsível. Precisamos de um embaralhamento que um atacante não possa prever, então o construímos nós mesmos sobre o `secrets.randbelow`.

A linha `items[i], items[j] = items[j], items[i]` é a sintaxe de **troca de tuplas** (tuple-swap) do Python para trocar dois valores sem uma variável temporária. Funciona porque o lado direito é totalmente avaliado antes de qualquer atribuição acontecer no lado esquerdo.

**Sublinhado inicial** em `_secure_shuffle`: convenção para "este é um auxiliar privado do módulo, não me importe de fora deste módulo". O Python não impõe isso; é uma documentação voltada para humanos.

---

## 4. `vault.py` — formato de arquivo, escritas atômicas, bloqueio

Abra [`src/password_manager/vault.py`](../src/password_manager/vault.py).

Este é o arquivo mais longo (~1000 linhas incluindo docstrings/comentários). É o que tem mais coisas acontecendo. Leia-o em partes.

### `from __future__ import annotations`

A primeiríssima importação. Este é um opt-in da [PEP 563](https://peps.python.org/pep-0563/) que faz com que os type hints sejam avaliados como strings em vez de objetos reais. O benefício: as classes podem se referir a si mesmas em suas próprias anotações (`def foo(self) -> UnlockedVault` de dentro de `UnlockedVault`) sem precisar colocá-las entre aspas. Também acelera ligeiramente o carregamento do módulo. Será o comportamento padrão em alguma versão futura do Python, por enquanto é opcional.

### Importações — para que servem, brevemente

```python
import base64           # codifica bytes brutos como texto ASCII para JSON
import contextlib       # `contextlib.suppress` e `@contextmanager`
import json             # analisa e serializa JSON
import os               # operações de sistema de arquivos de baixo nível (open/replace/fsync)
from collections.abc import Iterator   # type hint para retorno de gerador
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, UTC     # timestamps em UTC
from pathlib import Path
from types import TracebackType        # type hint para __exit__
from typing import Any, Self           # Any para JSON opaco, Self para tipos de retorno de método
```

O bloco `try`/`except ImportError` para o `fcntl` é um ajuste de portabilidade: o `fcntl` é apenas para POSIX. No Windows, `import fcntl` lançaria `ImportError`. Nós o capturamos, definimos a variável como `None` e verificamos por `None` no momento da chamada. O comentário `# pragma: no cover` diz à ferramenta de cobertura para pular aquela linha nos relatórios de cobertura.

### Exceções

Seis classes:

```python
class VaultError(Exception): pass
class VaultNotFoundError(VaultError): pass
class VaultAlreadyExistsError(VaultError): pass
class VaultFormatError(VaultError): pass
class EntryNotFoundError(VaultError): pass
class EntryAlreadyExistsError(VaultError): pass
```

`pass` é a palavra-chave para "este bloco não tem código". Uma classe com apenas `pass` é uma classe válida que apenas herda tudo de seu pai. Usamos isso aqui porque os _nomes_ são o ponto principal — `except VaultNotFoundError:` permite que quem chama trate esse erro específico sem capturar bugs não relacionados.

### Auxiliares de Base64

```python
def _b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")

def _b64decode(text: str) -> bytes:
    try:
        return base64.b64decode(text, validate=True)
    except (ValueError, TypeError) as exc:
        raise VaultFormatError(f"Invalid base64 in vault: {exc}") from exc
```

`base64.b64encode` retorna `bytes`. Usamos `.decode("ascii")` para obter uma `str` porque as chaves/valores JSON devem ser strings.

`validate=True` é importante: por padrão, o `b64decode` ignora silenciosamente caracteres inválidos. Com `validate=True`, ele lança um erro em caso de entrada inválida — que é o que queremos para "estou lendo um arquivo de vault e espero um base64 bem formado".

### `_validate_entry_name`

```python
def _validate_entry_name(name: str) -> None:
    if not name or not name.strip():
        raise ValueError("Entry name cannot be empty or whitespace")
    if name != name.strip():
        raise ValueError(
            "Entry name must not have leading or trailing whitespace"
        )
```

A verificação de espaços em branco no início/fim é sutil. Sem ela, `"github"` e `"github "` seriam duas chaves diferentes, parecendo idênticas na tela. Rejeitamos a ambiguidade na fronteira.

### `_file_lock` — o gerenciador de contexto

```python
@contextlib.contextmanager
def _file_lock(target_path: Path) -> Iterator[None]:
    if _fcntl is None:
        yield
        return

    lock_path = target_path.with_suffix(target_path.suffix + ".lock")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(
        lock_path,
        os.O_RDWR | os.O_CREAT,
        VAULT_FILE_MODE,
    )
    try:
        _fcntl.flock(fd, _fcntl.LOCK_EX)
        try:
            yield
        finally:
            _fcntl.flock(fd, _fcntl.LOCK_UN)
    finally:
        os.close(fd)
```

O decorador `@contextlib.contextmanager` transforma uma função geradora em um gerenciador de contexto (algo utilizável com `with`). O padrão é:

```python
@contextlib.contextmanager
def minha_coisa():
    # configuração (setup)
    yield recurso    # <-- a linha `with X as recurso:` recebe isso
    # desmontagem (teardown)
```

No nosso caso, "setup" é "adquirir o bloqueio" e "teardown" é "liberar o bloqueio". O `yield` não retorna um valor útil — ele apenas marca o ponto onde o bloco `with` é executado.

**O aninhamento `try`/`finally`** é o que torna a limpeza à prova de balas: mesmo que o código do usuário dentro do `with` lance uma exceção, os blocos `finally` ainda rodam, o bloqueio é liberado e o descritor de arquivo é fechado.

**`fcntl.LOCK_EX`** é um bloqueio exclusivo — apenas um processo pode detê-lo por vez. Se outro processo já o tiver, nós bloqueamos (esperamos) até que ele seja liberado. Para uma ferramenta CLI de usuário único, bloquear está ok.

### Dataclass `Entry`

```python
@dataclass(slots=True, frozen=True)
class Entry:
    username: str
    password: str
    url: str = ""
    notes: str = ""
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
```

`frozen=True` pelo mesmo motivo que `KdfParameters` — uma vez construída, uma entrada é imutável.

**`field(default_factory=_now_iso)`** é como você dá a um campo de dataclass um valor padrão _novo_ em cada nova instância. Se escrevêssemos `created_at: str = _now_iso()`, isso chamaria `_now_iso()` uma vez no momento da definição da classe e reutilizaria o mesmo timestamp para sempre. `default_factory=_now_iso` (nota: passando a função em si, não a chamando) diz à dataclass para chamá-la uma vez por invocação de `Entry()`.

### `Entry.from_dict`

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Entry:
    try:
        username = data["username"]
        password = data["password"]
    except KeyError as exc:
        raise VaultFormatError(
            f"Entry missing required field: {exc}"
        ) from exc
    if not isinstance(username, str) or not isinstance(password, str):
        raise VaultFormatError("Entry username and password must be strings")
    return cls(
        username=username,
        password=password,
        url=data.get("url", ""),
        notes=data.get("notes", ""),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
    )
```

Este é o caminho de "desserializar do JSON". Campos obrigatórios usam `data["username"]` — uma chave ausente lança `KeyError`, que capturamos e transformamos em `VaultFormatError`. Campos opcionais usam `data.get("url", "")` — `dict.get(key, default)` retorna o padrão se a chave estiver ausente.

Observe que os timestamps assumem `""` por padrão em vez de "agora". Se assumíssemos "agora" durante a leitura, uma entrada antiga que não registrou seu horário de criação pareceria recém-criada — enganoso.

### `UnlockedVault` — a classe principal

```python
@dataclass(slots=True)
class UnlockedVault:
    path: Path
    salt: bytes
    kdf_parameters: KdfParameters
    key: bytes
    entries: dict[str, Entry]
```

Esta dataclass **não é frozen**. Ela precisa ser mutável para que possamos adicionar/excluir entradas e rotacionar a senha mestra. O campo `key` contém a chave AES de 32 bytes derivada da senha mestra; o campo `entries` contém as linhas de credenciais descriptografadas.

### `UnlockedVault.create`

```python
@classmethod
def create(
    cls,
    path: Path,
    master_password: str,
    *,
    kdf_parameters: KdfParameters | None = None,
) -> Self:
    if path.exists():
        raise VaultAlreadyExistsError(f"Vault already exists at {path}")

    salt = generate_salt()
    kdf_parameters = kdf_parameters or KdfParameters.defaults()
    key = derive_key(master_password, salt, kdf_parameters)

    vault = cls(
        path=path,
        salt=salt,
        kdf_parameters=kdf_parameters,
        key=key,
        entries={},
    )
    vault.save()
    return vault
```

**`-> Self`** é a forma do Python 3.11 de dizer "este método retorna uma instância desta mesma classe". Útil para métodos herdados para manter os tipos corretos.

**`kdf_parameters or KdfParameters.defaults()`** usa o `or` de curto-circuito do Python. Se `kdf_parameters` for `None` (falso), o lado direito é executado e produz os padrões. Se um `KdfParameters` real foi passado, isso é verdadeiro e nós o usamos.

O argumento `kdf_parameters` é o ponto de entrada (seam) que os testes usam. Os testes passam parâmetros fracos para fazer o Argon2 terminar em milissegundos. Chamadores em produção passam `None` e recebem os padrões reais.

### `UnlockedVault.unlock`

```python
@classmethod
def unlock(cls, path: Path, master_password: str) -> Self:
    if not path.exists():
        raise VaultNotFoundError(f"No vault at {path}")

    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise VaultFormatError(f"...") from exc

    salt, kdf_parameters, nonce, ciphertext = _parse_envelope(envelope)

    key = derive_key(master_password, salt, kdf_parameters)
    plaintext_bytes = decrypt(ciphertext, nonce, key)

    try:
        entries_data = json.loads(plaintext_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise VaultFormatError(f"...") from exc

    entries = {
        name: Entry.from_dict(row)
        for name, row in entries_data.items()
    }

    return cls(
        path=path,
        salt=salt,
        kdf_parameters=kdf_parameters,
        key=key,
        entries=entries,
    )
```

Lido de cima para baixo:

1. **Verificação de existência do arquivo** — lança `VaultNotFoundError` se não existir.
2. **Lê + analisa o envelope JSON.** `Path.read_text(encoding="utf-8")` lê todo o arquivo como uma string em uma única chamada.
3. **`_parse_envelope`** extrai os quatro campos que precisamos, validando a versão e os nomes dos algoritmos. Retorna uma tupla, desempacotada em quatro variáveis.
4. **Deriva a chave usando o salt e os parâmetros do arquivo** — _não_ os padrões de hoje. Este é o segredo que permite que vaults antigos continuem funcionando.
5. **Descriptografa.** `WrongPasswordError` borbulha para cima.
6. **Analisa o JSON descriptografado** em um dicionário `entries_data`.
7. **Converte cada linha** (um dicionário simples) em uma instância de `Entry` via dict comprehension.

### `UnlockedVault.save`

```python
def save(self) -> None:
    entries_json = json.dumps(
        {name: entry.to_dict() for name, entry in self.entries.items()},
        sort_keys=True,
        indent=2,
    ).encode("utf-8")

    nonce, ciphertext = encrypt(entries_json, self.key)

    envelope = _build_envelope(
        salt=self.salt,
        kdf_parameters=self.kdf_parameters,
        nonce=nonce,
        ciphertext=ciphertext,
    )
    envelope_bytes = json.dumps(envelope, indent=2).encode("utf-8")

    self.path.parent.mkdir(parents=True, exist_ok=True)

    with _file_lock(self.path):
        self._atomic_write(envelope_bytes)
```

Cinco passos:

1. **Serializa o dicionário de entradas para bytes JSON.** `sort_keys=True` torna a saída determinística — bom para comparar arquivos criptografados.
2. **Criptografa.** Nonce novo gerado dentro de `encrypt()`.
3. **Constrói o dicionário do envelope.**
4. **Serializa o envelope para bytes.**
5. **Adquire o bloqueio, faz a escrita atômica.** O bloqueio é liberado automaticamente quando o bloco `with` termina.

### `UnlockedVault._atomic_write`

```python
def _atomic_write(self, envelope_bytes: bytes) -> None:
    tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")

    fd = os.open(
        tmp_path,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        VAULT_FILE_MODE,
    )
    try:
        try:
            os.write(fd, envelope_bytes)
            os.fsync(fd)
        finally:
            os.close(fd)

        os.replace(tmp_path, self.path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp_path)
        raise

    if os.name != "nt":
        dir_fd = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
```

As flags para `os.open`:

- **`os.O_WRONLY`** — abrir apenas para escrita.
- **`os.O_CREAT`** — criar se estiver ausente.
- **`os.O_TRUNC`** — truncar para zero se já existir.

O terceiro argumento (`VAULT_FILE_MODE = 0o600`) é o modo do arquivo aplicado no _momento da criação_. Usar `os.open` em vez do `Path.write_bytes` de nível superior nos permite definir o modo na mesma chamada de sistema, evitando a janela curta onde um arquivo recém-criado teria permissões mais amplas (determinadas pelo umask).

**`except BaseException`** — captura _tudo_, incluindo `KeyboardInterrupt` e `SystemExit`. Usamos a captura mais ampla aqui porque queremos limpar o arquivo temporário não importa o que nos tenha interrompido. O `raise` ao final relança a exceção original.

**`contextlib.suppress(FileNotFoundError)`** — uma linha para "ignore esta exceção específica se ela acontecer". Usado aqui porque o arquivo temporário pode não existir se tivermos caído antes de criá-lo.

**O fsync do diretório** ao final é a segunda de duas chamadas fsync. A primeira (`os.fsync(fd)`) descarrega os _bytes_ do arquivo. A segunda (`os.fsync(dir_fd)`) descarrega a _entrada_ do diretório — sem ela, a própria renomeação pode ser perdida em uma queda de energia. O POSIX exige ambas.

`os.name != "nt"` pula o fsync do diretório no Windows porque o NTFS não o suporta. O journaling do NTFS cuida da durabilidade lá.

### `UnlockedVault.add_entry`

```python
def add_entry(self, name: str, entry: Entry, *, force: bool = False) -> None:
    _validate_entry_name(name)
    if name in self.entries and not force:
        raise EntryAlreadyExistsError(f"Entry already exists: {name}")
    if name in self.entries:
        old = self.entries[name]
        entry = replace(entry, created_at=old.created_at, updated_at=_now_iso())
    self.entries[name] = entry
```

**`replace(entry, created_at=..., updated_at=...)`** é um auxiliar de dataclasses que constrói uma nova instância com alguns campos alterados. Como `Entry` é frozen, não podemos modificá-la no local — `replace` cria uma cópia nova com as sobreposições aplicadas. Isso preserva o `created_at` original enquanto atualiza o `updated_at`.

### `UnlockedVault.change_master_password`

```python
def change_master_password(
    self,
    new_master_password: str,
    *,
    kdf_parameters: KdfParameters | None = None,
) -> None:
    if not new_master_password:
        raise ValueError("new_master_password must not be empty")

    new_salt = generate_salt()
    new_kdf_parameters = kdf_parameters or KdfParameters.defaults()
    new_key = derive_key(new_master_password, new_salt, new_kdf_parameters)

    self.salt = new_salt
    self.kdf_parameters = new_kdf_parameters
    self.key = new_key
```

Nota: **este método apenas altera o estado em memória.** Ele não toca no disco. Quem chama deve chamar `save()` em seguida. Por que dividir assim? Porque manter efeitos colaterais em camadas diferentes torna os testes mais limpos — e porque se fizéssemos o salvamento dentro, um crash no meio do salvamento deixaria o _arquivo_ em um estado indefinido enquanto a memória diria "rotação bem-sucedida".

### `close`, `__enter__`, `__exit__`

```python
def close(self) -> None:
    self.entries = {}
    self.key = bytes(KEY_LENGTH_BYTES)

def __enter__(self) -> Self:
    return self

def __exit__(self, exc_type, exc_val, exc_tb) -> None:
    self.close()
```

`__enter__` e `__exit__` são os métodos especiais do Python que fazem o `with vault as v:` funcionar. `__enter__` roda no início e seu valor de retorno é o que o `as v` recebe. `__exit__` roda no final — normal ou via exceção.

`bytes(N)` constrói um objeto bytes de N bytes zero. Portanto, `self.key = bytes(32)` substitui a chave por 32 bytes zero. Não _podemos_ zerar os bytes originais no local porque os bytes do Python são imutáveis, mas podemos descartar a referência. Esta é uma limpeza de melhor esforço.

### `_build_envelope` and `_parse_envelope`

Estes são os auxiliares de "serializar esta dataclass no dicionário do envelope" e "desserializar o dicionário do envelope em partes tipadas". A parte interessante de `_parse_envelope` é a validação:

```python
if version != VAULT_FORMAT_VERSION:
    raise VaultFormatError(f"Unsupported vault version: {version} ...")
```

Recusamos vaults de uma versão de formato futura. Melhor falhar ruidosamente do que ler um vault escrito por uma versão futura da ferramenta com semânticas sutilmente diferentes.

A validação dos parâmetros Argon2 contra os mínimos algorítmicos é o resto da função. Um arquivo de vault corrompido com `time_cost=0` travaria nas profundezas do argon2-cffi; nós o capturamos na fronteira e exibimos um erro limpo.

---

## 5. `main.py` — a CLI

Abra [`src/password_manager/main.py`](../src/password_manager/main.py).

Este arquivo é a cola entre o teclado do usuário e o resto do código. Ele usa o **Typer** para análise de argumentos e o **Rich** para saída colorida.

### Básico do `Typer`

```python
app = typer.Typer(
    name="pv",
    help="Encrypted password manager (Argon2id + AES-256-GCM)",
    no_args_is_help=True,
    add_completion=False,
)
```

`typer.Typer()` cria um "app" — um registro ao qual os comandos se anexam. Então, cada comando é uma função decorada com `@app.command()`:

```python
@app.command()
def init(vault: VaultPath = DEFAULT_VAULT_PATH) -> None:
    """Create a new empty vault at --vault (or PV_VAULT or default path)"""
    ...
```

O nome da função torna-se o nome do comando. `pv init` executa a função `init`. A docstring da função torna-se o texto de `--help` para aquele comando. Os type hints nos parâmetros dizem ao Typer como analisá-los.

### `Annotated` e `typer.Option` / `typer.Argument`

```python
VaultPath = Annotated[
    Path,
    typer.Option(
        "--vault",
        "-v",
        help="Path to the vault file",
        envvar="PV_VAULT",
    ),
]
```

**`Annotated[T, metadata]`** é uma forma de anexar metadados extras a um type hint sem alterar seu tipo subjacente. O Typer lê os metadados para construir o comportamento da CLI; todo o resto (mypy, runtime) vê apenas `Path`.

Definimos `VaultPath` uma vez como um alias de tipo para que cada comando aceite a mesma flag `--vault` com a mesma descrição e suporte a variável de ambiente. Mantendo o código DRY (Don't Repeat Yourself).

`envvar="PV_VAULT"` é uma conveniência do Typer: se `--vault` não for passado, o Typer lê `$PV_VAULT` do ambiente. Se isso também estiver ausente, o padrão da função (`DEFAULT_VAULT_PATH`) entra em ação.

### Dois consoles, dois streams

```python
console = Console()
error_console = Console(stderr=True)
```

**stdout** é para o "resultado" do comando (saída de sucesso, o painel de senha, a tabela de entradas). **stderr** é para diagnósticos e erros. Esta divisão permite que os usuários redirecionem de forma limpa:

```bash
pv gen 32 | pbcopy           # apenas a senha vai para a área de transferência
pv get foo 2>/dev/null       # descarta erros, mantém o painel de credenciais
```

Se tudo passasse por um único console, nenhum redirecionamento funcionaria de forma limpa.

### `_prompt_master_password`

```python
def _prompt_master_password(prompt: str = PROMPT_MASTER_PASSWORD) -> str:
    return getpass.getpass(prompt)
```

`getpass.getpass(prompt)` lê a entrada do terminal _sem ecoá-la_. A mesma primitiva que o `sudo` usa. O usuário digita sua senha, não vê nada, pressiona Enter, e o `getpass` retorna a string.

Nós a envolvemos em uma função para termos um único lugar para trocar se algum dia quisermos um modo não interativo (ler do stdin sem solicitar, para scripts).

### `_unlock_or_exit`

```python
def _unlock_or_exit(path: Path, master_password: str) -> UnlockedVault:
    try:
        return UnlockedVault.unlock(path, master_password)
    except VaultNotFoundError:
        error_console.print(f"[red]{MSG_VAULT_NOT_FOUND.format(path=path)}[/red]")
        raise typer.Exit(code=1) from None
    except WrongPasswordError:
        error_console.print(f"[red]{MSG_WRONG_MASTER_PASSWORD}[/red]")
        raise typer.Exit(code=1) from None
    except VaultFormatError as exc:
        error_console.print(f"[red]Vault file is invalid: {exc}[/red]")
        raise typer.Exit(code=1) from None
    except VaultError as exc:
        error_console.print(f"[red]Vault error: {exc}[/red]")
        raise typer.Exit(code=1) from None
```

Um auxiliar que envolve o `UnlockedVault.unlock` e transforma cada tipo de erro na mensagem correta + código de saída. Os comandos da CLI chamam isso para não terem que repetir o bloco try/except.

**`typer.Exit(code=1)`** é a forma limpa do Typer de sair com um status diferente de zero. Nunca chamamos `sys.exit` nós mesmos; o Typer envolve toda a chamada `app()` em algo que converte `typer.Exit` em uma saída real.

**`from None`** ao final de `raise X from None` suprime o encadeamento do traceback. Sem ele, o usuário veria "While handling X, Y occurred" — útil para depuração, mas ruidoso para "sabíamos que isso poderia falhar e tratamos de forma limpa".

A marcação `[red]...[/red]` é a sintaxe de cor do Rich — ela é renderizada como texto vermelho em um terminal que suporta cores, e como texto simples em um terminal que não suporta.

### Um comando representativo — `add`

```python
@app.command()
def add(
    name: Annotated[str, typer.Argument(help="Entry name (must be unique)")],
    vault: VaultPath = DEFAULT_VAULT_PATH,
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite if exists")] = False,
    generate: Annotated[bool, typer.Option("--generate", "-g", help="...")] = False,
    length: Annotated[int, typer.Option("--length", "-n", help="...")] = DEFAULT_GENERATED_PASSWORD_LENGTH,
) -> None:
    """Add (or overwrite with --force) an entry in the vault"""
    master = _prompt_master_password()
    with _unlock_or_exit(vault, master) as unlocked:
        username = input(PROMPT_ENTRY_USERNAME.format(entry=name))

        if generate:
            try:
                password = generate_password(length)
            except PasswordTooShortError as exc:
                error_console.print(f"[red]{exc}[/red]")
                raise typer.Exit(code=1) from None
            console.print(f"[green]Generated password:[/green] {password}")
        else:
            password = _prompt_master_password(f"Password for {name} (hidden): ")

        url = input(PROMPT_ENTRY_URL).strip()
        notes = input(PROMPT_ENTRY_NOTES).strip()

        entry = Entry(username=username, password=password, url=url, notes=notes)

        try:
            unlocked.add_entry(name, entry, force=force)
        except EntryAlreadyExistsError:
            error_console.print(f"[red]{MSG_ENTRY_ALREADY_EXISTS.format(name=name)}[/red]")
            raise typer.Exit(code=1) from None
        except ValueError as exc:
            error_console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1) from None

        unlocked.save()
    console.print(f"[green]{MSG_ENTRY_ADDED.format(name=name)}[/green]")
```

O comando demonstra o padrão recorrente em cada comando:

1. **Solicitar senha mestra.**
2. **Abrir o bloco `with`** — `_unlock_or_exit` cuida do desbloqueio e de quaisquer erros nesse momento.
3. **Fazer o trabalho** — coletar entrada, chamar `add_entry`, tratar quaisquer erros durante o trabalho.
4. **`save()` dentro do bloco `with`** — precisamos da chave para salvar.
5. **Fim do bloco `with`** — o vault limpa sua chave e entradas.
6. **Imprimir mensagem de sucesso** — após a limpeza, a entrada não está mais na memória, mas a mensagem de sucesso não precisa dela.

Observe `password = _prompt_master_password(f"Password for {name} (hidden): ")`. Reutilizamos o mesmo auxiliar baseado em `getpass` que solicita a senha mestra, mas com uma string de prompt diferente, para que a senha da _entrada_ também seja digitada de forma oculta. Isso é apenas conveniência — a senha da entrada não é mais secreta que a mestra, mas é uma UX melhor não ecoá-la.

### `gen` — o único comando sem um vault

```python
@app.command()
def gen(
    length: Annotated[int, typer.Argument(help="Password length")] = DEFAULT_GENERATED_PASSWORD_LENGTH,
    no_symbols: Annotated[bool, typer.Option("--no-symbols", help="Letters and digits only")] = False,
    no_digits: Annotated[bool, typer.Option("--no-digits", help="Letters and symbols only")] = False,
    no_uppercase: Annotated[bool, typer.Option("--no-uppercase", help="No uppercase letters")] = False,
) -> None:
    try:
        password = generate_password(
            length,
            use_lowercase=True,
            use_uppercase=not no_uppercase,
            use_digits=not no_digits,
            use_symbols=not no_symbols,
        )
    except (PasswordTooShortError, ValueError) as exc:
        error_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from None

    print(password)
```

Observe o **`print()` simples em vez de `console.print()`**. O `console.print` do Rich adicionaria códigos de escape de cor ANSI se o terminal os suportasse. Não queremos isso dentro de uma senha que pode ser enviada para o `pbcopy`. O `print` simples é a ferramenta certa aqui.

As flags são negativas (`--no-symbols`, `--no-digits`, `--no-uppercase`) porque os padrões são _ativados_ — a maioria das pessoas quer uma senha forte com tudo. Dizer "eu não quero X" é o caso raro, o que é a semântica correta para uma flag.

### `change-password`

```python
@app.command(name="change-password")
def change_password(vault: VaultPath = DEFAULT_VAULT_PATH) -> None:
    current = _prompt_master_password("Current master password: ")
    with _unlock_or_exit(vault, current) as unlocked:
        new_password = _prompt_master_password_with_confirmation()
        unlocked.change_master_password(new_password)
        unlocked.save()
    console.print(f"[green]{MSG_MASTER_PASSWORD_CHANGED.format(path=vault)}[/green]")
```

O `name="change-password"` sobrepõe o nome gerado automaticamente (`change_password` a partir do nome da função) para usar um hífen em vez de um sublinhado. Hífens são mais convencionais em CLIs.

O fluxo:

1. Solicitar a senha mestra **atual**.
2. Desbloquear com ela. Se estiver errada, `_unlock_or_exit` sai com 1.
3. Solicitar a **nova** senha mestra (duas vezes, confirmação).
4. Chamar `change_master_password` — apenas altera o estado em memória.
5. `save()` — criptografa tudo sob a nova chave e escreve atomicamente.

Se algo falhar entre os passos 4 e 5, o arquivo no disco ainda terá o salt antigo e o ciphertext antigo. O usuário não terá prejuízo.

---

## 6. `__init__.py` e `__main__.py`

Dois arquivos minúsculos, mas importantes.

### `__init__.py`

Isso torna `password_manager/` um **pacote** Python. Sem um `__init__.py` (ou um `pyproject.toml` declarando-o como um pacote de namespace), o Python não saberia que tem permissão para olhar dentro da pasta.

Além disso, o arquivo reexporta a API pública:

```python
from password_manager.crypto import (
    CryptoError,
    KdfParameters,
    WrongPasswordError,
)
from password_manager.vault import (
    Entry,
    EntryAlreadyExistsError,
    # ...
)
```

Isso permite que chamadores externos (testes, outras ferramentas) escrevam:

```python
from password_manager import UnlockedVault
```

em vez de:

```python
from password_manager.vault import UnlockedVault
```

O benefício é que podemos dividir o `vault.py` em três arquivos mais tarde (ou renomeá-lo) sem quebrar os imports de ninguém — eles passam pela porta da frente do pacote, não pelo layout interno.

```python
__version__ = "1.0.0"

__all__ = [
    "CryptoError",
    "Entry",
    # ...
]
```

**`__version__`** é o nome convencional para a versão do pacote. Ferramentas (`pip`, sistemas de build) podem lê-la.

**`__all__`** é a lista explícita de nomes que `from password_manager import *` trará. Também é documentação: "estes são os nomes que consideramos públicos".

### `__main__.py`

```python
from password_manager.main import app

if __name__ == "__main__":
    app()
```

Este arquivo permite que você execute o pacote diretamente:

```bash
python -m password_manager init
```

Mesmo efeito que `pv init`. Útil quando o script `pv` ainda não está no seu PATH.

A verificação `if __name__ == "__main__":` é o idioma padrão do Python para "apenas execute este código se o arquivo for o ponto de entrada do script". Se algo importar este arquivo (o que não fariam, mas o idioma é universal), a chamada `app()` não dispara.

---

## 7. Os testes

Abra os arquivos em `tests/`. Não percorreremos cada teste, apenas apontaremos os padrões a serem observados.

### `conftest.py`

O Pytest trata o `conftest.py` como algo mágico. Qualquer coisa definida aqui está disponível para cada arquivo de teste no diretório sem um import explícito.

Três fixtures vivem aqui:

- **`vault_path`** — um caminho de vault novo e inexistente dentro de um diretório temporário. Construído sobre a fixture `tmp_path` nativa do pytest, que cria e limpa automaticamente por teste.
- **`master_password`** — uma senha mestra de teste estável (`"correto cavalo bateria grampo"`).
- **`fresh_vault`** — um `UnlockedVault` vazio usando parâmetros Argon2 rápidos.

Os parâmetros Argon2 rápidos são o truque principal:

```python
TEST_KDF_PARAMETERS = KdfParameters(
    time_cost=1,
    memory_cost=8,
    parallelism=1,
)
```

Estes estão abaixo das recomendações da OWASP — _deliberadamente_. Eles reduzem o tempo de execução dos testes de minutos para milissegundos. A correção criptográfica do código é a mesma independentemente da força dos parâmetros; o Argon2 faz as mesmas operações com menos iterações.

Observe que não há monkey-patching de `KdfParameters.defaults()`. Em vez disso, o teste passa `kdf_parameters=TEST_KDF_PARAMETERS` explicitamente para `UnlockedVault.create`. É por isso que o código de produção passa `kdf_parameters` através do construtor — para que os testes possam trocá-lo sem poluir o estado global.

### `test_crypto.py`

Os testes interessantes aqui:

- **Ida e volta (Round-trip).** Criptografa algo, descriptografa, afirma que obteve o original de volta.
- **Adulteração.** Criptografa algo, inverte um byte no ciphertext, afirma que o `decrypt` lança `WrongPasswordError`.
- **Chave errada.** Criptografa com a chave A, tenta descriptografar com a chave B, afirma `WrongPasswordError`.
- **Determinismo do salt.** Mesma senha + mesmo salt → mesma chave. Mesma senha + salt _diferente_ → chave _diferente_.

Os testes de adulteração são os críticos para a segurança. Se a autenticação GCM algum dia parasse de funcionar, esses testes falhariam ruidosamente.

### `test_vault.py`

Testes de ponta a ponta do vault. Os padrões a serem observados:

- **Cada teste recebe um caminho de vault novo.** O `tmp_path` do Pytest torna cada teste totalmente isolado.
- **Testes de ida e volta.** Cria o vault, adiciona entrada, salva, desbloqueia com a senha certa, recupera a entrada.
- **Testes de modos de falha.** Senha errada, arquivo ausente, JSON corrompido, ciphertext modificado, envelope modificado, campos ausentes, nome de algoritmo errado.
- **Testes de validação de nome/espaço em branco.** `"github "` é rejeitado. `""` é rejeitado.
- **Testes de `change_master_password`.** Rotaciona, salva, reabre com a nova senha, falha com a senha antiga.

### `test_generator.py`

Testes para o gerador de senhas:

- **Comprimento.** O resultado tem exatamente o comprimento solicitado.
- **Cobertura de pools.** O resultado contém pelo menos um caractere de cada pool ativado.
- **Exclusão de pools.** Pools desativados nunca aparecem.
- **Casos de recusa.** Comprimento abaixo do mínimo, nenhum pool ativado, comprimento menor que a contagem de pools.
- **Sanidade da aleatoriedade.** Gera muitas senhas, afirma que não são todas iguais. (Não é um teste de aleatoriedade _real_ — isso não seria estatisticamente significativo para tão poucas amostras — apenas uma verificação de sanidade de que a função não está retornando uma constante).

---

## Para onde ir em seguida

Você viu cada arquivo. Sabe o que cada função faz e por quê. A última peça é o **[04-Desafios.md](./04-Desafios.md)** — ideias de extensão se você quiser continuar.

Depois disso, o melhor movimento de aprendizado é escrever sua própria versão _sem olhar para esta_. Abra um arquivo vazio e tente reconstruir o projeto de memória. Os lugares onde você tiver que pesquisar algo são os lugares que você ainda não entende — volte para aquela seção e leia-a novamente.
