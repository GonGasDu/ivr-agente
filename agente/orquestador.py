"""
Orquestador: la máquina de estados del IVR-agente.

Novedades:
- Slot filling: si el primer mensaje ya trae un identificador (y opcionalmente el
  motivo), identifica y enruta sin volver a preguntar. La regla extrae; el LLM no.
- en_worker: delega varios turnos a un sub-agente multi-turno (pagos) hasta 'fin'.
- Desambiguación: "no tengo internet" de alguien con deuda va a pagos, no a soporte.
- Traza de herramientas: surface de las tools ejecutadas por el worker (Clase 4 + audit).

`clasificar` y `buscar` se inyectan para testear sin el modelo ni el CRM real.
"""
from agente.reglas import extraer_identificador, LEGIBLE
from agente.crm import buscar_cliente as _buscar_cliente
from agente.clasificador import clasificar_intencion
from agente.categorias import AGENTES_CATEGORIA
from agente import politica as pol


def nuevo_estado() -> dict:
    return {"nodo": "inicio", "cliente": None, "datos": {}, "worker": None, "sub": None}


def turno(estado, mensaje, decision="continuar", requiere_humano=False,
          agente_destino=None, traza=None) -> dict:
    return {"mensaje": mensaje, "decision": decision, "nodo": estado["nodo"],
            "requiere_humano": requiere_humano, "agente_destino": agente_destino,
            "traza": traza or []}


def _rutear(estado, mensaje, clasificar, traza):
    """Clasifica el motivo y entrega al worker. Devuelve turno, o None si no hay motivo claro."""
    cliente = estado["cliente"]
    intent = clasificar(mensaje, list(AGENTES_CATEGORIA))
    traza.append({"paso": "clasificar_motivo", "intent": intent})
    if intent == "soporte" and pol.problema_es_de_pago(cliente):
        traza.append({"paso": "desambiguacion", "de": "soporte", "a": "cuenta",
                      "estado_conexion": cliente.get("estado_conexion")})
        intent = "cuenta"
    if intent not in AGENTES_CATEGORIA:
        return None
    worker = AGENTES_CATEGORIA[intent]
    sub, t = worker.iniciar(cliente, mensaje, clasificar)
    if t.get("fin"):
        estado["nodo"] = "fin"
    else:
        estado["worker"], estado["sub"], estado["nodo"] = intent, sub, "en_worker"
    return turno(estado, t["mensaje"], decision=t["decision"],
                 requiere_humano=t["requiere_humano"], agente_destino=intent, traza=traza)


def _identificado(estado, cliente, mensaje, clasificar, traza):
    """Tras identificar: intenta rutear el motivo del MISMO mensaje (slot filling);
    si no hay motivo, saluda por nombre y lo pide."""
    estado["cliente"] = cliente
    r = _rutear(estado, mensaje, clasificar, traza)
    if r:
        r["mensaje"] = f"¡Hola {cliente['nombre']}! " + r["mensaje"]
        return r
    estado["nodo"] = "menu_cliente"
    return turno(estado, f"¡Hola {cliente['nombre']}! ¿Cuál es el motivo de tu llamado?", traza=traza)


