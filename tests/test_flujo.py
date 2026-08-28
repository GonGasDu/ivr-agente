"""
Tests deterministas del flujo, SIN el modelo real.

Inyectan un clasificador simulado y un CRM en memoria. Prueban que Python
—el que conserva el control— decide bien: identificación, reintento alternado,
derivación, ruteo, la negociación multi-turno de pagos y la desambiguación.

Correr desde la raíz:   python -m pytest -q   (o: python tests/test_flujo.py)
"""
from agente.orquestador import orquestador, nuevo_estado

_CLIENTES = {
    # debe 1 factura, conexión afectada por pago
    "36956909": {"nombre": "Ana Test", "dni": "36956909", "nro_cliente": "480001",
                 "plan": "FOEmp500", "velocidad_mbps": 500, "abono_mensual": 120000,
                 "deuda": 8500.0, "extension_pago": 1, "estado_conexion": "Cortada",
                 "facturas_adeudadas": 1, "saldo_refinanciar": 0, "estado_contrato": "Activo",
                 "estado_cliente": "Habilitado", "fecha_alta": "2023-01-10"},
    # al día, conexión sana -> soporte real
    "480002": {"nombre": "Carlos Test", "dni": "27888999", "nro_cliente": "480002",
               "plan": "WIHogar60", "velocidad_mbps": 60, "abono_mensual": 16000,
               "deuda": 0.0, "extension_pago": 0, "estado_conexion": "Habilitada",
               "facturas_adeudadas": 0, "saldo_refinanciar": 0, "estado_contrato": "Activo",
               "estado_cliente": "Habilitado", "fecha_alta": "2022-05-01"},
    # moroso -> "no tengo internet" debe ir a pagos por desambiguación
    "480003": {"nombre": "Moroso Test", "dni": "30111222", "nro_cliente": "480003",
               "plan": "FOHogar300", "velocidad_mbps": 300, "abono_mensual": 26000,
               "deuda": 26000.0, "extension_pago": 0, "estado_conexion": "Moroso",
               "facturas_adeudadas": 1, "saldo_refinanciar": 0, "estado_contrato": "Activo",
               "estado_cliente": "Habilitado", "fecha_alta": "2021-01-01"},
}


def buscar_fake(ident):
    return next((c for c in _CLIENTES.values()
                 if c["dni"] == ident or c["nro_cliente"] == ident), None)


def clasificar_fake(mensaje, opciones):
    m = mensaje.lower()
    tabla = {
        "contratar": ["contratar", "nuevo"], "cliente": ["cliente", "reclamo", "problema"],
        "hogar": ["hogar", "casa"], "empresa": ["empresa", "oficina"],
        "facturacion": ["factura"], "pagos": ["pagar", "deuda", "abonar"],
        "asesor": ["asesor"], "soporte": ["internet", "soporte", "conexion", "conexión"],
        "acepta": ["acepto", "dale", "ok", "bueno", "pago ahora", "quiero pagar"],
        "rechaza": ["no", "rechazo"], "no_puede": ["no puedo", "no llego", "muy caro", "es mucho"],
        "extension": ["extension", "dias", "plazo", "unos dias"],
        "competencia": ["competencia", "otra empresa", "me voy"],
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


def test_soporte_real_cuando_conexion_sana():
    r = correr(["tengo un reclamo", "480002", "hace horas que no tengo internet"])
    assert r["agente_destino"] == "soporte"


def test_desambiguacion_moroso_sin_internet_va_a_pagos():
    # Cliente Moroso dice "no tengo internet": es tema de pago, no técnico.
    r = correr(["soy cliente", "480003", "no tengo internet"])
    assert r["agente_destino"] == "pagos"


def test_negociacion_pagos_multiturno_acepta():
    # Identifica -> pagos -> propone 10% -> el cliente acepta -> cierra.
    r = correr(["soy cliente", "36956909", "quiero pagar", "dale, acepto"])
    assert r["agente_destino"] == "pagos"
    assert r["decision"] == "responder"


def test_escalon0_pide_pago_sin_descuento():
    # El primer turno de pagos NO ofrece descuento: pide abonar la factura.
    r = correr(["soy cliente", "36956909", "quiero pagar"])
    assert "abonarla ahora" in r["mensaje"]
    assert "%" not in r["mensaje"]          # sin descuento en el escalón 0


def test_no_puede_baja_a_10_luego_20():
    estado = nuevo_estado()
    for m in ["soy cliente", "36956909", "quiero pagar"]:
        orquestador(estado, m, clasificar=clasificar_fake, buscar=buscar_fake)
    r1 = orquestador(estado, "no puedo pagar todo", clasificar=clasificar_fake, buscar=buscar_fake)
    assert "10%" in r1["mensaje"] and r1["nodo"] == "en_worker"
    r2 = orquestador(estado, "no, sigue caro", clasificar=clasificar_fake, buscar=buscar_fake)
    assert "20%" in r2["mensaje"]


def test_pago_menciona_medios_de_pago():
    r = correr(["soy cliente", "36956909", "quiero pagar", "dale, acepto"])
    assert r["decision"] == "responder"
    assert "Medios de pago" in r["mensaje"]


def test_herramienta_no_registrada_no_se_ejecuta():
    from agente.herramientas import ejecutar
    r = ejecutar("borrar_deuda", nro_cliente="480001")
    assert r["ok"] is False


def test_slot_filling_identifica_en_inicio():
    # "soy el cliente 480001" -> identifica de una, sin volver a pedir el número.
    r = correr(["soy el cliente 480001"])
    assert "Ana Test" in r["mensaje"]
    assert "motivo" in r["mensaje"].lower()


def test_slot_filling_identifica_y_rutea_en_un_mensaje():
    # "soy cliente 480001, quiero pagar" -> identifica Y enruta a pagos en un paso.
    r = correr(["soy cliente 480001, quiero pagar"])
    assert r["agente_destino"] == "pagos"
    assert "Ana Test" in r["mensaje"]


def test_llm_openrouter_parsea_respuesta():
    # Simula la red: verifica que _consultar_openrouter parsea el content.
    import os, json, time, urllib.request
    from agente import llm
    os.environ["OPENROUTER_API_KEY"] = "test-key"

    class FakeResp:
        def read(self): return json.dumps(
            {"choices": [{"message": {"content": '{"intent":"pagos"}'}}]}).encode()
        def __enter__(self): return self
        def __exit__(self, *a): pass

    orig = urllib.request.urlopen
    urllib.request.urlopen = lambda req, timeout=60: FakeResp()
    try:
        r = llm._consultar_openrouter("sys", "quiero pagar", 0, 50, time.time())
    finally:
        urllib.request.urlopen = orig
    assert r["ok"] is True and '"intent"' in r["respuesta"]


def test_llm_openrouter_sin_api_key():
    import os, time
    from agente import llm
    os.environ.pop("OPENROUTER_API_KEY", None)
    r = llm._consultar_openrouter("sys", "hola", 0, 50, time.time())
    assert r["ok"] is False and r["modo"] == "sin_api_key"


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
