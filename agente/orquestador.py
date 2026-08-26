"""
Orquestador: la máquina de estados del IVR-agente.

Camina el flujo (inicio -> contratar / identificar -> menu_cliente), llama a las
herramientas (CRM), aplica reglas (extracción de identificador) y enruta a los
workers de categoría. El LLM SOLO interpreta la intención; Python controla el flujo.

`clasificar` y `buscar` se inyectan para poder testear sin el modelo ni el CRM real.
"""
from agente.reglas import extraer_identificador, LEGIBLE
from agente.crm import buscar_cliente as _buscar_cliente
from agente.clasificador import clasificar_intencion
from agente.categorias import AGENTES_CATEGORIA


def nuevo_estado() -> dict:
    """La memoria de la conversación: dónde vamos y a quién identificamos."""
    return {"nodo": "inicio", "cliente": None, "datos": {}}


def turno(estado, mensaje, decision="continuar", requiere_humano=False,
          agente_destino=None, traza=None) -> dict:
    """Contrato de cada turno: forma fija que consume el canal (WhatsApp, teléfono, ...)."""
    return {
        "mensaje": mensaje,                 # lo que el agente le dice al usuario
        "decision": decision,               # continuar | responder | derivar_* | fin
        "nodo": estado["nodo"],             # estado de la conversación (memoria)
        "requiere_humano": requiere_humano,
        "agente_destino": agente_destino,   # a qué worker se enrutó (si aplica)
        "traza": traza or [],
    }


def orquestador(estado, mensaje, clasificar=clasificar_intencion, buscar=_buscar_cliente):
    nodo = estado["nodo"]
    traza = []

    # --- Nodo inicial: ¿contratar o ya es cliente? ---
    if nodo == "inicio":
        intent = clasificar(mensaje, ["contratar", "cliente"])
        traza.append({"nodo": nodo, "intent": intent})
        if intent == "contratar":
            estado["nodo"] = "elegir_plan"
            return turno(estado, "¡Genial! ¿Te interesa un plan Hogar o un plan Empresa?", traza=traza)
        if intent == "cliente":
            estado["nodo"] = "identificar"
            return turno(estado, "Perfecto. Pasame tu DNI o número de cliente así te identifico.", traza=traza)
        return turno(estado, "¿Querés contratar un servicio o ya sos cliente?", traza=traza)

    # --- Contratación: hogar o empresa -> ventas ---
    if nodo == "elegir_plan":
        intent = clasificar(mensaje, ["hogar", "empresa"])
        traza.append({"nodo": nodo, "intent": intent})
        if intent in ("hogar", "empresa"):
            estado["datos"]["plan_interes"] = intent
            estado["nodo"] = "fin"
            return turno(estado, f"Buenísimo, te derivo con un asesor comercial de planes {intent}.",
                         decision="derivar_ventas", requiere_humano=True, traza=traza)
        return turno(estado, "¿Sería un plan Hogar o Empresa?", traza=traza)

    # --- Identificación: búsqueda alternada DNI <-> número de cliente ---
    if nodo == "identificar":
        probados = estado["datos"].setdefault("tipos_probados", [])
        ident, tipo = extraer_identificador(mensaje)
        traza.append({"paso": "extraer_id", "tipo": tipo, "hallado": bool(ident)})  # sin el número real
        if not ident:
            faltan = [t for t in ("dni", "nro_cliente") if t not in probados]
            pedido = LEGIBLE[faltan[0]] if len(faltan) == 1 else "tu DNI o número de cliente"
            return turno(estado, f"No pude leer {pedido}. ¿Me lo pasás?", traza=traza)

        cliente = buscar(ident)
        traza.append({"paso": "buscar_cliente", "por": tipo, "encontrado": cliente is not None})
        if cliente:
            estado["cliente"] = cliente
            estado["nodo"] = "menu_cliente"
            return turno(estado, f"¡Hola {cliente['nombre']}! ¿Cuál es el motivo de tu llamado?", traza=traza)

        if tipo not in probados:
            probados.append(tipo)
        otros = [t for t in ("dni", "nro_cliente") if t not in probados]
        if not otros:  # ya se probaron los dos -> humano
            estado["nodo"] = "fin"
            return turno(estado, "No encontré ningún cliente con esos datos. Te derivo con un asesor.",
                         decision="derivar_asesor", requiere_humano=True, traza=traza)
        return turno(estado, f"No encontré ningún cliente con ese {LEGIBLE[tipo]}. "
                             f"¿Me pasás tu {LEGIBLE[otros[0]]}?", traza=traza)

    # --- Menú del cliente: motivo libre -> worker de categoría ---
    if nodo == "menu_cliente":
        intent = clasificar(mensaje, list(AGENTES_CATEGORIA))
        traza.append({"nodo": nodo, "intent": intent})
        if intent in AGENTES_CATEGORIA:
            cliente = estado["cliente"]
            msg, decision, humano = AGENTES_CATEGORIA[intent](cliente)  # <- aquí entra el sub-agente
            estado["nodo"] = "fin"
            return turno(estado, msg, decision=decision, requiere_humano=humano,
                         agente_destino=intent, traza=traza)
        estado["datos"]["reintentos"] = estado["datos"].get("reintentos", 0) + 1
        if estado["datos"]["reintentos"] >= 2:
            estado["nodo"] = "fin"
            return turno(estado, "No logro entender el motivo. Te derivo con un asesor.",
                         decision="derivar_asesor", requiere_humano=True, traza=traza)
        return turno(estado, "¿Es por Facturación, Pagos, un tema administrativo o Soporte técnico?", traza=traza)

    return turno(estado, "Conversación finalizada.", decision="fin", traza=traza)
