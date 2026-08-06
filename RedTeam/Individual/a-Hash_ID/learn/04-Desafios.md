# Desafios

Você já leu o código. Já sabe o que cada linha faz. Agora, a única forma de tornar esse conhecimento realmente seu é _alterar_ o código. Esta página é uma escada de extensões, da mais fácil à mais difícil. Não pule degraus — cada um ensina algo que o próximo pressupõe.

Para cada desafio: **escreva o teste primeiro**. Depois faça o teste passar. Esse é o ritmo que desenvolvedores profissionais realmente usam. O arquivo de testes já mostra o padrão — copie uma das funções `test_*` existentes, mude a entrada e a saída esperada, veja o teste falhar e então ajuste o código até ele passar.

## Nível 1 — ficar confortável

### Desafio 1.1: Adicione uma nova regra de prefixo

`PREFIX_RULES` tem cerca de 25 entradas hoje. Existem dezenas a mais. Escolha uma da lista abaixo e adicione-a:

| Prefixo      | Algoritmo                 | Origem                                    |
| ------------ | ------------------------- | ----------------------------------------- |
| `$pbkdf2$`   | PBKDF2-SHA1 (Atlassian)   | Hashes antigos do Atlassian / Jira        |
| `$ml$`       | macOS / iCloud Keychain   | Apple PBKDF2-SHA512                       |
| `{x-pbkdf2}` | PBKDF2 (alguns Atlassian) | Invólucro no estilo LDAP                  |
| `$sha1$`     | sha1crypt                 | Uma variante rara de crypt(3)             |
| `$md5,`      | Solaris MD5 crypt         | Observe a vírgula em vez de `$` — cuidado |

**Passos:**

1. Abra `hash_identifier.py`. Adicione uma linha em `PREFIX_RULES`.
2. Abra `test_hash_identifier.py`. Copie um teste de prefixo existente (por exemplo, `test_argon2id_prefix_is_recognized`). Renomeie-o. Substitua a string de entrada por um exemplo do novo prefixo. Atualize a asserção.
3. Execute `just test`. O novo teste deve passar. O meta-teste `test_every_prefix_rule_is_recognized_with_high_confidence` também deve continuar passando.
4. Execute a ferramenta com a nova entrada: `just run -- '$pbkdf2$...'`. Confirme que o novo algoritmo aparece.

**O que você aprende:** o design orientado a tabela vale a pena — você escreveu zero lógica nova, apenas dados. Esse é o objetivo.

### Desafio 1.2: Adicione um comprimento a `HEX_LENGTH_RULES`

Ainda não existe regra para 24 caracteres hexadecimais (96 bits). Esse comprimento é raro, mas `Tiger-128` e alguns hashes personalizados antigos produzem isso.

1. Adicione `24: ["Tiger-128"]` a `HEX_LENGTH_RULES`.
2. Escreva um teste (`test_tiger128_length_returns_tiger128`).
3. Execute `just test`.

**Variação:** o que deve acontecer se alguém passar uma string de 24 caracteres que _não_ seja hexadecimal? A verificação existente `_is_hex` deve resolver isso. Leia a etapa 3 de `identify()` e confirme.

### Desafio 1.3: Adicione um modo de saída `--json`

Atualmente a CLI só imprime uma tabela colorida. Adicione uma flag `--json` que, em vez disso, imprima os candidatos em JSON. JSON é o que qualquer outra ferramenta vai querer consumir — sua saída passa a ser legível por máquina.

**Dicas:**

- `argparse` suporta flags booleanas com `action="store_true"`. Adicione `parser.add_argument("--json", action="store_true", help="...")`.
- O módulo padrão `json` possui `json.dumps(data)`.
- `HashCandidate` é uma dataclass, então `dataclasses.asdict(candidate)` a converte em um dicionário comum que `json.dumps` consegue serializar.
- Teste: `just run -- --json 5f4d...` deve produzir um array JSON.

**Variação:** faça o JSON incluir um campo de nível superior `input` com a string original, para que uma ferramenta subsequente saiba o que foi identificado. E use `indent=2` para formatar melhor.

## Nível 2 — comportamento realmente novo

### Desafio 2.1: Leia hashes de um arquivo ou do stdin

