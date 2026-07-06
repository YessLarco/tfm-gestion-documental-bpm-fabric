"""
Escenario B — Tasa de Detección de Manipulaciones (TDR)

Ejecuta 40 intentos de manipulación (5 por cada uno de 8 tipos de ataque)
contra el chaincode `gestiondocumental` y mide cuántos son bloqueados
correctamente.

Tipos de ataque:
  1. SoD-1: el registrador intenta aprobar revisión
  2. SEQ-1: publicar antes de aprobación legal
  3. UNI-1: crear dos veces el mismo doc_id
  4. ABAC: rol incorrecto en una función (revisor invoca AprobarLegal)
  5. Inmutabilidad: registrador "ajeno" intenta actualizar evidencia
  6. HASH-1: archivo off-chain alterado, VerificarIntegridad debe detectarlo
  7. Estado-máquina: reenviar un documento que no fue rechazado
  8. Sin atributo role: identidad por defecto (User1) intenta operar

TDR = bloqueos_correctos / total_intentos * 100

Uso (dentro de la VM):
    source ~/escenario-a/venv/bin/activate    # reusa el entorno
    python3 escenario_b.py --reporte ~/reporte_B.json --intentos-por-tipo 5
"""

import argparse
import hashlib
import json
import os
import random
import string
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


# ---------- Configuración base ----------
PEER_BIN = "/home/azureuser/bpm-fabric/fabric/fabric-samples/bin/peer"
TEST_NETWORK = "/home/azureuser/bpm-fabric/fabric/fabric-samples/test-network"
FABRIC_CFG = "/home/azureuser/bpm-fabric/fabric/fabric-samples/config"
CHANNEL = "mychannel"
CHAINCODE = "gestiondocumental"
OFFCHAIN_ROOT = "/opt/tfm-camunda/offchain"

# Rutas a los certificados de cada identidad
def msp_path(rol):
    return f"{TEST_NETWORK}/organizations/peerOrganizations/org1.example.com/users/{rol}@org1.example.com/msp"

PEER_TLS_CA = f"{TEST_NETWORK}/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt"
ORDERER_CA = f"{TEST_NETWORK}/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem"
PEER2_TLS_CA = f"{TEST_NETWORK}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt"


# ---------- Helpers para invocar al chaincode con una identidad ----------
def _env(rol):
    return {
        "PATH": f"{TEST_NETWORK}/../bin:/usr/bin:/bin",
        "FABRIC_CFG_PATH": FABRIC_CFG,
        "CORE_PEER_TLS_ENABLED": "true",
        "CORE_PEER_LOCALMSPID": "Org1MSP",
        "CORE_PEER_TLS_ROOTCERT_FILE": PEER_TLS_CA,
        "CORE_PEER_MSPCONFIGPATH": msp_path(rol),
        "CORE_PEER_ADDRESS": "localhost:7051",
    }


def invoke(rol, funcion, args):
    cmd = [
        PEER_BIN, "chaincode", "invoke",
        "-o", "localhost:7050", "--ordererTLSHostnameOverride", "orderer.example.com",
        "--tls", "--cafile", ORDERER_CA,
        "-C", CHANNEL, "-n", CHAINCODE,
        "--peerAddresses", "localhost:7051", "--tlsRootCertFiles", PEER_TLS_CA,
        "--peerAddresses", "localhost:9051", "--tlsRootCertFiles", PEER2_TLS_CA,
        "-c", json.dumps({"function": funcion, "Args": args}),
    ]
    res = subprocess.run(cmd, env=_env(rol), capture_output=True, text=True, timeout=30)
    return {
        "returncode": res.returncode,
        "stdout": res.stdout.strip(),
        "stderr": res.stderr.strip(),
    }


def query(rol, funcion, args):
    cmd = [
        PEER_BIN, "chaincode", "query",
        "-C", CHANNEL, "-n", CHAINCODE,
        "-c", json.dumps({"function": funcion, "Args": args}),
    ]
    res = subprocess.run(cmd, env=_env(rol), capture_output=True, text=True, timeout=30)
    return {
        "returncode": res.returncode,
        "stdout": res.stdout.strip(),
        "stderr": res.stderr.strip(),
    }


# ---------- Utilidades de setup ----------
def random_doc_id(prefix="DOC-B"):
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix}-{suffix}"


def sha256_string(s):
    return hashlib.sha256(s.encode()).hexdigest()


def crear_documento_helper(doc_id):
    """Crea un documento legítimamente como registrador (para setup de ataques).
       Espera 5s para asegurar que la transacción se comprometa antes de seguir."""
    hash_doc = sha256_string(f"contenido_{doc_id}")
    res = invoke("registrador", "CrearDocumento", [doc_id, hash_doc, "1"])
    time.sleep(5)  # esperar commit en el ledger antes de seguir
    return res, hash_doc


def aprobar_revisor_helper(doc_id):
    res = invoke("revisor", "AprobarRevision", [doc_id, "true", "OK"])
    time.sleep(5)
    return res

def aprobar_legal_helper(doc_id):
    res = invoke("legal", "AprobarLegal", [doc_id, "true", "OK"])
    time.sleep(5)
    return res

