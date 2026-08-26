"""
Registro de categorías: LA COSTURA de los futuros sub-agentes.

El orquestador enruta a la categoría y llama a su `manejar(cliente)`.
Para enchufar un agente real, reemplazás el valor por la función del agente:

    from agente.agentes.pagos import agente_pagos
    AGENTES_CATEGORIA["pagos"] = agente_pagos

...y no tocás el orquestador (patrón orchestrator–workers).
"""
from . import facturacion, pagos, asesor, soporte

AGENTES_CATEGORIA = {
    "facturacion": facturacion.manejar,
    "pagos":       pagos.manejar,
    "asesor":      asesor.manejar,
    "soporte":     soporte.manejar,
}
