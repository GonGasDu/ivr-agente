"""
Demo del IVR-agente en consola, con el LLM real.

Uso:
    python scripts/demo_consola.py

Escribí como un cliente. 'salir' para terminar.
Requiere el CRM generado (scripts/generar_crm.py) y el modelo (se descarga solo).
"""
from agente.llm import cargar_modelo
from agente.orquestador import orquestador, nuevo_estado


def main():
    cargar_modelo()   # informa el proveedor (local u openrouter)
    print("Listo. Escribí tu consulta ('salir' para terminar).\n")

    estado = nuevo_estado()
    print("AGENTE : Hola, soy el asistente. ¿Querés contratar un servicio o ya sos cliente?")
    while True:
        mensaje = input("VOS    : ").strip()
        if mensaje.lower() in {"salir", "chau", "exit", "quit"}:
            break
        r = orquestador(estado, mensaje)
        print("AGENTE :", r["mensaje"])
        if r["decision"] != "continuar":
            etiqueta = f" (a {r['agente_destino']})" if r["agente_destino"] else ""
            print(f"[decisión: {r['decision']}{etiqueta} | revisión humana: {r['requiere_humano']}]")
            print("\n--- fin del flujo ---")
            break


if __name__ == "__main__":
    main()
