# http-headers-scanner

Uma pequena ferramenta de linha de comando que visita um site, solicita as "regras" que o site informa ao seu navegador para seguir e atribui ao site uma nota de A a F com base na qualidade dessas regras.

## Por que alguém construiu isso

Toda vez que você visita um site, seu navegador e o servidor do site têm uma breve conversa. O navegador pede "me envie a página" e o servidor responde com duas coisas:

1. A própria página (HTML, imagens, scripts).
2. Uma pequena lista de **regras** sobre como essa página deve ser tratada.

É essa segunda lista que nos interessa aqui. Ela é chamada de **response headers**. Alguns desses headers estão relacionados à segurança. Eles informam ao navegador coisas como:

- "A partir de agora, fale comigo apenas via HTTPS. Nunca por HTTP puro."
- "Não permita que outro site me coloque dentro de um `<iframe>`."
- "Se você receber um arquivo meu e não tiver certeza do tipo dele, não tente adivinhar. Trate-o de forma estrita."
- "Bloqueie scripts, a menos que eles venham exatamente desta lista de locais confiáveis."

Se um site esquecer de enviar esses headers, ataques reais se tornam mais fáceis. Alguns exemplos que realmente aconteceram com empresas reais:

- **Clickjacking.** Sem `X-Frame-Options`, um atacante pode carregar o site da vítima dentro de um iframe oculto em uma página maliciosa, fazer você acreditar que está clicando em um botão da página maliciosa, quando, na verdade, o clique acontece no site da vítima. Isso foi utilizado contra Twitter, Facebook e as configurações do Adobe Flash entre 2008 e 2012.
- **SSL stripping.** Sem `Strict-Transport-Security`, um atacante conectado à mesma rede Wi-Fi pública pode rebaixar sua primeira visita para HTTP puro, posicionar-se no meio da comunicação e ler ou alterar tudo o que você enviar. Moxie Marlinspike demonstrou isso na Black Hat 2009, e o ataque continua eficaz contra qualquer site que esqueça de utilizar HSTS.
- **MIME sniffing.** Sem `X-Content-Type-Options: nosniff`, um navegador pode tratar um arquivo enviado como algo diferente do que ele realmente é (por exemplo, uma "imagem" que o navegador decide interpretar como HTML e executar como script). Esse foi um ataque real contra versões antigas do Internet Explorer, que acontecia porque o navegador tentava ser "prestativo".

Este scanner **NÃO** corrige nenhum desses problemas. Ele apenas informa se um site está sem os headers que os teriam evitado. Esse é o primeiro trabalho útil em segurança: saber o que está errado antes de tentar corrigir.

## O que você aprenderá ao construí-lo

Este não é um tutorial que ensina Python desde a primeira linha. Ele pressupõe que você consiga instalar algo no computador e executar um comando no terminal. A partir daí, explicaremos todo o restante.

Depois de concluir este projeto, você deverá compreender:

**Conceitos de segurança**

- O que são headers HTTP e por que alguns deles são importantes para a segurança
- Os ataques específicos que cada principal header de segurança previne (clickjacking, MIME sniffing, mixed content, XSS, vazamento de referer)
- Como uma "rubrica de avaliação" permite transformar diversas pequenas verificações em uma única pontuação final, exatamente como fazem scanners reais, como Mozilla Observatory e securityheaders.com

**Conceitos de Python**

- Como fazer uma requisição HTTP em código usando `httpx`
- Como `dataclasses` fornecem pequenas "estruturas" de dados sem precisar escrever construtores manualmente
- Como type hints com `Literal` restringem um valor a um pequeno conjunto fixo de strings, fazendo com que erros de digitação sejam detectados cedo
- Como separar "código que faz I/O" (comunica-se com a rede) de "código que é apenas matemática", permitindo testar a lógica sem tocar na rede
- Como o `pytest` executa testes, o que é uma fixture e como o `respx` permite simular respostas HTTP

**Ferramentas de linha de comando**

- Como o `argparse` interpreta flags como `--timeout 5` e as transforma em um objeto organizado
- Como códigos de saída (o número retornado por um programa ao terminar) podem comunicar sucesso ou falha para outros programas e sistemas de CI
- Como o `rich` desenha tabelas e painéis coloridos no terminal

## Como fica quando você o executa

```bash
$ just run -- https://github.com
```

Você verá algo semelhante a isto (as cores aparecem no terminal):

```
                  Headers for https://github.com/ (HTTP 200)
┌─────────────────────────────┬─────────┬──────────┬─────────────────────────┐
│ header                      │ status  │ severity │ note                    │
├─────────────────────────────┼─────────┼──────────┼─────────────────────────┤
│ Strict-Transport-Security   │ ok      │ high     │ Present and contains... │
│ Content-Security-Policy     │ ok      │ high     │ Present                 │
│ X-Content-Type-Options      │ ok      │ medium   │ Present and contains... │
│ X-Frame-Options             │ ok      │ medium   │ Present                 │
│ Referrer-Policy             │ ok      │ low      │ Present                 │
│ Permissions-Policy          │ missing │ low      │ Header ... is not set   │
└─────────────────────────────┴─────────┴──────────┴─────────────────────────┘
╭─ Result ───────────────────╮
│ Grade: A                   │
│ Score: 95 / 100            │
╰────────────────────────────╯

Recommendations:
  • Permissions-Policy — Add: Permissions-Policy: camera=(), microphone=(), geolocation=()
```

Os principais pontos são:

