# Conceitos Fundamentais

Este arquivo explica as ideias de segurança sobre as quais o scanner foi construído. Ao final, você deverá saber o que é HTTP, o que é um cabeçalho (header), por que os seis cabeçalhos que verificamos existem e que tipo de ataque cada um deles impede.

Leia este arquivo antes do código. O código é curto; os conceitos por trás dele são o que demandam tempo.

## 1. O que o HTTP realmente é

Quando você digita `github.com` no seu navegador, algo precisa buscar a página. Esse "algo" fala um protocolo chamado **HTTP** (HyperText Transfer Protocol). HTTPS é o mesmo protocolo com criptografia em volta dele.

O formato básico de uma conversa HTTP é:

```
                       Requisição HTTP
   ┌─────────────┐ ───────────────────────▶ ┌─────────────┐
   │             │                          │             │
   │  Navegador  │                          │  Servidor   │
   │   (você)    │                          │  (github)   │
   │             │ ◀─────────────────────── │             │
   └─────────────┘       Resposta HTTP      └─────────────┘
```

Você (o navegador) envia uma **requisição**. O servidor envia de volta uma **resposta**. A requisição diz "Eu gostaria da página em /home/index.html, por favor." A resposta diz "Aqui está essa página. Além disso, aqui estão algumas informações sobre a página."

Tanto a requisição quanto a resposta são apenas **texto**, com um layout específico.

### Como é uma resposta real

Se você removesse a criptografia e observasse os bytes retornando de `https://example.com`, veria algo assim:

```html
HTTP/2 200 content-type: text/html; charset=UTF-8 content-length: 1256
strict-transport-security: max-age=31536000 x-frame-options: DENY cache-control:
max-age=600 date: Tue, 13 May 2026 12:00:00 GMT

<!doctype html>
<html>
  <head>
    <title>Example Domain</title>
  </head>
  <body>
    ...
  </body>
</html>
```

Três partes para observar:

1. **A linha de status.** `HTTP/2 200` significa "HTTP versão 2, código de status 200." 200 significa "OK, aqui está sua página." 404 significaria "Eu não tenho essa página." 500 significaria "Eu quebrei tentando criar essa página."
2. **Os cabeçalhos (headers).** Tudo entre a linha de status e a linha em branco. Cada cabeçalho é uma linha, no formato `nome: valor`. Pode haver dezenas deles.
3. **O corpo (body).** Tudo após a linha em branco. O HTML real, imagem, JSON ou qualquer outra coisa que o servidor esteja enviando para você.

Os **cabeçalhos** são o que este scanner se importa. Alguns cabeçalhos são sobre cache, tipo de conteúdo, cookies e assim por diante. Nós ignoramos esses. Seis cabeçalhos específicos existem para segurança, e é sobre eles que damos a nota.

### Por que os cabeçalhos são insensíveis a maiúsculas e minúsculas

Às vezes você verá `Strict-Transport-Security` e às vezes `strict-transport-security`. **Eles significam a mesma coisa.** A RFC 7230, a especificação oficial do HTTP, diz que os nomes dos cabeçalhos são insensíveis a maiúsculas e minúsculas (case insensitive). Diferentes servidores e proxies usam diferentes padrões. O scanner tem que lidar com todos eles, e é por isso que convertemos ambos os lados para minúsculas antes de comparar.

## 2. O que um cabeçalho de segurança realmente é

Um cabeçalho de segurança é apenas um cabeçalho HTTP comum com um nome que o navegador foi programado para reconhecer como uma instrução de segurança. Não há nada de mágico neles. O servidor envia `Strict-Transport-Security: max-age=31536000` e o navegador pensa "ah, o site está me dizendo para lembrar de usar apenas HTTPS para falar com ele pelos próximos 31.536.000 segundos (um ano)."

Se o servidor esquecer de enviar o cabeçalho, o navegador volta ao seu comportamento padrão, que geralmente é "faça qualquer coisa, sem proteções especiais." Esse padrão é o que os atacantes esperam.

