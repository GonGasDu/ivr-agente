"""
Registro de categorías (la costura de los sub-agentes).

Taxonomía en la puerta (clasificador): cuenta / soporte / administrativo.
'cuenta' unifica facturación + pagos y ramifica info/pago adentro.
Cada worker: iniciar(cliente, mensaje, clasificar) -> (sub, turno) ; paso(...).
"""
from . import cuenta, soporte, administrativo

AGENTES_CATEGORIA = {
    "cuenta":         cuenta,
    "soporte":        soporte,
    "administrativo": administrativo,
}
