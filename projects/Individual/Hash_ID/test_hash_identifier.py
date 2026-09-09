"""
©AngelaMos | 2026
Copyright (C) 2026 Murilo Miacci
test_hash_identifier.py

Testes para o hash_identifier — focado nos casos mais utilizados

────────────────────────────────────────────────────────────────────
O que são "testes" e por que os escrevemos
────────────────────────────────────────────────────────────────────
Um teste é uma pequena função Python que chama nosso código real com uma
entrada conhecida e então AFIRMA (assert) que o resultado é o que esperávamos.
Se a afirmação falhar, o pytest imprime uma mensagem vermelha de FALHA — o que
significa que mudamos algo e quebramos um comportamento que nos importava.

Testes são um seguro. A primeira vez que você escreve o código, o teste
apenas confirma que ele funciona. Mas seis meses depois, quando você refatorar
ou adicionar um novo recurso, os testes existentes capturam qualquer quebra
acidental. É por isso que toda base de código sênior tem testes: não porque
o código é difícil de escrever, mas porque o código é difícil de manter
FUNCIONANDO ao longo do tempo.

────────────────────────────────────────────────────────────────────
O formato de um teste pytest
────────────────────────────────────────────────────────────────────
  def test_<o_que_estamos_verificando>() -> None:
      result = some_function(some_input)
      assert result == expected

Três regras:
  1. O nome da função deve começar com `test_` — o pytest apenas coleta
     funções que correspondem a esse padrão.
  2. A função não recebe argumentos (a menos que use fixtures).
  3. Use a palavra-chave `assert` para declarar o que deve ser verdadeiro.
     Se a condição for falsa, o teste falha.

Seguimos a estrutura "Arrange-Act-Assert" (Organizar-Agir-Afirmar) em cada teste:
  - Arrange: configurar as entradas (a linha `sample = ...`).
  - Act:     chamar o código real (`candidates = identify(sample)`).
  - Assert:  verificar o resultado (`assert candidates[0]...`).

────────────────────────────────────────────────────────────────────
Estratégia de cobertura
────────────────────────────────────────────────────────────────────
NÃO tentamos testar todos os algoritmos da tabela — isso resultaria em
centenas de testes quase idênticos. Em vez disso, exercitamos cada RAMO (branch)
do identify() pelo menos uma vez:

  - correspondências de prefixo (um bcrypt, um Argon2id, um Django, um crypt)
  - formato especial MySQL5
  - correspondências de comprimento hex (comprimentos MD5, SHA-1, SHA-256)
  - os fallbacks para vazio / lixo / espaços em branco
  - a imutabilidade do HashCandidate

Juntos, eles nos dão a confiança de que cada caminho de código executa sem
erros críticos e que as entradas mais comuns produzem o candidato esperado
no topo do ranking.
"""

# Importar de `hash_identifier` (NÃO `hash_identifier.py`) diz ao Python
# para carregar o módulo que vive neste mesmo diretório. Extraímos três coisas:
#   - `identify`     — a função sob teste
#   - `HashCandidate`— a dataclass do tipo de retorno (usada no teste de imutabilidade)
#   - `PREFIX_RULES` — a tabela de busca de prefixos (usada pelo teste
#                      parametrizado "every row is covered" no final deste arquivo)

# Terceiros: o próprio executor de testes. Também precisamos importá-lo aqui
# para podermos usar seu decorador `@pytest.mark.parametrize` abaixo.
import pytest

# Local: nosso próprio módulo. Extraímos as peças públicas sob teste —
# a tabela de regras de prefixo, a dataclass de resultado e a função de entrada.
from hash_identifier import PREFIX_RULES, HashCandidate, identify

# =============================================================================
# Correspondências de prefixo (alta confiança)
# =============================================================================
# Estes testes verificam o Passo 1 do identify(): quando a entrada começa com um
# prefixo conhecido, relatamos ALTA confiança. A carga útil (payload) exata do
# hash após o prefixo não importa para o identify() — ele apenas inspeciona os
# caracteres iniciais.


def test_bcrypt_prefix_is_recognized() -> None:
    """
    Um hash bcrypt real começa com `$2b$` e deve ser relatado como bcrypt
    """
    # Exemplo: um hash bcrypt real para a senha "password" com custo 12.
    # A parte interessante para o nosso teste é apenas o `$2b$` — nós nem
    # sequer decodificamos o resto.
    sample = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQNQy.uK4Of2T7G"

    # Chama a função sob teste. `candidates` é uma lista de HashCandidate.
    candidates = identify(sample)

    # Primeiro afirma que a lista não está vazia. `assert <coisa>` falha quando
    # <coisa> é avaliada como falsa — listas vazias são falsas, então isso
    # captura o bug de "nenhum candidato retornado".
    assert candidates
    # Em seguida, verifica se o PRIMEIRO candidato (palpite de maior prioridade) é bcrypt.
    # `candidates[0]` é o primeiro item; `.algorithm` é o campo que verificamos.
    assert candidates[0].algorithm == "bcrypt"
    # E a confiança deve ser "high" — correspondências de prefixo são definitivas.
    assert candidates[0].confidence == "high"


