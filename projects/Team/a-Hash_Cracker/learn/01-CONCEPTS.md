# Conceitos de Segurança Fundamentais

Este documento explica os conceitos de segurança por trás da quebra de hash. Estes não são apenas definições. Vamos nos aprofundar em como os ataques realmente funcionam, por que certas defesas existem e o que as violações reais nos ensinam sobre o armazenamento de senhas.

## Funções de Hash Criptográfico

### O Que São

Uma função de hash recebe uma entrada de qualquer comprimento e produz uma saída de comprimento fixo (o digest). A mesma entrada sempre produz a mesma saída, mas você não pode trabalhar de trás para frente a partir da saída para recuperar a entrada. Esta é uma transformação unidirecional, não criptografia.

```
"password"  → SHA256 → 5e884898da28047151d0e56f8dc...  (sempre isso, todas as vezes)
"password1" → SHA256 → 0b14d501a594442a01c6859541bc...  (completamente diferente)
"Password"  → SHA256 → 22ee405817c14cbf9d3c2b92b87c...  (completamente diferente de novo)
```

Três propriedades tornam as funções de hash úteis para o armazenamento de senhas:

1. **Determinística**: Mesma entrada, mesma saída. O servidor pode verificar sua senha fazendo o hash do que você digita e comparando com o hash armazenado.
2. **Resistente à pré-imagem**: Dado um hash, você não pode computar a entrada que o produziu. Mesmo que um atacante roube o banco de dados de hashes, ele não terá as senhas em texto simples.
3. **Efeito avalanche**: Alterar um bit da entrada altera aproximadamente metade dos bits da saída. "password" e "Password" produzem hashes completamente não relacionados.

### Algoritmos que Esta Ferramenta Suporta

| Algoritmo | Comprimento do Digest         | Status              | Uso no Mundo Real                                            |
| --------- | ----------------------------- | ------------------- | ------------------------------------------------------------ |
| MD5       | 128 bits (32 caracteres hex)  | Quebrado desde 2004 | Ainda encontrado em sistemas legados, WordPress antes da 4.x |
| SHA1      | 160 bits (40 caracteres hex)  | Quebrado desde 2017 | Invasão do LinkedIn (2012), Git (em transição)               |
| SHA256    | 256 bits (64 caracteres hex)  | Seguro              | Bitcoin, certificados TLS, muitos frameworks web             |
| SHA512    | 512 bits (128 caracteres hex) | Seguro              | Padrão do /etc/shadow no Linux, alguns sistemas corporativos |

"Quebrado" para MD5 e SHA1 significa que pesquisadores podem gerar colisões (duas entradas diferentes produzindo o mesmo hash). Para a quebra de senhas, o problema maior é a velocidade: eles foram projetados para serem rápidos, o que é exatamente o que você não quer para o hashing de senhas.

### O Que Funções de Hash NÃO São

Funções de hash não são criptografia. A criptografia é reversível com uma chave. O hashing não é reversível de forma alguma. Você não "descriptografa" um hash. Você adivinha as entradas, faz o hash delas e verifica se a saída coincide. Isso é quebrar (cracking).

## Dictionary Attacks (Ataques de Dicionário)

### Como Funcionam

Um ataque de dicionário tenta cada palavra de uma lista de senhas conhecidas. O atacante faz o hash de cada palavra e o compara com o hash alvo:

```
Alvo: 5e884898da28047151d0e56f8dc6292773603d0d...

Hash("123456")   → "e10adc..."  ≠ alvo
Hash("password") → "5e8848..."  = alvo  ← encontrado
```

Isso funciona porque as pessoas escolhem senhas previsíveis. A invasão da RockYou em 2009 vazou 32 milhões de senhas em texto simples, e as 10 principais foram:

```
1. 123456        6. monkey
2. 12345         7. 1234567
3. 123456789     8. letmein
4. password      9. trustno1
5. iloveyou     10. dragon
```

Essas listas são reutilizadas em todas as ferramentas de quebra. Um dicionário de 14 milhões de palavras leva segundos para ser esgotado contra um hash rápido como SHA256 em hardware moderno.

### Por Que São Tão Eficazes

O HaveIBeenPwned rastreia mais de 613 milhões de senhas de violações reais. Se sua senha já apareceu em qualquer violação, ela está em um dicionário de quebra. O reuso de senhas piora isso: a senha que você usa para um fórum descartável pode acabar em um dicionário usado para quebrar sua conta de e-mail.

## Brute Force Attacks (Ataques de Força Bruta)

### Como Funcionam

A força bruta gera cada combinação possível de caracteres até um comprimento máximo:

```
Comprimento 1: a, b, c, ..., z                              (26 combinações)
Comprimento 2: aa, ab, ac, ..., zz                           (676 combinações)
Comprimento 3: aaa, aab, ..., zzz                            (17.576 combinações)
Comprimento 4: aaaa, ..., zzzz                               (456.976 combinações)
...
Comprimento 8: aaaaaaaa, ..., zzzzzzzz                       (208 bilhões de combinações)
```

