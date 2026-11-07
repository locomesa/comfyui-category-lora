"""Small per-user LoRA presets, separate from individual workflow rows."""
import json
import math
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

from aiohttp import web


def key_for(name):
    if not isinstance(name, str) or not name.strip() or len(name) > 4096:
        raise ValueError("Choose a LoRA file before saving a preset.")
    name = name.replace("\\", "/").strip()
    if name.startswith("/") or ":" in name or ".." in name.split("/"):
        raise ValueError("LoRA preset names must be relative model names.")
    return name.lower()


def clean_preset(row):
    if not isinstance(row, dict):
        raise ValueError("A LoRA preset must be an object.")
    preset = {}
    for field in ("categories", "triggers", "custom"):
        values = row.get(field, [])
        if not isinstance(values, list) or len(values) > 64:
            raise ValueError(f"Preset {field} must be a list of up to 64 words or categories.")
        if any(not isinstance(value, str) or len(value) > 2048 for value in values):
            raise ValueError(f"Preset {field} contains an invalid word or category.")
        preset[field] = list(dict.fromkeys(value.strip() for value in values if value.strip()))
    for field in ("sm", "sc"):
        value = row.get(field, row.get("sm", 1.0))
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not -10 <= value <= 10:
            raise ValueError("Preset strengths must be finite numbers between -10 and 10.")
        preset[field] = round(value, 2)
    return preset


def read_presets(path):
    path = Path(path)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("presets"), dict):
        raise ValueError("The LoRA preset library has an unsupported format; restore its backup.")
    return data["presets"]


def write_preset(path, name, row):
    key = key_for(name)
    preset = clean_preset(row)
    path = Path(path)
    presets = read_presets(path)
    presets[key] = {"name": name, **preset}
    path.parent.mkdir(parents=True, exist_ok=True)
    # Preserve the previous good library before replacing it atomically.
    if path.exists():
        path.with_suffix(".json.bak").write_bytes(path.read_bytes())
    descriptor, temporary = tempfile.mkstemp(prefix="presets-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"version": 1, "presets": presets}, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return presets[key]


def register_routes(server):
    def library_path(request):
        # Fixed storage path; model names are keys inside JSON, never file paths.
        return server.user_manager.get_request_user_filepath(request, "category_lora/presets.json")

    @server.routes.get("/category_lora/presets")
    async def get_presets(request):
        try:
            return web.json_response({"version": 1, "presets": read_presets(library_path(request))})
        except (ValueError, OSError) as error:
            return web.json_response({"error": str(error)}, status=500)

    @server.routes.post("/category_lora/presets")
    async def save_preset(request):
        origin = request.headers.get("Origin")
        if origin and urlsplit(origin).netloc != request.host:
            return web.json_response({"error": "Cross-origin preset changes are not allowed."}, status=403)
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("Expected a LoRA preset object.")
            name = body.get("name")
            preset = write_preset(library_path(request), name, body.get("preset"))
            return web.json_response({"key": key_for(name), "preset": preset})
        except (ValueError, TypeError) as error:
            return web.json_response({"error": str(error)}, status=400)
        except OSError as error:
            return web.json_response({"error": f"Could not save the LoRA preset: {error}"}, status=500)