def test_argon2id_prefix_is_recognized() -> None:
    """
    Strings PHC Argon2id começam com `$argon2id$`
    """
    # Formato PHC para Argon2id: $argon2id$v=<versao>$m=...,t=...,p=...$<salt>$<hash>
    sample = "$argon2id$v=19$m=65536,t=3,p=4$c2FsdHNhbHQ$aGFzaA"
    candidates = identify(sample)
    # `any(...)` retorna True se pelo menos um elemento do iterável tornar a
    # expressão interna verdadeira. Verificamos se PELO MENOS UM candidato
    # é Argon2id — usar any() em vez de [0] mantém o teste robusto se algum
    # dia adicionarmos um segundo palpite ao mesmo prefixo.
    assert any(c.algorithm == "Argon2id" for c in candidates)


def test_sha512_crypt_prefix_is_recognized() -> None:
    """
    `$6$` é o marcador para SHA-512 crypt — o que o /etc/shadow usa no Linux
    """
    sample = "$6$rounds=10000$salt$hashedpasswordhere"
    candidates = identify(sample)
    # `[0]` porque queremos o candidato do TOPO. Se qualquer outra coisa fosse
    # classificada em primeiro, esta afirmação falharia ruidosamente.
    assert candidates[0].algorithm == "SHA-512 crypt"


def test_django_pbkdf2_prefix_is_recognized() -> None:
    """
    O Django armazena senhas como `pbkdf2_sha256$<iter>$<salt>$<hash>`
    """
    sample = "pbkdf2_sha256$260000$salt$hash"
    candidates = identify(sample)
    assert candidates[0].algorithm == "Django PBKDF2-SHA256"


def test_apr1_prefix_is_recognized() -> None:
    """
    Hashes MD5 do Apache `.htpasswd` começam com $apr1$

    A ferramenta htpasswd gera estes por padrão com a flag `-m`.
    Mesma família MD5 do formato Unix $1$, mas com a manipulação de salt
    própria do Apache — e MUITO mais comum no mundo real.
    """
    # Hash apr1 com aparência real. A carga útil após o segundo `$` é a
    # codificação estilo base64 do digest MD5 + salt.
    # identify() nunca o decodifica — apenas o `$apr1$` inicial importa.
    sample = "$apr1$rsalt$mp7TYYDvbgvNCJN3JTd6q1"
    candidates = identify(sample)
    assert candidates[0].algorithm == "Apache MD5-crypt"
    assert candidates[0].confidence == "high"


# =============================================================================
# Formatos especiais
# =============================================================================
# Passo 2 do identify(): formatos que NÃO são strings PHC, mas ainda têm
# formatos inconfundíveis. Hoje reconhecemos NetNTLMv1, NetNTLMv2 e
# MySQL5 — três registros estruturalmente distintos.


def test_mysql5_format_is_recognized() -> None:
    """
    MySQL5 = literal `*` seguido por 40 caracteres hex maiúsculos

    O MySQL5 armazena SHA-1(SHA-1(senha)) impresso em hex maiúsculo com
    um asterisco inicial. Portanto, o hash todo tem exatamente 41 caracteres.
    """
    # O * importa — sem ele, seriam apenas 40 caracteres hex e cairia
    # na regra de comprimento do SHA-1.
    sample = "*23AE809DDACAF96AF0FD78ED04B6A265E05AA257"
    candidates = identify(sample)

    # MySQL5 é um formato definitivo, então esperamos confiança ALTA (high).
    assert candidates[0].algorithm == "MySQL5"
    assert candidates[0].confidence == "high"


def test_mysql5_rejects_lowercase_body() -> None:
    """
    Hex minúsculo após o `*` inicial não é uma saída real do MySQL5

    O MySQL emite maiúsculas via `%02X`, então um `*` seguido por hex
    minúsculo é quase certamente lixo editado manualmente. Preferimos
    não retornar nada do que retornar uma resposta ERRADA com confiança.
    """
    # Versão minúscula do corpo do teste anterior. O `*` inicial é a única
    # coisa que compartilha com a saída real do MySQL5.
    lowercase_body = "23ae809ddacaf96af0fd78ed04b6a265e05aa257"
    candidates = identify("*" + lowercase_body)

    # Ou a lista está vazia (preferencial) OU o que quer que tenha
    # correspondido NÃO deve ser rotulado como MySQL5.
    if candidates:
        assert candidates[0].algorithm != "MySQL5"


