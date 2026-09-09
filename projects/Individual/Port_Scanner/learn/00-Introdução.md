# Scanner de Portas Simples

## O Que É Isso

Um scanner de portas TCP concorrente escrito em C++ que sonda hosts de destino para identificar portas abertas, fechadas e filtradas. Ele utiliza E/S (I/O) assíncrona para escanear múltiplas portas simultaneamente e tenta capturar banners de serviço para fingerprinting.

## Por Que Isso Importa

O escaneamento de portas é o primeiro passo em quase toda avaliação de segurança de rede e teste de invasão (penetration test). Antes de poder explorar um sistema, você precisa saber o que está escutando. Esta ferramenta ensina como os atacantes enumeram serviços de rede e como os defensores podem detectar tal reconhecimento.

**Cenários do mundo real onde isso se aplica:**

- **Reconhecimento inicial de teste de invasão (penetration testing)** - Todo pentest começa com escaneamentos de portas para mapear a superfície de ataque. Ferramentas como o Nmap são padrão, mas entender como elas funcionam internamente torna você um testador melhor.

- **Preparação para auditoria de segurança** - Antes de uma auditoria de conformidade (PCI-DSS, SOC 2), você precisa verificar quais portas estão expostas. Portas abertas inesperadas frequentemente indicam shadow IT ou configurações incorretas que causam falhas em auditorias.

- **Resposta a incidentes e threat hunting** - Ao investigar uma violação, você escaneia redes internas para encontrar backdoors, canais de C2 ou artefatos de movimentação lateral. Atacantes frequentemente abrem portas não padronizadas para persistência.

## O Que Você Aprenderá

Este projeto ensina como o reconhecimento de rede funciona na camada TCP. Ao construí-lo você mesmo, você entenderá:

**Conceitos de Segurança:**

- **Estados de porta e seus significados** - A diferença entre portas abertas, fechadas e filtradas informa tanto sobre o serviço quanto sobre o firewall. Aberta significa que um serviço está escutando, fechada significa que nada está lá mas o host respondeu, filtrada significa que um firewall descartou seus pacotes silenciosamente.

- **Mecânica de conexão TCP** - O escaneamento de portas explora o handshake de três vias (three-way handshake) do TCP. Entender pacotes SYN, SYN-ACK e RST é fundamental para a segurança de rede.

- **Banner grabbing para fingerprinting** - Serviços frequentemente se anunciam (strings de versão de SSH, cabeçalhos de servidor HTTP). Essas informações ajudam atacantes a selecionar exploits e ajudam defensores a identificar softwares desatualizados.

**Habilidades Técnicas:**

- **Programação de E/S (I/O) assíncrona** - Escanear dezenas de milhares de portas sequencialmente levaria horas. Este projeto usa operações assíncronas para sondar centenas de portas concorrentemente, completando escaneamentos completos em segundos.

- **Padrões de programação concorrente** - Gerenciar múltiplas operações assíncronas com estado compartilhado requer coordenação cuidadosa. Você usará strand executors e shared pointers para prevenir condições de corrida (race conditions).

- **Programação de sockets de rede** - Operações diretas de socket TCP ensinam o que acontece abaixo do HTTP e outros protocolos de aplicação. Este conhecimento de baixo nível é essencial para o trabalho de segurança de rede.

**Ferramentas e Técnicas:**

- **Boost.Asio para E/S de rede** - Biblioteca de E/S assíncrona padrão da indústria usada em sistemas de produção. Aprender Asio ensina padrões aplicáveis a qualquer aplicação de rede de alto desempenho.

- **Detecção de filtragem baseada em timeout** - Diferenciar entre portas fechadas (rejeição ativa) e portas filtradas (descarte silencioso) requer análise de tempo. Esta técnica se aplica a fingerprinting de firewall e evasão de IDS.

## Pré-requisitos

Antes de começar, você deve entender:

**Conhecimento necessário:**

- **Programação básica em C++** - Você precisa de familiaridade com classes, smart pointers (`std::shared_ptr`) e funções lambda. Este projeto usa recursos do C++20 como structured bindings.

- **Fundamentos de redes** - Saber o que é um endereço IP e um número de porta, entender a diferença entre TCP e UDP, e ter uma compreensão básica do handshake TCP (SYN, SYN-ACK, ACK).

