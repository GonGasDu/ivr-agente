"""Worker de SOPORTE TÉCNICO. Ver nota de arquitectura en pagos.py."""


def manejar(cliente: dict) -> tuple[str, str, bool]:
    return (f"Tu conexión figura: {cliente['estado_conexion']}. "
            "Te derivo a soporte técnico con ese dato.", "derivar_soporte", True)