def publicar_helper(doc_id):
    return invoke("publicador", "PublicarDocumento", [doc_id])


# ---------- Evaluador de un ataque ----------
def es_bloqueado(resultado_invoke):
    """Un ataque está correctamente bloqueado si el invoke devolvió error
       (returncode != 0 o mensaje de error específico en stderr)."""
    if resultado_invoke["returncode"] != 0:
        return True
    stderr = resultado_invoke["stderr"].lower()
    if "error" in stderr or "denegado" in stderr or "violado" in stderr:
        return True
    return False


# ---------- Los 8 tipos de ataques ----------
def ataque_1_sod_registrador_aprueba(intento):
    """SoD-1: registrador intenta aprobar revisión."""
    doc_id = random_doc_id("DOC-B-SOD")
    crear_documento_helper(doc_id)
    res = invoke("registrador", "AprobarRevision", [doc_id, "true", "intento ilegal"])
    return {
        "tipo": "SoD-1",
        "descripcion": "Registrador intenta aprobar revisión",
        "doc_id": doc_id,
        "bloqueado": es_bloqueado(res),
        "mensaje_chaincode": res["stderr"][-300:] if res["stderr"] else "",
    }


def ataque_2_seq_publicar_sin_legal(intento):
    """SEQ-1: publicar sin pasar por aprobación legal."""
    doc_id = random_doc_id("DOC-B-SEQ")
    crear_documento_helper(doc_id)
    # No aprobamos ni revisor ni legal; intentamos publicar directo
    res = invoke("publicador", "PublicarDocumento", [doc_id])
    return {
        "tipo": "SEQ-1",
        "descripcion": "Publicar sin aprobación legal",
        "doc_id": doc_id,
        "bloqueado": es_bloqueado(res),
        "mensaje_chaincode": res["stderr"][-300:] if res["stderr"] else "",
    }


def ataque_3_uni_duplicar_docid(intento):
    """UNI-1: crear dos veces el mismo doc_id."""
    doc_id = random_doc_id("DOC-B-UNI")
    crear_documento_helper(doc_id)
    # Intentar crear otra vez con el mismo ID
    res = invoke("registrador", "CrearDocumento", [doc_id, sha256_string("v2"), "1"])
    return {
        "tipo": "UNI-1",
        "descripcion": "Duplicar doc_id",
        "doc_id": doc_id,
        "bloqueado": es_bloqueado(res),
        "mensaje_chaincode": res["stderr"][-300:] if res["stderr"] else "",
    }


def ataque_4_abac_rol_incorrecto(intento):
    """ABAC: revisor intenta invocar AprobarLegal (no le toca)."""
    doc_id = random_doc_id("DOC-B-ABAC")
    crear_documento_helper(doc_id)
    aprobar_revisor_helper(doc_id)
    # Revisor intenta hacer la aprobación legal
    res = invoke("revisor", "AprobarLegal", [doc_id, "true", "uso indebido"])
    return {
        "tipo": "ABAC",
        "descripcion": "Revisor intenta hacer AprobarLegal",
        "doc_id": doc_id,
        "bloqueado": es_bloqueado(res),
        "mensaje_chaincode": res["stderr"][-300:] if res["stderr"] else "",
    }


def ataque_5_inmutabilidad_otro_registrador(intento):
    """Inmutabilidad: un actor que NO es el registrador original intenta
    actualizar la evidencia del documento. El chaincode debe rechazar."""
    doc_id = random_doc_id("DOC-B-INMUT")
    crear_documento_helper(doc_id)
    # El revisor intenta actualizar la evidencia (no es el registrador original)
    res = invoke("revisor", "ActualizarEvidencia", [doc_id, sha256_string("hash_alterado"), "1"])
    return {
        "tipo": "INMUTABILIDAD",
        "descripcion": "Revisor intenta ActualizarEvidencia (no es el registrador original)",
        "doc_id": doc_id,
        "bloqueado": es_bloqueado(res),
        "mensaje_chaincode": res["stderr"][-300:] if res["stderr"] else "",
    }


def ataque_6_hash_archivo_alterado(intento):
    """HASH-1: simulamos manipulación física del PDF off-chain y verificamos
    que VerificarIntegridad lo detecte."""
    doc_id = random_doc_id("DOC-B-HASH")
    _, hash_original = crear_documento_helper(doc_id)
    # Simulamos que el hash del archivo "post-manipulación" es distinto
    hash_alterado = sha256_string(f"contenido_alterado_{doc_id}")
    res = query("auditor", "VerificarIntegridad", [doc_id, hash_alterado])
    # Aquí "bloqueado" se interpreta como: el chaincode detectó la manipulación
    # (coincide=false)
    coincide_false_detectado = '"coincide":false' in res["stdout"] or '"coincide": false' in res["stdout"]
    return {
        "tipo": "HASH-1",
        "descripcion": "Archivo off-chain alterado, VerificarIntegridad debe detectar",
        "doc_id": doc_id,
        "bloqueado": coincide_false_detectado,
        "mensaje_chaincode": res["stdout"][:300] if res["stdout"] else res["stderr"][-300:],
    }


