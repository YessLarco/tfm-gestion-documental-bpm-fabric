# ============================================================
# Aprovisiona una VM en Azure para correr Docker + Docker Compose
# (Camunda + Hyperledger Fabric + API Gateway)
#
# Requisitos: Azure CLI instalado y autenticado (az login)
# Ejecutar en PowerShell, desde TU MÁQUINA WINDOWS.
#
# Uso:
#   .\01-azure-vm-setup.ps1
# ============================================================

# --- Variables configurables ---
$ResourceGroup = "rg-bpm-fabric"
$Location      = "eastus2"           # cambia esto si tu suscripción no permite esta región (ver mensaje de error)
$VmName        = "vm-bpm-fabric"
$VmSize        = "Standard_D4s_v3"    # 4 vCPU / 16 GB RAM. Sube a D8s_v3 si necesitas más holgura
$AdminUser     = "azureuser"
$OsDiskSizeGB  = 128

Write-Host ">> Creando grupo de recursos..."
az group create `
  --name $ResourceGroup `
  --location $Location

Write-Host ">> Creando VM Ubuntu 22.04 LTS..."
az vm create `
  --resource-group $ResourceGroup `
  --name $VmName `
  --image "Canonical:0001-com-ubuntu-server-jammy:22_04-lts:latest" `
  --size $VmSize `
  --admin-username $AdminUser `
  --generate-ssh-keys `
  --os-disk-size-gb $OsDiskSizeGB `
  --public-ip-sku Standard

Write-Host ">> Abriendo puertos necesarios..."
# 22   -> SSH (idealmente restringir luego a tu IP)
# 8080 -> Camunda
# 3000 -> API Gateway
# 7050-7054 -> Orderer / Peers / CA de Fabric (test-network)
# 5984 -> CouchDB (state DB de Fabric, opcional exponerlo)
az vm open-port --resource-group $ResourceGroup --name $VmName --port 22        --priority 1000
az vm open-port --resource-group $ResourceGroup --name $VmName --port 8080      --priority 1010
az vm open-port --resource-group $ResourceGroup --name $VmName --port 3000      --priority 1020
az vm open-port --resource-group $ResourceGroup --name $VmName --port 7050-7054 --priority 1030
az vm open-port --resource-group $ResourceGroup --name $VmName --port 5984      --priority 1040

Write-Host ">> Listo. Datos de conexión:"
$PublicIp = az vm show -d -g $ResourceGroup -n $VmName --query publicIps -o tsv
Write-Host "IP publica: $PublicIp"
Write-Host "Conectate con: ssh $AdminUser@$PublicIp"
Write-Host ""
Write-Host "Siguiente paso: conectate por SSH y ejecuta 02-install-docker.sh (eso si es bash, pero corre DENTRO de la VM Ubuntu, no en tu PC)."
