"""
Motor de política de pagos (la "herramienta" que consulta el agente).

Lee datos/politica_pagos.json —la fuente de verdad editable— y evalúa qué le
corresponde a cada cliente. Es la capa determinista: dada la situación del cliente,
Python decide qué ofertas son válidas. El LLM solo interpreta lo que dice el cliente.

Cambiar la política = editar el JSON. Este módulo no tiene números "hardcodeados".
"""
import json
import os
from datetime import date

RUTA_POLITICA = os.environ.get("IVR_POLITICA", "datos/politica_pagos.json")

_POL = None


def cargar_politica(ruta: str = RUTA_POLITICA) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def politica() -> dict:
    global _POL
    if _POL is None:
        _POL = cargar_politica()
    return _POL


def antiguedad_meses(cliente: dict, hoy: date | None = None) -> int:
    hoy = hoy or date.today()
    alta = date.fromisoformat(cliente["fecha_alta"])
    return (hoy.year - alta.year) * 12 + (hoy.month - alta.month)


def situacion(cliente: dict) -> str:
    """Carril determinista según la situación de cuenta del cliente."""
    esc = politica()["escalar_a_humano"]
    if cliente.get("estado_contrato") in esc["contratos"]:
        return "humano"
    f = cliente.get("facturas_adeudadas", 0)
    if f == 0:
        return "al_dia"
    if f >= esc["facturas_adeudadas_min"]:          # 3 o más
        return "humano"
    if f == 1 and cliente.get("saldo_refinanciar", 0) > 0:
        return "segunda_llamada"
    if f == 2:
        return "rehabilitacion"
    return "negociacion"                            # f == 1


def puede_extension(cliente: dict, dia_actual: int | None = None) -> dict:
    pol = politica()["extension_pago"]
    dia_actual = dia_actual if dia_actual is not None else date.today().day
    if cliente.get("facturas_adeudadas", 0) > pol["aplica_si_facturas_adeudadas_max"]:
        return {"disponible": False, "motivo": "aplica solo con hasta 1 factura"}
    if cliente.get("extension_pago", 0) >= pol["max_por_ciclo"]:
        return {"disponible": False, "motivo": "ya usó las 2 extensiones"}
    nueva = min(dia_actual + pol["dias_por_extension"], pol["tope_dia_mes"])
    if nueva <= dia_actual:
        return {"disponible": False, "motivo": "sin margen antes del día 30"}
    return {"disponible": True, "nueva_fecha_dia": nueva, "costo": pol["costo"]}


def monto_rehabilitacion(cliente: dict) -> dict:
    """75% de la deuda con 10% de descuento sobre ese pago."""
    pol = politica()["rehabilitacion_2_facturas"]
    base = cliente["deuda"] * pol["porcentaje_pago"] / 100
    a_pagar = base * (1 - pol["descuento_sobre_ese_pago"] / 100)
    return {"a_pagar": round(a_pagar, 2), "resto": round(cliente["deuda"] - base, 2)}


def descuento_maximo(cliente: dict, motivo: str, hoy: date | None = None) -> str:
    """Devuelve hasta qué escalón puede llegar el agente antes de derivar a humano."""
    pol = politica()["negociacion_descuento"]
    if motivo == "competencia":
        return "competencia"                        # 20% x 2, directo
    if antiguedad_meses(cliente, hoy) >= pol["antiguedad_minima_meses"]:
        return "nivel_2"                            # 10% -> 20%/5x3 -> humano
    return "nivel_1"                                # solo 10% -> humano