O keyspace cresce exponencialmente. Adicione letras maiúsculas e a base vai de 26 para 52. Adicione dígitos e será 62. Adicione caracteres especiais e será 95. Uma senha de 8 caracteres usando todos os tipos de caracteres tem 95^8 = 6,6 quatrilhões de combinações.

### A Matemática da Viabilidade

A 3 milhões de hashes SHA256 por segundo (o que esta ferramenta alcança na CPU):

| Senha   | Conjunto de Caracteres | Combinações | Tempo         |
| ------- | ---------------------- | ----------- | ------------- |
| 4 chars | minúsculas             | 456K        | 0,15 segundos |
| 6 chars | minúsculas             | 308M        | 1,7 minutos   |
| 6 chars | minúsculas + dígitos   | 2,2B        | 12 minutos    |
| 8 chars | minúsculas             | 208B        | 19 horas      |
| 8 chars | todos imprimíveis      | 6,6Q        | 70.000 anos   |

Ferramentas de quebra por GPU como o hashcat alcançam 3 bilhões por segundo (1000x mais rápido), mas mesmo assim, 8 caracteres com conjuntos completos levam 25 dias. É por isso que o comprimento da senha importa mais do que a complexidade.

## Mutações Baseadas em Regras

### Como Funcionam

Os humanos são previsíveis. Quando forçados a adicionar uma letra maiúscula, a maioria das pessoas capitaliza a primeira letra. Quando forçados a adicionar um número, eles o anexam ao final. Quando forçados a adicionar um caractere especial, usam `!` ou `@`. Ataques baseados em regras exploram esses padrões:

| Regra                | Entrada  | Saída       |
| -------------------- | -------- | ----------- |
| Capitalizar primeira | password | Password    |
| Tudo em maiúsculas   | password | PASSWORD    |
| Substituição Leet    | password | p@$$w0rd    |
| Anexar dígitos 0-999 | password | password123 |
| Inverter             | password | drowssap    |
| Alternar caixa       | password | PASSWORD    |

Isso transforma um dicionário de 14 milhões de palavras em bilhões de candidatos. A combinação de `capitalizar + leet + anexar dígitos` transforma `password` em `P@$$w0rd123`, que satisfaz todas as políticas de senha já escritas e ainda é quebrado em milissegundos.

### Por Que Requisitos de Complexidade Não Funcionam

A análise da Specops de 2021 de 800 milhões de senhas violadas descobriu que 83% atendiam aos requisitos padrão de complexidade (8+ caracteres, maiúsculas, minúsculas, número, caractere especial). Os padrões mais comuns:

```
[Palavra][Número]        → Password1
[Palavra][Número][!]     → Password1!
[Estação][Ano]           → Verão2024
[Nome][Aniversário]      → Michael1990!
```

Gerenciadores de senhas que geram strings aleatórias como `x7$kQ2!mR9pL` são a defesa real. Nenhum dicionário contém isso, e a força bruta de 12 caracteres aleatórios do conjunto imprimível completo é computacionalmente inviável.

## Salting de Senhas

### O Que É

Um salt é uma string aleatória armazenada junto com o hash da senha. Antes de fazer o hash, o salt é prefixado ou anexado à senha:

```
Sem salt:
  Usuário A: SHA256("password")       → 5e884898da...
  Usuário B: SHA256("password")       → 5e884898da...  (idênticos!)

Com salt:
  Usuário A: SHA256("x9f2" + "password") → a1b2c3d4...
  Usuário B: SHA256("k7m1" + "password") → 9z8y7x6w...  (completamente diferentes)
```

O salt não é secreto. Ele é armazenado em texto simples logo ao lado do hash no banco de dados. Seu único trabalho é tornar o hash de cada usuário único, mesmo que eles usem a mesma senha.

### O Que o Salt Previne

**Rainbow tables** são tabelas de consulta pré-computadas que mapeiam hashes para senhas. Sem salt, você computa SHA256("password") uma vez e ele coincide com cada usuário que escolheu "password". Uma rainbow table para SHA256 cobrindo senhas comuns pode ter 100GB, mas quebra milhões de hashes instantaneamente.

O salt torna as rainbow tables inúteis. Cada usuário tem um salt diferente, então você precisaria de uma rainbow table separada para cada valor de salt possível. Com um salt de 16 bytes, são 2^128 tabelas possíveis. Não vai acontecer.

**Quebra em massa** também é derrotada. Sem salt, se você quebrar um hash, quebrou todos os usuários com aquela senha. Com salt, você quebra um usuário por vez porque cada hash é computado de forma diferente.

### O Que o Salt NÃO Previne

O salt não desacelera a quebra direcionada. Se um atacante quiser quebrar o hash de um usuário específico, ele conhece o salt (está no banco de dados) e apenas o prefixa em cada tentativa. A velocidade de quebra é idêntica. Nossa flag `--salt` demonstra exatamente este ataque.

