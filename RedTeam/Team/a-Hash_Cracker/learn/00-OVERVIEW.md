# Ferramenta CLI Hash Cracker

## O Que É Isso

Uma ferramenta de linha de comando multi-threaded que recupera senhas em texto simples a partir de hashes criptográficos. Ela suporta MD5, SHA1, SHA256 e SHA512 usando três estratégias de ataque: dictionary attacks a partir de wordlists, brute force com geração de todas as combinações possíveis e mutações baseadas em regras que transformam palavras de dicionários em variações comuns de senhas, como `P@ssw0rd123`.

## Por Que Isso Importa

Quando atacantes invadem um banco de dados, eles não obtêm senhas em texto simples. Eles obtêm hashes. A segurança de cada usuário nesse banco de dados depende de quão resistentes esses hashes são à quebra (cracking). Construir um cracker ensina exatamente por que hashes rápidos sem salt, como MD5, são catastróficos para o armazenamento de senhas, e por que sistemas modernos usam bcrypt ou argon2.

**Cenários do mundo real onde isso se aplica:**

- Penetration testers usam ferramentas como hashcat e john the ripper para auditar a força das senhas após obterem acesso a hash dumps.
- A invasão do LinkedIn em 2012 vazou 6,5 milhões de hashes SHA1 sem salt. Pesquisadores quebraram 90% em 72 horas.
- A invasão da Adobe em 2013 expôs 153 milhões de contas usando criptografia 3DES (nem sequer era hashing) sem salts únicos. O mesmo blob criptografado aparecia milhões de vezes porque senhas idênticas produziam ciphertexts idênticos.

## O Que Você Aprenderá

**Conceitos de Segurança:**

- Funções de hash criptográfico: transformações unidirecionais que não podem ser revertidas.
- Dictionary attacks: aproveitando listas de senhas conhecidas de vazamentos reais.
- Ataques de brute force: busca exaustiva através de todas as combinações de caracteres possíveis.
- Mutações baseadas em regras: por que `Password123!` não é uma senha forte.
- Salting: o que ele previne (rainbow tables) e o que ele não previne (cracking direcionado).

**Habilidades Técnicas:**

- Design de templates baseado em políticas em C++23 com restrições de conceitos (concepts).
- `std::expected` para tratamento de erros combinável sem exceções.
- `std::generator` para avaliação preguiçosa (lazy evaluation) com coroutines.
- E/S de arquivo mapeada em memória com mmap para leitura de wordlist com zero-copy.
- Particionamento de trabalho multi-threaded com `std::jthread` e atomics.
- OpenSSL EVP API para computação de hash.

**Ferramentas e Técnicas:**

- CMake com presets para builds reproduzíveis.
- GoogleTest para testes unitários e de integração.
- OpenSSL para funções de hash criptográfico.
- Boost.program_options para parsing de argumentos CLI.

## Pré-requisitos

**Conhecimento necessário:**

- C++ básico: classes, templates, lambdas, move semantics.
- Compreensão do que uma função de hash faz (a entrada entra, uma saída de comprimento fixo sai, e você não pode revertê-la).
- Familiaridade com linha de comando.

**Ferramentas necessárias:**

- GCC 14 ou superior (suporte a C++23 necessário).
- CMake 3.25+.
- Sistema de build Ninja.
- Headers de desenvolvimento do OpenSSL.
- Boost.program_options.

**Útil, mas não obrigatório:**

- Experiência com templates e concepts.
- Familiaridade com threading e atomics.
- Compreensão de E/S mapeada em memória (memory-mapped I/O).

## Início Rápido

```bash
cd RedTeam/Team/a-HashCracker/

./install.sh

hashcracker --hash 5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8 \
  --wordlist wordlists/10k-most-common.txt
```

Saída esperada: A ferramenta detecta automaticamente o hash como SHA256, pesquisa no dicionário de 10.000 palavras e encontra a senha `password` em menos de um segundo. Se o seu terminal suportar, você verá uma barra de progresso com velocidade e ETA enquanto ela é executada.