def test_netntlmv2_format_is_recognized() -> None:
    """
    Registros NetNTLMv2 do Responder parecem com
    `usuario::dominio:desafio:hmac:blob`

    O campo hmac tem exatamente 32 caracteres hex. O `::` inicial é a
    pista de que este é um registro de desafio-resposta do AD.
    """
    # Constrói um registro NetNTLMv2 realista:
    #   alice :: CORP : <desafio de 16 chars> : <hmac de 32 hex> : <blob de 64 hex>
    sample = "alice::CORP:1122334455667788:" + "a" * 32 + ":" + "b" * 64
    candidates = identify(sample)

    # NetNTLMv2 é um formato definitivo — confiança ALTA (high).
    assert candidates[0].algorithm == "NetNTLMv2"
    assert candidates[0].confidence == "high"


def test_netntlmv1_format_is_recognized() -> None:
    """
    Registros NetNTLMv1 têm lmhash E nthash de 48 caracteres hex antes do desafio

    Layout: `usuario::dominio:lm(48 hex):nt(48 hex):desafio`.
    """
    sample = "alice::CORP:" + "a" * 48 + ":" + "b" * 48 + ":1122334455667788"
    candidates = identify(sample)
    assert candidates[0].algorithm == "NetNTLMv1"
    assert candidates[0].confidence == "high"


def test_descrypt_format_is_recognized() -> None:
    """
    O DES crypt tradicional NÃO possui prefixo — apenas o comprimento e o charset o identificam

    Arquivos /etc/passwd legados usavam este formato: 13 caracteres extraídos
    do alfabeto `./0-9A-Za-z`.
    """
    sample = "kRq14pmccuMOA"
    candidates = identify(sample)

    assert candidates[0].algorithm == "DES crypt"
    # Confiança MÉDIA (medium) porque uma string de 13 caracteres nesse charset
    # PODE tecnicamente ser outras coisas.
    assert candidates[0].confidence == "medium"


# =============================================================================
# Correspondências de comprimento hex (confiança média / baixa)
# =============================================================================
# Passo 3 do identify(): quando a entrada é hex puro, o comprimento estreita
# o algoritmo. O PRIMEIRO algoritmo listado para cada comprimento recebe
# confiança média; o restante é baixa.


def test_mysql323_length_returns_mysql323_first() -> None:
    """
    16 caracteres hex apontam para MySQL323 (saída OLD_PASSWORD legada do MySQL)
    """
    sample = "5d2e19393cc5ef67"
    candidates = identify(sample)

    # MySQL323 fica ACIMA de CRC-64 porque em um contexto de segurança,
    # o MySQL323 é de longe a fonte mais provável.
    assert candidates[0].algorithm == "MySQL323"
    assert candidates[0].confidence == "medium"


def test_md5_length_returns_md5_first() -> None:
    """
    32 caracteres hex correspondem a MD5, NTLM, MD4, RIPEMD-128

    MD5 é DE LONGE o hash de 32 hex mais comum, então deve ser o primeiro.
    """
    # O MD5 literal da string "password".
    sample = "5f4dcc3b5aa765d61d8327deb882cf99"
    candidates = identify(sample)

    # O principal candidato é MD5.
    assert candidates[0].algorithm == "MD5"
    assert candidates[0].confidence == "medium"

    # NTLM deve aparecer na lista de candidatos como uma opção menos provável.
    algorithms = [c.algorithm for c in candidates]
    assert "NTLM" in algorithms


def test_sha256_length_returns_sha256_first() -> None:
    """
    64 caracteres hex apontam para SHA-256 primeiro
    """
    # `"a" * 64` é um atalho Python para repetir o caractere 'a' 64 vezes.
    sample = "a" * 64
    candidates = identify(sample)
    assert candidates[0].algorithm == "SHA-256"


def test_sha1_length_returns_sha1_first() -> None:
    """
    40 caracteres hex = SHA-1 (RIPEMD-160 como palpite secundário)
    """
    sample = "a" * 40
    candidates = identify(sample)
    assert candidates[0].algorithm == "SHA-1"


# =============================================================================
# Casos de não correspondência / borda
# =============================================================================
# Sempre teste os casos de borda entediantes: entradas vazias, apenas espaços, lixo.


def test_empty_input_returns_no_candidates() -> None:
    """
    String vazia retorna uma lista vazia — nunca quebra
    """
    assert identify("") == []
    assert identify("   ") == []


def test_garbage_returns_no_candidates() -> None:
    """
    Uma string que não tem prefixo conhecido nem formato hex retorna []
    """
    assert identify("olá, isso não é um hash") == []


