# Desafios de Extensão

Ideias para estender este projeto, ordenadas por dificuldade. Cada uma ensina uma habilidade diferente. Não sinta que precisa segui-las em ordem.

## Desafios Fáceis

### 1. Adicionar Suporte a SHA3

O SHA3 (Keccak) é uma família de hash completamente diferente do SHA2, baseada em uma construção de esponja (sponge construction) em vez de Merkle-Damgard. O OpenSSL o suporta através da mesma EVP API.

**O que construir:** Adicionar hashers SHA3-256 e SHA3-512.

**O que você aprenderá:** Quão pouco código um novo algoritmo exige quando a arquitetura está correta. O template EVPHasher significa que esta é uma mudança de duas linhas, além da lógica de detecção.

**Dicas:**

- `EVP_sha3_256()` e `EVP_sha3_512()` são as funções do OpenSSL
- O SHA3-256 produz um digest hex de 64 caracteres (mesmo comprimento que o SHA256), então a detecção automática apenas pelo comprimento não os distinguirá. Você precisará de uma flag `--type sha3-256`
- Escreva testes contra vetores conhecidos da suíte de testes NIST SHA3

### 2. Quebra de Hash em Lote (Batch)

Atualmente, a ferramenta quebra um hash por vez. Dumps de violações reais têm milhões de hashes.

**O que construir:** Aceitar um arquivo de hashes (um por linha) e quebrá-los todos em uma única execução. Relatar quais foram quebrados e quais não foram.

**O que você aprenderá:** Amortizar as leituras de dicionário entre múltiplos alvos. Em vez de ler a wordlist novamente para cada hash, você faz o hash de cada candidato uma vez e compara contra todos os alvos simultaneamente.

**Dicas:**

- Carregue todos os hashes alvo em um `std::unordered_set<std::string>`
- Para cada candidato, faça o hash e verifique `targets.count(hash_result)`
- É assim que ferramentas de quebra reais funcionam. Quebrar 1000 hashes é apenas um pouco mais lento do que quebrar 1

### 3. Exibição Colorida do Tipo de Hash

Ao detectar automaticamente, mostre ao usuário qual tipo foi detectado antes do início da quebra.

**O que construir:** Adicionar uma linha colorida ao banner mostrando o algoritmo detectado com um indicador de confiança.

**O que você aprenderá:** Design de UI de terminal, sequências de escape ANSI e o problema da ambiguidade (SHA256 e SHA3-256 têm o mesmo comprimento de digest).

**Dicas:**

- Use as constantes de cores existentes em Config.hpp
- Considere mostrar "SHA256 (auto-detectado)" vs "SHA256 (especificado)" para que o usuário saiba qual caminho foi tomado

## Desafios Intermediários

### 4. Formato de Arquivo de Regras Personalizado

O conjunto de regras atual é fixo no código. Ferramentas de quebra reais como hashcat e john suportam arquivos de regras onde os usuários definem seus próprios padrões de mutação.

**O que construir:** Um parser de arquivo de regras que lê regras de um arquivo de texto:

```
:           # não faz nada (tenta a palavra como está)
c           # capitaliza a primeira letra
u           # tudo em maiúsculas
l           # tudo em minúsculas
r           # inverte
$[0-9]      # anexa dígito
^[0-9]      # prefixa dígito
sa@         # substitui a por @
se3         # substitui e por 3
```

**O que você aprenderá:** Parsing de linguagem, o formato de regras do hashcat (que é um padrão real da indústria) e como a composição de regras cria contagens exponenciais de candidatos.

**Dicas:**

- Comece com códigos de regra de um único caractere, depois adicione regras paramétricas como `$N` e `sXY`
- A documentação da engine de regras do hashcat descreve a sintaxe completa
- Um arquivo de regras com 50 regras aplicadas a uma wordlist de 10K produz 500K candidatos. Isso ainda é rápido

### 5. Arquivo de Progresso para Quebra Resumível

Se você estiver fazendo brute force de uma senha de 8 caracteres e sua máquina travar em 60% do progresso, você perde todo esse trabalho.

**O que construir:** Salvar periodicamente o progresso (índice atual, tempo decorrido, candidatos testados) em um arquivo. Ao reiniciar com `--resume`, continuar de onde parou.

**O que você aprenderá:** Checkpointing, escritas atômicas de arquivo (escrever em temp, renomear) e a importância do particionamento de trabalho determinístico (nosso brute force baseado em índice facilita isso, já que cada índice mapeia para exatamente um candidato).

**Dicas:**

- Para brute force, salve o índice plano atual. Isso é tudo que você precisa
- Para dicionário, salve o offset de bytes no arquivo
- Escreva o checkpoint a cada N segundos, não a cada N candidatos (E/S é cara em relação ao hashing)

### 6. Ataque de Máscara (Mask Attack)

Um ataque de máscara é um brute force mais inteligente. Em vez de tentar todos os caracteres em cada posição, você especifica um padrão: `?u?l?l?l?d?d?d?d` significa uma maiúscula, três minúsculas e quatro dígitos. Isso corresponde a senhas como `Pass1234`.

**O que construir:** Uma flag `--mask` que aceita a sintaxe de máscara estilo hashcat:

```
?l = minúscula    ?u = maiúscula
?d = dígito       ?s = especial
?a = tudo         A  = literal 'A'
```

**O que você aprenderá:** O enorme ganho de eficiência de espaços de busca restritos. `?u?l?l?l?d?d?d?d` são 26*26*26*26*10*10*10*10 = 4,5 bilhões de candidatos. O brute force total de 8 caracteres do mesmo conjunto é de 218 trilhões. Isso é uma redução de 48.000x.

