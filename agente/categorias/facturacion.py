"""Worker de FACTURACIÓN (single-turn). Interfaz uniforme iniciar/paso."""


def iniciar(cliente, hoy_dia=None):
    t = {"mensaje": f"Tu plan es {cliente['plan']} ({cliente['velocidad_mbps']} Mbps), "
                    f"abono ${cliente['abono_mensual']:.0f}. Deuda actual: ${cliente['deuda']:.0f}.",
         "decision": "responder", "requiere_humano": False, "fin": True, "agente_destino": "facturacion"}
    return None, t


def paso(sub, mensaje, clasificar):
    return {"mensaje": "¿Algo más sobre tu factura?", "decision": "fin",
            "requiere_humano": False, "fin": True, "agente_destino": "facturacion"}