Tente brute force:

```bash
hashcracker --hash 187ef4436122d1cc2f40dc2b92f0eba0 \
  --bruteforce --charset lower --max-length 4 --type md5
```

Saída esperada: Gera todas as combinações de letras minúsculas de até 4 caracteres, encontra `ab` após pesquisar cerca de 350.000 candidatos.

## Estrutura do Projeto

```
hash-cracker/
├── main.cpp                     Parsing de CLI e despacho
├── src/
│   ├── config/Config.hpp        Constantes, conjuntos de caracteres, cores
│   ├── core/
│   │   ├── Concepts.hpp         Conceitos Hasher e AttackStrategy
│   │   └── Engine.hpp           Engine de template (hasher + ataque + threading)
│   ├── hash/
│   │   ├── EVPHasher.hpp        Template de hasher OpenSSL EVP unificado
│   │   ├── HashDetector.hpp     Detecção automática do tipo de hash pelo comprimento hex
│   │   ├── MD5Hasher.hpp        Alias de tipo para EVPHasher<EVP_md5, ...>
│   │   ├── SHA1Hasher.hpp       Alias de tipo para EVPHasher<EVP_sha1, ...>
│   │   ├── SHA256Hasher.hpp     Alias de tipo para EVPHasher<EVP_sha256, ...>
│   │   └── SHA512Hasher.hpp     Alias de tipo para EVPHasher<EVP_sha512, ...>
│   ├── attack/
│   │   ├── DictionaryAttack     Leitor de wordlist mmap com particionamento
│   │   ├── BruteForceAttack     Gerador de keyspace com particionamento
│   │   └── RuleAttack           Dicionário + regras de mutação
│   ├── rules/RuleSet            Transformações de mutação via std::generator
│   ├── io/MappedFile            Wrapper RAII para mmap
│   ├── threading/ThreadPool     Particionamento de trabalho std::jthread
│   └── display/Progress         Exibição de progresso no terminal
├── tests/                       Suíte GoogleTest (38 testes)
├── wordlists/                   Wordlist de 10k senhas comuns incluída
├── install.sh                   Configuração em um comando
├── Justfile                     Comandos de build/test/clean
└── CMakeLists.txt               Configuração do CMake
```

## Próximos Passos

1. **Entenda os conceitos** - Leia [01-CONCEPTS.md](./01-CONCEPTS.md) para aprender como a quebra de hash funciona e por que ela importa.
2. **Estude a arquitetura** - Leia [02-ARCHITECTURE.md](./02-ARCHITECTURE.md) para ver como concepts, templates e threading se encaixam.
3. **Percorra o código** - Leia [03-IMPLEMENTATION.md](./03-IMPLEMENTATION.md) para um passo a passo detalhado do código.
4. **Estenda o projeto** - Leia [04-CHALLENGES.md](./04-CHALLENGES.md) para adicionar aceleração por GPU, rainbow tables ou novos algoritmos.

## Problemas Comuns

**"File not found" ao usar uma wordlist**

```
Error: File not found
```

Solução: Os caminhos são relativos ao local onde você executa o comando. Execute a partir do diretório raiz do projeto ou use um caminho absoluto.

**Erro "Invalid hash format"**

```
Error: Invalid hash format
```

Solução: O detector automático valida se todos os caracteres são hexadecimais (0-9, a-f) e se o comprimento corresponde a um algoritmo conhecido (32=MD5, 40=SHA1, 64=SHA256, 128=SHA512). Verifique se há espaços em branco no final ou caracteres não hexadecimais.

**Brute force é lento em senhas longas**
Isso é esperado. O keyspace cresce exponencialmente. 6 caracteres minúsculos = 308 milhões de combinações. Adicione dígitos e serão 2,2 bilhões. Adicione letras maiúsculas e caracteres especiais e você terá horas ou dias de processamento. Este é o ponto central: senhas fortes resistem ao brute force.