### Falhas Reais de Salt

A invasão do LinkedIn em 2012 vazou 6,5 milhões de hashes SHA1 sem salt. Pesquisadores quebraram 90% em 72 horas. Se o LinkedIn tivesse usado salts, a quebra teria exigido atacar cada hash individualmente em vez de quebrar o banco de dados inteiro de uma vez.

A invasão da Adobe em 2013 usou criptografia 3DES (nem sequer era hashing) com uma única chave e sem salts únicos. Como senhas idênticas produziam ciphertexts idênticos, os pesquisadores puderam identificar as senhas mais comuns apenas contando as duplicatas, e então as quebraram baseados em dicas de senha que também foram vazadas.

## Funções de Hash Lentas

### Por Que Hashes Rápidos São o Problema

O SHA256 foi projetado para fazer o hash de dados rapidamente. Isso é ótimo para verificar a integridade de arquivos ou handshakes TLS, mas terrível para o armazenamento de senhas. Uma GPU pode computar 3 bilhões de hashes SHA256 por segundo. Isso significa que um atacante pode tentar 3 bilhões de senhas por segundo.

### Como bcrypt e argon2 Corrigem Isso

bcrypt, scrypt e argon2 são funções de hash intencionalmente lentas. Elas adicionam um "fator de trabalho" configurável que controla quanto tempo cada hash leva:

```
SHA256:  ~3.000.000 hashes/seg (CPU)  ~3.000.000.000 hashes/seg (GPU)
bcrypt:  ~300 hashes/seg (CPU)        ~50.000 hashes/seg (GPU)
argon2:  ~10 hashes/seg (CPU)         Resistente a GPU por design
```

O bcrypt com fator de custo 12 leva cerca de 250ms por hash. Um usuário fazendo login espera 250ms (imperceptível). Um atacante tentando 14 milhões de palavras de dicionário espera 40 dias. Mesma matemática, resultado completamente diferente.

O argon2 vai além ao exigir grandes quantidades de memória por hash, o que limita o paralelismo da GPU. As GPUs têm milhares de núcleos, mas memória limitada por núcleo. O argon2 explora isso forçando cada hash a usar megabytes de RAM, tornando a quebra por GPU impraticável.

### Por Que Não os Quebramos

Esta ferramenta quebra apenas hashes rápidos (MD5, SHA1, SHA256, SHA512). Isso é intencional. Quebrar bcrypt com um dicionário de 10.000 palavras a 300 hashes/seg leva 33 segundos. O mesmo dicionário contra SHA256 leva 3 milissegundos. A diferença de velocidade é a lição.

## Padrões da Indústria

**OWASP Password Storage Cheat Sheet** recomenda:

- argon2id como a escolha primária
- bcrypt com fator de custo 10+ como alternativa
- Nunca MD5 ou família SHA para senhas
- Salt aleatório de no mínimo 16 bytes por senha

**NIST SP 800-63B** (Diretrizes de Identidade Digital):

- Segredos memorizados devem ser hasheados com um salt usando uma função de derivação de chave
- Pelo menos 10.000 iterações se usar PBKDF2
- Verificar senhas contra bancos de dados de violações conhecidas

**MITRE CWE-916**: Uso de Hash de Senha com Esforço Computacional Insuficiente. Atribuído a sistemas que usam MD5, SHA1 ou SHA256 para armazenamento de senhas sem uma função de derivação de chave lenta.

## Testando Seu Entendimento

1. Um atacante rouba um banco de dados com 1 milhão de hashes SHA256, todos sem salt. Como a falta de salt ajuda o atacante além de apenas rainbow tables?

2. Um site exige que as senhas tenham "pelo menos 8 caracteres com maiúsculas, minúsculas, número e caractere especial". Por que isso não previne ataques baseados em regras?

3. Por que o argon2 resiste especificamente à aceleração por GPU enquanto o bcrypt resiste apenas parcialmente?

4. Você encontra um hash `5f4dcc3b5aa765d61d8327deb882cf99` em um dump de violação. Sem rodar nenhuma ferramenta de quebra, o que você pode determinar sobre ele apenas olhando para ele?

## Leitura Adicional

**Essencial:**

- [Como as Senhas São Armazenadas](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) (OWASP)
- [Documentação do hashcat](https://hashcat.net/wiki/) para entender técnicas de quebra do mundo real

**Aprofundamento:**

- [Artigo do Bcrypt](https://www.usenix.org/legacy/events/usenix99/provos/provos.pdf) por Provos e Mazieres (1999)
- [Especificação do Argon2](https://github.com/P-H-C/phc-winner-argon2/blob/master/argon2-specs.pdf) (Vencedor da Password Hashing Competition)
- [Have I Been Pwned](https://haveibeenpwned.com/) para verificar se senhas aparecem em bancos de dados de violações.
