"""
Herramienta CRM: consulta la base de clientes.

Los datos viven en un JSON (datos/crm_ejemplo.json), separados del código.
En producción, esta capa se reemplaza por una consulta a la base/CRM real,
pero la firma `buscar_cliente(identificador)` se mantiene igual.
"""
import json
import os
from functools import lru_cache

RUTA_CRM = os.environ.get("IVR_CRM", "datos/crm_ejemplo.json")


def cargar_crm(ruta: str = RUTA_CRM) -> dict:
    """Lee el JSON y arma índices por DNI y por número de cliente."""
    with open(ruta, encoding="utf-8") as f:
        clientes = json.load(f)
    return {
        "por_dni": {c["dni"]: c for c in clientes},
        "por_nro": {c["nro_cliente"].upper(): c for c in clientes},
    }


@lru_cache(maxsize=1)
def _crm_defecto() -> dict:
    return cargar_crm()


def buscar_cliente(identificador: str, crm: dict | None = None) -> dict | None:
    """Devuelve el cliente por DNI o número de cliente, o None si no existe."""
    crm = crm or _crm_defecto()
    ident = identificador.strip().upper()
    return crm["por_dni"].get(ident) or crm["por_nro"].get(ident)