def test_input_is_trimmed_of_whitespace() -> None:
    """
    Quebras de linha e espaços iniciais não devem impedir o reconhecimento

    Isso importa porque copiar e colar de um terminal costuma trazer espaços.
    """
    sample = "   5f4dcc3b5aa765d61d8327deb882cf99\n"
    candidates = identify(sample)
    # Se o trim funcionar, ainda reconhecemos o MD5 apesar do ruído ao redor.
    assert candidates[0].algorithm == "MD5"


# =============================================================================
# Fallbacks de correspondência suave (dicas de formato, confiança BAIXA)
# =============================================================================
# Passos 4 e 5 do identify(): quando nada nas tabelas anteriores dispara,
# tentamos duas correspondências suaves — formato genérico de string PHC e
# "isso parece um JWT / blob base64". Ambos retornam confiança BAIXA (low).


def test_unknown_phc_string_falls_back_to_generic() -> None:
    """
    Uma string PHC de um algoritmo para o qual não temos uma regra específica
    ainda é relatada como string PHC com o nome do algoritmo extraído.
    """
    # Codificação PHC pbkdf2-sha512 do Passlib. Não temos regra específica para
    # ela em PREFIX_RULES — mas o formato `$pbkdf2-sha512$...` é inequívoco.
    sample = "$pbkdf2-sha512$25000$cnNhbHQ$aGFzaA"
    candidates = identify(sample)

    assert candidates
    # A coluna de algoritmo deve dizer "PHC string (pbkdf2-sha512)".
    assert "PHC" in candidates[0].algorithm
    assert "pbkdf2-sha512" in candidates[0].algorithm
    assert candidates[0].confidence == "low"


def test_jwt_input_is_called_out_as_not_a_hash() -> None:
    """
    JWTs começam com `eyJ` e devem ser sinalizados como não-hash

    Iniciantes costumam colar JWTs em identificadores de hash. Dizer "isso é
    um JWT, não um hash" é mais útil do que o silêncio.
    """
    sample = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.sig"
    candidates = identify(sample)

    assert candidates
    assert "JWT" in candidates[0].algorithm
    assert candidates[0].confidence == "low"


def test_base64_blob_is_called_out_as_not_a_hash() -> None:
    """
    Uma string contendo caracteres exclusivos de base64 (`+`, `/`, `=`) não é hex
    """
    sample = "VGhpcyBpcyBub3QgYSBoYXNoLCBpdHMgYmFzZTY0Lg=="
    candidates = identify(sample)

    assert candidates
    assert "Base64" in candidates[0].algorithm


# =============================================================================
# HashCandidate é imutável
# =============================================================================
# Declaramos HashCandidate com @dataclass(frozen=True). Frozen significa
# que você não pode reatribuir campos após a construção.


def test_hash_candidate_is_frozen() -> None:
    """
    Tentar mudar um HashCandidate deve gerar um erro
    """
    candidate = HashCandidate(
        algorithm="MD5",
        confidence="medium",
        reason="test",
    )

    # try/except é a sintaxe do Python para "proteger contra um erro".
    try:
        # `# type: ignore[misc]` diz ao mypy: "Eu sei que isso é um erro de tipo;
        # estou fazendo de propósito para verificar se realmente falha na execução"
        candidate.algorithm = "SHA-1"  # type: ignore[misc]
    except (AttributeError, TypeError):
        # Recebeu a exceção esperada — o teste passa.
        return

    # Se chegarmos aqui, nenhuma exceção foi lançada — o frozen está quebrado.
    raise AssertionError(
        "HashCandidate deveria estar congelado (frozen); a atribuição deveria ter falhado"
    )


# =============================================================================
# Cobertura abrangente da tabela PREFIX_RULES
# =============================================================================
# Este último teste garante que CADA linha de PREFIX_RULES seja exercitada,
# para que um erro de digitação em qualquer linha falhe seu próprio caso de teste.
#
# `@pytest.mark.parametrize(name, values)` é o mecanismo do pytest para
# expandir UMA função de teste em MUITOS casos de teste.


@pytest.mark.parametrize("prefix,algorithm,_note", PREFIX_RULES)
def test_every_prefix_rule_is_recognized_with_high_confidence(
    prefix: str,
    algorithm: str,
    _note: str,
) -> None:
    """
    Cada entrada em PREFIX_RULES produz um candidato de ALTA confiança
    com o algoritmo correspondente quando seu prefixo está no início da entrada.
    """
    sample = prefix + "corpofakequenaoimporta"
    candidates = identify(sample)

    # Se o identify() não retornar nada, o ramo do loop de prefixos está
    # quebrado — falha com uma mensagem que nomeia o prefixo problemático.
    assert candidates, f"nenhum candidato retornado para o prefixo `{prefix}`"
    assert candidates[0].algorithm == algorithm
    assert candidates[0].confidence == "high"
