"""
Clasificador de intención (el LLM propone, Python valida).

El modelo elige una opción; Python la valida contra la lista permitida.
Si el modelo rompe el JSON o inventa una opción, el resultado es 'otro'.

`consultar` se inyecta para poder testear sin el modelo real.
"""
import json

from agente.llm import consultar_llm


def extraer_json(texto: str) -> dict:
    ini, fin = texto.find("{"), texto.rfind("}")
    if ini == -1 or fin == -1:
        raise ValueError("la respuesta no contiene JSON")
    return json.loads(texto[ini:fin + 1])


def clasificar_intencion(mensaje: str, opciones: list[str], consultar=consultar_llm) -> str:
    """Clasifica el mensaje en UNA de las opciones dadas, o 'otro'."""
    instruccion = (
        "Sos el clasificador de intención de un IVR de una empresa de internet.\n"
        f"Clasificá el mensaje del usuario en UNA de estas opciones exactas: {opciones}, "
        "o 'otro' si no encaja en ninguna.\n"
        "No inventes opciones fuera de la lista.\n"
        'Respondé SOLO JSON válido: {"intent":"opcion"}'
    )
    salida = consultar(mensaje, instruccion, temperature=0)
    if not salida.get("ok"):
        return "otro"
    try:
        intent = extraer_json(salida["respuesta"]).get("intent")
    except (json.JSONDecodeError, ValueError):
        return "otro"
    return intent if intent in opciones else "otro"   # Python conserva la autoridad