Portanto, cabeçalhos de segurança são basicamente uma **promessa** que o site faz ao seu navegador. "Confie em mim, eu nunca sirvo conteúdo através de HTTP comum. Se você me vir em HTTP comum, alguém está mentindo para você, ignore-os."

## 3. Os seis cabeçalhos que avaliamos

O scanner verifica seis cabeçalhos. Cada um interrompe uma classe específica de ataque. Vamos passar por eles um por um.

### 3.1 Strict-Transport-Security (HSTS): severidade ALTA

**O que ele diz ao navegador**

"Pelos próximos N segundos, fale comigo apenas via HTTPS. Nunca via HTTP comum. Se alguém lhe entregar um link para `http://meu-site.com`, atualize-o para `https://` antes de fazer a requisição."

**O ataque que ele interrompe: SSL stripping**

Imagine que você está em uma cafeteria e digita `github.com` no seu navegador (sem o prefixo `https://`). Seu navegador, por padrão, tenta `http://github.com` primeiro. O servidor do GitHub então diz "na verdade, por favor, use HTTPS" e redireciona você. O navegador segue o redirecionamento, muda para HTTPS e agora tudo está criptografado.

No intervalo entre "você enviou uma requisição HTTP comum" e "o redirecionamento voltou", um atacante na mesma rede Wi-Fi (usando um notebook com `bettercap` ou `sslstrip`) pode interceptar tudo. Eles ficam no meio:

```
   ┌────────┐    HTTP comum    ┌──────────┐    HTTPS    ┌────────┐
   │  Você  │ ───────────────▶ │ Atacante │ ──────────▶ │ GitHub │
   └────────┘                  │  (MITM)  │             └────────┘
                               └──────────┘
```

O atacante continua falando com o GitHub via HTTPS real, mas fala com você via HTTP comum, e reescreve cada link `https://` na página de volta para `http://` para que você nunca escape. Você acha que o site parece normal. O atacante lê sua senha.

**Como o HSTS interrompe isso.** A primeira vez que você visita o GitHub com sucesso via HTTPS, seu navegador lembra do cabeçalho `Strict-Transport-Security`. Na próxima vez, mesmo que você digite `http://github.com`, o navegador se recusa a enviar uma requisição HTTP comum. Ele atualiza para `https://` localmente, antes que qualquer pacote saia da sua máquina. O truque de "interceptar a etapa de HTTP comum" do atacante para de funcionar.

**Como o valor se parece**

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

- `max-age=31536000`: lembre-se desta regra por 31.536.000 segundos (um ano).
- `includeSubDomains`: aplique a regra para `api.github.com`, `docs.github.com`, tudo que termine em `github.com`.

**Por que o scanner exige um `max-age` positivo.** Um servidor poderia enviar `Strict-Transport-Security:` sem valor, ou `Strict-Transport-Security: max-age=0`. Ambos são inúteis. `max-age=0` ativamente **desativa** o HSTS (ele diz ao navegador para esquecer qualquer regra HSTS anterior para este site). Portanto, a presença por si só não é suficiente. O scanner reporta `weak` sempre que o valor não corresponde ao padrão `max-age = <inteiro positivo>` — o que captura tanto o caso vazio quanto o caso deliberadamente zero.

**Exemplo real.** A demonstração do sslstrip de Moxie Marlinspike na Black Hat 2009 tornou este ataque famoso. Todos os grandes bancos passaram a impor apenas HTTPS após aquela palestra. Em 2026, quase todos os sites sérios enviam HSTS. Sites que não o fazem são geralmente sistemas internos antigos.

### 3.2 Content-Security-Policy (CSP): severidade ALTA

**O que ele diz ao navegador**

"Aqui está a lista exata de lugares de onde estou disposto a carregar scripts, estilos, imagens, fontes, frames e outros recursos. Se você vir algo na página pedindo para carregar de qualquer outro lugar, recuse."

**O ataque que ele interrompe: cross-site scripting (XSS)**

