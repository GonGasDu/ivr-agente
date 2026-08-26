"""Worker de FACTURACIÓN. Ver nota de arquitectura en pagos.py."""


def manejar(cliente: dict):
    return (f"Tu plan es {cliente['plan']} ({cliente['velocidad_mbps']} Mbps), "
            f"abono ${cliente['abono_mensual']:.0f}. Deuda actual: ${cliente['deuda']:.0f}.",
            "responder", False)
