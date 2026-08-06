# Conceitos

Esta página desenvolve os conceitos necessários para entender o código. Começaremos pela pergunta "o que é um hash?" e terminaremos em "por que exatamente uma string hexadecimal de 32 caracteres provavelmente é um MD5". Nenhum conhecimento prévio em segurança é necessário.

## 1. O que é um hash?

Uma **função hash criptográfica** recebe qualquer entrada — um único byte, uma senha, um arquivo de vídeo de 4 GB — e produz uma saída de tamanho fixo que parece um monte de caracteres aleatórios. A mesma entrada sempre gera a mesma saída. Entradas diferentes geram saídas diferentes. E, mais importante: se você possui apenas a saída, não consegue voltar à entrada original.

Imagine-a como um liquidificador de cozinha que só funciona em um sentido:

```
"password"  ─────► [ liquidificador MD5 ] ─────►  5f4dcc3b5aa765d61d8327deb882cf99
"hello"     ─────► [ liquidificador MD5 ] ─────►  5d41402abc4b2a76b9719d911017c592
"hello!"    ─────► [ liquidificador MD5 ] ─────►  d9014c4624844aa5bac314773d6b689a
                              │
                              └─ altere UM caractere → saída completamente diferente
```

Algumas propriedades que decorrem disso:

- **Determinística.** A mesma entrada produz a mesma saída, todas as vezes. Esse é o principal motivo pelo qual hashes são úteis — você pode armazenar o hash de uma senha e, quando alguém fizer login, basta calcular novamente o hash do que foi digitado e comparar.
- **Saída de tamanho fixo.** Não importa se você gera o hash de `"a"` ou da Bíblia inteira: o MD5 sempre produz 32 caracteres hexadecimais. O SHA-256 sempre produz 64. Esse comprimento é a primeira grande pista utilizada para identificar qual algoritmo foi usado.
- **Mão única.** Você consegue ir de senha → hash, mas não de hash → senha. Não existe um botão de "desfazer hash". A única forma de descobrir qual senha gerou determinado hash é _adivinhar senhas e calcular seus hashes_ até encontrar uma correspondência. É exatamente isso que o hashcat faz.
- **Efeito avalanche.** Altere apenas uma letra da entrada e toda a saída muda. `"password"` e `"Password"` produzem hashes que não compartilham nenhum caractere.

Se quiser experimentar isso por conta própria, em um REPL do Python (`uv run python`):

```python
>>> import hashlib
>>> hashlib.md5(b"password").hexdigest()
'5f4dcc3b5aa765d61d8327deb882cf99'
>>> hashlib.md5(b"Password").hexdigest()
'dc647eb65e6711e155375218212b3964'
```

A sintaxe `b"..."` significa "isto são bytes, não texto" — funções hash trabalham sobre bytes brutos, não sobre caracteres. Não se preocupe com essa distinção por enquanto; apenas observe que alterar uma única letra produziu um hash completamente diferente.

## 2. Por que hashes existem (o problema do armazenamento de senhas)

Imagine que você administra um site. Os usuários criam contas com uma senha. A abordagem mais ingênua seria armazenar as senhas diretamente no banco de dados:

```
+----------+------------+
| username | password   |
+----------+------------+
| alice    | hunter2    |
| bob      | letmein    |
+----------+------------+
```

