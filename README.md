# IVR-agente

Un IVR de atención al cliente para una empresa de internet, reconstruido como
**agente con LLM local**. Reemplaza el menú rígido ("presione 1...") por un
orquestador que entiende lenguaje natural, identifica al cliente contra un CRM
y enruta a la categoría correcta.

El diseño sigue una idea central: **el modelo solo propone; Python decide y controla.**

## Arquitectura (patrón orchestrator–workers)

```
mensaje
   │
   ▼
orquestador  ──(LLM interpreta intención)──►  decide nodo
   │
   ├─ contratar ─────────────────────────────►  ventas
   ├─ identificar ─(REGLA saca DNI/nro)─►[CRM]─►  cliente identificado
   └─ menu_cliente ─(motivo libre)──────────►  worker de categoría
                                               (facturacion | pagos | asesor | soporte)
```

- El **LLM** (`agente/llm.py`, `agente/clasificador.py`) solo clasifica intención.
- Las **reglas** (`agente/reglas.py`) extraen identificadores y bloquean secretos.
- La **herramienta** (`agente/crm.py`) consulta el CRM.
- El **orquestador** (`agente/orquestador.py`) camina el flujo y conserva el control.
- Los **workers** (`agente/categorias/`) resuelven cada categoría. Hoy son simples;
  mañana cada uno se reemplaza por un agente completo sin tocar el orquestador.

## Estructura

```
ivr-agente/
├── agente/
│   ├── llm.py            # wrapper del LLM local (Clase 2)
│   ├── crm.py            # herramienta: buscar_cliente
│   ├── reglas.py         # extraer_identificador, detectar_dato_sensible
│   ├── clasificador.py   # clasificar_intencion (LLM propone, Python valida)
│   ├── orquestador.py    # la máquina de estados
│   └── categorias/       # los workers (futuros sub-agentes)
├── datos/
│   └── crm_ejemplo.json  # clientes INVENTADOS (Faker)
├── scripts/
│   ├── generar_crm.py    # genera la base falsa
│   └── demo_consola.py   # probar el agente en consola
├── notebooks/            # las clases (importan de agente/)
└── tests/
    └── test_flujo.py     # tests deterministas, sin el modelo
```

## Puesta en marcha

```bash
python -m venv .venv && source .venv/bin/activate   # opcional
pip install -r requirements.txt

python scripts/generar_crm.py --n 40 --seed 42      # genera datos/crm_ejemplo.json
python -m pytest -q                                  # tests deterministas (no baja el modelo)
python scripts/demo_consola.py                       # demo con el LLM real (descarga el modelo)
```

## Generar la base de datos inventada

`scripts/generar_crm.py` usa **Faker** (locale `es_AR`) para producir datos falsos
realistas. La semilla hace la generación reproducible. Para agregar una columna,
editá `generar_cliente` (hay ejemplos comentados).

```bash
python scripts/generar_crm.py --n 100 --seed 7 --salida datos/crm_ejemplo.json
```

## Privacidad (importante)

- **Nunca** subas datos reales de clientes. En el repo solo va `crm_ejemplo.json` (inventado).
- La traza del agente guarda banderas (`hallado: true`), **no** el DNI ni datos personales.
- El modelo (`*.gguf`) y los secretos (`.env`) están en `.gitignore`.

## Notebooks y Git

Los `.ipynb` guardan salidas y ensucian los diffs. Este repo mantiene el código
estable en `agente/`; los notebooks solo importan de ahí. Si querés diffs limpios,
`pip install nbstripout && nbstripout --install`.
