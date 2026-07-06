#!/usr/bin/env bash
# ============================================================
# Crea la estructura de carpetas del repositorio de trabajo
# (Paso 1, punto 1)
#
# Uso: ./init-repo-structure.sh [nombre-carpeta-raiz]
# ============================================================

set -e

ROOT_DIR="${1:-proyecto-bpm-fabric}"

mkdir -p "$ROOT_DIR"/{bpmn-models,chaincode,scripts-prueba,evidencias,resultados}
mkdir -p "$ROOT_DIR"/docker/{api-gateway,fabric-network/wallet,fabric-network/connection-profile}

cat > "$ROOT_DIR/.gitignore" << 'EOF'
.env
docker/fabric-network/wallet/*
node_modules/
*.log
EOF

cat > "$ROOT_DIR/README.md" << 'EOF'
# Proyecto BPM + Hyperledger Fabric

Estructura de carpetas:
- bpmn-models/      -> modelos BPMN
- chaincode/         -> código de los contratos inteligentes
- scripts-prueba/    -> scripts de prueba
- docker/            -> configuración Docker (compose, .env, api-gateway, red de Fabric)
- evidencias/        -> capturas, logs y evidencias de ejecución
- resultados/        -> resultados de las pruebas

Ver docker/README.md para la guía de configuración del entorno en Azure
y el registro de versiones de cada componente.
EOF

echo "Estructura creada en: $ROOT_DIR"
find "$ROOT_DIR" -maxdepth 3 -type d | sort
