"""
Wrapper del LLM — CONMUTABLE entre proveedor local (llama.cpp) y OpenRouter.

El resto del sistema NUNCA se entera del proveedor: solo usa consultar_llm(),
que devuelve siempre la misma forma de dict. Cambiar de modelo es configuración,
no código (fue justo para esto que aislamos el modelo detrás del wrapper).

Configuración (por variables de entorno o por un archivo .env en la raíz):
    IVR_PROVEEDOR      "local" (por defecto) | "openrouter"
    OPENROUTER_API_KEY tu clave (solo para openrouter). NUNCA la subas al repo.
    IVR_MODELO         slug del modelo en openrouter (por defecto deepseek v4 flash)

Privacidad: con "openrouter" el texto viaja a un tercero. Para datos reales de
clientes, es una decisión de privacidad a considerar (ISO 42001).
"""
import os
import time
import json
import urllib.request
import urllib.error


def _cargar_dotenv(ruta: str = ".env"):
    """Carga un .env simple (KEY=VALUE) si existe, sin pisar variables ya definidas."""
    if os.path.exists(ruta):
        for linea in open(ruta, encoding="utf-8"):
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_cargar_dotenv()

PROVEEDOR = os.environ.get("IVR_PROVEEDOR", "local")          # "local" | "openrouter"
MODELO_OPENROUTER = os.environ.get("IVR_MODELO", "deepseek/deepseek-v4-flash-0731")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# --- local (llama.cpp) ---
REPO_ID = "unsloth/LFM2.5-1.2B-Instruct-GGUF"
FILENAME = "LFM2.5-1.2B-Instruct-Q8_0.gguf"
_llm = None


def cargar_modelo(n_ctx: int = 4096, n_gpu_layers: int = 0):
    """Con 'local' descarga/carga el modelo. Con 'openrouter' no hay nada que cargar."""
    if PROVEEDOR == "openrouter":
        print(f"Proveedor: OpenRouter · modelo {MODELO_OPENROUTER}. Sin descarga local.")
        return None
    global _llm
    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama
    ruta = hf_hub_download(repo_id=REPO_ID, filename=FILENAME)
    _llm = Llama(model_path=ruta, n_ctx=n_ctx, n_gpu_layers=n_gpu_layers, verbose=False)
    print(f"Proveedor: local · {REPO_ID}")
    return _llm


def _consultar_local(instruccion, consulta, temperature, max_tokens, inicio):
    if _llm is None:
        return {"ok": False, "error": "modelo local no cargado (llamá a cargar_modelo())",
                "modo": "sin_modelo"}
    salida = _llm.create_chat_completion(
        messages=[{"role": "system", "content": instruccion},
                  {"role": "user", "content": consulta}],
        temperature=temperature, max_tokens=max_tokens,
    )
    return {"ok": True, "pregunta": consulta,
            "respuesta": salida["choices"][0]["message"]["content"].strip(),
            "modo": REPO_ID, "duracion_s": round(time.time() - inicio, 2)}


def _consultar_openrouter(instruccion, consulta, temperature, max_tokens, inicio):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return {"ok": False, "error": "falta OPENROUTER_API_KEY en el entorno/.env",
                "modo": "sin_api_key"}
    cuerpo = json.dumps({
        "model": MODELO_OPENROUTER,
        "messages": [{"role": "system", "content": instruccion},
                     {"role": "user", "content": consulta}],
        "temperature": temperature,
        # Los modelos de razonamiento pueden gastar el presupuesto "pensando" y dejar
        # content vacío. Para clasificar no hace falta: apagamos el razonamiento y damos
        # margen holgado de tokens de respuesta.
        "max_tokens": max(max_tokens, 512),
        "reasoning": {"enabled": False},
    }).encode("utf-8")
    req = urllib.request.Request(
        OPENROUTER_URL, data=cuerpo, method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.read().decode('utf-8')[:200]}",
                "modo": "openrouter"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "modo": "openrouter"}
    try:
        mensaje = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        return {"ok": False, "error": "respuesta sin 'choices'", "modo": "openrouter"}
    # content puede venir None (p. ej. modelos de razonamiento que usan otro campo).
    contenido = mensaje.get("content") or mensaje.get("reasoning")
    if not contenido:
        return {"ok": False, "error": "el proveedor devolvió content vacío", "modo": "openrouter"}
    return {"ok": True, "pregunta": consulta, "respuesta": contenido.strip(),
            "modo": MODELO_OPENROUTER, "duracion_s": round(time.time() - inicio, 2)}


def consultar_llm(consulta, instruccion, temperature=0.2, max_tokens=160):
    """Única puerta al modelo. Enruta al proveedor configurado; misma forma de salida."""
    if not isinstance(consulta, str) or not consulta.strip():
        return {"ok": False, "error": "consulta vacía", "modo": "validacion"}
    inicio = time.time()
    if PROVEEDOR == "openrouter":
        return _consultar_openrouter(instruccion, consulta, temperature, max_tokens, inicio)
    return _consultar_local(instruccion, consulta, temperature, max_tokens, inicio)
