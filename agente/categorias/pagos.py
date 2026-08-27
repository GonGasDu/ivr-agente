"""
Worker de PAGOS — sub-agente multi-turno.

Negocia: propone una oferta, ESPERA la respuesta del cliente, y según acepte o
no, cierra o escala hasta el techo -> humano. La lógica de negocio (montos,
escalones, extensiones) vive en agente.politica; acá va la conversación.

Interfaz:
    iniciar(cliente, hoy_dia=None)        -> (sub_estado, turno)
    paso(sub_estado, mensaje, clasificar) -> turno

El primer mensaje explica el estado de la conexión cuando el servicio está
afectado por deuda, para que el cliente entienda por qué (aunque haya llamado
diciendo "no tengo internet").
"""
from agente import politica as pol


def _turno(mensaje, decision="continuar", requiere_humano=False, fin=False):
    return {"mensaje": mensaje, "decision": decision,
            "requiere_humano": requiere_humano, "fin": fin, "agente_destino": "pagos"}


def _preambulo_conexion(cliente):
    """Explica, en una frase, por qué el servicio está afectado (si lo está)."""
    return {
        "Cortada":       "Tu servicio está cortado por una deuda pendiente. ",
        "Moroso":        "Tu conexión figura como morosa por falta de pago. ",
        "Forzada":       "Tu servicio sigue activo de forma condicional por una deuda pendiente. ",
        "Deshabilitada": "Tu servicio está deshabilitado por tu situación de pago. ",
    }.get(cliente.get("estado_conexion"), "")


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

    # negociacion (1 factura)
    sub["paso"] = "negociando"
    return sub, _turno(_preambulo_conexion(cliente) +
                       f"Tenés 1 factura pendiente de ${cliente['deuda']:.0f}. Puedo ofrecerte un 10% de "
                       f"descuento si la abonás ahora, o una extensión de pago si necesitás unos días. "
                       f"¿Qué preferís?")


def paso(sub, mensaje, clasificar):
    p = sub["paso"]
    c = sub["cliente"]

    if p == "espera_rehab":
        if clasificar(mensaje, ["acepta", "rechaza"]) == "acepta":
            m = pol.monto_rehabilitacion(c)
            return _turno(f"Perfecto. Aboná ${m['a_pagar']:.0f} y volvé a comunicarte para refinanciar los "
                          f"${m['resto']:.0f} restantes. Te paso los medios de pago.", "responder", fin=True)
        return _turno("Entiendo. Te paso con un asesor para ver otras alternativas.",
                      "derivar_asesor", requiere_humano=True, fin=True)

    if p == "espera_refin":
        if clasificar(mensaje, ["acepta", "rechaza"]) == "acepta":
            resto = c["saldo_refinanciar"]
            return _turno(f"Listo, refinanciamos ${resto:.0f} en 2 cuotas de ${resto/2:.0f}, aplicadas a tus "
                          f"próximas facturas.", "responder", fin=True)
        return _turno("De acuerdo. Te paso con un asesor.", "derivar_asesor", requiere_humano=True, fin=True)

    if p == "espera_competencia":
        if clasificar(mensaje, ["acepta", "rechaza"]) == "acepta":
            return _turno("¡Genial! Aplico el 20% por 2 meses. Gracias por quedarte.", "responder", fin=True)
        return _turno("Entiendo. Te paso con un asesor.", "derivar_asesor", requiere_humano=True, fin=True)

    if p == "negociando":
        r = clasificar(mensaje, ["acepta", "rechaza", "extension", "competencia"])
        if r == "acepta":
            pct = "10%" if sub["nivel"] == 1 else "20%"
            return _turno(f"Genial, aplico el {pct} de descuento sobre tu factura. Te paso los medios de pago.",
                          "responder", fin=True)
        if r == "extension":
            ext = pol.puede_extension(c, sub.get("dia"))
            if ext["disponible"]:
                return _turno(f"Te doy una extensión hasta el día {ext['nueva_fecha_dia']} "
                              f"(costo ${ext['costo']}). Queda registrada.", "responder", fin=True)
            return _turno(f"No puedo darte una extensión ({ext['motivo']}). Te paso con un asesor.",
                          "derivar_asesor", requiere_humano=True, fin=True)
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

    return _turno("No entendí. ¿Podés repetirlo?")