**Dicas:**

- Analise a máscara em um vector de conjuntos de caracteres, um por posição
- O cálculo do keyspace torna-se o `produto do tamanho do charset de cada posição`
- O particionamento funciona da mesma forma que o brute force (índice plano, decomposição de base mista)

## Desafios Avançados

### 7. Gerador e Consulta de Rainbow Table

Rainbow Tables são cadeias de hash pré-computadas que trocam espaço em disco por tempo de quebra. Em vez de fazer o hash de cada candidato em tempo de execução, você constrói uma tabela offline e faz uma consulta.

**O que construir:** Dois modos: `--generate-table` cria um arquivo de rainbow table para um determinado charset e comprimento, e `--rainbow` quebra usando uma tabela pré-computada.

**O que você aprenderá:** O tradeoff tempo-memória em criptoanálise, funções de redução, construção de cadeias e por que os salts tornam as rainbow tables inúteis. Este é um dos ataques mais elegantes em toda a segurança de computadores.

**Dicas:**

- Uma rainbow table não armazena cada hash. Ela armazena cadeias: pontos iniciais e pontos finais. Cada cadeia cobre milhares de hashes
- A função de redução converte um hash de volta em um candidato (não é o inverso do hash, apenas um mapeamento determinístico)
- O comprimento da cadeia controla o tradeoff: cadeias mais longas = tabela menor, mas consulta mais lenta
- Comece com um exemplo pequeno (4 caracteres minúsculos) para verificar a correção antes de escalar
- O artigo original de Martin Hellman de 1980 descreve o conceito. O artigo de Philippe Oechslin de 2003 introduz a melhoria "rainbow"

### 8. Quebra Acelerada por GPU com CUDA

A opção nuclear. Mover o loop de hash-e-comparação para a GPU.

**O que construir:** Um kernel CUDA que faz o hash de candidatos em paralelo na GPU. A CPU gera os candidatos e faz o upload de lotes; a GPU faz o hash de milhares simultaneamente.

**O que você aprenderá:** Programação de GPU, design de kernel CUDA, gerenciamento de memória host-device e por que as GPUs são muito mais rápidas em computação paralela (milhares de núcleos simples vs alguns núcleos complexos).

**Dicas:**

- Você não pode usar OpenSSL na GPU. Implemente o SHA256 em CUDA puro (o algoritmo é público, cerca de 100 linhas de código de kernel)
- Faça o upload de candidatos em lotes (ex: 1 milhão por vez) para amortizar o custo de transferência host-to-device
- Use `cudaMemcpyAsync` com streams para sobrepor computação e transferência
- Comece apenas com SHA256. Fazer um algoritmo funcionar na GPU é uma conquista significativa
- Isso poderia ser seu próprio projeto avançado independente no repositório

## Desafio Especialista

### 9. Quebra Distribuída pela Rede

Dividir o keyspace entre múltiplas máquinas. Um coordenador atribui intervalos de trabalho; os workers fazem o hash e reportam de volta.

**O que construir:** Um coordenador que aceita conexões de nós workers, atribui intervalos de keyspace, coleta resultados e lida com falhas de workers (reatribuindo seu intervalo para outro worker).

**O que você aprenderá:** Fundamentos de sistemas distribuídos: distribuição de trabalho, heartbeating, tolerância a falhas e o padrão coordenador. Esta é a mesma arquitetura que operações de quebra de senha em larga escala utilizam.

**Dicas:**

- Use sockets TCP ou gRPC para comunicação
- O coordenador divide o keyspace total em pedaços e os atribui sob demanda
- Os workers enviam heartbeats periódicos com seu progresso. Se um worker silenciar, o coordenador reatribui seu pedaço
- Pense no que acontece se dois workers alegarem quebrar o mesmo hash (o coordenador deve lidar com resultados duplicados de forma graciosa)
- Isso combina bem com o Desafio 8 (cada worker poderia ser acelerado por GPU)

## Desafios de Desempenho

### 10. Suíte de Benchmark

Quão rápida é a ferramenta na realidade? Compare diferentes algoritmos de hash, configurações de threading e modos de ataque.

**O que construir:** Um modo de benchmark (`--benchmark`) que executa testes padronizados e relata os resultados:

```
SHA256 dictionary (10K words):  2.4M h/s
SHA256 brute force (6 chars):   2.1M h/s
MD5 dictionary (10K words):     3.8M h/s
SHA512 dictionary (10K words):  1.9M h/s
Threads: 1=600K  2=1.2M  4=2.3M  8=2.4M
```

**O que você aprenderá:** Metodologia de microbenchmarking, por que os resultados variam entre as execuções e onde estão os gargalos reais (dica: é o OpenSSL, não o seu código).

**Dicas:**

- Use `std::chrono::steady_clock` para temporização
- Execute cada benchmark múltiplas vezes e relate a mediana, não a média
- Fixe as threads em núcleos específicos com `pthread_setaffinity_np` para resultados consistentes
- Compare seus números com os benchmarks do hashcat para ver a diferença entre CPU e GPU

## Obtendo Ajuda

Se você ficar travado em qualquer desafio:

1. Leia o código-fonte relevante. A arquitetura foi projetada para que cada componente seja compreensível isoladamente
2. Escreva um teste que falhe primeiro. Se você conseguir descrever o comportamento esperado em um teste, a implementação ficará mais clara
3. Comece pequeno. Faça a versão mais simples possível funcionar, depois adicione complexidade
4. Verifique a documentação do hashcat para precedentes do mundo real. A maioria desses desafios são versões simplificadas de recursos que ferramentas de quebra de produção já implementam