XSS é quando um atacante consegue injetar seu próprio JavaScript em uma página que outros usuários verão. Exemplo clássico:

```html
Caixa de comentário no site permite: Eu amo este produto! Atacante digita:
<script>
  steal_cookie();
</script>
O site exibe isso literalmente. Agora, cada usuário que carregar o comentário
executa o JS do atacante em sua sessão.
```

Esse JS é executado com a total confiança do site, portanto, pode ler cookies, ler o token de sessão da página, enviar requisições para a API como o usuário e assim por diante. Esta é a classe de bug número 7 no OWASP Top 10 há anos.

**Como o CSP interrompe isso.** O site diz ao navegador "scripts só podem vir de `https://meu-site.com` ou de `https://cdn.meu-site.com`." Quando o navegador vê `<script>steal_cookie()</script>` incorporado inline no HTML, ele pensa "esse script não vem de uma das origens permitidas, eu me recuso a executá-lo." O XSS injetado torna-se apenas texto inerte.

**Como o valor se parece**

```
Content-Security-Policy: default-src 'self'; script-src 'self' https://cdn.example.com
```

- `default-src 'self'`: para qualquer coisa não listada especificamente abaixo, permita apenas conteúdo deste site exato.
- `script-src 'self' https://cdn.example.com`: JavaScript pode vir deste site ou de cdn.example.com.

Um CSP real é muito mais longo porque sites reais utilizam fontes, analytics, embeds, etc. Um bom CSP **nunca** contém `'unsafe-inline'` para scripts (o que permitiria as tags `<script>` inline das quais um ataque XSS depende).

**Exemplo real.** O CSP do GitHub é um dos mais longos da indústria. Após o XSS no GitHub-Pages em 2018, eles o restringiram significativamente. Você mesmo pode ver: carregue github.com no seu navegador, abra as ferramentas de desenvolvedor (dev tools) e observe os cabeçalhos de resposta.

**Por que verificamos apenas a presença.** Analisar o CSP corretamente é difícil. O Mozilla Observatory faz uma análise muito mais profunda (verifica `unsafe-inline`, origens curinga, ausência de `default-src`, etc.). Nosso scanner apenas verifica se o cabeçalho está presente. Essa é a decisão correta para um projeto de fundamentos: mude para o Observatory quando desejar uma análise mais profunda.

### 3.3 X-Content-Type-Options: severidade MÉDIA

**O que ele diz ao navegador**

"Quando eu te envio um arquivo, estou te dizendo o tipo dele com o cabeçalho `Content-Type`. Acredite em mim. Não olhe para os bytes e decida por si mesmo."

**O ataque que ele interrompe: MIME sniffing**

Versões antigas do Internet Explorer tinham um recurso "útil": se um servidor dissesse que um arquivo era `text/plain`, mas o conteúdo parecesse HTML, o IE o trataria como HTML e o renderizaria. A intenção era ser tolerante com servidores mal configurados. O efeito foi uma enorme brecha de segurança.

Ataque: um site permite que os usuários enviem uma foto de perfil. O atacante envia um arquivo chamado `gatinho_fofo.gif` cujos primeiros bytes parecem um GIF válido, mas contém `<script>steal_everything()</script>` mais adiante. O servidor o armazena. O servidor mais tarde o serve de volta para outros usuários com `Content-Type: image/gif`. O IE olha para os bytes, vê a tag `<script>`, diz "isso na verdade é HTML" e executa o script. Agora o atacante tem XSS via upload de imagem.

**Como o cabeçalho interrompe isso.** `X-Content-Type-Options: nosniff` diz ao navegador "não tente adivinhar meu Content-Type." Se eu disser `image/gif`, você o trata como uma imagem, e ponto final. A tag de script nunca é executada.

**Como o valor se parece**

```
X-Content-Type-Options: nosniff
```

Esse é literalmente o único valor permitido. O cabeçalho é o mais monótono dos seis porque existe apenas uma configuração correta e pronto.

