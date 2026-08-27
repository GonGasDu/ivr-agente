"""
Genera una base de datos de clientes INVENTADA (datos falsos) para el IVR-agente.

Uso:
    python scripts/generar_crm.py --n 40 --seed 42 --salida datos/crm_ejemplo.json

Claves del diseño:
- Faker (locale es_AR) produce nombres, teléfonos y direcciones argentinas.
- La semilla hace la generación reproducible: mismo seed => mismos datos.
- Los estados se generan por PERFIL, para que sean coherentes entre sí
  (nadie 'De baja' con conexión 'Habilitada' y deuda).
- Los datos son claramente falsos: NUNCA pongas clientes reales acá.
"""
import argparse
import json
import random

from faker import Faker


# Catálogo de planes: código -> tecnología, segmento, velocidad y abono.
PLANES = {
    "FOEmp300":  {"tech": "fibra",    "segmento": "empresa", "velocidad": 300,  "abono": 85000},
    "FOEmp500":  {"tech": "fibra",    "segmento": "empresa", "velocidad": 500,  "abono": 120000},
    "FOHogar100":{"tech": "fibra",    "segmento": "hogar",   "velocidad": 100,  "abono": 18000},
    "FOHogar300":{"tech": "fibra",    "segmento": "hogar",   "velocidad": 300,  "abono": 26000},
    "WIEmp60":   {"tech": "wireless", "segmento": "empresa", "velocidad": 60,   "abono": 55000},
    "WIEmp100":  {"tech": "wireless", "segmento": "empresa", "velocidad": 100,  "abono": 75000},
    "WIHogar25": {"tech": "wireless", "segmento": "hogar",   "velocidad": 25,   "abono": 12000},
    "WIHogar60": {"tech": "wireless", "segmento": "hogar",   "velocidad": 60,   "abono": 16000},
}

NODOS_BASE = ["CENTRO", "GODOY", "GUAYMALLEN", "MAIPU", "LUJAN", "CHACRAS",
              "DORREGO", "PALMIRA", "RODEO", "SARMIENTO", "BELGRANO", "LAVALLE"]

# Perfiles coherentes: (peso, estado_cliente, estado_contrato, estado_conexion, facturas_adeudadas, [extensiones_usadas])
PERFILES = [
    (0.48, "Habilitado",    "Activo",          "Habilitada",    0, [0]),      # al dia
    (0.15, "Habilitado",    "Activo",          "Moroso",        1, [0, 1]),   # debe 1, conectado
    (0.07, "Habilitado",    "Activo",          "Forzada",       1, [1, 2]),   # debe 1, reconectado con extension
    (0.10, "Habilitado",    "Activo",          "Cortada",       2, [0, 1]),   # debe 2 -> cortado
    (0.05, "Habilitado",    "Proceso de baja", "Habilitada",    1, [0]),      # en proceso de baja
    (0.04, "Deshabilitado", "Proceso de baja", "Cortada",       3, [0]),      # 3 facturas -> cobranzas humanas
    (0.06, "Deshabilitado", "De baja",         "De Baja",       0, [0]),      # dado de baja
    (0.05, "Deshabilitado", "Inactivo",        "Deshabilitada", 0, [0]),      # inactivo
]


def elegir_perfil():
    r = random.random()
    acum = 0.0
    for peso, *resto in PERFILES:
        acum += peso
        if r <= acum:
            return resto
    return list(PERFILES[0][1:])


def elegir_rubro(segmento):
    if segmento == "hogar":
        return random.choices(["familia", "negocio"], weights=[0.9, 0.1])[0]
    return random.choice(["empresa", "negocio", "acuerdo", "licitacion"])


def elegir_categoria(segmento):
    if segmento == "empresa":
        return random.choices(["basico", "vip", "free"], weights=[0.5, 0.4, 0.1])[0]
    return random.choices(["basico", "free", "vip"], weights=[0.7, 0.2, 0.1])[0]


def generar_cliente(fake, indice):
    nombre = f"{fake.first_name()} {fake.last_name()}"
    cod_plan = random.choice(list(PLANES))
    plan = PLANES[cod_plan]

    estado_cliente, estado_contrato, estado_conexion, facturas_adeudadas, exts = elegir_perfil()
    # La deuda deriva de las facturas adeudadas x abono (+ pequeño recargo), para que sea coherente.
    deuda = round(facturas_adeudadas * plan["abono"] * random.uniform(1.0, 1.08), 2) if facturas_adeudadas else 0.0
    extension_pago = random.choice(exts) if deuda > 0 else 0   # sin deuda no hay extensión

    # Resto a refinanciar: algunos clientes con 1 factura ya pagaron el 75% de una deuda
    # previa de 2 facturas y les quedó un saldo pendiente (escenario "segunda llamada").
    saldo_refinanciar = 0.0
    if facturas_adeudadas == 1 and random.random() < 0.25:
        saldo_refinanciar = round(plan["abono"] * random.uniform(0.4, 0.6), 2)

    prefijo = "F" if plan["tech"] == "fibra" else "W"
    nodo = f"{prefijo}-{random.choice(NODOS_BASE)}-{random.randint(1, 15):02d}"

    tel2 = fake.msisdn()[-10:] if random.random() < 0.7 else ""

    return {
        "nombre": nombre,
        "dni": str(fake.random_int(min=20_000_000, max=45_000_000)),
        "nro_cliente": str(480000 + indice),               # 6 dígitos, único
        "categoria_cliente": elegir_categoria(plan["segmento"]),
        "rubro": elegir_rubro(plan["segmento"]),
        "telefono1": fake.msisdn()[-10:],
        "telefono2": tel2,
        "direccion": fake.address().replace("\n", ", "),
        "plan": cod_plan,
        "velocidad_mbps": plan["velocidad"],
        "abono_mensual": plan["abono"],
        "nodo": nodo,
        "estado_cliente": estado_cliente,
        "estado_conexion": estado_conexion,
        "estado_contrato": estado_contrato,
        "facturas_adeudadas": facturas_adeudadas,
        "deuda": deuda,
        "extension_pago": extension_pago,
        "saldo_refinanciar": saldo_refinanciar,
        "email": f"{nombre.split()[0]}.{nombre.split()[1]}@{fake.free_email_domain()}".lower(),
        "fecha_alta": fake.date_between(start_date="-4y", end_date="-2M").isoformat(),
    }


def generar_base(n, seed):
    fake = Faker("es_AR")
    Faker.seed(seed)
    random.seed(seed)
    return [generar_cliente(fake, i) for i in range(1, n + 1)]


def main():
    p = argparse.ArgumentParser(description="Genera un CRM de clientes inventados.")
    p.add_argument("--n", type=int, default=40)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--salida", default="datos/crm_ejemplo.json")
    args = p.parse_args()
    clientes = generar_base(args.n, args.seed)
    with open(args.salida, "w", encoding="utf-8") as f:
        json.dump(clientes, f, ensure_ascii=False, indent=2)
    print(f"OK: {len(clientes)} clientes inventados -> {args.salida}")


if __name__ == "__main__":
    main()
