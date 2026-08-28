"""
Herramientas registradas del agente (patrón de la Clase 4).

Lección de la Clase 4: describir una herramienta NO concede acceso. El acceso
existe solo si la función está en el registro HERRAMIENTAS y se ejecuta vía
ejecutar(). Aunque algo 'proponga' una herramienta, Python solo corre las permitidas.

Decisión de diseño (dominio = plata): en pagos, QUIÉN elige la herramienta y con
qué argumentos lo decide Python (máquina de estados + motor de política), NO el LLM.
Tomamos de la Clase 4 el registro y la ejecución controlada; no dejamos que un
modelo de 1.2B elija acciones de dinero.

Las acciones acá están SIMULADAS (devuelven ok). En producción escribirían en el
sistema de facturación / CRM.
"""
from agente.politica import politica


# --- solo lectura ---
def consultar_medios_pago():
    medios = politica().get("medios_pago", ["transferencia", "tarjeta", "efectivo"])
    return {"ok": True, "medios": medios}


# --- acciones (efecto sobre la cuenta) ---
def registrar_pago(nro_cliente, monto):
    return {"ok": True, "accion": "pago_registrado", "nro_cliente": nro_cliente, "monto": round(monto, 2)}


def aplicar_descuento(nro_cliente, porcentaje):
    return {"ok": True, "accion": "descuento_aplicado", "nro_cliente": nro_cliente, "porcentaje": porcentaje}


def registrar_extension(nro_cliente, hasta_dia, costo):
    return {"ok": True, "accion": "extension_registrada", "nro_cliente": nro_cliente,
            "hasta_dia": hasta_dia, "costo": costo}


def registrar_refinanciacion(nro_cliente, monto, cuotas):
    return {"ok": True, "accion": "refinanciacion_registrada", "nro_cliente": nro_cliente,
            "monto": round(monto, 2), "cuotas": cuotas}


HERRAMIENTAS = {
    "consultar_medios_pago":   consultar_medios_pago,
    "registrar_pago":          registrar_pago,
    "aplicar_descuento":       aplicar_descuento,
    "registrar_extension":     registrar_extension,
    "registrar_refinanciacion": registrar_refinanciacion,
}


def ejecutar(nombre, **argumentos):
    """El gate de la Clase 4: solo se ejecutan herramientas registradas."""
    if nombre not in HERRAMIENTAS:
        return {"ok": False, "error": f"herramienta no permitida: {nombre}"}
    return HERRAMIENTAS[nombre](**argumentos)
