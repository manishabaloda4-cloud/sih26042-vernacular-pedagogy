"""Swappable translation and text-to-speech engines.

TRANSLATION_ENGINE is a comma-separated list tried in order (default: google_free,mymemory).
  google_free | mymemory | local_model | mock
  local_model = our fine-tuned NLLB + LoRA adapter (see notebooks/train_hi_pa_lora.ipynb)
translate() returns (text, engine_name) so every answer can be traced to the engine that made it.
"""
import os


class EngineError(Exception):
    pass


def _google_free(text: str, source: str, target: str) -> str:
    from deep_translator import GoogleTranslator
    return GoogleTranslator(source=source, target=target).translate(text)


_MYMEMORY_NAMES = {"hi": "hindi", "pa": "punjabi", "en": "english"}


def _mymemory(text: str, source: str, target: str) -> str:
    from deep_translator import MyMemoryTranslator
    return MyMemoryTranslator(source=_MYMEMORY_NAMES[source],
                              target=_MYMEMORY_NAMES[target]).translate(text)


_NLLB_CODES = {"hi": "hin_Deva", "pa": "pan_Guru", "en": "eng_Latn"}
_LOCAL = {}


def _local_model(text: str, source: str, target: str) -> str:
    """Base NLLB-200 (distilled 600M) + our LoRA adapter, merged, run on this machine."""
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    if "model" not in _LOCAL:
        base = os.environ.get("LOCAL_MODEL_BASE", "facebook/nllb-200-distilled-600M")
        adapter = os.environ.get("LOCAL_MODEL_DIR", "models/hi-pa-lora")
        if not os.path.isdir(adapter):
            raise EngineError(f"Adapter folder '{adapter}' not found. Train it with the notebook "
                              "and unzip hi-pa-lora.zip there.")
        from peft import PeftModel
        tok = AutoTokenizer.from_pretrained(base)
        model = AutoModelForSeq2SeqLM.from_pretrained(base, use_safetensors=False)
        model = PeftModel.from_pretrained(model, adapter).merge_and_unload()
        model.eval()
        _LOCAL.update(tok=tok, model=model)
    tok, model = _LOCAL["tok"], _LOCAL["model"]
    tok.src_lang = _NLLB_CODES[source]
    inputs = tok(text, return_tensors="pt", truncation=True, max_length=128)
    with torch.no_grad():
        out = model.generate(**inputs, num_beams=4, max_new_tokens=128,
                             forced_bos_token_id=tok.convert_tokens_to_ids(_NLLB_CODES[target]))
    return tok.batch_decode(out, skip_special_tokens=True)[0]


_ENGINES = {"google_free": _google_free, "mymemory": _mymemory, "local_model": _local_model}


def translate(text: str, source: str, target: str):
    """Try each configured engine in order. Returns (translated_text, engine_name)."""
    names = [n.strip() for n in
             os.environ.get("TRANSLATION_ENGINE", "google_free,mymemory").split(",") if n.strip()]
    if "mock" in names:
        return f"[{target}] {text}", "mock"
    errors = []
    for name in names:
        fn = _ENGINES.get(name)
        if fn is None:
            errors.append(f"{name}: unknown engine")
            continue
        try:
            out = fn(text, source, target)
            if out:
                return out, name
            errors.append(f"{name}: empty result")
        except Exception as e:  # rate limit, network error, missing model ...
            errors.append(f"{name}: {e}")
    raise EngineError("All translation engines failed: " + " | ".join(errors))


def synthesize(text: str, lang: str, out_path: str) -> None:
    name = os.environ.get("TTS_ENGINE", "gtts")
    if name == "mock":
        with open(out_path, "wb") as f:
            f.write(b"MOCKMP3")
        return
    if name == "gtts":
        try:
            from gtts import gTTS
            gTTS(text=text, lang=lang).save(out_path)
        except Exception as e:
            raise EngineError(f"Text-to-speech failed: {e}")
        return
    raise EngineError(f"Unknown TTS_ENGINE '{name}'")
