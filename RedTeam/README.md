# 🔴 Red Team — 1º Semestre

> [!NOTE]
> Esta frente reúne os projetos ofensivos do Insper Sec para o **1º semestre**.

O Red Team olha para sistemas pela perspectiva de quem quer entender como eles podem ser observados, mapeados, testados e, em contexto autorizado, quebrados.

A proposta aqui não é "hackear por hackear". É desenvolver base técnica sólida em áreas que aparecem o tempo todo em segurança real: hashes, aplicações web, redes, credenciais e segredos. Cada trilha começa com um projeto individual, mais focado em fundamentos, e evolui para um projeto em equipe, mais completo e mais próximo de uma ferramenta ou fluxo real.

A lógica geral é simples:

- o projeto **Individual** introduz a base técnica da trilha e representa a **entrega intermediária** do semestre;
- o projeto **Team** amplia essa base, exigindo mais integração, mais contexto e mais engenharia, e representa a **entrega final do semestre**, com apresentação à Insper Sec.

> [!IMPORTANT]
> As letras **A/B/C/D** nos nomes de pasta indicam **ramo temático** (domínio), **não** dificuldade. A dificuldade de cada projeto é sempre explícita e separada do tema, usando os **5 níveis (N1–N5)**.

---

## 📅 Calendário do Semestre

> [!NOTE]
> As datas abaixo são as **janelas de entrega** de cada projeto. Você **não é obrigado(a)** a avançar para o próximo projeto imediatamente — pode fazer múltiplos projetos primários em paralelo, desde que respeite as entregas.

| Projeto        | Modo       | Janela de entrega |
| -------------- | ---------- | ----------------- |
| `Hash_ID`      | Individual | 09 Set – 07 Out   |
| `Headers`      | Individual | 09 Set – 07 Out   |
| `Port_Scanner` | Individual | 09 Set – 07 Out   |
| `Pass_Vault`   | Individual | 09 Set – 07 Out   |
| `Hash_Cracker` | Team       | 14 Out – 02 Dez   |
| `V_Scanner`    | Team       | 14 Out – 02 Dez   |
| `Net_Analyzer` | Team       | 14 Out – 02 Dez   |
| `Secrets`      | Team       | 14 Out – 02 Dez   |

> [!TIP]
> Os projetos **Individual** são entregas intermediárias (09 Set – 07 Out). Os projetos **Team** são entregas finais do semestre (14 Out – 02 Dez), com apresentação à Insper Sec.

---

## Estrutura das trilhas

<table>
  <thead>
    <tr>
      <th>Ramo</th>
      <th>Área</th>
      <th>Individual</th>
      <th>Team</th>
      <th>Dificuldade (Ind → Team)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>A</td>
      <td>Cryptography &amp; Hashing</td>
      <td align="center">
        <div><code>Hash_ID</code></div>
        <div><img src="https://img.shields.io/badge/N1_Iniciante-brightgreen" alt="N1 Iniciante"></div>
      </td>
      <td align="center">
        <div><code>Hash_Cracker</code></div>
        <div><img src="https://img.shields.io/badge/N4_Avan%C3%A7ado-orange" alt="N4 Avançado"></div>
      </td>
      <td>N1 → N4</td>
    </tr>
    <tr>
      <td>B</td>
      <td>Web &amp; Supply Chain</td>
      <td align="center">
        <div><code>Headers</code></div>
        <div><img src="https://img.shields.io/badge/N2_B%C3%A1sico-green" alt="N2 Básico"></div>
      </td>
      <td align="center">
        <div><code>V_Scanner</code></div>
        <div><img src="https://img.shields.io/badge/N4_Avan%C3%A7ado-orange" alt="N4 Avançado"></div>
      </td>
      <td>N2 → N4</td>
    </tr>
    <tr>
      <td>C</td>
      <td>Network Security</td>
      <td align="center">
        <div><code>Port_Scanner</code></div>
        <div><img src="https://img.shields.io/badge/N3_Intermedi%C3%A1rio-yellow" alt="N3 Intermediário"></div>
      </td>
      <td align="center">
        <div><code>Net_Analyzer</code></div>
        <div><img src="https://img.shields.io/badge/N5_Especialista-red" alt="N5 Especialista"></div>
      </td>
      <td>N3 → N5</td>
    </tr>
    <tr>
      <td>D</td>
      <td>Secrets &amp; Detection</td>
      <td align="center">
        <div><code>Pass_Vault</code></div>
        <div><img src="https://img.shields.io/badge/N4_Avan%C3%A7ado-orange" alt="N4 Avançado"></div>
      </td>
      <td align="center">
        <div><code>Secrets</code></div>
        <div><img src="https://img.shields.io/badge/N5_Especialista-red" alt="N5 Especialista"></div>
      </td>
      <td>N4 → N5</td>
    </tr>
  </tbody>
