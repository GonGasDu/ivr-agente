"""Worker de SOPORTE TÉCNICO (single-turn). Problemas de conexión, instalación,
turnos de técnicos, contraseña del wifi, etc."""


def iniciar(cliente, mensaje="", clasificar=None, hoy_dia=None):
    t = {"mensaje": f"Tu conexión figura: {cliente['estado_conexion']}. "
                    "Te derivo a soporte técnico con ese dato.",
         "decision": "derivar_soporte", "requiere_humano": True, "fin": True,
         "agente_destino": "soporte"}
    return None, t


def paso(sub, mensaje, clasificar):
    return {"mensaje": "Te derivo a soporte técnico.", "decision": "derivar_soporte",
            "requiere_humano": True, "fin": True, "agente_destino": "soporte"}
