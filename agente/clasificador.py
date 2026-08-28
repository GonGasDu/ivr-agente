"""
Clasificador de intención (el LLM propone, Python valida).

El prompt DESCRIBE cada categoría y da EJEMPLOS (few-shot). Sin eso, el modelo
tiene que adivinar qué significan nombres pelados como 'cuenta' o 'soporte' —y se
equivoca, sin importar cuán grande sea (lo comprobamos: DeepSeek mandó "quiero
pagar" a facturación con una lista sin descripciones).

El prompt se arma a partir de las opciones que se le pasen, así sirve para todos
los puntos de decisión (menú, contratar/cliente, hogar/empresa, aceptar/rechazar).
"""
import json

from agente.llm import consultar_llm


DESCRIPCIONES = {
    # nivel 0
    "contratar":     "es un cliente NUEVO: quiere contratar un servicio o pregunta precios/planes para contratar",
    "cliente":       "YA es cliente y quiere gestionar algo de su servicio actual",
    # plan
    "hogar":         "plan para una casa, una familia o uso particular",
    "empresa":       "plan para una empresa, oficina, comercio o negocio",
    # menú del cliente
    "cuenta":        "temas de su cuenta o factura: pagar, saldar deuda, refinanciar, pedir extensión o descuento, o consultar su plan/saldo/factura",
    "soporte":       "problemas TÉCNICOS: sin internet, cortes, intermitencias, lentitud, cobertura, instalación, turnos de técnicos, cambiar la contraseña del wifi",
    "administrativo":"trámites o reclamos administrativos: cambio de titularidad, cambio de datos personales, y todo lo que no sea técnico ni de pago",
    # dentro de cuenta
    "pagar":         "quiere pagar, abonar, saldar, refinanciar, una extensión o un descuento",
    "consultar":     "SOLO quiere información (ver su plan, saldo o factura), sin pagar ahora",
    # negociación
    "acepta":        "acepta la oferta, dice que sí, quiere avanzar",
    "rechaza":       "rechaza la oferta o dice que no le sirve",
    "no_puede":      "dice que no puede pagar, que es mucho, que no le alcanza",
    "extension":     "pide más tiempo, unos días, una prórroga para pagar",
    "competencia":   "dice que se va a otra empresa o que se cambia de compañía",
}

EJEMPLOS = {
    "contratar":     ["quiero contratar internet", "cuánto sale un plan"],
    "cliente":       ["ya soy cliente", "tengo un problema con mi servicio"],
    "hogar":         ["es para mi casa"],
    "empresa":       ["es para mi oficina"],
    "cuenta":        ["quiero pagar mi factura", "cuánto debo", "necesito una extensión de pago"],
    "soporte":       ["no tengo internet", "cuándo viene el técnico", "anda muy lento"],
    "administrativo":["quiero cambiar la titularidad", "necesito cambiar mis datos"],
    "pagar":         ["quiero abonar", "puedo refinanciar la deuda"],
    "consultar":     ["cuál es mi plan", "solo quiero ver mi saldo"],
    "acepta":        ["dale, acepto", "sí, está bien"],
    "no_puede":      ["no puedo pagar todo", "es mucho para mí"],
    "extension":     ["necesito unos días más"],
    "competencia":   ["me voy a otra empresa"],
}


def _armar_instruccion(opciones):
    lineas = [f"- {op}: {DESCRIPCIONES.get(op, op)}" for op in opciones]
    ejemplos = [f'"{ej}" -> {op}' for op in opciones for ej in EJEMPLOS.get(op, [])]
    return (
        "Sos el clasificador de intención de un IVR de una empresa de internet.\n"
        "Clasificá el mensaje del usuario en UNA de estas categorías:\n"
        + "\n".join(lineas)
        + "\n- otro: si no encaja claramente en ninguna.\n\n"
        + ("Ejemplos:\n" + "\n".join(ejemplos) + "\n\n" if ejemplos else "")
        + "No inventes categorías fuera de la lista.\n"
        'Respondé SOLO JSON válido: {"intent":"..."}'
    )


def extraer_json(texto: str) -> dict:
    ini, fin = texto.find("{"), texto.rfind("}")
    if ini == -1 or fin == -1:
        raise ValueError("la respuesta no contiene JSON")
    return json.loads(texto[ini:fin + 1])


def clasificar_intencion(mensaje: str, opciones: list[str], consultar=consultar_llm) -> str:
    """Clasifica el mensaje en UNA de las opciones dadas, o 'otro'."""
    salida = consultar(mensaje, _armar_instruccion(opciones), temperature=0)
    if not salida.get("ok"):
        return "otro"
    try:
        intent = extraer_json(salida["respuesta"]).get("intent")
    except (json.JSONDecodeError, ValueError):
        return "otro"
    return intent if intent in opciones else "otro"
