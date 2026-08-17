# Conceitos

Este arquivo explica cada ideia criptográfica que o vault de senhas utiliza, começando do zero absoluto. Se você nunca pensou seriamente sobre o que a "criptografia" realmente é, este é o lugar certo para começar. Se você já sabe a diferença entre uma KDF e um hash, pode ler por cima — mas leia as seções sobre LastPass e Adobe, porque elas são o _porquê_ de cada escolha de design no código ser do jeito que é.

## Tabela de conteúdos

1. [O problema: armazenar segredos que você precisará mais tarde](#1-o-problema-armazenar-segredos-que-você-precisará-mais-tarde)
2. [O que a "criptografia" realmente é](#2-o-que-a-criptografia-realmente-é)
3. [Simétrica vs assimétrica — nós usamos simétrica](#3-simétrica-vs-assimétrica--nós-usamos-simétrica)
4. [O problema da chave: de onde vem a chave?](#4-o-problema-da-chave-de-onde-vem-a-chave)
5. [Funções de derivação de chave: tornando senhas caras](#5-funções-de-derivação-de-chave-tornando-senhas-caras)
6. [Argon2id especificamente, e por quê](#6-argon2id-especificamente-e-por-quê)
7. [Salts: derrotando a pré-computação](#7-salts-derrotando-a-pré-computação)
8. [Cifras de bloco e modos: apenas "criptografado" não é suficiente](#8-cifras-de-bloco-e-modos-apenas-criptografado-não-é-suficiente)
9. [AES-256-GCM: confidencialidade + autenticidade em um único pacote](#9-aes-256-gcm-confidencialidade--autenticidade-em-um-único-pacote)
10. [Nonces: a coisa mais perigosa nesta base de código](#10-nonces-a-coisa-mais-perigosa-nesta-base-de-código)
11. [random vs secrets: o erro mais comum do lado do Python](#11-random-vs-secrets-o-erro-mais-comum-do-lado-do-python)
12. [Juntando tudo: o modelo de ameaça](#12-juntando-tudo-o-modelo-de-ameaça)
13. [Violações reais que tornaram essas escolhas as corretas](#13-violações-reais-que-tornaram-essas-escolhas-as-corretas)

---

## 1. O problema: armazenar segredos que você precisará mais tarde

Um gerenciador de senhas tem um trabalho estranho. Ele precisa:

- Lembrar suas senhas _exatamente_ (sem correspondência aproximada — `hunter2` e `Hunter2` são senhas diferentes).
- Recusar-se a entregá-las a qualquer pessoa que não seja você.
- Sobreviver ao roubo do seu computador.
- Sobreviver ao seu computador ser apreendido e periciado.
- Ainda assim, permitir que _você_ entre com uma string curta que você possa guardar na cabeça.

Esses objetivos estão em tensão. "Lembrar a senha exatamente" puxa para "armazene-a em texto simples em algum lugar". "Não entregue a ninguém além de você" puxa para "não armazene nada". Todo o resto deste documento é sobre como navegar nessa tensão.

O plano que resolve isso: **armazenar as senhas embaralhadas com uma chave que apenas a senha mestra pode recriar.** Se alguém roubar o arquivo, tudo o que terá é um blob embaralhado e um problema _muito caro_ para resolver. Se você digitar a senha mestra, a chave é recriada em segundos e o blob é desembaralhado.

Essa é a estrutura completa do projeto. O resto deste documento é sobre como cada peça desse plano realmente funciona.

---

## 2. O que a "criptografia" realmente é

Criptografia é uma função. Ela recebe três coisas na entrada:

- Um pedaço de dado (o **plaintext** ou texto simples), como `"minha senha do github é hunter2"`.
- Uma **chave**, que é apenas um bloco de bytes aleatórios — geralmente 16 ou 32 bytes.
- Um **algoritmo** (um procedimento específico para embaralhar dados usando aquela chave).

E produz uma coisa na saída:

- O **ciphertext** (ou texto cifrado) — a versão embaralhada. Tem o mesmo comprimento que o plaintext (mais um pequeno overhead, falaremos disso mais tarde), mas cada byte parece ruído.

```
┌──────────────┐
│ "hunter2..." │ ──┐
└──────────────┘   │
                   ▼
            ┌────────────┐    ┌─────────────────────────┐
            │ ENCRYPT()  │ ─► │ "Vh\x91\x03\x7f\xe2..." │
            └────────────┘    └─────────────────────────┘
                   ▲
┌──────────────┐   │
│ chave 32-byte│ ──┘
└──────────────┘
```

**Descriptografia** é a mesma função ao contrário. Mesma chave, mesmo algoritmo, o ciphertext entra, o plaintext sai.

```
┌─────────────────────────┐
│ "Vh\x91\x03\x7f\xe2..." │ ──┐
└─────────────────────────┘   │
                              ▼
                       ┌────────────┐    ┌──────────────┐
                       │ DECRYPT()  │ ─► │ "hunter2..." │
                       └────────────┘    └──────────────┘
                              ▲
┌──────────────┐              │
│ chave 32-byte│ ─────────────┘
└──────────────┘
```

Se você tem a chave, a descriptografia é rápida e devolve o original. Se você tem a chave errada — mesmo que apenas um bit esteja diferente — você obtém lixo na saída ou (para algoritmos modernos) a função de descriptografia se recusa a rodar e gera um erro. Nós usamos o segundo tipo.

**Uma coisa importante que isso _não_ é:** criptografia não é uma operação de via única como um hash. Uma função de hash (SHA-256, MD5, etc.) descarta deliberadamente informações para que o original nunca possa ser recuperado. A criptografia mantém cada bit — ela apenas os embaralha para que você não possa lê-los sem a chave. Todo o objetivo é que o original seja recuperável, _mas apenas por você_.

---

## 3. Simétrica vs assimétrica — nós usamos simétrica

Existem duas grandes famílias de criptografia.

**Criptografia simétrica** usa a _mesma_ chave para criptografar e descriptografar. Como um armário com uma única chave física — quem detém a chave pode tanto trancá-lo quanto destrancá-lo. O AES é o famoso algoritmo simétrico. Nós o usamos.

**Criptografia assimétrica** usa duas chaves _diferentes_ que são matematicamente relacionadas. Uma ("pública") tranca as coisas, a outra ("privada") as destranca. Você pode entregar a chave pública para o mundo e eles podem lhe enviar coisas criptografadas que apenas você pode ler. RSA e algoritmos de curva elíptica são os famosos assimétricos. É isso que alimenta o HTTPS no início de cada conexão, assina suas atualizações de software e alimenta o login via SSH. Nós **não** usamos isso.

Por que não assimétrica? Porque um gerenciador de senhas é uma operação de uma única pessoa. Não existe "você criptografa, depois outra pessoa descriptografa" — _você_ criptografa, _você_ descriptografa. A simétrica é a ferramenta certa. Algoritmos assimétricos também são massivamente mais lentos por byte, o que importa para os raros casos onde fazem sentido e os descarta para todo o resto.

---

## 4. O problema da chave: de onde vem a chave?

Acabamos de dizer que "a criptografia precisa de uma chave de 32 bytes". De onde um ser humano tira 32 bytes aleatórios?

Não da sua cabeça. Seres humanos não conseguem lembrar de 32 bytes aleatórios — isso são 256 bits de entropia, o que é o mesmo que pedir para alguém memorizar um número de 78 dígitos. O melhor que um humano consegue fazer sem anotar é algo como `correto cavalo bateria grampo` (~40 bits) ou talvez uma frase longa (~60 bits). A lacuna de 256 bits é _enorme_.

Portanto, não pedimos ao humano uma chave. Pedimos a ele uma **senha** (que ele consegue lembrar) e a transformamos em uma chave usando uma **função de derivação de chave** (KDF).

```
┌──────────────────┐      ┌─────────────────┐     ┌─────────────────┐
│ "correto cavalo  │      │   FUNÇÃO DE     │     │ <32 bytes       │
│  bateria grampo" │ ───► │   DERIVAÇÃO     │ ──► │  aleatórios>    │
└──────────────────┘      │   DE CHAVE      │     └─────────────────┘
                          └─────────────────┘
                                  ▲
┌──────────────────┐              │
│ salt aleatório   │ ─────────────┘
│ (no arquivo)     │
└──────────────────┘
```

A transformação é determinística: a mesma senha + o mesmo salt sempre produzem a mesma chave. É assim que podemos derivar a chave novamente amanhã quando o usuário voltar. Mas a transformação também é **deliberadamente lenta**, que é o truque que torna todo o sistema seguro.

---

## 5. Funções de derivação de chave: tornando senhas caras

Imagine que um atacante roubou seu arquivo de vault. Dentro dele está:

- O salt (16 bytes de dados aleatórios públicos).
- O ciphertext (suas senhas criptografadas).
- O nome do algoritmo e os parâmetros.

O atacante agora quer adivinhar sua senha mestra. A maneira ingênua: pegar cada senha candidata, fazer o hash com o salt, tentar o resultado como uma chave contra o ciphertext e ver se o resultado é válido.

Se nossa derivação de chave fosse apenas `SHA-256(senha + salt)`, o atacante poderia fazer **bilhões de tentativas por segundo** em uma GPU moderna. Mesmo uma senha que parece forte como `Tr0ub4dor&3` seria quebrada em menos de um minuto. Isso porque o SHA-256 foi projetado para _velocidade_ — ele é otimizado para verificar a integridade de arquivos enormes em frações de segundo.

**A correção: use uma função que seja deliberadamente lenta para computar.**

Se cada tentativa levar meio segundo, então um milhão de tentativas levam 6 dias, um bilhão de tentativas levam 16 anos e um trilhão de tentativas (o universo de "senhas comuns de 12 caracteres") leva 16.000 anos. O usuário legítimo paga o custo apenas _uma vez_ por sessão — meio segundo está ótimo. O atacante o paga em _cada_ tentativa, para sempre.

Este é todo o objetivo de uma função de derivação de chave (uma "KDF"). É uma operação do tipo hash, mas ajustada para ser cara — tanto em tempo de CPU quanto em memória.

Por que ambos? Porque atacantes não usam CPUs. Eles usam GPUs e hardware personalizado chamado ASICs. Uma GPU tem milhares de pequenos núcleos de computação, mas muito pouca memória rápida por núcleo. Portanto, se usarmos um algoritmo que precisa de muita memória (digamos, 64 megabytes) por tentativa, os milhares de núcleos da GPU subitamente não conseguem rodar em paralelo — eles precisariam de cem gigabytes de memória rápida apenas para tentar adivinhações paralelas. ASICs enfrentam o mesmo problema. **Tornar a função faminta por memória é o que interrompe ataques baseados em hardware.**

O termo técnico para isso é "memory-hard". As KDFs modernas são todas memory-hard. As antigas (PBKDF2 de 2000) são CPU-hard, mas não memory-hard, e é por isso que caíram em desuso.

---

## 6. Argon2id especificamente, e por quê

Em 2013, a comunidade criptográfica realizou a **Password Hashing Competition** — um concurso aberto para escolher uma nova KDF padrão. Pesquisadores enviaram designs, atacaram as submissões uns dos outros e, após dois anos de análise, o vencedor foi o [**Argon2**](https://www.password-hashing.net/argon2-specs.pdf), especificamente a variante chamada **Argon2id**.

Existem três variantes:

- **Argon2d** — maximiza a resistência à quebra por GPU, mas é vulnerável a ataques de canal lateral (onde um atacante observa os tempos de acesso à memória da sua CPU).
- **Argon2i** — maximiza a resistência a ataques de canal lateral, mas é mais fraco contra quebra por GPU.
- **Argon2id** — um híbrido que faz ambos, escolhido como o padrão recomendado.

Nós usamos o Argon2id. O [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) também o usa, assim como gerenciadores de senhas como 1Password e Bitwarden, e a ferramenta de criptografia de arquivos `age`.

O Argon2id tem **três botões de ajuste** que controlam o quão caro ele é:

| Botão         | O que ele controla                                             | Nosso padrão   | Por quê                                                                                                                                                                |
| ------------- | -------------------------------------------------------------- | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `time_cost`   | Número de passagens sobre o buffer de memória                  | 3              | Forte para uso interativo; cada passagem extra é outro fator de desaceleração.                                                                                         |
| `memory_cost` | KiB de memória usados durante a derivação (1 KiB = 1024 bytes) | 65536 (64 MiB) | Confortavelmente acima de cada perfil da OWASP; derrota atacantes de GPU/ASIC que carecem de memória rápida por núcleo.                                                |
| `parallelism` | Threads que o Argon2 pode usar                                 | 4              | Um único usuário em um laptop moderno se beneficia do ganho de velocidade paralelo. O atacante obtém o mesmo ganho, então é neutro para a segurança, mas melhora a UX. |

Esses números vivem em [`constants.py`](../src/password_manager/constants.py) para que sejam fáceis de aumentar daqui a cinco anos, quando os laptops forem mais rápidos.

**Detalhe importante:** os parâmetros são armazenados _dentro do arquivo do vault_. Se você alterar os padrões no código, os vaults antigos ainda abrem porque lembram com quais parâmetros foram criados. Voltaremos a isso — é também o que torna o comando `change-password` capaz de atualizar vaults antigos para novos parâmetros.

---

## 7. Salts: derrotando a pré-computação

Um **salt** é um pedaço de dado aleatório misturado com a senha antes da derivação da chave. Ele não é secreto — nós o armazenamos em texto simples dentro do arquivo do vault.

Por que isso importa?

Imagine que você não usasse um salt. Então `derive_key("hunter2") = <alguns 32 bytes fixos>` — o mesmo em cada máquina, para cada usuário. Um atacante poderia, _anos antes de qualquer violação_, computar as chaves para o milhão de senhas mais comuns e armazená-las em uma tabela de consulta gigante. Rouba um vault → consulta a chave → destranca o vault. Nenhum trabalho por vault.

Essa pré-computação é chamada de **rainbow table**. Costumava ser um ataque real — existem rainbow tables para download para MD5 sem salt cobrindo trilhões de hashes de senhas comuns.

Um salt destrói esse ataque. Agora `derive_key("hunter2", <16 bytes aleatórios>) = <32 bytes diferentes>` para cada vault, porque cada vault tem um salt diferente. O atacante não pode pré-computar nada — ele tem que fazer o trabalho completo do Argon2 _depois_ de roubar o arquivo do vault, _por cada vault que ele queira atacar_.

**Mais dois usos para salts:**

1. **Unicidade por usuário.** Dois usuários escolhendo a mesma senha (`hunter2` novamente) obtêm chaves _diferentes_, porque seus salts diferem. Útil para bancos de dados de senhas em escala, onde muitos usuários infelizmente escolhem as mesmas senhas.
2. **Unicidade para o mesmo usuário em vaults diferentes.** Se você tiver dois vaults com a mesma senha mestra, seus ciphertexts serão completamente diferentes porque seus salts são diferentes. Isso não é uma ameaça ativa para um gerenciador de senhas de um único usuário, mas é um benefício gratuito de ter salts.

O tamanho do salt importa menos do que você imagina. 16 bytes (128 bits) é a recomendação padrão. Maior está ok; menor começa a arriscar colisões na população global de vaults.

---

## 8. Cifras de bloco e modos: apenas "criptografado" não é suficiente

Agora temos uma chave. Precisamos realmente criptografar o conteúdo do vault com ela. É aqui que a maioria dos projetos de criptografia para iniciantes erra, então preste atenção.

O **AES** é uma "cifra de bloco". Ele criptografa dados em blocos de tamanho fixo (16 bytes por vez). Dado um bloco de 16 bytes e uma chave, ele produz outro bloco de 16 bytes que parece aleatório. Por si só, o AES é apenas uma função de um bloco de 16 bytes para outro.

Mas seu vault tem muito mais do que 16 bytes. Portanto, você precisa de uma maneira de encadear os blocos. Essa maneira é chamada de **modo de operação**.

O modo mais simples é o **ECB** ("electronic codebook"): corte o plaintext em blocos de 16 bytes, criptografe cada um independentemente e concatene os resultados. Isso está errado. É famosa e ilustrativamente errado:

```
                Versão criptografada em ECB
                de uma imagem do Tux, o pinguim do Linux
                (você ainda consegue ver o pinguim)

                ┌────────────────┐
                │ ░░░░░░░░░░░░░░ │
                │ ░░░██████░░░░░ │
                │ ░░██░░░░██░░░░ │      Blocos de entrada idênticos
                │ ░░░░██████░░░░ │  →   produzem blocos de saída
                │ ░░░░░██░░░░░░░ │      idênticos, então o contorno
                │ ░░░░██████░░░░ │      da imagem vaza.
                │ ░░░░██░░██░░░░ │
                │ ░░██░░░░░░██░░ │
                │ ░░░░░░░░░░░░░░ │
                └────────────────┘
```

É por isso que "nós usamos AES" sem especificar o modo não diz quase nada sobre se um sistema é seguro.

O próximo modo é o **CBC** (cipher block chaining), que faz um XOR de cada bloco com o bloco de ciphertext anterior antes de criptografar. Melhor que o ECB — blocos de plaintext idênticos agora produzem blocos de ciphertext diferentes. Mas o CBC tem _outro_ problema: ele não diz se o ciphertext foi adulterado. Um atacante pode inverter bits específicos no ciphertext para inverter bits _previsíveis_ no plaintext descriptografado, mesmo sem a chave. Isso é chamado de **ataque de inversão de bits** (bit-flipping attack) e já foi usado contra sistemas reais.

A resposta certa é um **modo autenticado** — um que não apenas criptografa, mas também carimba a saída com um selo de evidência de adulteração.

---

## 9. AES-256-GCM: confidencialidade + autenticidade em um único pacote

O **GCM** ("Galois/Counter Mode") é um modo autenticado para o AES. Ele produz duas coisas:

1. Os bytes criptografados (mesmo comprimento que o plaintext).
2. Uma **tag de autenticação** de 16 bytes — uma pequena impressão digital de "este ciphertext exato foi produzido por alguém que detém esta chave exata".

```
┌──────────────────┐
│ bytes plaintext  │
│ (conteúdo vault) │
└──────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│            AES-256-GCM                  │
│                                         │
│   chave ─┐                              │
│   nonce ├─► [embaralhar & autenticar]   │
│         │                               │
└─────────┴───────────────────────────────┘
         │                  │
         ▼                  ▼
┌─────────────────┐  ┌─────────────────┐
│ ciphertext      │  │ tag de aut.     │
│ (mesmo tamanho  │  │ de 16 bytes     │
│  do plaintext)  │  │                 │
└─────────────────┘  └─────────────────┘
```

A biblioteca agrupa esses elementos em uma única string de bytes para você — o "ciphertext" retornado pela biblioteca de criptografia é na verdade `ciphertext || tag`, com a tag concatenada ao final.

**Na descriptografia**, a cifra verifica a tag _antes_ de lhe entregar o plaintext. Se a tag não coincidir (porque a chave está errada, o ciphertext foi modificado ou o nonce está errado), a cifra gera um erro e se recusa a produzir qualquer plaintext. Essa é a proteção que torna o "criptografado com AES-GCM" realmente seguro.

Usamos especificamente o **AES-256**-GCM — o "256" é o tamanho da chave em bits. O AES-128 também está ok, mas chaves de 256 bits são o padrão para níveis de margem do tipo "não quero nunca mais ter que pensar nisso". A diferença de desempenho em CPUs modernas é insignificante porque o AES possui instruções de CPU dedicadas (AES-NI em Intel/AMD, ARMv8 Crypto Extensions em ARM).

---

## 10. Nonces: a coisa mais perigosa nesta base de código

Um **nonce** ("number used once" ou número usado uma única vez) é um valor passado para o AES-GCM junto com a chave. Ele deve ser único para cada criptografia realizada com a mesma chave. **Reutilizar um nonce com a mesma chave no GCM é catastrófico** — vaza informações do plaintext para qualquer um que esteja observando e, em alguns casos, revela a própria chave de autenticação.

Esta é a aresta mais afiada do AES-GCM e a razão pela qual somos extremamente cuidadosos com isso em [`crypto.py`](../src/password_manager/crypto.py).

O que "vaza plaintext" significa concretamente? Se você criptografar duas mensagens diferentes M1 e M2 com a mesma chave K e o mesmo nonce N, então `C1 XOR C2 = M1 XOR M2`. Um atacante que vê C1 e C2 pode computar `M1 XOR M2` sem saber a chave. A partir daí, se ele conseguir adivinhar qualquer parte de M1 ou M2, ele pode recuperar a parte correspondente da outra.

**A correção é mecânica: gere um nonce aleatório novo de 12 bytes em cada criptografia.** O GCM permite até aproximadamente 2³² (4 bilhões) de criptografias com segurança sob uma única chave com nonces aleatórios de 12 bytes. Um único ser humano nunca salvará seu vault 4 bilhões de vezes.

Um nonce _não_ é um salt. As diferenças:

| Propriedade        | Salt                          | Nonce                                        |
| ------------------ | ----------------------------- | -------------------------------------------- |
| Usado em           | Derivação de chave (Argon2id) | Criptografia (AES-GCM)                       |
| Com que frequência | Uma vez por _vault_ (no init) | Uma vez por _criptografia_ (cada salvamento) |
| Deve ser único?    | Sim (entre todos os vaults)   | Sim (por chave, vida útil)                   |
| Secreto?           | Não                           | Não                                          |

Ambos são aleatórios, ambos vão para o arquivo, ambos são públicos. Mas eles têm trabalhos diferentes e tempos de vida diferentes.

---

## 11. random vs secrets: o erro mais comum do lado do Python

O Python tem dois módulos que produzem números aleatórios, e a diferença importa mais do que quase qualquer outra escolha de API neste projeto:

- [`random`](https://docs.python.org/3/library/random.html) — usa o algoritmo **Mersenne Twister**. Rápido, estatisticamente uniforme, **previsível**. Se um atacante vir 624 saídas consecutivas, ele pode reconstruir o estado interno e prever cada saída futura para sempre.
- [`secrets`](https://docs.python.org/3/library/secrets.html) — extrai bytes da fonte aleatória criptográfica do sistema operacional (`/dev/urandom` no Linux/Mac, `BCryptGenRandom` no Windows). Imprevisível por design.

Salts, nonces e chaves DEVEM vir de `secrets`. Senhas geradas DEVEM vir de `secrets`. Se você usasse `random` para qualquer um desses, um atacante que visse uma saída poderia prever cada senha subsequente que sua ferramenta gerasse — para _cada_ usuário, em _cada_ máquina, para sempre.

Este projeto usa `secrets` em todos os lugares onde importa:

- `crypto.generate_salt()` e `crypto.generate_nonce()` → `secrets.token_bytes()`.
- `generator.generate_password()` → `secrets.choice()` e `secrets.randbelow()`.
- O embaralhamento Fisher-Yates em `generator._secure_shuffle()` → `secrets.randbelow()` em vez de `random.shuffle()`.

A regra é simples: **se a saída deve ser difícil de prever, use `secrets`. Sempre.**

---

## 12. Juntando tudo: o modelo de ameaça

Um "modelo de ameaça" é uma resposta escrita para "quem pode quebrar isso, e como?". Aqui está o nosso:

**O que defendemos contra:**

- **Roubo do arquivo do vault.** Alguém copia o `vault.json` do seu laptop. Sem a senha mestra, tudo o que eles têm é um problema de adivinhação lento e caro (Argon2id com nossos padrões: ~0,5 segundos/tentativa, ~15 anos para um bilhão de tentativas).
- **Adulteração do arquivo do vault.** Alguém modifica bytes no `vault.json` para tentar causar um comportamento estranho na descriptografia. A tag de autenticação do AES-GCM se recusa a descriptografar.
- **Queda de energia no meio do salvamento.** O padrão de renomeação atômica + fsync significa que você sempre termina com o vault ANTIGO ou o vault NOVO, nunca metade de um deles. Detalhado em [02-ARCHITECTURE.md](./02-ARCHITECTURE.md).
- **Dois processos `pv` salvando ao mesmo tempo.** Um bloqueio de arquivo consultivo os serializa, para que o salvamento de nenhum deles seja sobrescrito silenciosamente.
- **Esquecer sua senha mestra (e o arquivo estar seguro em repouso por causa disso).** Esse é todo o objetivo.

**O que explicitamente NÃO defendemos contra:**

- **Um keylogger na sua máquina.** Se algo está lendo cada tecla digitada, ele vê sua senha mestra enquanto você a digita, e o jogo acaba. A defesa para isso vive em uma camada diferente (criptografia de disco total, detecção de keylogger em nível de SO, chaves de segurança de hardware). Este não é um projeto de entrada segura em nível de sistema.
- **Um atacante observando sua tela enquanto o vault está desbloqueado.** O comando `pv get` imprime senhas no stdout em texto simples. O atacante lendo sua tela já domina a sessão de qualquer maneira.
- **Um SO verdadeiramente comprometido que pode ler a memória do processo.** Enquanto o vault está desbloqueado, as entradas descriptografadas e a chave AES vivem na memória do seu processo. Um atacante privilegiado que possa ler essa memória vence. O método `close()` no `UnlockedVault` é um esforço de melhor tentativa para limpar, não uma garantia.
- **Uma senha mestra fraca.** O Argon2id torna a força bruta cara, mas não impossível. Se sua senha mestra for `senha123`, um atacante disposto a esperar acabará por quebrá-la. A defesa está em você: escolha algo longo.
- **Backups sob seu controle.** A ferramenta escreve um arquivo, de forma atômica e durável. Fazer o backup para outro lugar (um pendrive, Syncthing, etc.) é seu trabalho. A criptografia significa que é seguro fazer backup em lugares que você não confiaria com texto simples.

Ser honesto sobre o que uma ferramenta defende ou não é uma habilidade de segurança por si só. Incidentes do mundo real quase sempre acontecem nas fronteiras de um modelo de ameaça, não dentro dele.

---

## 13. Violações reais que tornaram essas escolhas as corretas

**[Adobe 2013](https://www.troyhunt.com/adobe-credentials-and-serious/)** — 153 milhões de registros. A Adobe criptografou senhas com uma única chave no **modo ECB** com **nenhum salt por registro**. Resultado: senhas idênticas produziram ciphertexts idênticos. Pesquisadores puderam agrupar usuários com a mesma senha sem saber a senha em si. Combinado com dicas de senha armazenadas em texto simples, grandes frações das senhas vazadas foram recuperadas na mesma semana. Lição: aleatoriedade por criptografia (salts, nonces) e modos autenticados (não ECB) não são opcionais.

**[LinkedIn 2012](https://en.wikipedia.org/wiki/2012_LinkedIn_hack)** — 6,5 milhões de registros. Senhas armazenadas como **SHA-1 sem salt**. O SHA-1 é rápido em uma GPU; sem salts, o atacante pôde pré-computar uma rainbow table uma vez e usá-la para sempre. 90% dos hashes foram quebrados em poucos dias. Lição: salts mais uma KDF lenta (não um hash rápido) são o mínimo moderno.

**[LastPass 2022](https://blog.lastpass.com/posts/notice-of-recent-security-incident)** — backups de vaults criptografados roubados. Os vaults em si usavam uma KDF real (PBKDF2 com 100.100 iterações na época da violação), mas o PBKDF2 não é memory-hard, então ataques de GPU contra senhas mestras fracas têm sido em escala industrial desde então. Vários relatórios públicos descrevem atacantes quebrando subconjuntos de vaults e usando as senhas recuperadas para roubo de criptomoedas. Lição: uma KDF memory-hard (Argon2id, scrypt) é significativamente mais forte que o PBKDF2 contra hardware moderno. Nós usamos o Argon2id.

**[Heartbleed 2014](https://heartbleed.com)** — um bug de divulgação de memória no OpenSSL. Não foi diretamente sobre armazenamento de senhas, mas demonstrou um princípio relacionado: os bytes de material secreto que vivem na memória do processo são reais e vulneráveis. A disciplina do `UnlockedVault.close()` limpando a chave e a instrução `with` minimizando quanto tempo o vault permanece desbloqueado é um desdobramento desta lição.

**[Yahoo 2013 / 2016](https://en.wikipedia.org/wiki/Yahoo!_data_breaches)** — 3 bilhões de registros (a maior violação da história). Senhas armazenadas como **MD5**. Em 2016, o MD5 já estava 20 anos além de ser considerado quebrado para armazenamento de senhas. Lição: agilidade criptográfica (a capacidade de atualizar escolhas de hash/KDF ao longo do tempo) importa. A razão pela qual este projeto armazena os parâmetros KDF _no arquivo do vault_ — em vez de fixá-los no código — é para que vaults antigos possam ser atualizados mais tarde sem forçar os usuários a perder dados. O comando `change-password` exercita essa capacidade.

---

## Para onde ir em seguida

Agora você sabe o _porquê_ de cada escolha de design no código ser o que é. Hora de ver _como_ ele está organizado.

**[02-Arquitetura.md](./02-Arquitetura.md)** explica como o projeto é dividido em módulos, como o arquivo do vault se parece no disco e o fluxo passo a passo de cada comando CLI.

Depois disso, o **[03-Implementação.md](./03-Implementação.md)** percorre cada arquivo fonte linha por linha com os recursos do Python explicados conforme aparecem.
