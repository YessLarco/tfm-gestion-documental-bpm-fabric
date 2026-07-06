#!/usr/bin/env bash
# ============================================================
# Instala Docker Engine + Docker Compose plugin
# Ejecutar DENTRO de la VM de Azure (después de hacer ssh)
# ============================================================

set -e

echo ">> Actualizando paquetes..."
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

echo ">> Agregando repositorio oficial de Docker..."
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo ">> Instalando Docker Engine y plugins..."
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo ">> Permitiendo ejecutar docker sin sudo..."
sudo usermod -aG docker "$USER"

echo ""
echo ">> Instalación completa. Cierra sesión y vuelve a conectarte por SSH"
echo "   (o ejecuta 'newgrp docker') para que el grupo 'docker' tome efecto."
echo ""
echo "Verificación tras reconectar:"
echo "  docker --version"
echo "  docker compose version"
