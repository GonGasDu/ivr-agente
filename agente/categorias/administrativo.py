"""Worker ADMINISTRATIVO (single-turn). Trámites/reclamos: cambio de titularidad,
cambio de datos, etc. Van a un humano (verifican identidad, son sensibles)."""


def iniciar(cliente, mensaje="", clasificar=None, hoy_dia=None):
    t = {"mensaje": "Para trámites administrativos como cambio de titularidad o de datos, "
                    "te derivo con un asesor que va a verificar tu identidad y ayudarte.",
         "decision": "derivar_asesor", "requiere_humano": True, "fin": True,
         "agente_destino": "administrativo"}
    return None, t


def paso(sub, mensaje, clasificar):
    return {"mensaje": "Te derivo con un asesor administrativo.", "decision": "derivar_asesor",
            "requiere_humano": True, "fin": True, "agente_destino": "administrativo"}
