"""
Wrapper estable del LLM local (Clase 2).

El resto del sistema NUNCA toca llama.cpp: solo usa `consultar_llm`.
Esto hace el modelo intercambiable (LFM2.5, Hermes, etc.): cambiás REPO_ID/FILENAME
y nada más se entera.

El modelo se carga una sola vez con `cargar_modelo()`. Si no se cargó,
`consultar_llm` devuelve el contrato de error en vez de romper: así las partes
deterministas del sistema (reglas, orquestación) se pueden usar y testear sin el modelo.
"""
import time

# Modelo por defecto (el de las Clases 2 y 3). Para usar Hermes, cambiá estas dos líneas.
REPO_ID = "unsloth/LFM2.5-1.2B-Instruct-GGUF"
FILENAME = "LFM2.5-1.2B-Instruct-Q8_0.gguf"

_llm = None  # instancia única del modelo (se llena con cargar_modelo)


def cargar_modelo(n_ctx: int = 4096, n_gpu_layers: int = 0):
    """Descarga (si falta) y carga el modelo local. Devuelve la instancia."""
    global _llm
    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama

    ruta = hf_hub_download(repo_id=REPO_ID, filename=FILENAME)  # usa caché si ya existe
    _llm = Llama(model_path=ruta, n_ctx=n_ctx, n_gpu_layers=n_gpu_layers, verbose=False)
    return _llm


def consultar_llm(consulta: str, instruccion: str,
                  temperature: float = 0.2, max_tokens: int = 160) -> dict:
    """Única puerta al modelo. Devuelve SIEMPRE un dict con la misma forma."""
    if not isinstance(consulta, str) or not consulta.strip():
        return {"ok": False, "error": "consulta vacía", "modo": "validacion"}
    if _llm is None:
        return {"ok": False, "error": "modelo no cargado (llamá a cargar_modelo())",
                "modo": "sin_modelo"}

    inicio = time.time()
    salida = _llm.create_chat_completion(
        messages=[
            {"role": "system", "content": instruccion},
            {"role": "user", "content": consulta},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return {
        "ok": True,
        "pregunta": consulta,
        "respuesta": salida["choices"][0]["message"]["content"].strip(),
        "modo": REPO_ID,
        "duracion_s": round(time.time() - inicio, 2),
    }