Isso é uma catástrofe esperando para acontecer. No momento em que alguém invade seu banco de dados — e, cedo ou tarde, isso acontece — todas as senhas dos usuários ficam expostas. Pior ainda: como muitas pessoas [reutilizam senhas em vários sites](https://www.security.org/digital-safety/password-reuse-statistics/), o invasor agora possui acesso potencial ao banco da Alice, ao e-mail da Alice e à conta da Alice na Netflix.

A solução é nunca armazenar a senha em si. Armazene apenas seu hash:

```
+----------+----------------------------------+
| username | password_hash                    |
+----------+----------------------------------+
| alice    | 5f4dcc3b5aa765d61d8327deb882cf99 |  ← MD5("hunter2")... se fosse
| bob      | 0d107d09f5bbe40cade3de5c71e9e9b7 |     "password" (não é)
+----------+----------------------------------+
```

Quando Alice faz login, você calcula o hash da senha que ela acabou de digitar e compara com o hash armazenado. Se forem iguais, ela entra. Você nunca soube qual era a senha dela e nunca precisou saber.

Quem rouba esse banco de dados agora possui hashes, não senhas. Será necessário _adivinhar_ cada senha, calcular seu hash e comparar. Com um hash rápido como MD5, uma GPU moderna consegue testar bilhões de tentativas por segundo. Com um hash lento como bcrypt, apenas milhares. Esse é todo o motivo pelo qual sistemas modernos utilizam hashes lentos — não porque sejam "mais seguros" em um sentido abstrato, mas porque tornam o processo de adivinhação _caro_.

## 3. Violações reais em que a identificação do hash foi essencial

Identificar o formato do hash é o _primeiro passo_ em qualquer incidente de vazamento de senhas. Até saber qual algoritmo gerou os hashes, nada mais pode ser feito.

**[Vazamento do LinkedIn em 2012](https://en.wikipedia.org/wiki/2012_LinkedIn_hack)** — 6,5 milhões de hashes SHA-1 sem salt foram vazados. Cada um possuía quarenta caracteres hexadecimais. Pesquisadores identificaram o formato em segundos e quebraram 90% dos hashes em 72 horas porque o SHA-1 é rápido e as senhas não possuíam salt (falaremos sobre salt mais adiante). Mais tarde, o LinkedIn admitiu que [117 milhões de contas adicionais](https://www.theguardian.com/technology/2016/may/19/linkedin-2012-data-breach-hack-117-million-email-password-details) haviam sido expostas além do inicialmente divulgado.

**[Vazamento da Adobe em 2013](https://krebsonsecurity.com/2013/11/adobe-breach-impacted-at-least-38-million-users/)** — 153 milhões de contas, com senhas armazenadas usando criptografia 3DES (nem sequer hashing) e sem salts únicos. A ausência de salts exclusivos fez com que senhas iguais gerassem exatamente o mesmo texto cifrado. Apenas olhando para o dump, pesquisadores conseguiram identificar que 1,9 milhão de contas compartilhavam a senha `123456`.

**[Vazamento do Yahoo em 2016](https://en.wikipedia.org/wiki/Yahoo!_data_breaches)** — 3 bilhões de contas. Algumas utilizavam MD5 (catastrófico), outras bcrypt (muito melhor). A coexistência de formatos diferentes tornou a identificação a primeira tarefa antes de qualquer análise de segurança.

**[Collection #1 (2019)](https://www.troyhunt.com/the-773-million-record-collection-1-data-reach/)** — 773 milhões de pares de e-mail/senha reunidos de vazamentos anteriores. Pesquisadores precisaram separar quais hashes pertenciam a quais algoritmos antes de qualquer outra etapa.

O padrão é sempre o mesmo: surge o dump → identifica-se o algoritmo → decide-se se a quebra é viável → utiliza-se o hashcat.

## 4. Os três sinais que um hash revela sobre si mesmo

Este é o núcleo da ferramenta. Uma string de hash carrega até três pistas sobre sua origem: seu **prefixo**, seu **comprimento** e seu **conjunto de caracteres**. Utilizamos essas pistas nessa ordem, da mais forte para a mais fraca.

### Sinal 1: prefixo (a pista mais forte)

Hashes modernos para senhas utilizam um formato autoexplicativo chamado **PHC string format** (PHC significa "Password Hashing Competition", a competição que originou o Argon2 em 2015). Uma string PHC começa com um marcador que informa explicitamente qual algoritmo foi utilizado:

```
$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$RdescudvJCsgt3ub+b+dWRWJTmaaJObG
^^^^^^^^^^
 │
 └─ "Sou um hash Argon2id. Você não precisa adivinhar."
```

```
$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQNQy.uK4Of2T7G.VHvgvWK
^^^^
 │
 └─ "Sou um hash bcrypt, variante 2b, fator de custo 12."
```

Quando um hash se identifica dessa forma, descobri-lo é praticamente gratuito — basta comparar o prefixo. A ferramenta informa **HIGH confidence** para correspondências por prefixo, porque o próprio hash diz o que é. A especificação completa do PHC pode ser encontrada [aqui](https://github.com/P-H-C/phc-string-format/blob/master/phc-sf-spec.md).

Hashes antigos _não_ fazem isso. MD5 e SHA-1 simplesmente retornam o digest hexadecimal puro, sem qualquer prefixo. É justamente por isso que a adoção do formato PHC foi tão importante: ele torna o sistema autoexplicativo.

Segue uma tabela resumida com alguns prefixos comuns. A tabela completa está em `hash_identifier.py`, na estrutura `PREFIX_RULES`:

| Prefixo          | Algoritmo         | Onde costuma aparecer                                |
| ---------------- | ----------------- | ---------------------------------------------------- |
| `$argon2id$`     | Argon2id          | Aplicações web modernas, padrão ouro atual           |
| `$2b$`           | bcrypt            | Principal algoritmo utilizado nos últimos 15 anos    |
| `$6$`            | SHA-512 crypt     | `/etc/shadow` na maioria das distribuições Linux     |
| `$apr1$`         | Apache MD5-crypt  | Arquivos `.htpasswd` (autenticação básica do Apache) |
| `$P$`            | phpass            | WordPress e fóruns phpBB antigos                     |
| `pbkdf2_sha256$` | Django PBKDF2     | Padrão das aplicações web em Django                  |
| `{SSHA}`         | LDAP salted SHA-1 | Senhas de diretórios LDAP                            |

### Sinal 2: comprimento (a segunda pista mais forte)

Funções hash produzem saídas de tamanho fixo. Se você não vê nenhum prefixo, mas possui 64 caracteres hexadecimais, pode ter bastante confiança de que o hash pertence à família dos algoritmos de 256 bits (SHA-256, SHA3-256, BLAKE2s-256, RIPEMD-256). Cada algoritmo sempre gera o mesmo número de bytes:

```
algoritmo       bytes      caracteres hex
─────────────────────────────────────────
MD5               16              32
SHA-1             20              40
SHA-224           28              56
SHA-256           32              64
SHA-384           48              96
SHA-512           64             128
```

O motivo pelo qual o número de caracteres hexadecimais é o dobro do número de bytes é simples: cada byte possui 8 bits, enquanto cada caractere hexadecimal representa apenas 4 bits (um entre 16 valores possíveis: `0-9a-f`). Portanto, cada byte precisa de dois caracteres hexadecimais.

O comprimento reduz bastante o conjunto de possibilidades, mas raramente determina um único algoritmo. Trinta e dois caracteres hexadecimais podem representar MD5, NTLM, MD4 ou RIPEMD-128 — todos produzem 128 bits de saída. Por isso, quando a ferramenta identifica apenas pelo comprimento, ela informa **MEDIUM confidence** para o algoritmo mais provável e **LOW** para os demais. "Mais provável" significa "mais comum na prática em 2026" — MD5 é muito mais frequente do que RIPEMD-128.

### Sinal 3: conjunto de caracteres (utilizado como verificação)

O conjunto de caracteres utilizado pelo hash ajuda a restringir ainda mais as possibilidades. Três alfabetos aparecem com frequência:

- **Hexadecimal:** apenas `0-9a-f` (ou `0-9A-F` quando em maiúsculas). Utilizado por MD5 puro, família SHA, NTLM etc.
- **Semelhante a Base64:** `0-9A-Za-z+/=`. Utilizado por LDAP e alguns formatos de senha do ecossistema Java.
- **Base64 do crypt(3):** um alfabeto peculiar `./0-9A-Za-z` (observe que começa com `.` e `/` e não utiliza `=` como preenchimento). Utilizado por bcrypt e pelos antigos formatos Unix crypt.

Uma string contendo `+` _não_ pode ser um hash hexadecimal. Uma string iniciada por `*` seguida de 40 caracteres hexadecimais em maiúsculas é quase certamente um hash MySQL5 (e apenas MySQL5 — porque o MySQL imprime seus hashes usando o especificador `%02X` da linguagem C, que gera apenas letras maiúsculas).

O conjunto de caracteres raramente identifica sozinho um algoritmo, mas serve como critério de desempate para _eliminar possibilidades_. Por exemplo, a função auxiliar `_is_mysql5` no código rejeita qualquer entrada cujo corpo esteja em letras minúsculas, porque a saída real do MySQL5 é sempre em maiúsculas. É melhor responder "não sei" do que afirmar algo incorreto com confiança.

## 5. Salts (um pequeno desvio)

Você encontrará a palavra **salt** com frequência ao estudar armazenamento de senhas. Um salt é uma sequência aleatória única adicionada à senha antes de calcular seu hash, sendo armazenada junto com o próprio hash:

```
hash = bcrypt("hunter2" + random_salt_for_alice)
```

O objetivo do salt é fazer com que cada usuário possua um hash _diferente_, mesmo quando dois usuários escolhem exatamente a mesma senha. Sem salts, basta ordenar o banco de dados pela coluna de hashes, contar repetições e descobrir imediatamente qual é a senha mais popular (foi exatamente assim que pesquisadores descobriram que `123456` era a senha mais comum entre os usuários da Adobe — sem precisar quebrar nenhum hash).

Salts também impedem o uso de **rainbow tables**: tabelas pré-computadas que mapeiam `hash → senha` para bilhões de senhas comuns. Quando cada usuário possui um salt diferente, seria necessário recomputar toda a rainbow table para _cada salt_, tornando essa abordagem inviável.

Uma string PHC como `$2b$12$EixZaYVK1fsbw1ZfbX3OXe...` já contém o salt embutido (a parte `EixZaYVK1fsbw1ZfbX3OXe`). Isso não representa um problema de segurança — o salt foi projetado para ser público. Sua função é tornar cada hash único, não permanecer secreto.

## 6. Por que a identificação precisa vir primeiro

Ferramentas de quebra de senhas não detectam automaticamente o algoritmo — elas dependem de você para informá-lo.

```bash
# Hashcat, modo 0 (MD5):
hashcat -m 0 -a 0 5f4dcc3b5aa765d61d8327deb882cf99 wordlist.txt

# Hashcat, modo 3200 (bcrypt):
hashcat -m 3200 -a 0 '$2b$12$EixZaY...' wordlist.txt

# John the Ripper, --format=raw-md5:
john --format=raw-md5 --wordlist=wordlist.txt hashes.txt
```

Escolha o modo errado e o hashcat ficará comparando um hash bcrypt contra saídas MD5 indefinidamente, sem encontrar nenhuma correspondência. Portanto, _antes_ de quebrar um hash, você precisa identificá-lo.

É por isso que existem ferramentas como esta (e projetos mais antigos como [`hashid`](https://github.com/psypanda/hashID) e [`hash-identifier`](https://github.com/blackploit/hash-identifier), nos quais ela se inspira). Ela representa o primeiro passo. Nossa ferramenta é uma versão voltada para iniciantes dessa ideia, escrita para que você consiga ler cada linha e compreender cada decisão.

## 7. O compromisso assumido por esta ferramenta

Poderíamos obter uma precisão maior tentando todos os algoritmos possíveis e executando verificações adicionais. Não fazemos isso. Todas as decisões são tomadas apenas com base no _formato da string_:

- Nunca executamos qualquer função hash.
- Nunca realizamos requisições de rede.
- Nunca acessamos o sistema de arquivos.
- Nunca chamamos ferramentas externas.

Isso torna a ferramenta **rápida** (resposta instantânea), **segura** (impossível vazar dados) e **extremamente fácil de testar** (cada teste consiste em "dada a entrada X, espera-se a saída Y"). Trata-se de uma função pura, no sentido matemático — a mesma entrada sempre gera a mesma saída, sem efeitos colaterais.

O custo dessa abordagem é que, às vezes, relatamos múltiplos candidatos com níveis de confiança MEDIUM/LOW. Em teoria, poderíamos escolher um vencedor testando cada algoritmo contra uma wordlist conhecida — mas isso seria outra ferramenta. Essa outra ferramenta é o hash_cracker. O único objetivo desta ferramenta é indicar _qual modo do cracker_ você deve utilizar.

## 8. O que a ferramenta faz e o que ela não faz

| Faz                                                          | Não faz                                      |
| ------------------------------------------------------------ | -------------------------------------------- |
| Identifica aproximadamente 30 formatos de hash por prefixo   | Quebra qualquer hash                         |
| Identifica hashes hexadecimais comuns pelo comprimento       | Calcula hashes para você                     |
| Reconhece MySQL5, NetNTLM e DES crypt pelo formato           | Executa hashcat ou John the Ripper para você |
| Informa "isto é um JWT" ou "isto é Base64, não um hash"      | Descobre a senha                             |
| Exibe candidatos classificados por confiança e justificativa | Faz requisições de rede                      |
| Executa como uma ferramenta CLI instantânea                  | Acessa o sistema de arquivos                 |

## 9. Para onde ir agora

Agora que você entende _o que_ esta ferramenta faz e _por que_ ela existe, leia **[02-Arquitetura.md](./02-Arquitetura.md)** para ver como o código está organizado em um pipeline de decisão de seis etapas. Em seguida, **[03-Implementação.md](./03-Implementação.md)** percorre o arquivo Python real juntamente com você, função por função.
