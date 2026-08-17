# Desafios

Você leu o projeto inteiro. Você entende por que cada linha é o que é. E agora?

A resposta honesta é: **construa algo sobre ele.** A maneira mais rápida de realmente aprender o que você acabou de ler é estendê-lo. Os desafios abaixo estão ordenados aproximadamente do fácil para o difícil. Escolha um que lhe interesse, esboce o que você mudaria e tente.

Se você ficar travado, as partes relevantes do código existente estão vinculadas. Se você terminar um e quiser compartilhá-lo, faça um fork do repositório e abra um PR — o nível foundations deve ser um degrau, não algo estático.

## Uma nota sobre o escopo

Não tente fazer todos esses desafios. Não tente fazer nem cinco. Escolha _um_, faça-o bem e pare. O objetivo não é adicionar recursos — é internalizar o código existente interagindo com ele.

Para cada desafio abaixo, você encontrará:

- **O quê** — uma ou duas frases descrevendo o recurso.
- **Por que é interessante** — o que você aprenderá ao construí-lo.
- **Por onde começar** — qual(is) arquivo(s) você tocaria.
- **Cuidado com** — as armadilhas de segurança ou correção que pegam iniciantes.

---

## Nível 1 — pequenos recursos (~30 minutos cada)

### 1. Adicione um comando `search`

**O quê:** `pv search <substring>` lista cada nome de entrada que contém a substring (insensível a maiúsculas). Como o `pv list`, mas filtrado.

**Por que é interessante:** Fácil de fazer, mas força você a ler o `main.py` e o `vault.py` cuidadosamente e encontrar o ponto certo para adicionar um novo comando. Bom aquecimento para um "primeiro PR".

**Por onde começar:** Copie o comando `list_entries` no `main.py`. Filtre `unlocked.names()` antes de renderizar a tabela.

**Cuidado com:**

- Comparação insensível a maiúsculas: use `name.lower()` e `query.lower()`.
- Uma consulta de busca vazia deve ser rejeitada, não retornar "todas as entradas".

### 2. Adicione um comando `count`

**O quê:** `pv count` imprime apenas o número de entradas. Útil para scripts de shell.

**Por que é interessante:** O menor comando novo possível. Força você a pensar sobre o formato de saída (número + quebra de linha, sem decoração) para que possa ser usado em pipes: `if [ "$(pv count)" -eq 0 ]; then ...`.

**Por onde começar:** Copie o `gen` — é o comando existente mais simples. Leia as entradas, imprima `len(unlocked.entries)`.

**Cuidado com:**

- Use `print()`, não `console.print()`, para que a saída seja amigável para pipes.
- Um vault vazio ainda imprime `0`, não "vault está vazio".

### 3. Mostre um timestamp de "último uso"

**O quê:** Adicione um campo `last_used_at` ao `Entry`. O comando `get` o atualiza (e salva o vault).

**Por que é interessante:** Você tocará em cada camada — a dataclass `Entry`, seu `from_dict`/`to_dict`, o caminho de salvamento e o `get` no `main.py`. Boa maneira de ver a arquitetura em movimento.

**Por onde começar:** Adicione o campo com `field(default_factory=lambda: "")` para que os vaults antigos abram sem ele. Aumente a contagem implícita de campos no `from_dict`.

**Cuidado com:**

- Vaults antigos não terão o campo — trate o caso de chave ausente da mesma forma que `created_at` e `updated_at` fazem.
- O `get` agora altera o vault → deve chamar `save()` antes que o bloco `with` termine.
- Isso altera o modelo de ameaça: um atacante que rouba o vault agora descobre _qual entrada você usou mais recentemente_. Documente o compromisso.

### 4. Esconda as senhas no `get`, a menos que `--show` seja passado

**O quê:** `pv get github` mostra tudo, exceto a senha (`••••••••`). `pv get github --show` mostra a senha real.

**Por que é interessante:** Pequena mudança de UX, mas é o tipo de recurso que gerenciadores de senhas reais oferecem para momentos de "compartilhamento de tela em uma reunião".

**Por onde começar:** Adicione uma flag `--show / -s` ao comando `get`. No `_render_entry`, crie um desvio baseado na flag.

**Cuidado com:**

- Padrão oculto, opt-in para visível — seguro por padrão.
- O caractere de ponto `•` pode não ser renderizado em todos os terminais — forneça uma alternativa.

---

## Nível 2 — recursos médios (algumas horas cada)

### 5. Implemente `pv export` e `pv import`

**O quê:** `pv export <path>` escreve cada entrada em um arquivo JSON de texto simples (após solicitar a senha mestra e um forte aviso de "VOCÊ TEM CERTEZA"). `pv import <path>` faz o inverso.