def ataque_7_estado_maquina_reenviar_sin_rechazo(intento):
    """Estado-máquina: intentar RegistrarReenviado sobre un documento que
    está en CREADO o APROBADO_REVISOR (no en RECHAZADO_*)."""
    doc_id = random_doc_id("DOC-B-ESTADO")
    crear_documento_helper(doc_id)
    # El documento está en CREADO; intentamos reenviar (debería requerir RECHAZADO_*)
    res = invoke("registrador", "RegistrarReenviado", [doc_id, sha256_string("nuevo"), "2"])
    return {
        "tipo": "ESTADO_MAQUINA",
        "descripcion": "Reenviar documento en estado CREADO (no rechazado)",
        "doc_id": doc_id,
        "bloqueado": es_bloqueado(res),
        "mensaje_chaincode": res["stderr"][-300:] if res["stderr"] else "",
    }


def ataque_8_sin_atributo_role(intento):
    """Identidad por defecto (User1) sin atributo role= intenta crear documento."""
    doc_id = random_doc_id("DOC-B-NOROLE")
    res = invoke("User1", "CrearDocumento", [doc_id, sha256_string(doc_id), "1"])
    return {
        "tipo": "SIN_ROLE",
        "descripcion": "User1 sin atributo role intenta CrearDocumento",
        "doc_id": doc_id,
        "bloqueado": es_bloqueado(res),
        "mensaje_chaincode": res["stderr"][-300:] if res["stderr"] else "",
    }


# ---------- Main ----------
ATAQUES = [
    ("SoD-1", ataque_1_sod_registrador_aprueba),
    ("SEQ-1", ataque_2_seq_publicar_sin_legal),
    ("UNI-1", ataque_3_uni_duplicar_docid),
    ("ABAC", ataque_4_abac_rol_incorrecto),
    ("INMUTABILIDAD", ataque_5_inmutabilidad_otro_registrador),
    ("HASH-1", ataque_6_hash_archivo_alterado),
    ("ESTADO_MAQUINA", ataque_7_estado_maquina_reenviar_sin_rechazo),
    ("SIN_ROLE", ataque_8_sin_atributo_role),
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--reporte", default="/home/azureuser/reporte_B.json")
    p.add_argument("--intentos-por-tipo", type=int, default=5)
    args = p.parse_args()

    inicio_global = time.time()
    resultados = []
    print(f"Ejecutando {args.intentos_por_tipo} intentos por cada uno de {len(ATAQUES)} tipos = "
          f"{args.intentos_por_tipo * len(ATAQUES)} ataques totales\n")

    for nombre, fn in ATAQUES:
        print(f"--- Ataque: {nombre} ---")
        for i in range(1, args.intentos_por_tipo + 1):
            print(f"  [{i}/{args.intentos_por_tipo}]", end=" ", flush=True)
            try:
                r = fn(i)
            except Exception as e:
                r = {
                    "tipo": nombre,
                    "descripcion": f"EXCEPCIÓN al ejecutar: {e}",
                    "doc_id": "(n/a)",
                    "bloqueado": False,
                    "mensaje_chaincode": str(e),
                }
            r["intento"] = i
            r["timestamp"] = datetime.now(timezone.utc).isoformat()
            resultados.append(r)
            print(f"bloqueado={r['bloqueado']} ({r['doc_id']})")
            time.sleep(1.0)  # evitar saturar al peer

    # ---- Reporte ----
    total = len(resultados)
    bloqueados = sum(1 for r in resultados if r["bloqueado"])
    tdr = (bloqueados / total) * 100 if total else 0

    # Por categoría
    por_tipo = {}
    for r in resultados:
        t = r["tipo"]
        por_tipo.setdefault(t, {"total": 0, "bloqueados": 0})
        por_tipo[t]["total"] += 1
        if r["bloqueado"]:
            por_tipo[t]["bloqueados"] += 1
    for t, v in por_tipo.items():
        v["tdr"] = round(v["bloqueados"] / v["total"] * 100, 2)

    reporte = {
        "fecha": datetime.now(timezone.utc).isoformat(),
        "duracion_segundos": round(time.time() - inicio_global, 1),
        "total_intentos": total,
        "bloqueados_correctamente": bloqueados,
        "TDR_porcentaje": round(tdr, 2),
        "por_tipo": por_tipo,
        "detalle": resultados,
    }

    Path(args.reporte).write_text(json.dumps(reporte, indent=2, ensure_ascii=False))

    print()
    print("=" * 60)
    print("RESUMEN ESCENARIO B")
    print("=" * 60)
    print(f"Total intentos:           {total}")
    print(f"Bloqueados correctamente: {bloqueados}")
    print(f"TDR global:               {tdr:.2f}%")
    print()
    print(f"{'Tipo':<20} {'Bloqueados/Total':<20} {'TDR':<10}")
    print("-" * 50)
    for t, v in por_tipo.items():
        print(f"{t:<20} {v['bloqueados']}/{v['total']:<19} {v['tdr']:.2f}%")
    print()
    print(f"Reporte detallado en: {args.reporte}")


if __name__ == "__main__":
    main()
