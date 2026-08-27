"""Worker de SOPORTE TÉCNICO (single-turn). Interfaz uniforme iniciar/paso."""


def iniciar(cliente, hoy_dia=None):
    t = {"mensaje": f"Tu conexión figura: {cliente['estado_conexion']}. "
                    "Te derivo a soporte técnico con ese dato.",
         "decision": "derivar_soporte", "requiere_humano": True, "fin": True, "agente_destino": "soporte"}
    return None, t


def paso(sub, mensaje, clasificar):
    return {"mensaje": "Te derivo a soporte técnico.", "decision": "derivar_soporte",
            "requiere_humano": True, "fin": True, "agente_destino": "soporte"}
