"""
Worker de PAGOS.

Hoy es un manejador simple. Mañana lo reemplazás por un agente completo
(con su prompt, herramientas de cobro y contrato) SIN tocar el orquestador:
solo cambiás la entrada en categorias/__init__.py.

Recibe al cliente ya identificado y devuelve: (mensaje, decision, requiere_humano).
"""


def manejar(cliente: dict):
    if cliente["deuda"] > 0:
        extra = ""
        if cliente.get("extension_pago", 0) > 0:
            extra = f" Tenés {cliente['extension_pago']} extensión(es) de pago vigente(s)."
        return (f"Registrás una deuda de ${cliente['deuda']:.0f}. Te paso los medios de pago.{extra}",
                "responder", False)
    return ("No tenés deuda pendiente. ¿Necesitás algo más?", "responder", False)
