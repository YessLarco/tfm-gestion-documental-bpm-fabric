# Configuración del entorno Docker en Azure — BPM (Camunda) + Hyperledger Fabric


## 1. Recomendación de recurso de Azure

| Opción | Cuándo usarla | Por qué (no) en este caso |
|---|---|---|
| **VM + Docker Engine + Docker Compose** ✅ recomendado | Entornos de prueba/demo/tesis, control total de redes Docker, costo predecible | Es el equivalente más cercano a un entorno local; Fabric necesita redes Docker propias y volúmenes persistentes que Compose maneja de forma nativa |
| AKS (Kubernetes) | Producción a escala, múltiples nodos, autoescalado | Agrega complejidad (manifiestos, Helm) y costo que no aporta valor para validar un flujo BPM + Fabric |
| Azure Container Instances (ACI) | Contenedores aislados de corta duración | No maneja bien topologías multi-contenedor con redes personalizadas, como las que requiere Fabric (orderer, peers, CAs, CouchDB) |

**Tamaño sugerido de VM:** `Standard_D4s_v3` (4 vCPU / 16 GB RAM), disco de 128 GB.
Si notas lentitud al levantar Fabric + Camunda + Postgres + API Gateway al mismo tiempo,
sube a `Standard_D8s_v3`.

## 2. Orden de pasos

1. `az login`
2. Ejecutar `01-azure-vm-setup.sh` desde tu máquina local (requiere Azure CLI).
3. Conectarte por SSH a la IP pública que muestra el script.
4. Dentro de la VM, ejecutar `02-install-docker.sh`. Reconectar para que el grupo `docker` tome efecto.
5. Dentro de la VM, ejecutar `init-repo-structure.sh` (o clonar tu repositorio ya existente).
6. Clonar `fabric-samples` y levantar `test-network` (esto crea la red Docker `fabric_test`).
7. Copiar `.env.example` a `.env` dentro de `docker/` y completar los valores.
8. Copiar `docker-compose.yml` dentro de `docker/` y levantar el stack:
   ```bash
   cd docker
   docker compose up -d
   ```

## 3. Estructura del repositorio 

Resultado de ejecutar `init-repo-structure.sh`:

```
proyecto-bpm-fabric/
├── bpmn-models/
├── chaincode/
├── scripts-prueba/
├── docker/
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── api-gateway/
│   └── fabric-network/
│       ├── wallet/
│       └── connection-profile/
├── evidencias/
└── resultados/
```

## 4. Registro de versiones 

| Componente | Versión usada |
|---|---|
| Motor BPM (Camunda) | |
| SDK de Hyperledger Fabric | |
| Hyperledger Fabric | |
| Lenguaje del middleware (Go / Node / Python) | |
| Python | |
| Sistema operativo (VM Azure) | Ubuntu 22.04 LTS |
| Docker Engine | |
| Docker Compose | |

Tip: ejecuta `docker --version`, `docker compose version`, `fabric --version`
(o el binario `peer version`) y `camunda --version` (o revisa el tag de la imagen)
para completar esta tabla.

## 5. Variables de entorno y credenciales 

Ver `.env.example`. Resumen de cada bloque:

- **PostgreSQL**: credenciales de la base de datos off-chain y del motor Camunda.
- **Camunda**: usuario/clave del admin del BPMS y tag de imagen a usar.
- **API Gateway**: rutas al perfil de conexión y wallet de Fabric, nombre de canal y chaincode.
- **CA de Fabric**: credenciales de enrolamiento del admin de la organización.


## 6. Convención de nombres 

Definida como prefijos en `.env`:

- `DOC_ID_PREFIX` → identificador de documentos (ej. `DOC-2026-0001`)
- `PROCESS_INSTANCE_PREFIX` → instancias de proceso en Camunda (ej. `PI-2026-0001`)
- `TEST_FILE_PREFIX` → archivos de prueba (ej. `TEST-caso01-deploy.json`)

Recomendación: usar el mismo sufijo (numérico o timestamp) en los tres, para poder
correlacionar un `doc_id` con su instancia de proceso, su evidencia (`evidencias/`)
y su resultado on-chain/off-chain.

## 7. Seguridad y costos en Azure

- Apaga la VM (`az vm stop`) cuando no la uses, para no generar costos de cómputo.
- Restringe el puerto 22 (SSH) a tu IP en el NSG en vez de dejarlo abierto a `*`.
- Si el proyecto pasa a un entorno compartido, considera mover las credenciales
  de `.env` a Azure Key Vault.
