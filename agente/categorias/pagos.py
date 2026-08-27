"""
Worker de PAGOS — ahora un sub-agente multi-turno.

A diferencia de los workers simples (una respuesta y listo), pagos NEGOCIA:
propone una oferta, ESPERA la respuesta del cliente, y según acepte o no,
cierra o escala hasta el techo -> humano.

Interfaz multi-turno:
    iniciar(cliente, hoy_dia)      -> (sub_estado, turno)   # primer mensaje
    paso(sub_estado, mensaje, clasificar) -> turno          # turnos siguientes

`clasificar(mensaje, opciones)` se inyecta (el LLM real o uno simulado en tests).
La lógica de negocio (montos, escalones, extensiones) vive en agente.politica.

Nota: el orquestador todavía usa manejar() (single-shot). El cableado del
seam multi-turno es el próximo paso. manejar() queda como compatibilidad.
"""
from agente import politica as pol


def _turno(mensaje, decision="continuar", requiere_humano=False, fin=False):
    return {"mensaje": mensaje, "decision": decision,
            "requiere_humano": requiere_humano, "fin": fin, "agente_destino": "pagos"}


def iniciar(cliente, hoy_dia=None):
    sit = pol.situacion(cliente)
    sub = {"cliente": cliente, "sit": sit, "paso": None, "nivel": 1, "dia": hoy_dia}

    if sit == "al_dia":
        return sub, _turno("No registrás deuda pendiente. ¿Necesitás algo más?", "responder", fin=True)

    if sit == "humano":
        return sub, _turno("Por la situación de tu cuenta, te paso con un asesor que va a poder ayudarte.",
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
        return sub, _turno(f"Veo un saldo de ${resto:.0f} pendiente de tu pago anterior. Lo podemos "
                           f"refinanciar en tus próximas 2 facturas (${resto/2:.0f} cada una). ¿Lo hacemos así?")

    # negociacion (1 factura)
    sub["paso"] = "negociando"
    return sub, _turno(f"Tenés 1 factura pendiente de ${cliente['deuda']:.0f}. Puedo ofrecerte un 10% de "
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
        tope = pol.descuento_maximo(c, "no_puede_pagar")
        if sub["nivel"] == 1 and tope == "nivel_2":
            sub["nivel"] = 2
            return _turno("Puedo mejorarlo: 20% en esta factura, o 5% este mes y 5% los próximos dos. "
                          "¿Cuál te viene mejor?")
        return _turno("Entiendo. Te paso con un asesor que puede ofrecerte una mejor alternativa.",
                      "derivar_asesor", requiere_humano=True, fin=True)

    return _turno("No entendí. ¿Podés repetirlo?")


# --- Compatibilidad con el seam actual (single-shot). Se reemplaza al cablear multi-turno. ---
def manejar(cliente):
    _, t = iniciar(cliente)
    return (t["mensaje"], t["decision"], t["requiere_humano"])
