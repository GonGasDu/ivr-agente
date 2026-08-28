"""
Worker de CUENTA — unifica facturación + pagos.

En la puerta clasificamos GRUESO ('cuenta'); acá adentro ramificamos FINO:
- consultar  -> muestra plan / saldo / factura (info)
- pagar/otro -> negociación de pago (delegada al motor en pagos.py)

Recibe el mensaje del cliente para desambiguar sin volver a preguntar cuando ya
está claro. Interfaz uniforme: iniciar(cliente, mensaje, clasificar) / paso(...).
"""
from agente.categorias import pagos as _neg


def _turno(mensaje, decision="responder", requiere_humano=False, fin=True):
    return {"mensaje": mensaje, "decision": decision, "requiere_humano": requiere_humano,
            "fin": fin, "agente_destino": "cuenta"}


def _info(cliente):
    txt = (f"Tu plan es {cliente['plan']} ({cliente['velocidad_mbps']} Mbps), "
           f"abono ${cliente['abono_mensual']:.0f}. ")
    if cliente.get("deuda", 0) > 0:
        txt += f"Tenés una factura pendiente de ${cliente['deuda']:.0f}; cuando quieras la podés abonar."
    else:
        txt += "Estás al día."
    return _turno(txt)


def iniciar(cliente, mensaje="", clasificar=None, hoy_dia=None):
    intent2 = clasificar(mensaje, ["pagar", "consultar"]) if clasificar else "otro"
    if intent2 == "consultar":
        return {"cliente": cliente}, _info(cliente)
    # pagar u 'otro': negociación según la situación (pagos ya maneja al_dia como info)
    return _neg.iniciar(cliente, hoy_dia)


def paso(sub, mensaje, clasificar):
    return _neg.paso(sub, mensaje, clasificar)