def orquestador(estado, mensaje, clasificar=clasificar_intencion, buscar=_buscar_cliente):
    nodo = estado["nodo"]
    traza = []

    if nodo == "inicio":
        # SLOT FILLING: si el mensaje ya trae un identificador, identificamos de una.
        ident, tipo = extraer_identificador(mensaje)
        if ident:
            cliente = buscar(ident)
            traza.append({"paso": "slot_filling", "tipo": tipo, "encontrado": cliente is not None})
            if cliente:
                return _identificado(estado, cliente, mensaje, clasificar, traza)
            estado["nodo"] = "identificar"
            estado["datos"].setdefault("tipos_probados", []).append(tipo)
            otros = [t for t in ("dni", "nro_cliente") if t not in estado["datos"]["tipos_probados"]]
            pedido = LEGIBLE[otros[0]] if otros else "tu DNI o número de cliente"
            return turno(estado, f"No encontré ningún cliente con ese {LEGIBLE[tipo]}. ¿Me pasás tu {pedido}?", traza=traza)
        intent = clasificar(mensaje, ["contratar", "cliente"])
        traza.append({"nodo": nodo, "intent": intent})
        if intent == "contratar":
            estado["nodo"] = "elegir_plan"
            return turno(estado, "¡Genial! ¿Te interesa un plan Hogar o un plan Empresa?", traza=traza)
        if intent == "cliente":
            estado["nodo"] = "identificar"
            return turno(estado, "Perfecto. Pasame tu DNI o número de cliente así te identifico.", traza=traza)
        return turno(estado, "¿Querés contratar un servicio o ya sos cliente?", traza=traza)

    if nodo == "elegir_plan":
        intent = clasificar(mensaje, ["hogar", "empresa"])
        traza.append({"nodo": nodo, "intent": intent})
        if intent in ("hogar", "empresa"):
            estado["datos"]["plan_interes"] = intent
            estado["nodo"] = "fin"
            return turno(estado, f"Buenísimo, te derivo con un asesor comercial de planes {intent}.",
                         decision="derivar_ventas", requiere_humano=True, traza=traza)
        return turno(estado, "¿Sería un plan Hogar o Empresa?", traza=traza)

    if nodo == "identificar":
        probados = estado["datos"].setdefault("tipos_probados", [])
        ident, tipo = extraer_identificador(mensaje)
        traza.append({"paso": "extraer_id", "tipo": tipo, "hallado": bool(ident)})
        if not ident:
            faltan = [t for t in ("dni", "nro_cliente") if t not in probados]
            pedido = LEGIBLE[faltan[0]] if len(faltan) == 1 else "tu DNI o número de cliente"
            return turno(estado, f"No pude leer {pedido}. ¿Me lo pasás?", traza=traza)
        cliente = buscar(ident)
        traza.append({"paso": "buscar_cliente", "por": tipo, "encontrado": cliente is not None})
        if cliente:
            return _identificado(estado, cliente, mensaje, clasificar, traza)
        if tipo not in probados:
            probados.append(tipo)
        otros = [t for t in ("dni", "nro_cliente") if t not in probados]
        if not otros:
            estado["nodo"] = "fin"
            return turno(estado, "No encontré ningún cliente con esos datos. Te derivo con un asesor.",
                         decision="derivar_asesor", requiere_humano=True, traza=traza)
        return turno(estado, f"No encontré ningún cliente con ese {LEGIBLE[tipo]}. "
                             f"¿Me pasás tu {LEGIBLE[otros[0]]}?", traza=traza)

    if nodo == "menu_cliente":
        r = _rutear(estado, mensaje, clasificar, traza)
        if r:
            return r
        estado["datos"]["reintentos"] = estado["datos"].get("reintentos", 0) + 1
        if estado["datos"]["reintentos"] >= 2:
            estado["nodo"] = "fin"
            return turno(estado, "No logro entender el motivo. Te derivo con un asesor.",
                         decision="derivar_asesor", requiere_humano=True, traza=traza)
        return turno(estado, "¿Es sobre tu cuenta o factura, un problema técnico, o un trámite administrativo?", traza=traza)

    if nodo == "en_worker":
        worker = AGENTES_CATEGORIA[estado["worker"]]
        t = worker.paso(estado["sub"], mensaje, clasificar)
        usadas = estado["sub"].get("herramientas_usadas")
        if usadas:
            traza.append({"herramientas": [h["herramienta"] for h in usadas]})
        if t.get("fin"):
            estado["nodo"] = "fin"
        return turno(estado, t["mensaje"], decision=t["decision"],
                     requiere_humano=t["requiere_humano"], agente_destino=estado["worker"], traza=traza)

    return turno(estado, "Conversación finalizada.", decision="fin", traza=traza)
