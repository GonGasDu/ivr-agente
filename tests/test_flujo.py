"""
Tests deterministas del flujo, SIN el modelo real.

Inyectamos un clasificador simulado y un CRM en memoria. Prueba que Python
—el que conserva el control— decide bien: identificación, reintento alternado,
derivación a humano y ruteo a categoría.

Correr desde la raíz del repo:   python -m pytest -q   (o: python tests/test_flujo.py)
"""
from agente.orquestador import orquestador, nuevo_estado

# --- CRM falso en memoria (esquema nuevo: nro de 6 dígitos) ---
_CLIENTES = {
    "36956909": {"nombre": "Ana Test", "dni": "36956909", "nro_cliente": "480001",
                 "plan": "FOEmp500", "velocidad_mbps": 500, "abono_mensual": 120000,
                 "deuda": 8500.0, "extension_pago": 1, "estado_conexion": "Cortada"},
    "480002": {"nombre": "Carlos Test", "dni": "27888999", "nro_cliente": "480002",
               "plan": "WIHogar60", "velocidad_mbps": 60, "abono_mensual": 16000,
               "deuda": 0.0, "extension_pago": 0, "estado_conexion": "Cortada"},
}


def buscar_fake(ident):
    return _CLIENTES.get(ident)


def clasificar_fake(mensaje, opciones):
    m = mensaje.lower()
    tabla = {
        "contratar": ["contratar", "nuevo"], "cliente": ["cliente", "reclamo", "problema"],
        "hogar": ["hogar", "casa"], "empresa": ["empresa", "oficina"],
        "facturacion": ["factura"], "pagos": ["pagar", "deuda", "abonar"],
        "asesor": ["asesor"], "soporte": ["internet", "soporte", "conexion", "conexión"],
    }
    for op in opciones:
        if any(kw in m for kw in tabla.get(op, [])):
            return op
    return "otro"


def correr(mensajes):
    estado = nuevo_estado()
    ultimo = None
    for msg in mensajes:
        ultimo = orquestador(estado, msg, clasificar=clasificar_fake, buscar=buscar_fake)
    return ultimo


def test_cliente_identificado_va_a_pagos():
    r = correr(["soy cliente", "mi DNI es 36.956.909", "quiero abonar la deuda"])
    assert r["agente_destino"] == "pagos"
    assert "8500" in r["mensaje"]


def test_identifica_por_numero_de_cliente_6_digitos():
    r = correr(["soy cliente", "mi numero es 480002", "una factura"])
    assert r["agente_destino"] == "facturacion"


def test_reintento_alternado_pide_el_otro_documento():
    estado = nuevo_estado()
    orquestador(estado, "soy cliente", clasificar=clasificar_fake, buscar=buscar_fake)
    r = orquestador(estado, "mi numero de cliente 999999", clasificar=clasificar_fake, buscar=buscar_fake)
    assert "DNI" in r["mensaje"]
    assert r["nodo"] == "identificar"


def test_fallan_los_dos_deriva_a_humano():
    r = correr(["soy cliente", "DNI 11111111", "numero 999999"])
    assert r["decision"] == "derivar_asesor"
    assert r["requiere_humano"] is True


def test_contratar_empresa_va_a_ventas():
    r = correr(["quiero contratar", "es para mi oficina"])
    assert r["decision"] == "derivar_ventas"


def test_soporte_incluye_estado_de_conexion():
    r = correr(["tengo un reclamo", "480002", "hace horas que no tengo internet"])
    assert r["agente_destino"] == "soporte"
    assert "Cortada" in r["mensaje"]


if __name__ == "__main__":
    import sys, traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    fallos = 0
    for fn in fns:
        try:
            fn(); print(f"PASS  {fn.__name__}")
        except AssertionError:
            fallos += 1; print(f"FAIL  {fn.__name__}"); traceback.print_exc()
    print(f"\n{len(fns) - fallos}/{len(fns)} tests OK")
    sys.exit(1 if fallos else 0)
