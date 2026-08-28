"""
Worker de PAGOS — sub-agente multi-turno.

Negociación con ANCLAJE (escalón 0): primero se pide el pago normal SIN descuento
(el cliente quizás solo se olvidó). El descuento aparece solo si no puede pagar.

Escalones:
  0) pagar la factura (sin descuento)  -> si acepta, cierra
  1) 10% sobre la factura              -> si el cliente no puede
  2) 20% ó 5%x3 (si >=12 meses)        -> si sigue sin poder
  techo -> humano

Usa herramientas registradas (patrón Clase 4): consulta medios de pago y registra
las acciones vía agente.herramientas.ejecutar(). Python elige la herramienta; el
LLM solo interpreta al cliente.
"""
from agente import politica as pol
from agente import herramientas as herr


def _turno(mensaje, decision="continuar", requiere_humano=False, fin=False):
    return {"mensaje": mensaje, "decision": decision,
            "requiere_humano": requiere_humano, "fin": fin, "agente_destino": "pagos"}


def _preambulo_conexion(cliente):
    return {
        "Cortada":       "Tu servicio está cortado por una deuda pendiente. ",
        "Moroso":        "Tu conexión figura como morosa por falta de pago. ",
        "Forzada":       "Tu servicio sigue activo de forma condicional por una deuda pendiente. ",
        "Deshabilitada": "Tu servicio está deshabilitado por tu situación de pago. ",
    }.get(cliente.get("estado_conexion"), "")


def _medios_pago_txt():
    r = herr.ejecutar("consultar_medios_pago")
    if not r.get("ok"):
        return ""
    return "Medios de pago: " + ", ".join(r["medios"]) + "."


def _reg(sub, nombre, **args):
    """Ejecuta una herramienta registrada y deja traza en el sub-estado (Clase 4 + audit)."""
    r = herr.ejecutar(nombre, **args)
    sub.setdefault("herramientas_usadas", []).append({"herramienta": nombre, "ok": r.get("ok")})
    return r


def iniciar(cliente, hoy_dia=None):
    sit = pol.situacion(cliente)
    sub = {"cliente": cliente, "sit": sit, "paso": None, "nivel": 1, "dia": hoy_dia}

    if sit == "al_dia":
        return sub, _turno("No registrás deuda pendiente. ¿Necesitás algo más?", "responder", fin=True)

    if sit == "humano":
        return sub, _turno(_preambulo_conexion(cliente) +
                           "Por la situación de tu cuenta, te paso con un asesor que va a poder ayudarte.",
                           "derivar_asesor", requiere_humano=True, fin=True)

    if sit == "rehabilitacion":
        m = pol.monto_rehabilitacion(cliente)
        sub["paso"] = "espera_rehab"
        return sub, _turno(f"Tu servicio está cortado por 2 facturas impagas. Para rehabilitarlo podés "
                           f"pagar el 75% con 10% de descuento (${m['a_pagar']:.0f}) y volver a comunicarte; "
                           f"el resto lo refinanciamos. ¿Querés avanzar así?")

    if sit == "segunda_llamada":
        resto = cliente["saldo_refinanciar"]
        sub["paso"] = "espera_refin"
        return sub, _turno(_preambulo_conexion(cliente) +
                           f"Veo un saldo de ${resto:.0f} pendiente de tu pago anterior. Lo podemos "
                           f"refinanciar en tus próximas 2 facturas (${resto/2:.0f} cada una). ¿Lo hacemos así?")

    # negociacion (1 factura) -> ESCALÓN 0: pedir el pago normal, sin descuento
    sub["paso"] = "espera_pago"
    return sub, _turno(_preambulo_conexion(cliente) +
                       f"Tenés una factura pendiente de ${cliente['deuda']:.0f}. ¿Querés abonarla ahora? "
                       f"{_medios_pago_txt()} Si necesitás unos días, puedo darte una extensión de pago.")


