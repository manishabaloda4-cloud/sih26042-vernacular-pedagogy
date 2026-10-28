"""Swappable translation and text-to-speech engines.

TRANSLATION_ENGINE is a comma-separated list tried in order (default: google_free,mymemory).
  google_free | mymemory | mock
TTS_ENGINE = gtts (default) | mock
To add Bhashini / Google Cloud / IndicTrans2, add a function and register it in _ENGINES.
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


_ENGINES = {"google_free": _google_free, "mymemory": _mymemory}


def translate(text: str, source: str, target: str) -> str:
    names = [n.strip() for n in
             os.environ.get("TRANSLATION_ENGINE", "google_free,mymemory").split(",") if n.strip()]
    if "mock" in names:
        return f"[{target}] {text}"
    errors = []
    for name in names:
        fn = _ENGINES.get(name)
        if fn is None:
            errors.append(f"{name}: unknown engine")
            continue
        try:
            out = fn(text, source, target)
            if out:
                return out
            errors.append(f"{name}: empty result")
        except Exception as e:  # rate limit, network error, unsupported language ...
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