**Por que o scanner exige `nosniff`.** Alguns servidores mal configurados enviam `X-Content-Type-Options: off` ou outro lixo. O cabeçalho tem que conter literalmente a string `nosniff` para ser útil. Se não contiver, reportamos `weak`.

**Exemplo real.** A maioria das vulnerabilidades de MIME sniffing ocorreu no IE 6 ao 9. Navegadores modernos adotam o comportamento nosniff por padrão para recursos de `script` e `style`, independentemente do cabeçalho. O cabeçalho ainda importa para navegadores mais antigos e para contextos que não sejam de script.

### 3.4 X-Frame-Options: severidade MÉDIA

**O que ele diz ao navegador**

"Não deixe que outros sites me coloquem dentro de um `<iframe>` em suas páginas."

**O ataque que ele interrompe: clickjacking**

Imagine que o atacante cria uma página da web que diz:

```
   ┌────────────────────────────────────────┐
   │  Ganhe um iPhone grátis! Clique aqui!  │
   │                                        │
   │   ┌──────────────────────────┐         │
   │   │ [iframe INVISÍVEL com    │         │
   │   │  github.com carregado    │         │
   │   │  dentro dele, posicionado│         │
   │   │  para que o botão        │         │
   │   │  "Delete repo" fique     │         │
   │   │  exatamente sobre o      │         │
   │   │  botão "Clique aqui"]    │         │
   │   └──────────────────────────┘         │
   └────────────────────────────────────────┘
```

Você está logado no GitHub em outra aba. Você vê a página do "iPhone grátis" no site do atacante. Você clica. O clique não atinge o botão visível "Clique aqui". Ele passa pelo iframe transparente e atinge o botão "Delete repo" do GitHub. Seu cookie de sessão viaja com o clique. O GitHub pensa que você quis deletar o repositório, então ele o deleta.

Isso é **clickjacking**. O CSS para configurar a sobreposição é trivial. A única coisa que impede isso de funcionar em cada sessão de login em todos os lugares é o site da vítima se recusar a ser enquadrado (framed).

**Como o cabeçalho interrompe isso.** `X-Frame-Options: DENY` diz ao navegador "se você me vir sendo carregado dentro de um iframe em qualquer outra página, recuse-se a me renderizar." O iframe de clickjacking permanece em branco. O clique não vai para lugar nenhum prejudicial.

**Como o valor se parece**

```
X-Frame-Options: DENY            # nunca permite enquadramento, jamais
X-Frame-Options: SAMEORIGIN      # permite enquadramento apenas por páginas no mesmo domínio
```

`X-Frame-Options` é a maneira antiga. A maneira moderna é a diretiva `frame-ancestors` dentro do `Content-Security-Policy`. A maioria dos sites reais envia ambos por motivos de compatibilidade de navegador. O scanner verifica apenas o `X-Frame-Options` para manter as coisas simples.

**Exemplo real.** A página de configurações do Adobe Flash em 2008 era passível de clickjacking. O botão "Seguir este usuário" do Twitter sofreu clickjacking em ataques de "Re-tweetar qualquer coisa" em 2009. O Facebook teve um worm de clickjacking em 2010 que se espalhou via "curtidas" em páginas manipuladas. O padrão é o mesmo todas as vezes.

### 3.5 Referrer-Policy: severidade BAIXA

**O que ele diz ao navegador**

"Quando você sair da minha página para ir para outro site, não diga a esse outro site exatamente de qual página você veio."

**O vazamento que ele interrompe: referer leakage**

Navegadores, por padrão, enviam um cabeçalho `Referer` com cada requisição de saída que diz "o usuário chegou aqui a partir desta URL." Sim, a grafia é `Referer` com apenas um R. Isso foi um erro de digitação na especificação original do HTTP de 1996 e estamos presos a isso para sempre. Hilário.

Por que isso importa. Suponha que seu site tenha URLs como:

```
https://meu-site.com/password-reset?token=abc123xyz
```

