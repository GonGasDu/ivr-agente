"""Worker de ASESOR ADMINISTRATIVO (single-turn). Interfaz uniforme iniciar/paso."""


def iniciar(cliente, hoy_dia=None):
    t = {"mensaje": "Te derivo con un asesor administrativo.", "decision": "derivar_asesor",
         "requiere_humano": True, "fin": True, "agente_destino": "asesor"}
    return None, t


def paso(sub, mensaje, clasificar):
    return {"mensaje": "Te derivo con un asesor.", "decision": "derivar_asesor",
            "requiere_humano": True, "fin": True, "agente_destino": "asesor"}