</table>

---

## Ramo A — Cryptography & Hashing

> [!NOTE]
> Identificação, análise e quebra controlada de hashes.

Esta trilha introduz conceitos fundamentais de criptografia aplicada à segurança. A ideia é sair do "ver um hash" para o "entender o que aquele hash representa, como ele é produzido e por que isso importa".

O ponto central aqui é perceber que hash não é criptografia reversível. Em vez disso, a trilha trabalha com identificação de algoritmos, análise de formatos, força de busca e custo computacional. No projeto em equipe, a discussão avança para recuperação controlada de entradas a partir de hashes conhecidos, explorando ataques de dicionário, brute force, salts e limitações práticas de cada abordagem.

### `Hash_ID` — Individual

![Difficulty](https://img.shields.io/badge/Difficulty-N1_Iniciante-brightgreen)

Projeto voltado à identificação de algoritmos de hash com base em padrões observáveis como comprimento, formatação e características conhecidas.

Na prática, o foco é aprender a reconhecer o que um hash pode sugerir e, principalmente, o que ele não permite concluir com certeza.

### `Hash_Cracker` — Team

![Difficulty](https://img.shields.io/badge/Difficulty-N4_Avan%C3%A7ado-orange)

Projeto que testa candidatos contra hashes-alvo para recuperar valores originais ou senhas, dentro de um ambiente autorizado.

Aqui o aluno começa a medir o custo real de quebrar um hash e a entender por que escolhas fracas de senha ou de algoritmo tornam o sistema vulnerável.

---

## Ramo B — Web & Supply Chain

> [!NOTE]
> Inspeção de headers HTTP e análise de dependências / supply chain.

Esta trilha trabalha com a camada web e com a cadeia de dependências de software, duas das superfícies de ataque mais expostas em sistemas modernos.

A base está em interpretar respostas HTTP, headers de segurança, cookies, políticas de navegador e sinais de configuração insegura. Depois, a trilha evolui para a construção de um scanner de **dependências Python** capaz de automatizar verificações de vulnerabilidades conhecidas (CVEs) e atualizações seguras.

### `Headers` — Individual

![Difficulty](https://img.shields.io/badge/Difficulty-N2_B%C3%A1sico-green)

Projeto focado em analisar headers HTTP e identificar configurações ausentes, inadequadas ou que indiquem pouca proteção.

É um bom ponto de entrada para entender como muita coisa sobre um sistema pode ser inferida só olhando a forma como ele responde.

### `V_Scanner` — Team

![Difficulty](https://img.shields.io/badge/Difficulty-N4_Avan%C3%A7ado-orange)

Projeto em equipe voltado à **verificação automatizada de dependências Python** em busca de vulnerabilidades conhecidas (via OSV.dev) e à atualização segura de pacotes.

O desafio deixa de ser apenas observar e passa a ser combinar múltiplas checagens em uma ferramenta útil, organizada e minimamente confiável. Este projeto faz a ponte entre o tema web (`Headers`) e a frente defensiva (Blue Team).

---

## Ramo C — Network Security

> [!NOTE]
> Descoberta de serviços, portas, protocolos e análise de tráfego de rede.

Esta trilha aproxima segurança de redes e programação de sistemas.

Aqui a pergunta principal é: o que está exposto, o que está acontecendo e como interpretar isso? O primeiro projeto costuma explorar descoberta de portas e serviços. O segundo amplia a visão para análise de tráfego e comportamento de comunicação entre hosts.

### `Port_Scanner` — Individual

![Difficulty](https://img.shields.io/badge/Difficulty-N3_Intermedi%C3%A1rio-yellow)

Projeto para mapear portas abertas em um alvo autorizado e descobrir serviços expostos na rede.

Mesmo parecendo simples, esse projeto envolve conceitos importantes como sockets, estados de conexão, timeouts, concorrência e diferenças entre TCP e UDP.

### `Net_Analyzer` — Team

![Difficulty](https://img.shields.io/badge/Difficulty-N5_Especialista-red)

Projeto em equipe voltado à análise de tráfego de rede e interpretação de protocolos.

Aqui o foco passa a ser entender o que os pacotes carregam, como os hosts se comunicam e de que forma isso pode ser usado para diagnóstico, reconhecimento ou investigação.

> [!NOTE]
> `Net_Analyzer` possui **duas implementações**: Python (baseline principal) e C++ (variante avançada). A implementação Python é o caminho recomendado; a C++ é uma extensão para membros veteranos.

---

## Ramo D — Secrets & Detection

> [!NOTE]
> Armazenamento seguro de credenciais e detecção de exposição de segredos.

Esta trilha trata de um dos problemas mais delicados em segurança: como lidar com informação sensível sem expô-la.

A progressão começa com o armazenamento seguro de credenciais em um cofre e avança para a **detecção de segredos expostos** em bases de código e repositórios git.

### `Pass_Vault` — Individual

![Difficulty](https://img.shields.io/badge/Difficulty-N4_Avan%C3%A7ado-orange)

Projeto individual focado em construir um cofre seguro para armazenar senhas e outros dados sensíveis.

O objetivo aqui é colocar em prática criptografia, derivação de chaves, integridade e proteção de acesso de forma coerente.

### `Secrets` — Team

![Difficulty](https://img.shields.io/badge/Difficulty-N5_Especialista-red)

Projeto em equipe voltado à **detecção de segredos expostos** em bases de código e histórico de repositórios git.

A discussão sai do "guardar com segurança" e entra em temas como exposição, vazamento, entropia, verificação HIBP e risco operacional.

---

## 📖 O que estudar antes

> [!NOTE]
> A maioria das linguagens **são ensinadas** nos projetos (os módulos `learn/` explicam cada conceito do zero). Mas um estudo básico prévio evita frustração e acelera o desenvolvimento. Aqui estão recomendações por stack:

| Stack      | Recomendação prévia                                                                                       |
| ---------- | --------------------------------------------------------------------------------------------------------- |
| **Python** | [Tutorial oficial do Python](https://docs.python.org/3/tutorial/) — sintaxe, funções, estruturas de dados |
| **C++**    | [learncpp.com](https://www.learncpp.com/) — fundamentos de C++ moderno                                    |
| **Go**     | [Tour of Go](https://go.dev/tour/) — sintaxe, goroutines, pacotes                                         |
| **SQL**    | [SQLBolt](https://sqlbolt.com/) - guia prático de SQL                                                     |

> [!TIP]
> Não precisa dominar tudo antes de começar. O objetivo é ter **familiaridade básica** com a sintaxe e os conceitos centrais. O projeto vai te guiar no resto.

---

## 🗣️ Qual trilha é a sua?

Escolher uma trilha é como escolher um caminho no mapa — cada uma te leva a um lugar diferente, mas todas valem a pena. Aqui vai um papo reto sobre cada uma:

### Ramo A — Cryptography & Hashing

> "Curte desmontar problemas e entender padrões? Ramo A é pra quem gosta de pensar como um analista: identificar formatos, padrões e limitações de hashes. Começa com reconhecimento (o que uma string pode — e não pode — nos dizer) e avança para técnicas práticas de recuperação controlada (dicionário, brute force, regras). Aqui o foco é medir custo e margem de erro, não só 'quebrar' por quebrar: por que um algoritmo, uma salt ou uma política de senha muda tudo."

### Ramo B — Web & Supply Chain

> "Gosta de entender o que um serviço 'fala' quando responde a requisições? Ramo B é sobre interpretar essa linguagem: headers HTTP, políticas do navegador e sinais que revelam configuração insegura. Você aprende a avaliar e pontuar headers e, em seguida, aplica essa mentalidade ao supply chain — construindo uma ferramenta que escaneia dependências Python por vulnerabilidades e sugere atualizações seguras. Resultado: conhecimento aplicável tanto para auditoria quanto para mitigação."

### Ramo C — Network Security

> "Curte ver o que está exposto e entender o quê e como se comunica na rede? Ramo C leva você do reconhecimento (scanner de portas eficiente) à observação aprofundada (captura de pacotes, parsing de protocolos, estatísticas em tempo real). É a trilha ideal para quem gosta de sistemas e quer entender as implicações práticas de exposição de serviços e comportamento da rede."}

### Ramo D — Secrets & Detection

> "Ramo D é sobre segurança aplicada: proteger dados sensíveis e detectar quando eles vazam. Começa implementando práticas robustas de armazenamento (derivação de chaves, AES-GCM, escritas atômicas) e avança para a detecção em escala — regras confiáveis, análise de entropia e verificações de vazamento (HIBP/k-anonimato) que preservam privacidade. Aqui você trabalha tanto na proteção quanto na capacidade de descobrir exposição real, sempre com foco em reduzir risco operacional."
> No fim, a ideia é sempre a mesma: entender o problema antes de tentar automatizá-lo.

> [!TIP]
> Leia a documentação da trilha antes de começar a codar. Isso costuma poupar bastante tempo.
>
> Consulte também o [mapa curricular completo](../docs/CURRICULUM.md) e os [padrões de README](../CONTRIBUTING.md#-padrões-de-readme).
