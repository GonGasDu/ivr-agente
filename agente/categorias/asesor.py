"""Worker de ASESOR ADMINISTRATIVO. Ver nota de arquitectura en pagos.py."""


def manejar(cliente: dict) -> tuple[str, str, bool]:
    return ("Te derivo con un asesor administrativo.", "derivar_asesor", True)