- Uma linha verde significa "este header está configurado e é útil".
- Uma linha amarela significa "este header existe, mas seu valor está incorreto" (por exemplo, `Strict-Transport-Security` foi enviado com `max-age=0`, o que o desativa ativamente).
- Uma linha vermelha significa "este header está completamente ausente".
- O painel com a nota resume tudo em uma única letra para que você possa verificar rapidamente se o site possui o básico de segurança em ordem.

## Para quem é este projeto

Você pode ser completamente iniciante tanto em Python quanto em segurança. Basta já saber:

- Como abrir um terminal no seu computador.
- Como clonar um repositório Git (ou baixar uma pasta de arquivos).
- Como ler textos e não entrar em pânico quando algo não funcionar na primeira tentativa.

Você **NÃO** precisa saber antecipadamente:

- O que é HTTP. Nós explicaremos.
- O que é uma dataclass. Nós explicaremos.
- O que é pytest, mocking ou argparse. Tudo será explicado.

## Pré-requisitos em termos práticos

**Softwares que você precisa ter instalados no computador.** Os três são gratuitos.

- **Python 3.13 ou superior.** Python é a linguagem em que este projeto foi escrito. A versão 3.13 introduziu parte da sintaxe utilizada aqui. Se você tiver uma versão mais antiga (3.10, 3.11 ou 3.12), receberá erros. Verifique com `python3 --version`.
- **Um terminal.** macOS e Linux já possuem um integrado (Terminal.app ou qualquer um dos diversos terminais disponíveis no Linux). Usuários do Windows devem instalar o Windows Terminal pela Microsoft Store ou utilizar o terminal integrado do VS Code.
- **Uma conexão ativa com a internet.** O scanner faz uma requisição HTTPS real para qualquer URL que você fornecer.

O script de instalação (`install.sh`) configurará automaticamente todo o restante: `uv` (gerenciador de pacotes Python), `just` (executor de comandos), um ambiente virtual e todas as bibliotecas utilizadas neste projeto.

## Início rápido

Na pasta do projeto:

```bash
# Instalação em uma única etapa. Configura as ferramentas Python e instala as dependências.
sudo apt update
wget -qO- https://astral.sh/uv/install.sh | sh
uv venv --python 3.14
source .venv/bin/activate
./install.sh

# Escaneia um site real.
just run -- https://example.com

# Define um timeout personalizado caso o site demore para responder.
just run -- https://github.com --timeout 5

# Executa os testes para confirmar que o código funciona na sua máquina.
just test
```

Se `./install.sh` retornar o erro "permission denied", execute primeiro `chmod +x install.sh` para marcar o arquivo como executável e tente novamente.

## Estrutura do projeto

Todo o projeto é propositalmente pequeno. Apenas dois arquivos Python, além das ferramentas auxiliares.

```
http-headers-scanner/
├── http_headers_scanner.py        o scanner propriamente dito: regras, pontuação e CLI
├── test_http_headers_scanner.py   testes do scanner
├── pyproject.toml                 metadados do projeto + lista de dependências
├── uv.lock                        versões exatas de todas as dependências
├── justfile                       comandos de atalho (just test, just run etc.)
├── install.sh                     instalador em uma única etapa
├── README.md                      breve README para a página do GitHub
├── assets/                        gif, imagens e capturas de tela
└── learn/                         esta pasta que você está lendo
    ├── 00-Introdução.md           você está aqui
    ├── 01-Conceitos.md            o que é HTTP, o que cada header faz, ataques reais
    ├── 02-Arquitetura.md          como o código está organizado e por quê
    ├── 03-Implementação.md        explicação linha por linha do código
    └── 04-Desafios.md             ideias de extensões para tornar o projeto seu
```

Tudo o que importa está concentrado em **um único arquivo Python** (`http_headers_scanner.py`).

## Problemas comuns na primeira execução

**`python3: command not found`**

Provavelmente você tem o Python instalado com outro nome. Tente `python --version`. Se ele mostrar a versão 3.13 ou superior, edite o `install.sh` e substitua `python3` por `python`. Se nenhum dos dois funcionar, instale o Python em python.org (ou execute `brew install python@3.13` no macOS ou `sudo apt install python3.13` no Debian/Ubuntu).

**`./install.sh: Permission denied`**

O arquivo não está marcado como executável. Execute `chmod +x install.sh` e tente novamente.

**`just: command not found` após a instalação**

O script instala o `just` em `~/.local/bin`. Essa pasta pode não estar no seu `PATH` em um terminal recém-aberto. Reinicie o terminal ou execute `export PATH="$HOME/.local/bin:$PATH"`. Para tornar isso permanente, adicione essa linha ao `~/.bashrc` ou `~/.zshrc`.

**Erros de rede ao escanear uma URL real**

Se você estiver atrás de um firewall corporativo ou conectado a uma VPN, alguns sites podem se recusar a responder ou bloquear o User-Agent padrão do scanner. Isso não é um bug do código; é apenas o mundo sendo inconveniente. Tente primeiro uma URL como `https://example.com` para confirmar que a infraestrutura básica está funcionando.

## Para onde ir em seguida

1. **[01-Conceitos.md](./01-Conceitos.md)** explica HTTP desde o início, o que cada header realmente faz e os ataques do mundo real que eles previnem. Leia este arquivo antes de estudar o código. O código faz muito mais sentido depois que você entende o que esses headers protegem.
2. **[02-Arquitetura.md](./02-Arquitetura.md)** explica como o código foi dividido em partes e por quê. É útil quando você quiser estender o scanner sem transformá-lo em uma bagunça.
3. **[03-Implementação.md](./03-Implementação.md)** percorre o código linha por linha. Este é o maior dos cinco arquivos.
4. **[04-Desafios.md](./04-Desafios.md)** é para depois que você tiver lido tudo e quiser ideias para expandir o projeto.
