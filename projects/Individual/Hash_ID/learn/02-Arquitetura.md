# Arquitetura

Esta página trata de _como o código é estruturado_. Não do que cada linha faz — isso ficará para a próxima página. Aqui damos um passo para trás e observamos como as peças se encaixam, como os dados fluem e por que escolhemos essa arquitetura em vez de outras.

## 1. A visão geral

Toda a ferramenta consiste em um único arquivo Python: `hash_identifier.py`. Tudo o que é executado está nesse arquivo. Internamente, ele é dividido em três camadas:

```
┌─────────────────────────────────────────────────────────────┐
│  Camada CLI (main, _build_argument_parser, _render_table)   │
│  - lê os argumentos da linha de comando                     │
│  - imprime a tabela colorida no terminal                    │
│  - retorna um código de saída                               │
└──────────────────────────┬──────────────────────────────────┘
                           │ chama
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Camada de funções puras (identify)                         │
│  - contém toda a lógica de decisão                          │
│  - recebe uma string e retorna uma lista de HashCandidate   │
│  - NÃO acessa arquivos, NÃO usa rede, NÃO usa estado global │
└──────────────────────────┬──────────────────────────────────┘
                           │ utiliza
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Camada de dados (PREFIX_RULES, HEX_LENGTH_RULES, charsets)  │
│ - tabelas contendo o conhecimento sobre hashes              │
│ - somente leitura, definidas ao carregar o módulo           │
└─────────────────────────────────────────────────────────────┘
```

Lendo de cima para baixo, a camada CLI representa o **lado externo** do programa: ela interage com o usuário. A camada de funções puras é o **cérebro**: recebe uma string limpa e devolve uma resposta limpa. A camada de dados representa o **conhecimento**: tudo o que "sabemos sobre determinado hash" fica centralizado nessas tabelas, em vez de espalhado pelo código.

Essa separação em três partes é intencional. Podemos testar o cérebro isoladamente sem sequer executar a CLI — e é exatamente isso que o arquivo de testes faz, chamando `identify()` diretamente. Podemos alterar a aparência da tabela (cores, layout, saída JSON) sem tocar na lógica de decisão. E podemos adicionar novos formatos de hash simplesmente acrescentando uma linha a uma tabela, sem escrever novas funções.

## 2. Fluxo de dados durante uma execução

Veja o que acontece quando você executa:

```bash
just run -- 5f4dcc3b5aa765d61d8327deb882cf99
```

```
                                              (seu terminal)
                                                    │
                                                    │  "5f4dcc3b5aa765d61d8327deb882cf99"
                                                    ▼
                               ┌─────────────────────────────────────┐
                               │  argparse                           │
                               │  converte sys.argv em args.hash     │
                               └────────────────┬────────────────────┘
                                                │ args.hash = "5f4dcc..."
                                                ▼
                               ┌─────────────────────────────────────┐
                               │  identify(args.hash)                │
                               │                                     │
                               │  text = args.hash.strip()           │
                               │                                     │
                               │  ┌─────────────────────────────┐    │
                               │  │ Etapa 1: corresponde a um   │    │
                               │  │ prefixo conhecido?          │    │
                               │  └────────────┬────────────────┘    │
                               │  não          │                     │
                               │               ▼                     │
                               │  ┌─────────────────────────────┐    │
                               │  │ Etapa 2: formato especial?  │    │
                               │  │ (NetNTLM / MySQL5 / DES)    │    │
                               │  └────────────┬────────────────┘    │
                               │  não          │                     │
                               │               ▼                     │
                               │  ┌─────────────────────────────┐    │
                               │  │ Etapa 3: hexadecimal +      │    │
                               │  │ comprimento?                │    │
                               │  │ → 32 hex → MD5/NTLM...      │ ✔  │
                               │  └────────────┬────────────────┘    │
                               │               │                     │
                               │     retorna [HashCandidate, ...]    │
                               └────────────────┬────────────────────┘
                                                │
                                                ▼
                               ┌─────────────────────────────────────┐
                               │  _render_table()                    │
                               │  monta uma rich.Table e imprime     │
                               └────────────────┬────────────────────┘
                                                │
                                                ▼
                                        (seu terminal)

      ┌─────────────────────────────────────────────────────────┐
      │ Candidatos para: 5f4dcc3b5aa765d61d8327deb882cf99       │
      │ ╭───────────┬────────────┬────────────────────────────╮ │
      │ │ algoritmo │ confiança  │ motivo                     │ │
      │ ├───────────┼────────────┼────────────────────────────┤ │
      │ │ MD5       │ medium     │ 32 caracteres hex — mais   │ │
      │ │           │            │ provável                   │ │
      │ │ NTLM      │ low        │ 32 caracteres hex — também │ │
      │ │           │            │ possível                   │ │
      │ │ MD4       │ low        │ 32 caracteres hex — também │ │
      │ │           │            │ possível                   │ │
      │ │ RIPEMD-128│ low        │ 32 caracteres hex — também │ │
      │ │           │            │ possível                   │ │
      │ ╰───────────┴────────────┴────────────────────────────╯ │
      └─────────────────────────────────────────────────────────┘
```