Um usuário chega nessa página, clica em um link externo (digamos, para um vídeo de ajuda no YouTube). O navegador dele diz ao YouTube "este usuário veio de `https://meu-site.com/password-reset?token=abc123xyz`." O YouTube agora tem o token de redefinição de senha do usuário em seus logs de acesso. Qualquer pessoa com acesso aos logs no YouTube também o tem.

Isso aconteceu na vida real muitas vezes. O padrão: tokens secretos em URLs vazam via cabeçalho Referer para cada recurso de terceiros que a página carrega.

**Como o cabeçalho interrompe isso.** `Referrer-Policy: strict-origin-when-cross-origin` é um padrão sensato. Ele diz "quando o usuário for para outro site, diga a esse site apenas minha origem (`https://meu-site.com`), nunca a URL completa com parâmetros de consulta. Esconda o caminho e a query string."

**Como o valor se parece**

```
Referrer-Policy: strict-origin-when-cross-origin
Referrer-Policy: no-referrer                       # mais paranoico
Referrer-Policy: same-origin                       # seguro para links de saída
```

**Por que a severidade é BAIXA.** O vazamento de referer é real e ruim, mas depende do site colocar segredos em URLs em primeiro lugar, o que é um erro separado. O cabeçalho é uma defesa útil de "cinto e suspensórios", mas a ausência dele não é uma perda garantida.

### 3.6 Permissions-Policy: severidade BAIXA

**O que ele diz ao navegador**

"Esta página não usa a câmera. Não deixe nenhum código nesta página, incluindo scripts de terceiros incorporados, pedir ao usuário acesso à câmera."

Você pode fazer isso para câmera, microfone, geolocalização, dispositivos USB, APIs de pagamento, acelerômetro e uma longa lista de outros recursos do navegador.

**O ataque que ele interrompe: abuso de recursos através de terceiros comprometidos**

Imagine que seu site incorpora um script de analytics de um terceiro. Esse terceiro é hackeado. O atacante lança uma atualização maliciosa para o script de analytics. Agora, cada página do seu site que inclui o script está executando o código do atacante com acesso a tudo o que o navegador permitir. Se o atacante escrever `navigator.mediaDevices.getUserMedia({ audio: true })`, o usuário recebe um aviso "este site deseja usar seu microfone". Muitos usuários clicarão em sim porque confiam no seu site.

**Como o cabeçalho interrompe isso.** `Permissions-Policy: camera=(), microphone=()` diz ao navegador "nenhum código nesta página pode solicitar câmera ou microfone, independentemente da fonte. Nem mostre o aviso." O script do atacante recebe uma resposta de negado e segue em frente.

**Como o valor se parece**

```
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
```

Os parênteses vazios significam "nenhuma origem tem permissão para usar este recurso." Você também pode permitir origens explicitamente em uma lista branca (allowlist), mas para a maioria dos sites a resposta correta para a maioria dos recursos é "ninguém."

**Por que a severidade é BAIXA.** Isso só importa se (a) seu site incorpora código de terceiros, E (b) esse terceiro for comprometido, E (c) o terceiro tentasse usar esses recursos. É genuinamente defesa em profundidade, mas está a vários passos de distância da superfície de ataque imediata.

## 4. A rubrica de pontuação

Portanto, temos seis cabeçalhos. Cada um tem uma severidade (alta, média, baixa) que mapeia para um valor de pontos:

```
alta   = 30 pontos cada
média  = 15 pontos cada
baixa  = 5 pontos cada
```

A tabela de regras atual tem 2 altas, 2 médias, 2 baixas. Total alcançável: `2*30 + 2*15 + 2*5 = 90` pontos. Espere, isso não soma 100? Correto. A matemática:

```
60 (duas altas)   + 30 (duas médias) + 10 (duas baixas) = 100 pontos
```

Eu contei errado. Deixe-me refazer: alta=30, duas altas é 60. Média=15, duas médias é 30. Baixa=5, duas baixas é 10. Total: 60+30+10 = **100**.

Para cada cabeçalho, o scanner produz um resultado (finding):

