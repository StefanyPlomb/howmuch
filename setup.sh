#!/usr/bin/env sh
# Passo obrigatório antes do primeiro `make up`: garante que o `make` (e o
# Docker, que é o que o `make up` usa) existam na máquina.
# Uso:  sh setup.sh && make up
set -eu

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    echo "!! Execute como root ou instale o sudo." >&2
    exit 1
  fi
fi

if command -v make >/dev/null 2>&1; then
  echo ">> make já instalado: $(make --version | head -n1)"
else
  echo ">> Instalando make..."
  if command -v apt-get >/dev/null 2>&1; then
    $SUDO apt-get update && $SUDO apt-get install -y make
  elif command -v dnf >/dev/null 2>&1; then
    $SUDO dnf install -y make
  elif command -v yum >/dev/null 2>&1; then
    $SUDO yum install -y make
  elif command -v pacman >/dev/null 2>&1; then
    $SUDO pacman -Sy --noconfirm make
  elif command -v zypper >/dev/null 2>&1; then
    $SUDO zypper install -y make
  elif command -v apk >/dev/null 2>&1; then
    $SUDO apk add make
  elif command -v brew >/dev/null 2>&1; then
    brew install make
  else
    echo "!! Gerenciador de pacotes não reconhecido. Instale o 'make' manualmente." >&2
    exit 1
  fi
  echo ">> make instalado: $(make --version | head -n1)"
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "!! Docker não encontrado. Instale em https://docs.docker.com/engine/install/ e rode de novo." >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "!! Docker Compose (plugin 'docker compose') não encontrado." >&2
  exit 1
fi

echo ">> Tudo certo. Agora rode: make up"