**Por que é interessante:** Isso é real, útil e perigoso. Real porque todo gerenciador de senhas precisa de migração de entrada e saída. Útil porque usuários morrem, perdem telefones, trocam de ferramentas. Perigoso porque credenciais em texto simples no disco é exatamente o que construímos esta ferramenta para evitar.

**Por onde começar:** Adicione dois comandos ao `main.py`. O export serializa `unlocked.entries` e escreve um arquivo JSON com modo 0600. O import lê o JSON, valida a estrutura e chama `add_entry` para cada um.

**Cuidado com:**

- O arquivo de exportação é texto simples. Imprima um aviso vermelho gigante antes de escrever.
- Defina o caminho de exportação padrão como `./pv-export.json`, não o diretório home do usuário — faça-os pensar sobre onde ele ficará.
- O import deve lidar com "entrada já existe" de forma graciosa — ou perguntar, ou aceitar uma flag `--force`, ou pular.
- Valide o JSON importado da mesma forma que o `Entry.from_dict` valida — não confie na estrutura do arquivo.
- Um arquivo exportado com permissões de sistema de arquivos fracas é um perigo real. Defina o modo 0600 explicitamente com `os.open` (mesmo truque que o `_atomic_write` usa).

### 6. Adicione pontuação de força de senha

**O quê:** Quando um usuário executa `pv add`, mostre a ele uma pontuação de força (fraca/razoável/forte/excelente) antes de salvar. Use uma biblioteca como [`zxcvbn-python`](https://github.com/dwolfhub/zxcvbn-python).

**Por que é interessante:** Recurso prático de UX. Força você a adicionar uma nova dependência (tocando no `pyproject.toml` e `uv.lock`) e a entender a diferença entre "parece aleatório para um humano" e "sobreviveria a um ataque de adivinhação offline".

**Por onde começar:** Adicione `zxcvbn` ao `pyproject.toml`. Chame-o na senha digitada. Mapeie a pontuação de 0-4 para uma cor e rótulo. Permita que o usuário prossiga de qualquer maneira.

**Cuidado com:**

- Não _impeça_ o usuário de salvar uma senha fraca — ele pode ter um bom motivo. Avise e pergunte.
- A pontuação deve ser exibida antes que a senha seja permanente — se você esperar até depois do `save()`, o usuário terá que excluir e adicionar novamente para tentar de novo.

### 7. Adicione um comando `pv copy <name>`

**O quê:** Copie uma senha para a área de transferência do sistema sem imprimi-la. Use [`pyperclip`](https://github.com/asweigart/pyperclip).

**Por que é interessante:** Gerenciadores de senhas reais fazem isso. Força você a pensar sobre as diferenças de plataforma (as APIs de área de transferência diferem no Linux/Mac/Windows) e o compromisso de segurança de ter credenciais na área de transferência.

**Por onde começar:** Adicione `pyperclip` às dependências. Novo comando que desbloqueia o vault, busca a entrada, copia sua senha e imprime uma confirmação (NÃO a senha).

**Cuidado com:**

- No Linux, você precisa do `xclip` ou `wl-clipboard` instalado no nível do sistema — documente isso.
- O conteúdo da área de transferência persiste até que outra coisa o sobrescreva. Desafio bônus: inicie uma thread em segundo plano que limpe a área de transferência após 30 segundos.
- O Pyperclip em sessões SSH remotas não funciona — trate a falha no momento da importação com um erro claro.

### 8. Adicione uma flag `--verify` ao `init`

**O quê:** Após criar um vault, tente imediatamente desbloqueá-lo com a mesma senha. Se o desbloqueio falhar, entre em pânico — algo está corrompido.

**Por que é interessante:** Defesa em profundidade. O ciclo salvar → re-desbloquear teria capturado algumas classes de bugs durante o desenvolvimento. Constrói o hábito de "testar o caminho de leitura em cada escrita" do qual projetos de formato de arquivo se beneficiam.

**Por onde começar:** Adicione uma flag `--verify / -V` ao `init`. Após o retorno de `UnlockedVault.create()`, chame `UnlockedVault.unlock()` com a mesma senha. Imprima um check verde ou um pânico vermelho.

**Cuidado com:**

- A chamada de verificação custa outra derivação Argon2 completa (~0.5s). Torne-a opt-in, não padrão.
- Se a verificação _falhar_, algo está muito errado — recuse-se a deixar o novo vault no lugar. Exclua-o.

---

## Nível 3 — recursos maiores (um fim de semana cada)

### 9. Adicione TOTP (senhas de uso único baseadas em tempo)

**O quê:** Alguns sites usam TOTP para 2FA. Atualmente, você armazena o segredo em outro lugar (Google Authenticator, Authy). Adicione um campo de segredo TOTP ao `Entry` e um comando `pv totp <name>` que imprime o código atual de 6 dígitos.

**Por que é interessante:** Você aprenderá o que o TOTP realmente é (é a [RFC 6238](https://datatracker.ietf.org/doc/html/rfc6238) e surpreendentemente simples — HMAC-SHA1 da janela atual de 30 segundos). A biblioteca Python `pyotp` faz isso em duas linhas, mas escrever o núcleo você mesmo é um exercício de 30 linhas.

**Por onde começar:** Adicione `pyotp` às dependências. Adicione um campo opcional `totp_secret` ao `Entry`. Adicione o comando no `main.py`.

**Cuidado com:**

- O segredo TOTP é pelo menos tão sensível quanto a senha. Ele pertence ao _interior_ do vault criptografado, não a um arquivo lateral.
- O desvio de tempo (time skew) importa. Imprima "este código é válido por mais X segundos" para que o usuário não tente usar um que está prestes a expirar.
- Importar segredos TOTP de códigos QR é um projeto à parte — não tente fazer isso aqui.

### 10. Torne a atualização do custo KDF transparente

**O quê:** Quando um usuário desbloqueia um vault cujos parâmetros Argon2 estão abaixo dos padrões do código atual, re-derive _automaticamente_ a chave com os novos padrões e salve — mesma senha, derivação mais forte. Imprima uma mensagem: "Parâmetros do vault atualizados para os padrões atuais."

**Por que é interessante:** É isso que os gerenciadores de senhas reais fazem. É por isso que armazenamos os parâmetros KDF no arquivo. Força você a entender completamente o fluxo do `change_master_password` e a pensar na UX para uma "operação de longa duração que os usuários não pediram".

**Por onde começar:** Dentro de `UnlockedVault.unlock`, após a descriptografia bem-sucedida, compare `kdf_parameters` com `KdfParameters.defaults()`. Se eles diferirem, faça uma alteração no local (chame algo como `change_master_password(mesma_senha, new_kdf_parameters=...)`) e salve.

**Cuidado com:**

- Pague o novo custo do Argon2 apenas uma vez, não duas. Refatore o `change_master_password` para que ele também possa "atualizar no local" sem rotacionar a senha.
- O usuário verá duas pausas sequenciais de ~0.5 segundo. Diga a ele o porquê com uma mensagem antes da segunda pausa.
- Adicione uma flag `--no-auto-upgrade` para usuários que não desejam isso.

### 11. Implemente um comando `pv backup` com snapshots versionados

**O quê:** `pv backup` escreve uma cópia do vault atual em `~/.password-vault/backups/vault-AAAA-MM-DD-HHMMSS.json` e mantém os últimos N backups. Adicione um comando `pv restore <timestamp>` que sobrescreve o vault ativo a partir de um backup.

**Por que é interessante:** Sistemas reais precisam de backups, mas backups _também_ são uma superfície de segurança — são mais arquivos que um atacante pode roubar. Força você a pensar sobre: quantos manter, onde armazenar, se deve também criptografar o índice de backup, o que acontece na restauração (você quer semântica atômica).

**Por onde começar:** Adicione os dois comandos. Use o padrão de escrita atômica existente (não escreva o backup com `Path.write_bytes`; use `_atomic_write`). Use o padrão de bloqueio de arquivo existente.

**Cuidado com:**

- Backups são cópias completas do arquivo criptografado — eles estão criptografados, então são "seguros para perder para perícia de disco" _na mesma medida_ que o vault ativo é, mas não mais.
- A limpeza de backups antigos requer cuidado — não exclua o arquivo que está sendo lido no momento por outro processo `pv`. Use o mesmo bloqueio consultivo.
- O "restaurar do backup N" precisa validar que o backup N é um vault _real_ (analisar o envelope, verificar a versão) antes de sobrescrever o arquivo ativo.

### 12. Adicione uma UI web em um comando `pv web` separado

**O quê:** Um servidor web apenas local (`localhost:8080`) que serve uma UI simples para navegar no vault. Desliga automaticamente após 10 minutos de inatividade.

**Por que é interessante:** Força você a pensar sobre _cada_ compromisso de segurança que você não precisou pensar com uma CLI. Tratamento de senha mestra em um navegador, CSRF, XSS, timeout de sessão, HTTPS-ou-não no localhost, o que fazer quando uma segunda aba abre.

**Por onde começar:** Use [`starlette`](https://www.starlette.io) ou [`fastapi`](https://fastapi.tiangolo.com) para o servidor. Renderize as entradas com templates Jinja2. Não use cookies — use uma única sessão em memória que expira automaticamente.

**Cuidado com:**

- Isso é genuinamente mais difícil do que parece. As UIs web de gerenciadores de senhas reais são trabalhos de engenharia em tempo integral. O objetivo _desta_ versão é aprender quais são os compromissos, não lançar uma ferramenta de produção.
- O navegador agora faz parte do seu modelo de ameaça. Extensões de navegador podem ler o DOM. Outras abas podem navegar para o seu `localhost:8080`. A política de mesma origem (same-origin policy) é sua única amiga.
- Registro (Logging) — Starlette/FastAPI registrarão prestativamente cada requisição. Certifique-se de que o log de acesso não inclua a senha mestra (não incluirá, se você fizer o POST do formulário corretamente, mas verifique).

---

## Nível 4 — projetos com sabor de pesquisa

Estes não têm um formato limpo de "construa este recurso exato". São direções para levar o projeto adiante se você absorveu tudo e quer continuar.

### 13. Audite o modelo de ameaça de um gerenciador de senhas real

Escolha um gerenciador de senhas real e de código aberto: [Bitwarden](https://github.com/bitwarden), [KeePassXC](https://github.com/keepassxreboot/keepassxc), [pass](https://www.passwordstore.org). Leia sua documentação e código-fonte para as partes equivalentes a _este_ projeto: como ele deriva chaves, como armazena o arquivo, como lida com a rotação da senha mestra? Escreva uma comparação.

Você aprenderá que gerenciadores de senhas reais fazem compromissos diferentes — às vezes por bons motivos, às vezes por motivos de legado. O exercício de identificar _qual é qual_ é o tipo de análise que engenheiros de segurança fazem para viver.

### 14. Escreva um leitor de formato de vault em outra linguagem

O formato do vault está documentado em [02-Arquitetura.md §3](./02-Arquitetura.md#3-o-formato-do-arquivo-de-vault-no-disco) e as chaves JSON são constantes no `constants.py`. Escreva um cliente de apenas leitura em Rust, Go ou qualquer outra linguagem que você esteja aprendendo. Você encontrará as bibliotecas para usar (`argon2`, `aes-gcm`), fará a correspondência de versões/parâmetros e validará a ida e volta entre as linguagens.

Este é um exercício muito bom. Ele demonstra _por que_ escrevemos o formato — e provavelmente expõe lugares onde o formato é subespecificado (que é o tipo de coisa que projetos de interoperabilidade do mundo real encontram o tempo todo).

### 15. Modele a ameaça de uma fraqueza deliberada

Escolha uma suposição da seção de modelo de ameaça do [01-Conceitos.md §12](./01-Conceitos.md#12-juntando-tudo-o-modelo-de-ameaça). Tente derrotá-la.

Exemplos:

- "Não defendemos contra um keylogger." Tente escrever um keylogger em Python que observe o stdin do processo `pv` (você descobrirá que é surpreendentemente difícil porque o `getpass` lê do dispositivo de terminal, não do stdin). Então tente escrever um que se conecte no nível do SO no Linux — quais permissões ele precisa?
- "Não limpamos verdadeiramente a chave da memória." Use uma ferramenta de depuração de memória (`gcore` + `strings`) em um processo `pv` em execução para encontrar a chave AES. Então projete o que _realmente_ protegeria contra isso e explique por que não o implementamos.

O objetivo não é transformar nada em arma. É sentir visceralmente a diferença entre "não afirmamos defender contra X" e "não poderíamos mesmo se quiséssemos".

---

## O que ler em seguida

Se você passou pelo 03-Implementação e terminou este projeto:

- **[Crypto 101](https://www.crypto101.io)** por Laurens Van Houtven — um livro gratuito que se aprofunda em cada ideia criptográfica deste projeto. Especialmente recomendado se você achou as seções §8-9 no [01-Conceitos.md](./01-Conceitos.md) interessantes e quer o histórico completo.
- **[Cryptography Engineering](https://www.schneier.com/books/cryptography-engineering/)** por Ferguson, Schneier e Kohno — o livro-texto. Mais pesado que o Crypto 101, mas a referência definitiva para "como sistemas criptográficos realmente falham na prática".

Você agora sabe mais sobre armazenamento de senhas no mundo real do que os engenheiros responsáveis pela [maioria das violações que citamos](./01-Conceitos.md#13-violações-reais-que-tornaram-essas-escolhas-as-corretas). Vale a pena parar para apreciar isso.

&nbsp;

## Fim

<p align="center">
  <img src="../assets/cat.gif" width="300" alt="Cat">
</p>

Agora você chegou ao final de seu projeto. Se conseguiu realizar a maioria dos desafios, saiba que estará pronto para o que virá em seguida. **Parabéns!**

Minha recomendação agora é que você _se arrisque em mais um projeto disponível_, mas no seu tempo. Aliás, esse é o ponto mais forte de qualquer currículo ao lado das experiências: **os projetos**. Então, sem medo, quanto mais fizer, melhor.
