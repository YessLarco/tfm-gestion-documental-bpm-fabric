#!/usr/bin/env bash
# ============================================================
# Aprovisiona una VM en Azure para correr Docker + Docker Compose
# (Camunda + Hyperledger Fabric + API Gateway)
#
# Requisitos: Azure CLI instalado y autenticado (az login)
# Ejecutar desde TU MÁQUINA LOCAL, no dentro de la VM.
# ============================================================

set -e

# --- Variables configurables ---
RESOURCE_GROUP="rg-bpm-fabric"
LOCATION="eastus"            # cambia a la región que prefieras
VM_NAME="vm-bpm-fabric"
VM_SIZE="Standard_D4s_v3"     # 4 vCPU / 16 GB RAM. Sube a D8s_v3 si necesitas más holgura
ADMIN_USER="azureuser"
OS_DISK_SIZE_GB=128

echo ">> Creando grupo de recursos..."
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION"

echo ">> Creando VM Ubuntu 22.04 LTS..."
az vm create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$VM_NAME" \
  --image "Canonical:0001-com-ubuntu-server-jammy:22_04-lts:latest" \
  --size "$VM_SIZE" \
  --admin-username "$ADMIN_USER" \
  --generate-ssh-keys \
  --os-disk-size-gb "$OS_DISK_SIZE_GB" \
  --public-ip-sku Standard

echo ">> Abriendo puertos necesarios..."
# 22   -> SSH (idealmente restringir luego a tu IP)
# 8080 -> Camunda
# 3000 -> API Gateway
# 7050-7054 -> Orderer / Peers / CA de Fabric (test-network)
# 5984 -> CouchDB (state DB de Fabric, opcional exponerlo)
az vm open-port --resource-group "$RESOURCE_GROUP" --name "$VM_NAME" --port 22           --priority 1000
az vm open-port --resource-group "$RESOURCE_GROUP" --name "$VM_NAME" --port 8080         --priority 1010
az vm open-port --resource-group "$RESOURCE_GROUP" --name "$VM_NAME" --port 3000         --priority 1020
az vm open-port --resource-group "$RESOURCE_GROUP" --name "$VM_NAME" --port 7050-7054    --priority 1030
az vm open-port --resource-group "$RESOURCE_GROUP" --name "$VM_NAME" --port 5984         --priority 1040

echo ">> Listo. Datos de conexión:"
PUBLIC_IP=$(az vm show -d -g "$RESOURCE_GROUP" -n "$VM_NAME" --query publicIps -o tsv)
echo "IP pública: $PUBLIC_IP"
echo "Conéctate con: ssh ${ADMIN_USER}@${PUBLIC_IP}"
echo ""
echo "Siguiente paso: copia 02-install-docker.sh a la VM y ejecútalo."