def paso(sub, mensaje, clasificar):
    p = sub["paso"]
    c = sub["cliente"]

    if p == "espera_pago":                                   # ESCALÓN 0
        r = clasificar(mensaje, ["acepta", "extension", "competencia", "no_puede"])
        if r == "acepta":
            _reg(sub, "registrar_pago", nro_cliente=c["nro_cliente"], monto=c["deuda"])
            return _turno(f"¡Perfecto! Registré tu intención de pago de ${c['deuda']:.0f}. {_medios_pago_txt()} "
                          "Apenas se acredite, tu servicio se normaliza.", "responder", fin=True)
        if r == "extension":
            return _ofrecer_extension(sub, c)
        if r == "competencia":
            sub["paso"] = "espera_competencia"
            return _turno("Lamento que quieras irte. Para que te quedes, puedo ofrecerte un 20% de descuento "
                          "durante los próximos 2 meses. ¿Te sirve?")
        if r == "no_puede":                                  # solo la imposibilidad destraba el 10%
            sub["paso"] = "negociando"
            sub["nivel"] = 1
            return _turno(f"Entiendo. Puedo ofrecerte un 10% de descuento sobre la factura de ${c['deuda']:.0f} "
                          "si la abonás ahora. ¿Te sirve?")
        # ambiguo / "solo miraba" -> cerrar sin regalar descuento
        return _turno("De acuerdo, cuando quieras podés abonar la factura. ¿Algo más?", "responder", fin=True)

    if p == "negociando":
        r = clasificar(mensaje, ["acepta", "rechaza", "extension", "competencia"])
        if r == "acepta":
            pct = 10 if sub["nivel"] == 1 else 20
            _reg(sub, "aplicar_descuento", nro_cliente=c["nro_cliente"], porcentaje=pct)
            return _turno(f"Genial, aplico el {pct}% de descuento sobre tu factura. {_medios_pago_txt()}",
                          "responder", fin=True)
        if r == "extension":
            return _ofrecer_extension(sub, c)
        if r == "competencia":
            sub["paso"] = "espera_competencia"
            return _turno("Lamento que quieras irte. Para que te quedes, puedo ofrecerte un 20% de descuento "
                          "durante los próximos 2 meses. ¿Te sirve?")
        # rechaza
        if sub["nivel"] == 1 and pol.descuento_maximo(c, "no_puede_pagar") == "nivel_2":
            sub["nivel"] = 2
            return _turno("Puedo mejorarlo: 20% en esta factura, o 5% este mes y 5% los próximos dos. "
                          "¿Cuál te viene mejor?")
        return _turno("Entiendo. Te paso con un asesor que puede ofrecerte una mejor alternativa.",
                      "derivar_asesor", requiere_humano=True, fin=True)

    if p == "espera_rehab":
        if clasificar(mensaje, ["acepta", "rechaza"]) == "acepta":
            m = pol.monto_rehabilitacion(c)
            _reg(sub, "registrar_pago", nro_cliente=c["nro_cliente"], monto=m["a_pagar"])
            return _turno(f"Perfecto. Aboná ${m['a_pagar']:.0f} y volvé a comunicarte para refinanciar los "
                          f"${m['resto']:.0f} restantes. {_medios_pago_txt()}", "responder", fin=True)
        return _turno("Entiendo. Te paso con un asesor para ver otras alternativas.",
                      "derivar_asesor", requiere_humano=True, fin=True)

    if p == "espera_refin":
        if clasificar(mensaje, ["acepta", "rechaza"]) == "acepta":
            resto = c["saldo_refinanciar"]
            _reg(sub, "registrar_refinanciacion", nro_cliente=c["nro_cliente"], monto=resto, cuotas=2)
            return _turno(f"Listo, refinanciamos ${resto:.0f} en 2 cuotas de ${resto/2:.0f}, aplicadas a tus "
                          f"próximas facturas.", "responder", fin=True)
        return _turno("De acuerdo. Te paso con un asesor.", "derivar_asesor", requiere_humano=True, fin=True)

    if p == "espera_competencia":
        if clasificar(mensaje, ["acepta", "rechaza"]) == "acepta":
            _reg(sub, "aplicar_descuento", nro_cliente=c["nro_cliente"], porcentaje=20)
            return _turno("¡Genial! Aplico el 20% por 2 meses. Gracias por quedarte.", "responder", fin=True)
        return _turno("Entiendo. Te paso con un asesor.", "derivar_asesor", requiere_humano=True, fin=True)

    return _turno("No entendí. ¿Podés repetirlo?")


def _ofrecer_extension(sub, c):
    ext = pol.puede_extension(c, sub.get("dia"))
    if ext["disponible"]:
        _reg(sub, "registrar_extension", nro_cliente=c["nro_cliente"],
             hasta_dia=ext["nueva_fecha_dia"], costo=ext["costo"])
        return _turno(f"Te doy una extensión hasta el día {ext['nueva_fecha_dia']} (costo ${ext['costo']}). "
                      f"Queda registrada. {_medios_pago_txt()}", "responder", fin=True)
    return _turno(f"No puedo darte una extensión ({ext['motivo']}). Te paso con un asesor.",
                  "derivar_asesor", requiere_humano=True, fin=True)
