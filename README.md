# tfm-gestion-documental-bpm-fabric
Repositorio digital con archivos y evidencias para reproducir TFM de gestión documental con BPMN y Blockchain

# Trazabilidad documental con BPMN, API Gateway y Hyperledger Fabric

Piloto experimental del TFM (Luis Carrión y Yessenia Larco).

## Contenido
- bpmn/, api-gateway/, chaincode/, scripts/, datos/, reportes/

## Requisitos
Camunda 7.24, Hyperledger Fabric v2.5, Go, Python 3, Ubuntu 22.04.

## Reproducción rápida
1. Levantar la red Fabric y crear el canal.
2. Emitir las 5 identidades X.509 (registrador, revisor, legal, publicador, auditor).
3. Desplegar el chaincode y el modelo BPMN.
4. Arrancar el Worker y ejecutar los escenarios A y B.

## Nota
Los datos son sintéticos. El material criptográfico y las credenciales
no se incluyen por seguridad.