- `ok` → ganha o valor total de pontos para aquela regra
- `weak` → ganha metade dos pontos (o cabeçalho está presente, mas o valor está incorreto)
- `missing` → ganha zero

Então:

```
pontuação = arredondar( (pontos ganhos / total de pontos) * 100 )
```

A pontuação torna-se uma nota por um corte padrão de nota por letra:

```
pontuação >= 90 → A
pontuação >= 80 → B
pontuação >= 70 → C
pontuação >= 60 → D
caso contrário   → F
```

Isso reflete como o Mozilla Observatory e o securityheaders.com funcionam. Eles usam valores de pontos exatos diferentes e verificam mais cabeçalhos, mas o formato é o mesmo: resultados ponderados, pontuação percentual, nota por letra.

## 5. O que este scanner NÃO faz

Ser claro sobre o escopo é importante. Este é um projeto de fundamentos. Ele **não** é:

- **Um crawler.** Ele varre exatamente a URL que você fornecer. Uma requisição. Ele não segue links dentro da página e avalia cada subpágina.
- **Um analisador de CSP.** Nós apenas verificamos se o `Content-Security-Policy` existe. Não olhamos dentro do valor para `unsafe-inline`, fontes curinga, ausência de `default-src`, etc.
- **Um scanner de vulnerabilidades.** Ele não tenta encontrar injeção de SQL, XSS, redirecionamentos abertos ou qualquer falha explorável real. Ele apenas relata configurações defensivas ausentes.
- **Uma autoridade.** Sites reais às vezes removem intencionalmente certos cabeçalhos porque eles quebram um recurso de que precisam. Um cabeçalho ausente é um sinal que vale a pena investigar, não um veredito automático.

Quando você quiser uma visão mais completa, mude para:

- **Mozilla Observatory** (`observatory.mozilla.org`): faz tudo o que fazemos, além de análise profunda de CSP, verificações de cookies e avaliação de configuração de TLS.
- **securityheaders.com**: ideia semelhante, interface mais simples.
- **`nmap` com o script http-security-headers**: para entusiastas de linha de comando.

## 6. Referências da indústria

Se você quiser pesquisar isso por conta própria em documentos oficiais:

- **MDN** (developer.mozilla.org) possui artigos autoritativos sobre cada cabeçalho. Procure pelo nome do cabeçalho mais "MDN".
- **OWASP Secure Headers Project** (owasp.org/www-project-secure-headers) tem a lista canônica e os valores recomendados.
- **RFC 6797** é a especificação para HSTS. RFC 7034 é a especificação para X-Frame-Options. Ler especificações é uma habilidade útil, mesmo quando a especificação é monótona.
- **CWE-693** "Protection Mechanism Failure" é o ID de fraqueza comum para cabeçalhos defensivos ausentes ou mal configurados.

## 7. Verificação rápida

Você deve ser capaz de responder a estas perguntas antes de passar para a arquitetura:

1. Qual é a diferença entre uma requisição HTTP e uma resposta HTTP?
2. Onde os cabeçalhos ficam em uma resposta (em relação à linha de status e ao corpo)?
3. Qual cabeçalho teria evitado o SSL stripping na cafeteria?
4. Qual cabeçalho teria evitado o ataque de "deletar repositório" no estilo clickjacking?
5. Por que o scanner reporta `weak` em vez de `ok` quando o `X-Content-Type-Options` está presente, mas seu valor não é literalmente `nosniff`?
6. Contra que tipo de ataque o CSP defende e por que ele não analisa o valor do CSP profundamente?
7. Qual é a nota para um site com pontuação 75? E 60? E 59?

Se alguma destas parecer confusa, releia a seção relevante. A implementação nos próximos dois arquivos fará muito mais sentido quando estes pontos estiverem sólidos.

## Próximo

Siga para **[02-Arquitetura.md](./02-Arquitetura.md)** para ver como o scanner está organizado no código, ou pule direto para **[03-Implementação.md](./03-Implementação.md)** para o passo a passo linha por linha.
