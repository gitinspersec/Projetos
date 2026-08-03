# Explicação da implementação

Esta página percorre `hash_identifier.py` do início ao fim junto com você. Cada recurso do Python é explicado na primeira vez em que aparece. Se você está começando agora em Python, leia este material com o arquivo-fonte aberto em outra janela para acompanhar exatamente as linhas discutidas.

> Ao longo desta página, quando mencionarmos "o arquivo-fonte", estaremos nos referindo a `hash_identifier.py`. Abra-o agora: `code hash_identifier.py`, `nano hash_identifier.py` ou qualquer editor que você utilize.

## 1. O cabeçalho do arquivo

```python
"""
©AngelaMos | 2026
Copyright (C) 2026 Murilo Miacci
hash_identifier.py

Identifica que tipo de hash é a string, inspecionando o seu formato
...
"""
```

Esse bloco delimitado por aspas triplas no início do arquivo é chamado de **docstring do módulo**.

Em Python, qualquer conteúdo entre `"""..."""` é um literal do tipo string. Quando o interpretador carrega o arquivo, percebe que essa string está logo no início, sem estar atribuída a nenhuma variável, e passa a tratá-la como a documentação oficial do módulo. Posteriormente, ela pode ser consultada com `help(hash_identifier)` ou exibida automaticamente pela IDE ao passar o cursor sobre um `import`.

A primeira linha, `©AngelaMos | 2026`, é o aviso de copyright exigido em todos os arquivos deste repositório. A segunda linha contém outro aviso de copyright para a refatoração desse material para a Liga Insper Sec. Em seguida vem uma descrição legível para humanos explicando o propósito do módulo. Você encontrará exatamente esse padrão em todos os projetos da categoria `PROJECTS/foundations/`.

> **Por que usar uma docstring em vez de um comentário?** Python possui ambos. Um comentário (`#`) é descartado antes da execução do código. Já uma `"""docstring"""` fica armazenada no atributo `__doc__` do módulo, função ou classe e permanece disponível durante a execução. Ferramentas como Sphinx, mkdocs e a ajuda da própria IDE utilizam docstrings, não comentários. Regra prática: use docstrings para explicar "o que isto é e como utilizar"; use comentários para explicar "por que esta linha específica existe".

## 2. Imports

```python
import argparse
import sys
from dataclasses import dataclass
from typing import Literal

from rich.console import Console
from rich.table import Table
```

Uma instrução `import` traz código de outro arquivo para o seu.

