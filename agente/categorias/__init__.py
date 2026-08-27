"""
Registro de categorías: LA COSTURA de los sub-agentes.

Cada worker expone la misma interfaz:
    iniciar(cliente, hoy_dia=None) -> (sub_estado, turno)
    paso(sub_estado, mensaje, clasificar) -> turno
El turno lleva la clave 'fin': True cuando el worker terminó su conversación.
Los workers simples terminan en iniciar; pagos es multi-turno.
"""
from . import facturacion, pagos, asesor, soporte

AGENTES_CATEGORIA = {
    "facturacion": facturacion,
    "pagos":       pagos,
    "asesor":      asesor,
    "soporte":     soporte,
}