Hoje a ferramenta aceita um hash por execução. Fluxos reais têm arquivos com milhões de hashes. Estenda a CLI para aceitar entrada de um arquivo (`--file hashes.txt`) ou do stdin quando nenhum argumento posicional for fornecido (assim `cat hashes.txt | hashid` funciona).

**Dicas:**

- Torne o argumento posicional `hash` opcional com `nargs="?"`.
- Adicione `--file` com `type=argparse.FileType("r")`.
- Use `sys.stdin.read()` (ou itere sobre `sys.stdin` linha por linha) quando ambos estiverem ausentes.
- A saída para entrada em lote deve ser diferente — provavelmente uma linha por entrada, não uma tabela colorida para cada uma. Decida um formato que faça sentido e documente-o.

**Variação:** o que deve acontecer se a mesma entrada aparecer 1000 vezes no arquivo? Você deve executar `identify()` a cada vez, ou armazenar resultados em cache? Teste os dois e meça com `just run` em um arquivo com 1 milhão de hashes repetidos. (Lição maior: cache só ajuda quando a função é pura. A nossa é.)

### Desafio 2.2: Adicione dicas de `hashcat` mode

O hashcat atribui um modo numérico para cada algoritmo: 0 para MD5, 100 para SHA-1, 3200 para bcrypt etc. A lista completa está documentada em [hashcat.net/wiki/doku.php?id=example_hashes](https://hashcat.net/wiki/doku.php?id=example_hashes).

Estenda `HashCandidate` com um campo opcional `hashcat_mode: int | None`. Ao criar um candidato, consulte seu modo (você precisará de um mapeamento `dict[str, int]` de nome do algoritmo → modo) e preencha esse campo.

Depois imprima o modo na tabela e atualize a sugestão de "próximo passo" no final de `main()` para indicar o comando exato do hashcat:

```
Próximo passo: hashcat -m 3200 -a 0 '$2b$12$EixZ...' wordlist.txt
```

**Dicas:**

- Campos opcionais em uma dataclass precisam de valores padrão: `hashcat_mode: int | None = None`.
- A consulta do modo é outra tabela de dados — mantenha o design orientado a dados.
- John the Ripper usa nomes diferentes (por exemplo, `bcrypt`, `raw-md5`). Adicione esses também se quiser ir além.

### Desafio 2.3: Reconheça mais entradas que "não são hashes"

A etapa 5 atualmente só detecta JWTs e blobs base64. Muitas outras coisas são coladas em identificadores de hash por engano. Adicione detectores para:

- **URLs** — começam com `http://` ou `https://`. Diga ao usuário que é uma URL.
- **Hex com prefixo `0x`** — endereços Ethereum, endereços de memória. Informe isso ao usuário.
- **Base58** — usado por endereços Bitcoin e hashes IPFS. O alfabeto é `123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz` (sem `0`, `O`, `I`, `l`).
- **Base32** — letras maiúsculas + dígitos 2-7. Usado em alguns endereços onion do Tor e segredos TOTP.

Cada um é um novo ramo na etapa 5, retornando um candidato "não é um hash" com confiança LOW. Seja honesto com a confiança — essas são pistas de _forma_, não certezas.

## Nível 3 — estenda o modelo

### Desafio 3.1: Detectar múltiplos hashes em uma única string

Alguns dumps de vazamento contêm registros _combinados_ como `user:hash:salt`. Fluxos reais frequentemente precisam separar esses registros em partes constituintes antes de identificar. Adicione um modo `--split` que:

1. Receba uma string com campos separados por dois-pontos.
2. Identifique cada campo independentemente.
3. Imprima uma tabela mostrando o que cada campo é (nome de usuário, hash, salt, lixo).

**Dicas:**

- Isso é principalmente heurística. Um campo composto só por letras provavelmente é um nome de usuário; um campo que corresponde a uma regra de hash provavelmente é o hash; um campo curto e aleatório pode ser um salt.
- Extraia a lógica de classificação de campos para fora de `identify()` — isso é uma nova camada acima dela.
- Teste com linhas realistas como `alice:$2b$12$EixZ...`, `bob:5f4dcc3b5aa765d61d8327deb882cf99:salt123`.

### Desafio 3.2: Rebalanceamento da confiança com pesos de evidência

Atualmente `confidence` é um único valor: high, medium ou low. Mas a evidência é mais nuançada. Uma string hex de 32 caracteres que _também_ não contém caracteres acima de `'f'` é "muito provavelmente hex". Uma string de 13 caracteres do conjunto DES é "compatível com DES crypt de 13 caracteres", mas os mesmos caracteres podem aparecer em muitas strings curtas.

Substitua `confidence: Literal["high", "medium", "low"]` por `confidence_score: float` no intervalo de 0.0–1.0. Calcule a pontuação a partir de múltiplos pesos de evidência:

- correspondência de prefixo: 0.95
- correspondência de formato especial: 0.85
- correspondência de comprimento (1º candidato): 0.55
- correspondência de comprimento (N-ésimo candidato): 0.55 / N
- correspondência de charset: pequeno bônus aditivo
- pista de não é hash: 0.30

Depois, na CLI, mapeie a pontuação de volta para uma cor (>0.8 verde, 0.5–0.8 amarela, <0.5 ciano) para exibição. O usuário ainda vê três faixas; o modelo interno fica mais rico.

**O que você aprende:** como sistemas de pontuação funcionam internamente. Essa é a mesma ideia por trás de classificadores bayesianos de spam, ranking de relevância em busca e heurísticas de antivírus — combinar vários sinais fracos em uma única pontuação numérica e depois agrupá-la para exibição.

### Desafio 3.3: Sugira a _dificuldade de quebra_ junto com o algoritmo

Depois que você sabe o algoritmo, você também sabe, implicitamente, o quão difícil ele é de quebrar. MD5 é quebrado a bilhões de tentativas por segundo em uma GPU moderna; bcrypt, a milhares. Argon2id com parâmetros fortes pode ficar na casa das centenas.

Adicione um campo `crack_difficulty: Literal["trivial", "moderate", "hard", "very_hard"]` a `HashCandidate`, preenchido a partir de uma tabela por algoritmo. Imprima-o na tabela de saída.

**Variação:** para hashes parametrizados (cost factor do bcrypt, memória/tempo do Argon2), interprete os parâmetros da string PHC. Um bcrypt com cost factor 4 é muito mais fraco que um com cost factor 14. Faça sua saída refletir isso:

```
algoritmo  dificuldade  motivo
─────────  ──────────  ──────────────────────────────────────────
bcrypt     moderate    cost=4 — muito mais fraco que o padrão 12
bcrypt     hard        cost=12 — o padrão moderno
bcrypt     very_hard   cost=14 — configuração paranoica
```

## Nível 4 — tornar isso real

### Desafio 4.1: Execute a identificação em um dump real de vazamento

O arquivo de senhas do [HaveIBeenPwned](https://haveibeenpwned.com/Passwords) é uma lista distribuída publicamente de cerca de 1 bilhão de hashes SHA-1 de senhas vazadas, disponível via torrent. (Use a versão **SHA-1**, não a versão NTLM — e use-a apenas para análise educacional; não tente "quebrá-la" para qualquer propósito malicioso. Os próprios hashes são públicos.)

Execute sua ferramenta nas primeiras 1000 linhas. Confirme que ela identifica todas como SHA-1 (40 caracteres hexadecimais). Meça a vazão: quantos hashes por segundo sua ferramenta consegue processar? Qual é o gargalo?

**Lição maior:** o cérebro leva microssegundos; o gargalo é a impressão da CLI. Para processar milhões de hashes, você não usaria `rich` — você emitiria JSON em streaming para o stdout. Isso já é outro programa, para outro caso de uso.

### Desafio 4.2: Compare com `hashid` e `name-that-hash`

Duas ferramentas existentes fazem aproximadamente o que a nossa faz:

- [hashid](https://github.com/psypanda/hashID) — o clássico, com cerca de 10 anos, escrito em Python puro.
- [name-that-hash](https://github.com/HashPals/Name-That-Hash) — mais novo, mais completo e mais agressivo ao adivinhar.

Execute as três sobre as mesmas entradas. Compare:

- Qual detecta mais formatos?
- Qual tem melhor taxa de falso positivo (diz "definitivamente SHA-256" quando a entrada é lixo)?
- Qual é mais rápido em entrada em lote?

Escreva suas conclusões. Esse é exatamente o tipo de trabalho que pesquisadores de segurança fazem ao escolher uma ferramenta para uso em produção.

### Desafio 4.3: Envolva a ferramenta em um hook de `pre-commit`

`pre-commit` é uma ferramenta que executa verificações antes de você fazer `git commit`. Às vezes pessoas acidentalmente comitam hashes de senha em repositórios (isso é gravíssimo). Construa um hook de `pre-commit` que rode seu identificador em cada arquivo alterado e recuse o commit se encontrar algo que pareça um hash real.

**Dicas:**

- Leia o tutorial de hooks do [pre-commit](https://pre-commit.com/#new-hooks).
- Para cada linha de cada arquivo alterado, execute `identify(line)`. Se o candidato no topo for HIGH confidence e não for generic-PHC ou não é hash, recuse.
- Código de saída 1 = bloquear o commit; código 0 = permitir.
- Adicione comentários de allowlist como `# pragma: allow-hash` para que fixtures legítimos de teste não sejam bloqueadas.

Esse é o tipo de projeto "ferramenta pequena, impacto real" que acaba entrando em toolchains de times de segurança de verdade.

## Nível 5 — quebrar o modelo

### Desafio 5.1: Por que isso é um problema difícil?

Até agora, o que foi feito é correspondência por _estrutura_: prefixo, comprimento, charset. Mas o modelo tem limites. Considere:

- Dois algoritmos diferentes produzindo a mesma saída de tamanho (MD5 vs NTLM com 32 caracteres hexadecimais). Não é possível distingui-los apenas pela estrutura.
- Um algoritmo cuja saída às vezes vem em maiúsculas e às vezes em minúsculas (bibliotecas diferentes produzem casos diferentes para o mesmo algoritmo).
- Um SHA-256 truncado — alguém pegou os primeiros 32 caracteres hexadecimais de uma saída SHA-256 e chamou aquilo de "hash". Nós o identificaríamos como MD5.

Escreva um documento curto (`docs/limitations.md`) listando todos os casos em que a ferramenta _não consegue_ distinguir dois formatos e explique o motivo. Essa é a forma honesta como boas ferramentas de segurança documentam seus limites desde o início. Não finja que a ferramenta é mais capaz do que realmente é.

### Desafio 5.2: Identificação probabilística com um classificador de ML

A abordagem estrutural é interpretável, mas limitada. O extremo oposto é treinar um classificador com hashes rotulados e deixá-lo aprender a estrutura sozinho.

Monte um pequeno experimento:

1. Gere 100 mil amostras de treinamento rotuladas: senhas conhecidas hasheadas com cada algoritmo. (Use `hashlib`, `bcrypt`, `argon2-cffi` etc.)
2. Treine um classificador simples — `sklearn.linear_model.LogisticRegression` com features de n-gramas de caracteres funciona bem para isso.
3. Rode o classificador em amostras de teste separadas. Meça a acurácia.
4. Compare com o identificador baseado em regras usando o mesmo conjunto de teste.

**O que você vai aprender:** o sistema baseado em regras provavelmente vence nos formatos comuns (ele já possui todas as prioridades estruturais embutidas) e o modelo de ML provavelmente vence em casos incomuns (ele aprende padrões que você não pensou em codificar). Ferramentas do mundo real combinam os dois — regras primeiro, ML para desempate. É assim que classificadores de spam, firewalls de aplicação web e motores de antivírus realmente funcionam.

> **Não execute nenhum desses desafios com dados reais de usuários sem permissão.** Os desafios assumem arquivos de vazamentos publicamente divulgados, seus próprios dados de teste ou entradas de CTF. Identificar hashes a partir de dados que você não tem direito de usar é outra conversa e está fora do escopo deste projeto.

&nbsp;

## Fim

<p align="center">
  <img src="../assets/cat.gif" width="300" alt="Cat">
</p>

Agora você chegou ao final de seu projeto. Se conseguiu realizar os níveis 4 e 5, saiba que estará pronto para o que virá em seguida. **Parabéns!**

Minha recomendação agora é que você treine bem python e, se possível, _se arrisque em mais um projeto disponível_. Aliás, esse é o ponto mais forte de qualquer currículo ao lado das experiências: **os projetos**. Então, sem medo, quanto mais fizer, melhor.