O cérebro é o bloco central. Tudo acima e abaixo dele é apenas infraestrutura: colocar a string para dentro e apresentar a tabela na saída.

## 3. O pipeline de decisão em seis etapas

O cérebro (`identify()`) é organizado em **seis etapas numeradas**. Cada etapa representa uma oportunidade de retornar imediatamente um resultado. Se houver uma correspondência, a função termina. Caso contrário, a execução continua para a próxima etapa.

Essa estrutura — "tentar primeiro o sinal mais forte e depois recorrer aos mais fracos" — é chamada de **cascata de decisão** (_decision cascade_) ou **pipeline de regras** (_rule pipeline_). Você encontrará esse padrão em diversas ferramentas de segurança: filtros antispam, IDS, heurísticas de antivírus e fingerprinting.

```
        ┌────────────────────────────────┐
        │ Etapa 1: PREFIX_RULES?         │ HIGH confidence
        │ Percorre a tabela de prefixos. │ ────────► retorna
        │ Primeiro prefixo que casar.    │ imediatamente
        └─────────────┬──────────────────┘
                      │ não encontrou
                      ▼
        ┌────────────────────────────────┐
        │ Etapa 2: formatos especiais?   │ HIGH/MEDIUM
        │ NetNTLMv2 / NetNTLMv1 (`::`)   │ ────────► retorna
        │ MySQL5 (`*` + 40 hex maiúsc.)  │ imediatamente
        │ DES crypt (13 caracteres)      │
        └─────────────┬──────────────────┘
                      │ não encontrou
                      ▼
        ┌────────────────────────────────┐
        │ Etapa 3: hexadecimal puro?     │ MEDIUM/LOW
        │ Se sim, consulta               │ ────────► retorna
        │ HEX_LENGTH_RULES               │ lista ordenada
        └─────────────┬──────────────────┘
                      │ não é hexadecimal
                      ▼
        ┌────────────────────────────────┐
        │ Etapa 4: `$algo$...` genérico? │ LOW
        │ Parece uma string PHC, mas     │ ────────► retorna
        │ sem regra específica.          │ correspondência
        └─────────────┬──────────────────┘
                      │ não
                      ▼
        ┌────────────────────────────────┐
        │ Etapa 5: pista de formato?     │ LOW
        │ Parece JWT (eyJ...) ou         │ ────────► retorna
        │ Base64 (`+`, `/`, `=`)?        │ "não é um hash"
        └─────────────┬──────────────────┘
                      │ não
                      ▼
        ┌────────────────────────────────┐
        │ Etapa 6: desistir.             │ nenhuma
        │ Retorna lista vazia.           │ ────────► []
        │ CLI imprime "não foi possível  │
        │ identificar".                  │
        └────────────────────────────────┘
```

A ordem é importante e não foi escolhida por acaso. Sempre executamos **o teste mais específico primeiro** e **o mais genérico por último**:

1. Prefixos PHC praticamente revelam o algoritmo.
2. Formatos especiais (NetNTLM, MySQL5, DES crypt) também possuem estruturas muito características.
3. Hexadecimal + comprimento apenas reduz as possibilidades; não identifica um algoritmo específico.
4. O fallback PHC genérico captura hashes que possuem formato PHC, mas não estão cadastrados.
5. As pistas de formato tratam o caso comum em que o usuário colou um JWT ou outro conteúdo por engano.
6. Lista vazia significa um honesto "não sei".

Se invertêssemos essa ordem — verificando comprimento antes do prefixo, por exemplo — poderíamos classificar incorretamente um bcrypt antes mesmo de analisar seu prefixo `$2b$`. A ordem representa a prioridade dos critérios.

## 4. O objeto `HashCandidate`

O cérebro não retorna apenas uma string — ele retorna uma lista de objetos `HashCandidate`. Cada candidato possui três campos:

```
┌─────────────────────────────────────────────────────────────┐
│  HashCandidate                                              │
│                                                             │
│    algorithm:   str         ex.: "MD5", "bcrypt", "SHA-256" │
│    confidence:  Literal     "high" | "medium" | "low"       │
│    reason:      str         "prefix `$2b$` — bcrypt PHC..." │
│                                                             │
│  frozen=True ── imutável após a criação                     │
│  slots=True  ── otimizado em memória (sem __dict__)         │
└─────────────────────────────────────────────────────────────┘
```

Essa estrutura foi planejada cuidadosamente.

