"""
Orquestador: la máquina de estados del IVR-agente.

Camina el flujo, llama herramientas (CRM), aplica reglas y enruta a workers.
Novedades:
- Nodo 'en_worker': delega varios turnos seguidos a un sub-agente multi-turno
  (como pagos) hasta que este declara 'fin'.
- Desambiguación: "no tengo internet" de alguien con problema de pago va a pagos,
  no a soporte (mira estado_conexion / facturas / estado_cliente vía politica).

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


def orquestador(estado, mensaje, clasificar=clasificar_intencion, buscar=_buscar_cliente):
    nodo = estado["nodo"]
    traza = []

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
            estado["cliente"] = cliente
            estado["nodo"] = "menu_cliente"
            return turno(estado, f"¡Hola {cliente['nombre']}! ¿Cuál es el motivo de tu llamado?", traza=traza)
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
        intent = clasificar(mensaje, list(AGENTES_CATEGORIA))
        traza.append({"nodo": nodo, "intent": intent})
        # Desambiguación: "no tengo internet" de alguien con deuda es un tema de pago.
        if intent == "soporte" and pol.problema_es_de_pago(estado["cliente"]):
            traza.append({"paso": "desambiguacion", "de": "soporte", "a": "pagos",
                          "estado_conexion": estado["cliente"].get("estado_conexion")})
            intent = "pagos"
        if intent in AGENTES_CATEGORIA:
            worker = AGENTES_CATEGORIA[intent]
            sub, t = worker.iniciar(estado["cliente"])
            if t.get("fin"):
                estado["nodo"] = "fin"
            else:                                   # sub-agente multi-turno: nos quedamos adentro
                estado["worker"], estado["sub"], estado["nodo"] = intent, sub, "en_worker"
            return turno(estado, t["mensaje"], decision=t["decision"],
                         requiere_humano=t["requiere_humano"], agente_destino=intent, traza=traza)
        estado["datos"]["reintentos"] = estado["datos"].get("reintentos", 0) + 1
        if estado["datos"]["reintentos"] >= 2:
            estado["nodo"] = "fin"
            return turno(estado, "No logro entender el motivo. Te derivo con un asesor.",
                         decision="derivar_asesor", requiere_humano=True, traza=traza)
        return turno(estado, "¿Es por Facturación, Pagos, un tema administrativo o Soporte técnico?", traza=traza)

    if nodo == "en_worker":
        worker = AGENTES_CATEGORIA[estado["worker"]]
        t = worker.paso(estado["sub"], mensaje, clasificar)
        if t.get("fin"):
            estado["nodo"] = "fin"
        return turno(estado, t["mensaje"], decision=t["decision"],
                     requiere_humano=t["requiere_humano"], agente_destino=estado["worker"], traza=traza)

    return turno(estado, "Conversación finalizada.", decision="fin", traza=traza)