- **Conforto com linha de comando** - Você compilará com CMake e executará o scanner a partir do terminal. Familiaridade básica com bash e sistemas de build ajuda.

**Ferramentas necessárias:**

- **CMake 3.31+** - Sistema de build para projetos C++. Instale via gerenciador de pacotes (`apt install cmake` no Ubuntu, `brew install cmake` no macOS).

- **Compilador C++20** - GCC 10+, Clang 12+, ou MSVC 2019+. O projeto utiliza recursos da biblioteca padrão do C++20.

- **Bibliotecas Boost** - Especificamente Boost.Asio para E/S assíncrona e Boost.Program_options para parsing de CLI. Instale com `apt install libboost-all-dev` ou `brew install boost`.

**Útil, mas não obrigatório:**

- **Wireshark ou tcpdump** - Ferramentas de captura de pacotes permitem que você veja os pacotes TCP reais que seu scanner envia. Observar pacotes SYN voando ajuda a entender o que está acontecendo no fio.

- **Familiaridade com Nmap** - Se você já usou o Nmap antes, reconhecerá conceitos como SYN scans e detecção de serviço. Este projeto implementa versões simplificadas dessas técnicas.

## Início Rápido

Coloque o projeto para rodar localmente:

```bash
# Clone e navegue
cd projects/Individual/Port_Scanner

# Crie o diretório de build
mkdir build && cd build

# Configure e compile
cmake ..
make

# Execute o scanner no localhost
./simplePortScanner -i 127.0.0.1 -p 1-1024

# Escaneie portas específicas com configurações personalizadas
./simplePortScanner -i scanme.nmap.org -p 80,443,8080 -t 50 -e 3
```

Saída esperada: Uma tabela mostrando o número da porta, estado (OPEN/CLOSED/FILTERED), nome do serviço se reconhecido e qualquer banner capturado do serviço. Portas abertas aparecem em verde, fechadas em vermelho.

## Estrutura do Projeto

```
simple-port-scanner/
├── src/
│   ├── PortScanner.hpp      # Definição da classe, variáveis de membro, assinaturas de métodos
│   └── PortScanner.cpp      # Lógica central de escaneamento, operações assíncronas, banner grabbing
├── main.cpp                 # Ponto de entrada, parsing de argumentos CLI com boost::program_options
└── CMakeLists.txt           # Configuração de build, dependências (Boost)
```

## Próximos Passos

1. **Entenda os conceitos** - Leia [01-Conceitos.md](./01-Conceitos.md) para aprender sobre estados de porta TCP, banner grabbing e técnicas de reconhecimento de rede.

2. **Estude a arquitetura** - Leia [02-Arquitetura.md](./02-Arquitetura.md) para ver como a E/S assíncrona e o escaneamento concorrente são projetados.

3. **Percorra o código** - Leia [03-Implementação.md](./03-Implementação.md) para uma explicação detalhada do algoritmo de escaneamento e padrões assíncronos.

4. **Estenda o projeto** - Leia [04-Desafios.md](./04-Desafios.md) para ideias como escaneamento UDP, fingerprinting de SO e técnicas furtivas (stealth).

## Problemas Comuns

**"boost/asio.hpp: No such file or directory"**

```
fatal error: boost/asio.hpp: No such file or directory
```

Solução: Instale as bibliotecas de desenvolvimento do Boost. No Ubuntu/Debian: `sudo apt install libboost-all-dev`. No macOS: `brew install boost`. No Windows, baixe de boost.org e configure o CMake com `-DBOOST_ROOT=C:\caminho\para\boost`.

**"Connection refused" em todas as portas**

```
1	CLOSED	---	---
22	CLOSED	SSH	---
80	CLOSED	HTTP	---
```

Solução: Isso é normal se estiver escaneando uma máquina sem serviços em execução. Tente escanear `scanme.nmap.org`, que possui portas abertas intencionais para testes, ou escaneie sua própria máquina após iniciar um servidor web (`python3 -m http.server 8000`).

**O scanner trava ou roda muito lentamente**
Solução: Seu firewall pode estar limitando sua taxa (rate-limiting). Reduza a contagem de threads (`-t 10` em vez do padrão 100) e aumente o timeout (`-e 5`). Além disso, certifique-se de que não está escaneando de uma rede que bloqueia conexões de saída.