O campo **`algorithm`** informa exatamente o que o hashcat precisa saber.

O campo **`confidence`** indica ao usuário o quanto aquela hipótese merece confiança.

O campo **`reason`** fornece a evidência — uma explicação de uma linha sobre o motivo da identificação. Esse campo transforma a ferramenta em um recurso didático: em vez de mostrar apenas "bcrypt", ela informa "prefixo `$2b$` — string PHC do bcrypt, variante 2b (atual)".

Utilizamos `@dataclass(frozen=True, slots=True)` em vez de escrever manualmente uma classe com `__init__` e `__repr__`:

- **`frozen=True`** significa que, após criar um `HashCandidate`, ele não pode mais ser modificado. Se algum trecho do código tentar executar `candidate.algorithm = "outra coisa"`, o Python lançará `FrozenInstanceError`. Isso torna o fluxo de dados previsível.
- **`slots=True`** é uma otimização de memória. Sem `slots`, cada objeto possui um `__dict__` para adicionar atributos dinamicamente. Como não precisamos disso, desativamos esse comportamento e economizamos memória.

Mais importante do que a economia de memória é a intenção comunicada ao leitor: "este objeto representa um valor, não um estado mutável".

## 5. As tabelas de dados como fonte única da verdade

Se você quiser adicionar um novo formato de hash à ferramenta, não precisará escrever lógica nova. Basta adicionar uma linha em uma das tabelas:

```
PREFIX_RULES: lista de (prefixo, algoritmo, descrição)
──────────────────────────────────────────────────────
("$argon2id$", "Argon2id", "string PHC moderna..."),
("$2b$",       "bcrypt",   "string PHC do bcrypt..."),
("$6$",        "SHA-512 crypt", "Unix crypt..."),
... cerca de mais 25 linhas


HEX_LENGTH_RULES: dict {comprimento_hex: [algoritmos]}
─────────────────────────────────────────────────────
32:  ["MD5", "NTLM", "MD4", "RIPEMD-128"],
40:  ["SHA-1", "RIPEMD-160"],
64:  ["SHA-256", "SHA3-256", "BLAKE2s-256", "RIPEMD-256"],
128: ["SHA-512", "SHA3-512", "BLAKE2b-512", "Whirlpool"],
...


HEX_CHARSET, _HEX_UPPER_CHARSET, _DESCRYPT_CHARSET
──────────────────────────────────────────────────
Os alfabetos utilizados por cada formato.
Implementados como frozenset para consultas rápidas.
```

Isso é chamado de **design orientado a dados** (_data-driven design_). As regras vivem em dados, não em código.

As vantagens são claras:

1. **Adicionar um novo formato exige apenas uma linha.** Nenhuma função nova precisa ser escrita.
2. **As regras podem ser inspecionadas facilmente.** Basta ler `PREFIX_RULES` para saber tudo o que a ferramenta reconhece.
3. **As regras podem ser testadas automaticamente.** O arquivo de testes percorre `PREFIX_RULES` e verifica que todos os prefixos são reconhecidos, impedindo que dados e comportamento fiquem inconsistentes.

Ao estudar a implementação, observe como poucas funções utilizam longas cadeias de `if/elif`. A maior parte das decisões acontece por meio de consultas às tabelas, não através de condicionais.

## 6. As funções auxiliares

O cérebro consiste principalmente em `identify()`, mas existem três pequenas funções auxiliares responsáveis por responder perguntas de sim/não sobre a entrada:

```
┌──────────────────────────────────────────────────────────┐
│  _is_hex(text) -> bool                                   │
│    "Todos os caracteres são dígitos hexadecimais?"       │
│    Utilizada na etapa 3.                                 │
├──────────────────────────────────────────────────────────┤
│  _is_mysql5(text) -> bool                                │
│    "O texto possui o formato `*` + 40 hex maiúsculos?"   │
│    Utilizada na etapa 2.                                 │
├──────────────────────────────────────────────────────────┤
│  _is_descrypt(text) -> bool                              │
│    "O texto possui 13 caracteres de `./0-9A-Za-z`?"      │
│    Utilizada na etapa 2.                                 │
└──────────────────────────────────────────────────────────┘
```

O sublinhado inicial (`_is_hex`, e não `is_hex`) segue uma convenção do Python indicando que aquela função é **privada do módulo**. Ela faz parte da implementação interna de `hash_identifier.py` e não deve ser importada por outros módulos.

O Python não impede esse uso, mas linters e revisores normalmente apontam esse tipo de importação como inadequada.

As funções auxiliares são pequenas de propósito. Cada uma responde apenas a uma pergunta booleana. Elas foram extraídas de `identify()` não por serem complexas, mas porque um nome descritivo torna o código muito mais legível.

## 7. A camada CLI