O Python já acompanha centenas de módulos em sua **biblioteca padrão** (disponíveis sem qualquer instalação), mas você também pode instalar bibliotecas externas pelo [PyPI](https://pypi.org/) usando `uv add <pacote>`.

Existem duas formas principais de importar:

- `import argparse` — importa o módulo inteiro sob seu próprio nome. Depois você acessa seus elementos usando `argparse.ArgumentParser`.
- `from dataclasses import dataclass` — importa apenas um elemento específico, permitindo utilizá-lo diretamente como `dataclass`, em vez de `dataclasses.dataclass`.

Prefira a segunda forma quando precisar de apenas um ou dois elementos bem definidos. Utilize a primeira quando importar muitos nomes poderia causar conflitos.

A linha em branco separando módulos da biblioteca padrão de bibliotecas de terceiros segue uma convenção definida pela [PEP 8](https://peps.python.org/pep-0008/#imports). Os linters verificarão isso automaticamente.

Resumo dos imports utilizados:

| Import      | O que é                                                              | Por que precisamos dele                                     |
| ----------- | -------------------------------------------------------------------- | ----------------------------------------------------------- |
| `argparse`  | Parser de argumentos da linha de comando da biblioteca padrão        | Converte `sys.argv` em atributos como `args.hash`           |
| `sys`       | Módulo da biblioteca padrão para interação com o interpretador       | Utilizado em `sys.exit(...)` para definir o código de saída |
| `dataclass` | Decorador que transforma uma classe em um pequeno registro           | Evita escrever manualmente o `__init__` de `HashCandidate`  |
| `Literal`   | Type hint indicando que um valor só pode assumir determinados textos | Restringe `confidence` a `"high"`, `"medium"` ou `"low"`    |
| `Console`   | Classe da biblioteca [`rich`](https://github.com/Textualize/rich)    | Responsável pela saída colorida no terminal                 |
| `Table`     | Também da biblioteca `rich`                                          | Constrói a tabela colorida apresentada ao usuário           |

## 3. O tipo `Literal`

```python
Confidence = Literal["high", "medium", "low"]
```

Essa linha cria um **apelido de tipo** (_type alias_).

Em vez de escrever repetidamente `Literal["high", "medium", "low"]`, damos a esse tipo o nome `Confidence`.

Um tipo `Literal` significa:

> "Este valor deve ser exatamente um destes textos, e nenhum outro."

Assim, um código como:

```python
candidate = HashCandidate(algorithm="MD5", confidence="hgih", reason=...)
                                                       ^^^^^^
                                                       erro de digitação
```

será detectado pelo `mypy` antes mesmo da execução.

Sem `Literal`, o tipo seria simplesmente `str`, e `"hgih"` passaria despercebido até alguém notar o erro na saída do programa.

Foi escolhido `Literal` em vez de `Enum` porque o conjunto de valores é pequeno. Para conjuntos maiores ou quando os valores possuem comportamento próprio, `Enum` costuma ser mais adequado.

## 4. A dataclass `HashCandidate`

```python
@dataclass(frozen=True, slots=True)
class HashCandidate:
    """One possible identification of a hash string ..."""
    algorithm: str
    confidence: Confidence
    reason: str
```

Esse é o objeto retornado pelo cérebro da aplicação.

Vamos analisar seus componentes:

- **`class HashCandidate:`** cria um novo tipo chamado `HashCandidate`.
- **`algorithm: str`** declara um atributo chamado `algorithm` do tipo `str`. A sintaxe `:` seguida do tipo é uma **anotação de tipos** (_type annotation_).
- **`@dataclass(...)`** é um _decorador_. Decoradores recebem uma classe (ou função), modificam seu comportamento e devolvem uma nova versão.

Nesse caso, `@dataclass` gera automaticamente:

- `__init__`
- `__repr__`
- `__eq__`
- e outros métodos especiais.

Sem `@dataclass`, seria necessário escrever manualmente:

```python
class HashCandidate:
    def __init__(self, algorithm: str, confidence: Confidence, reason: str):
        self.algorithm = algorithm
        self.confidence = confidence
        self.reason = reason

    def __repr__(self):
        ...

    def __eq__(self, other):
        ...
```

O parâmetro **`frozen=True`** torna os objetos imutáveis. Após sua criação:

```python
candidate.algorithm = "SHA-256"
```

gera `FrozenInstanceError`.

Isso transforma `HashCandidate` em um **objeto de valor** (_value object_).

Já **`slots=True`** é uma otimização de memória.

Normalmente cada objeto Python possui um `__dict__` para permitir adicionar atributos dinamicamente.

Como sabemos exatamente quais atributos existirão (`algorithm`, `confidence` e `reason`), podemos eliminar esse dicionário interno.

Além de economizar memória, isso impede erros como:

```python
candidate.algoritm = "MD5"
```

(erro de digitação), pois novos atributos deixam de ser aceitos.

Esses dois parâmetros aparecem frequentemente juntos em pequenos registros de dados.

## 5. A tabela `PREFIX_RULES`

```python
PREFIX_RULES: list[tuple[str, str, str]] = [
    ("$argon2id$", "Argon2id", "modern PHC string, the current standard"),
    ("$argon2i$",  "Argon2i",  "PHC string, side-channel-resistant variant"),
    ...
]
```

Essa estrutura é uma **lista de tuplas**.

Uma **lista** (`list`) é a estrutura ordenada mais comum do Python:

```python
[1, 2, 3]
```

Ela permite inserção, remoção e indexação.

Uma **tupla** (`tuple`) é semelhante, porém imutável:

```python
(1, 2, 3)
```

Ela é utilizada quando a posição dos elementos possui significado.

Neste caso:

```
(prefixo,
 algoritmo,
 descrição)
```

sempre aparecem exatamente nessa ordem.

A anotação

```python
list[tuple[str, str, str]]
```

significa exatamente isso:

> uma lista cujos elementos são tuplas contendo três strings.

Essa informação serve apenas para leitores humanos e ferramentas como o `mypy`.

> **Por que usar uma lista em vez de um dicionário?**

Um `dict` permite busca O(1), porém precisamos responder à pergunta:

> "alguma chave deste dicionário é prefixo desta string?"

Como os prefixos possuem comprimentos diferentes, ainda precisaríamos percorrê-los.

Com apenas cerca de 25 entradas, uma lista é suficientemente rápida.

Outro detalhe importante:

A ordem importa.

Por exemplo:

```
$argon2id$
$argon2$
```

O prefixo mais específico precisa aparecer primeiro.

Caso contrário, `$argon2id$...` também corresponderia a `$argon2$`.

## 6. A tabela `HEX_LENGTH_RULES`

```python
HEX_CHARSET: frozenset[str] = frozenset("0123456789abcdefABCDEF")
_HEX_UPPER_CHARSET: frozenset[str] = frozenset("0123456789ABCDEF")

HEX_LENGTH_RULES: dict[int, list[str]] = {
    16:  ["MySQL323", "CRC-64"],
    32:  ["MD5", "NTLM", "MD4", "RIPEMD-128"],
    ...
}
```

Um **set** é uma coleção sem ordem e sem elementos repetidos.

Um **frozenset** é um conjunto imutável.

Ele foi escolhido porque:

1. O conjunto de caracteres hexadecimais nunca muda.
2. Consultas como

```python
c in HEX_CHARSET
```

executam em tempo O(1).

3. O próprio tipo comunica ao leitor que essa estrutura é constante.

Já um **dict** é um mapeamento chave → valor.

Neste caso:

```
comprimento
      ↓
lista de algoritmos
```

Assim,

```python
HEX_LENGTH_RULES[32]
```

retorna:

```python
["MD5", "NTLM", "MD4", "RIPEMD-128"]
```

O `_HEX_UPPER_CHARSET` existe porque o MySQL5 gera apenas letras maiúsculas.

## 7. A função `_is_hex`

```python
def _is_hex(text: str) -> bool:
    """Return True iff every character in text is a hex digit and text is non-empty"""
    return bool(text) and all(c in HEX_CHARSET for c in text)
```

Uma instrução `def` define uma função.

Sua assinatura indica:

- recebe `text` do tipo `str`;
- retorna um `bool`.

Vamos analisar a implementação.

A expressão

```python
(c in HEX_CHARSET for c in text)
```

é uma **generator expression**.

Ela produz uma sequência de valores booleanos.

Depois,

```python
all(...)
```

retorna `True` somente se todos forem verdadeiros.

Já

```python
bool(text)
```

garante que a string não seja vazia.

Isso é necessário porque:

```python
all([])
```

retorna `True`.

Do ponto de vista matemático faz sentido.

Do ponto de vista prático, uma string vazia não é um hash hexadecimal.

O operador `and` faz curto-circuito (_short-circuit_).

Se `bool(text)` for `False`, o restante nem chega a ser avaliado.

A palavra **iff** presente na docstring significa "if and only if" ("se, e somente se").

## 8. Detecção de MySQL5

```python
_MYSQL5_HEX_BODY_LENGTH = 40
_MYSQL5_TOTAL_LENGTH = _MYSQL5_HEX_BODY_LENGTH + 1
```

Essas constantes seguem uma regra do projeto:

> nunca utilizar números mágicos.

Compare:

```python
len(text) != 41
```

com

```python
len(text) != _MYSQL5_TOTAL_LENGTH
```

Ambos funcionam.

O segundo explica imediatamente de onde vem o valor 41.

A função executa três verificações:

1. comprimento total igual a 41;
2. primeiro caractere igual a `*`;
3. corpo composto apenas por caracteres hexadecimais maiúsculos.

Observe também:

```python
body = text[1:]
```

Essa operação é chamada de **slice**.

Ela significa:

```
do índice 1 até o final
```

ou seja, remove apenas o primeiro caractere.

A docstring também explica por que não utilizamos:

```python
body.isupper()
```

`isupper()` retorna `False` para strings compostas apenas por dígitos.

Assim, uma entrada válida contendo somente números seria rejeitada.

Por isso verificamos pertencimento em `_HEX_UPPER_CHARSET`.

Esse é um detalhe sutil que costuma causar erros.

## 9. Detecção de DES crypt

```python
_DESCRYPT_CHARSET: frozenset[str] = frozenset(
    "./0123456789"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
)
```

Aqui aparece um recurso interessante:

**concatenação automática de literais de string.**

Essas três linhas são equivalentes a:

```python
"./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
```

A segunda forma seria muito mais difícil de ler.

A função `_is_descrypt()` apenas verifica:

- comprimento igual a 13;
- caracteres pertencentes ao alfabeto permitido.

Os parênteses existem apenas para facilitar a quebra de linha.

## 10. A função `identify()` — o cérebro

Essa é a principal função do programa.

Ela possui cerca de 100 linhas e segue exatamente as seis etapas descritas em **02-ARCHITECTURE.md**.

### 10a. Comentário do pylint

```python
# pylint: disable=too-many-return-statements,too-many-branches
```

Esse comentário desativa duas verificações do pylint apenas para essa função.

Normalmente muitas ramificações significam que o código deveria ser refatorado.

Neste caso, porém, as ramificações **são** a arquitetura.

Separar cada etapa em uma função diferente tornaria a leitura pior.

Por isso o aviso é desativado de forma explícita.

Boa prática:

> nunca desative um linter globalmente quando apenas uma função exige essa exceção.

### 10b. Assinatura

```python
def identify(raw_input: str) -> list[HashCandidate]:
```

Recebe uma string.

Retorna uma lista de `HashCandidate`.

Entradas desconhecidas não geram exceções.

A função simplesmente retorna:

```python
[]
```

Isso simplifica o código de quem a utiliza.

### 10c. Remoção de espaços

```python
text = raw_input.strip()

if not text:
    return []
```

`strip()` remove espaços e quebras de linha nas extremidades.

Importante:

Strings são imutáveis.

Logo,

```python
strip()
```

retorna uma nova string.

Ela não modifica a original.

Também não transformamos o texto em minúsculas, pois alguns formatos distinguem maiúsculas de minúsculas (como MySQL5).

## 10d. Etapa 1 — percorrer `PREFIX_RULES`

```python
for prefix, algorithm, note in PREFIX_RULES:
```

Cada elemento da lista é uma tupla.

Python permite fazer o **desempacotamento de tuplas** diretamente:

```python
(prefix,
 algorithm,
 note)
```

Depois:

```python
text.startswith(prefix)
```

verifica se a string começa com aquele prefixo.

Outro recurso importante:

```python
f"..."
```

é uma **f-string**.

Tudo entre `{}` é avaliado automaticamente.

Por exemplo:

```python
f"prefix `{prefix}`"
```

insere o conteúdo da variável `prefix` no texto.

Atualmente as f-strings são a forma recomendada para formatação de strings em Python.

## 10e. Etapa 2 — formatos especiais

Trechos como:

```python
"::" in text
```

utilizam o operador `in`.

Ele verifica se uma substring aparece dentro de outra.

Também aparecem:

```python
text.count(":")
```

e

```python
text.split(":")
```

que contam ocorrências e dividem a string em partes.

NetNTLMv1 e NetNTLMv2 possuem estruturas muito específicas.

Por isso basta verificar alguns campos específicos para distingui-los.

Depois entram as funções auxiliares:

```python
_is_mysql5(...)
_is_descrypt(...)
```

Observe que MySQL5 recebe **HIGH confidence**, enquanto DES crypt recebe **MEDIUM**, porque seu formato é menos exclusivo.

## 10f. Etapa 3 — comprimento hexadecimal

Novidades importantes:

```python
dict.get(chave, padrão)
```

Evita `KeyError`.

Depois:

```python
enumerate(lista)
```

gera pares:

```
(índice,
 valor)
```

permitindo descobrir qual algoritmo aparece primeiro.

Também aparece o operador ternário:

```python
"medium" if index == 0 else "low"
```

equivalente ao operador `?:` presente em C e JavaScript.

## 10g. Etapa 4 — fallback PHC

Caso a string comece com `$`, mas não corresponda a nenhum prefixo conhecido, tenta-se extrair o nome do algoritmo.

Aqui aparece:

```python
split("$", 1)
```

O segundo argumento limita o número de divisões.

Também é utilizada:

```python
isalnum()
```

que verifica se um caractere é letra ou número.

Somente nomes válidos são aceitos.

## 10h. Etapa 5 — pistas de formato

```python
text.startswith("eyJ")
```

identifica JWTs.

Já

```python
any(c in text for c in "+/=")
```

verifica se existe pelo menos um caractere típico de Base64.

`any()` é o complemento de `all()`.

Enquanto `all()` exige que todos sejam verdadeiros,

`any()` exige apenas um.

## 10i. Etapa 6 — desistir

```python
return []
```

Lista vazia.

A CLI traduz isso como:

> "não foi possível identificar".

É melhor admitir desconhecimento do que fornecer uma resposta incorreta.

## 11. A camada CLI

### 11a. O parser de argumentos

```python
def _build_argument_parser() -> argparse.ArgumentParser:
```

Cria o parser da linha de comando.

Define:

- um argumento obrigatório (`hash`);
- um argumento opcional (`--top` ou `-n`).

Ele retorna apenas o parser.

Não executa `parse_args()`.

Isso facilita os testes.

Separar construção e execução é um padrão recorrente em software testável.

### 11b. O renderizador da tabela

```python
_render_table(...)
```

Cria uma `rich.Table`.

Adiciona colunas.

Adiciona linhas.

Imprime.

As cores são obtidas por meio de um pequeno dicionário:

```python
confidence_colors = {
    ...
}
```

Em vez de criar internamente um objeto `Console`, ele o recebe como parâmetro.

Esse é outro exemplo de **injeção de dependências**.

## 11c. `main()` e o script guard

```python
if __name__ == "__main__":
    sys.exit(main())
```

Esse é um dos padrões mais importantes do Python.

Quando o arquivo é executado diretamente:

```
python hash_identifier.py
```

o Python define:

```python
__name__ == "__main__"
```

Quando o arquivo é apenas importado:

```python
import hash_identifier
```

o valor passa a ser:

```python
__name__ == "hash_identifier"
```

Assim, a CLI não é executada durante os testes.

`sys.exit()` apenas encerra o programa utilizando o código retornado por `main()`.

## 12. Executando um exemplo real

Para a entrada:

```bash
just run -- '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQNQy.uK4Of2T7G'
```

o fluxo é:

1. O shell executa o programa.
2. Python inicializa `sys.argv`.
3. `main()` é chamado.
4. O parser interpreta os argumentos.
5. `identify()` recebe a string.
6. A Etapa 1 percorre `PREFIX_RULES`.
7. O prefixo `$2b$` é encontrado.
8. Um `HashCandidate` é criado.
9. `_render_table()` monta a tabela.
10. `rich` imprime a saída colorida.
11. O programa retorna código 0.

O tempo gasto pelo cérebro é inferior a um milissegundo.

A maior parte do tempo total é consumida apenas pela renderização da tabela.

## 13. O arquivo de testes

Abra `test_hash_identifier.py`.

Ele contém aproximadamente 25 funções `test_*`.

Cada uma segue exatamente o mesmo padrão:

1. cria uma entrada conhecida;
2. chama `identify()`;
3. verifica o resultado usando `assert`.

Alguns testes particularmente interessantes:

- `test_every_prefix_rule_is_recognized_with_high_confidence`
- `test_mysql5_rejects_lowercase_body`
- `test_hash_candidate_is_frozen`

Execute-os com:

```bash
just test
```

Toda a suíte termina em menos de um segundo.

## 14. O que experimentar agora

Depois de terminar a leitura:

1. Execute `just run -- <hash>` com entradas estranhas: strings vazias (entre aspas), números, JWTs, Base64 e hashes contendo espaços.
2. Adicione temporariamente um `print()` dentro de `identify()` para descobrir qual etapa do pipeline está sendo utilizada em cada entrada. Depois remova esse `print()`.
3. Acrescente um novo prefixo em `PREFIX_RULES` (por exemplo, `$scrypt$`), escreva um teste correspondente e execute `just test`.
4. Leia **[04-Desafios.md](./04-Desafios.md)** para explorar desafios de extensão mais avançados.
