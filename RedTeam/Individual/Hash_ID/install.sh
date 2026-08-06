#!/usr/bin/env bash
# ©AngelaMos | 2026
# Copyright (C) 2026 Murilo Miacci
# install.sh
#
# Script de instalação sem atrito. Qualquer pessoa que clonar este projeto
# deve ser capaz de rodar `./install.sh` e terminar com uma configuração funcional,
# independentemente de já possuírem o uv ou o just instalados.
#
# O que este script faz, em ordem:
#   1. Verifica se o Python 3.13+ está instalado (precisamos da sintaxe moderna de type-hints)
#   2. Instala o uv se estiver ausente (uv é o gerenciador de pacotes Python que usamos)
#   3. Instala o just se estiver ausente (just é o executor de comandos)
#   4. Chama `just setup` para criar o venv e instalar as dependências
#   5. Imprime os próximos passos
#
# Execute com:  ./install.sh
# Ou:           bash install.sh

# -----------------------------------------------------------------------------
# Flags de segurança do Bash — falha rápido e de forma visível
# -----------------------------------------------------------------------------
# -e : sai imediatamente se qualquer comando retornar um status diferente de zero (erro)
# -u : trata variáveis não definidas como um erro
# -o pipefail : se qualquer comando em um pipeline falhar, o pipeline inteiro falha
set -euo pipefail

# -----------------------------------------------------------------------------
# Auxiliares de cores — saída de terminal bonita sem dependências externas
# -----------------------------------------------------------------------------
# Estes são códigos de escape ANSI. \033 é o caractere ESC; os dígitos entre
# colchetes dizem ao terminal para qual cor mudar. NC = "no color" (sem cor),
# redefine para a cor padrão que o terminal tinha antes.
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Pequenas funções auxiliares para não repetir as strings de formato em todo lugar.
# `>&2` redireciona para stderr (onde os erros pertencem) em vez de stdout.
info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1" >&2; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }

# -----------------------------------------------------------------------------
# Passo 1 — Confirmar se o Python 3.13+ está no sistema
# -----------------------------------------------------------------------------
check_python() {
    info "Verificando Python 3.13+..."

    # `command -v <nome>` imprime o caminho de <nome> se ele existir, nada
    # caso contrário. `&>/dev/null` descarta tanto stdout quanto stderr — só
    # nos importamos com o código de saída (0 = encontrado, não-zero = ausente).
    if ! command -v python3 &>/dev/null; then
        error "python3 não encontrado. Por favor, instale o Python 3.13 ou mais recente."
        error "  macOS:   brew install python@3.13"
        error "  Linux:   sudo apt install python3.13   (Debian/Ubuntu)"
        error "  Windows: baixe de python.org"
        exit 1
    fi

    # Lê a versão do próprio Python — a fonte mais confiável.
    # `local` torna essas variáveis restritas ao escopo da função.
    local version
    version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

    local major minor
    # `cut -d. -f1` divide a string no `.` e pega o primeiro campo.
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)

    # `(( ... ))` é o contexto aritmético do bash — permite escrever `<` `>` etc.
    # A condição composta falha se major < 3, OU se major == 3 e minor < 13.
    # Assim, Python 3.12 falha, 3.13 passa, 4.0 passa.
    if (( major < 3 )) || { (( major == 3 )) && (( minor < 13 )); }; then
        error "Python 3.13+ é necessário, encontrado Python $version"
        exit 1
    fi

    success "Python $version detectado"
}

# -----------------------------------------------------------------------------
# Passo 2 — Instalar uv se estiver ausente (https://docs.astral.sh/uv)
# -----------------------------------------------------------------------------
install_uv() {
    # Já está instalado? Imprime confirmação e sai desta função.
    # `return 0` sai da função com sucesso — o chamador continua.
    if command -v uv &>/dev/null; then
        success "uv já instalado ($(uv --version))"
        return 0
    fi

    info "Instalando uv (gerenciador de pacotes Python)..."
    # Envia o script de instalação oficial para o sh. `-LsSf`:
    #   -L : segue redirecionamentos
    #   -s : silencioso (sem barra de progresso)
    #   -S : mostra erros mesmo em modo silencioso
    #   -f : falha em erros HTTP em vez de gravá-los no disco
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # O instalador coloca o uv em ~/.local/bin ou ~/.cargo/bin.
    # Adiciona ambos ao PATH para o restante da execução DESTE script.
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

    # Se ainda não conseguirmos encontrar o uv, algo deu errado.
    if ! command -v uv &>/dev/null; then
        error "A instalação do uv foi concluída, mas \`uv\` ainda não está no PATH."
        error "Reinicie seu shell e execute este script novamente, ou adicione o uv ao PATH manualmente."
        exit 1
    fi
    success "uv instalado"
}

# -----------------------------------------------------------------------------
# Passo 3 — Instalar just se estiver ausente (https://github.com/casey/just)
# -----------------------------------------------------------------------------
install_just() {
    if command -v just &>/dev/null; then
        success "just já instalado ($(just --version))"
        return 0
    fi

    info "Instalando just (executor de comandos)..."
    # Certifica-se de que o diretório de destino existe primeiro.
    mkdir -p "$HOME/.local/bin"
    # Script de instalação oficial. `--to <dir>` controla onde o binário cai.
    # `--proto '=https'` rejeita qualquer protocolo exceto HTTPS.
    # `--tlsv1.2` insiste em uma versão moderna de TLS.
    curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh \
        | bash -s -- --to "$HOME/.local/bin"

    export PATH="$HOME/.local/bin:$PATH"
    success "just instalado"
}

# -----------------------------------------------------------------------------
# Passo 4 — Usar o just para configurar o projeto (venv + dependências)
# -----------------------------------------------------------------------------
project_setup() {
    info "Executando 'just setup'..."
    # Chamando nossa própria receita do justfile — fonte única da verdade para a configuração.
    just setup
}

# -----------------------------------------------------------------------------
# Main — orquestra os passos e imprime as próximas instruções
# -----------------------------------------------------------------------------
main() {
    echo ""
    echo "================================================"
    echo "  hash-identifier — instalação"
    echo "================================================"
    echo ""

    check_python
    install_uv
    install_just
    project_setup

    echo ""
    echo "================================================"
    success "Instalação concluída!"
    echo "================================================"
    echo ""
    echo "Próximos passos:"
    echo "  just run -- 5f4dcc3b5aa765d61d8327deb882cf99   # identificar um hash"
    echo "  just run -- --help                              # ver opções"
    echo "  just test                                       # executar a suíte de testes"
    echo ""
}

# `"$@"` encaminha todos os argumentos com os quais o script foi chamado para o main.
# Não usamos nenhum argumento hoje, mas manter esse padrão significa que flags
# futuras podem ser adicionadas sem alterar o final do arquivo.
main "$@"
