"""
Reglas deterministas (Clase 3).

Lo que es un patrón exacto NO se le confía al modelo probabilístico:
- extraer_identificador: saca DNI (7-8 díg.) o número de cliente (6 díg.) de un texto.
- detectar_dato_sensible: portón (guardrail) que corta el flujo si aparece un secreto.
"""
import re

LEGIBLE = {"dni": "DNI", "nro_cliente": "número de cliente"}


def extraer_identificador(texto: str):
    """Devuelve (valor, tipo). tipo ∈ {'dni', 'nro_cliente', None}."""
    # Número de cliente: exactamente 6 dígitos aislados.
    m = re.search(r"\b\d{6}\b", texto)
    if m:
        return m.group(), "nro_cliente"
    # DNI: 7-8 dígitos, con o sin puntos.
    m = re.search(r"\b\d{1,3}[.\s]?\d{3}[.\s]?\d{3}\b|\b\d{7,8}\b", texto)
    if m:
        return "".join(ch for ch in m.group() if ch.isdigit()), "dni"
    return None, None


PATRONES_SENSIBLES = {
    "tarjeta_completa":  r"(?<!\d)(?:\d[ -]?){15,16}(?!\d)",
    "contraseña":        r"(?:mi )?(?:clave|contraseña|password)\s*(?:es|:)",
    "codigo_seguridad":  r"(?:cvv|cvc|código de seguridad)\s*(?:es|:)?\s*\d{3,4}",
}


def detectar_dato_sensible(texto: str):
    """Nombre del patrón sensible hallado, o None. Corta ANTES de llamar al modelo."""
    for nombre, patron in PATRONES_SENSIBLES.items():
        if re.search(patron, texto, flags=re.IGNORECASE):
            return nombre
    return None


# Palabras de saludo/identificación: si el mensaje (sin números) solo tiene estas,
# no hay un motivo que rutear -> conviene preguntarlo en vez de adivinar.
_PALABRAS_IDENTIFICACION = {
    "hola", "buenas", "buenos", "buen", "dia", "dias", "día", "días", "tardes", "noches",
    "soy", "el", "la", "los", "las", "mi", "cliente", "clienta", "abonado", "socio",
    "numero", "número", "nro", "dni", "documento", "es", "son", "con", "de", "que", "tal",
    "hey", "señor", "señora", "sr", "sra", "gracias",
}


def es_solo_identificacion(mensaje: str) -> bool:
    """True si el mensaje es solo un saludo y/o el identificador, sin un motivo real."""
    limpio = re.sub(r"[\d.\-]", " ", mensaje.lower())
    palabras = [w for w in re.findall(r"[a-záéíóúñ]+", limpio)
                if w not in _PALABRAS_IDENTIFICACION]
    return len(palabras) == 0