A camada CLI é a parte com a qual o usuário realmente interage. Ela executa três tarefas:

```
┌────────────────────────────────────────────────────────────┐
│ _build_argument_parser()                                   │
│ Configura o argparse: define um argumento posicional       │
│ (`hash`) e uma opção `--top N`.                            │
│                                                            │
│ Foi separado de main() para que os testes possam criar     │
│ o parser sem executar a CLI.                               │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ _render_table(raw_input, candidates, console)              │
│ Constrói uma rich.Table, adiciona uma linha para cada      │
│ candidato, colore a coluna de confiança e imprime          │
│ a tabela.                                                  │
│                                                            │
│ Recebe um objeto Console como parâmetro para que os        │
│ testes possam utilizar uma Console que captura a saída.    │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ main()                                                     │
│ Processa os argumentos, chama identify() e imprime         │
│ a tabela.                                                  │
│                                                            │
│ Retorna um código de saída:                                │
│   0 → pelo menos um candidato encontrado                   │
│   1 → nenhum candidato encontrado                          │
│                                                            │
│ Isso permite escrever scripts como:                        │
│                                                            │
│     if hashid "$x"; then ...                               │
└────────────────────────────────────────────────────────────┘
```

A principal decisão de projeto nessa camada é a **injeção de dependências** (_dependency injection_). `_render_table` recebe um objeto `Console` como parâmetro em vez de criá-lo internamente.

Na prática, isso significa apenas: "use a impressora que eu fornecer". Pode ser um terminal real ou uma Console utilizada pelos testes para capturar a saída. Essa abordagem torna a função facilmente testável.

## 8. O arquivo de testes espelha o cérebro

`test_hash_identifier.py` foi organizado para refletir diretamente a estrutura de `hash_identifier.py`. Cada comportamento prometido pela ferramenta possui um teste correspondente:

```
test_bcrypt_prefix_is_recognized
test_argon2id_prefix_is_recognized
test_apr1_prefix_is_recognized
test_sha512_crypt_prefix_is_recognized
test_django_pbkdf2_prefix_is_recognized

test_mysql5_format_is_recognized
test_mysql5_rejects_lowercase_body
test_netntlmv2_format_is_recognized
test_netntlmv1_format_is_recognized
test_descrypt_format_is_recognized

test_md5_length_returns_md5_first
test_sha1_length_returns_sha1_first
test_sha256_length_returns_sha256_first
test_mysql323_length_returns_mysql323_first

test_unknown_phc_string_falls_back_to_generic

test_jwt_input_is_called_out_as_not_a_hash
test_base64_blob_is_called_out_as_not_a_hash

test_empty_input_returns_no_candidates
test_garbage_returns_no_candidates
test_input_is_trimmed_of_whitespace

test_hash_candidate_is_frozen

test_every_prefix_rule_is_recognized_with_high_confidence
```

O teste mais interessante é o último. Trata-se de um **meta-teste**: ele percorre automaticamente `PREFIX_RULES` e verifica que cada linha gera uma identificação com HIGH confidence.

Assim, se alguém adicionar um novo prefixo e esquecer de atualizar a lógica de identificação, esse teste falhará imediatamente. Os testes crescem automaticamente junto com a tabela de dados.

## 9. Por que funções puras importam

O cérebro (`identify()`) é uma **função pura**:

- Recebendo a mesma entrada, sempre produz a mesma saída.
- Não modifica nada fora dela (nenhum arquivo, variável global ou conexão de rede).
- Não depende de nada externo (horário atual, variáveis de ambiente ou números aleatórios).

Isso possui consequências importantes:

- **É extremamente fácil de testar.** Basta executar `assert identify(...) == ...`.
- **É trivialmente paralelizável.** Milhões de hashes podem ser processados simultaneamente sem qualquer coordenação.
- **É trivialmente cacheável.** Mesma entrada → mesma saída.
- **É fácil de compreender.** Você pode entender `identify()` isoladamente, sem conhecer o restante do programa.

A maioria dos programas reais não consegue ser totalmente pura, pois precisa ler arquivos, enviar pacotes de rede e acessar bancos de dados. Porém, quase sempre é possível isolar um núcleo puro e construir uma pequena camada externa responsável pelos efeitos colaterais.

Essa arquitetura é conhecida como **Functional Core, Imperative Shell** e vale a pena aprender esse nome. Depois de reconhecê-la uma vez, você começará a percebê-la em muitos outros projetos.

## 10. Próximo passo

Agora você já conhece a estrutura geral: três camadas, seis etapas, três tabelas de dados, três funções auxiliares, um registro `HashCandidate` e uma camada CLI. O próximo material é **[03-Implementação.md](./03-Implementação.md)**, onde percorreremos `hash_identifier.py` linha por linha.
