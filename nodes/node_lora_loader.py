import comfy.sd
import comfy.samplers
import folder_paths
from server import PromptServer
from aiohttp import web
import os
from ..node_tools import get_file_name_without_extension, get_flow_path, load_json, save_json, calculate_sha256, get_model_info, map_base

db_path = get_flow_path("db/loras.json")
print(f"[Flow Control] Lora info database : {db_path}")

def load_lora_info(lora_name):
    db = load_json(db_path)
    lora_info = db.get(lora_name, {})

    if isinstance(lora_info, str):
        lora_info = {}
    
    base = lora_info.get("base", "")
    hash = lora_info.get("hash", "")
    triggers = lora_info.get("triggers", "")
    url = lora_info.get("url", "")

    if base == "":
        print(f"[Flow Control] {lora_name} : Fetch lora information.")
        lora_path = folder_paths.get_full_path("loras", lora_name)
        sha256 = calculate_sha256(lora_path)
        model_info = get_model_info(sha256)
        base = map_base(model_info.get("baseModel", ""))
        if model_info.get("trainedWords", None) is None:
            triggers = ""
        else:
            triggers = ",".join(model_info.get("trainedWords"))
        modelID = model_info.get("modelId", "")
        hash = sha256
        url = f"https://civitai.com/models/{modelID}"

        db[lora_name] = {
            "base": base,
            "hash": hash,
            "triggers": triggers,
            "url": url
            }
        save_json(db_path, db)

    print(f"[Flow Control] {lora_name} : Lora info loaded.")   
    
    return (base, hash, triggers, url)

def save_lora_info(lora_name, base, triggers, url):
    db = load_json(db_path)
    lora_info = db.get(lora_name, {})

    if isinstance(lora_info, str):
        lora_info = {}
    
    if base == "":
        base = lora_info.get("base", "")

    hash = lora_info.get("hash", "")

    if base == "" or hash == "":
        print(f"[Flow Control] {lora_name} : Fetch lora information.")
        lora_path = folder_paths.get_full_path("loras", lora_name)
        sha256 = calculate_sha256(lora_path)
        model_info = get_model_info(sha256)
        base = map_base(model_info.get("baseModel", ""))
        if model_info.get("trainedWords", None) is None:
            triggers = ""
        else:
            triggers = ",".join(model_info.get("trainedWords"))
        modelID = model_info.get("modelId", "")
        hash = sha256
        url = f"https://civitai.com/models/{modelID}"

    db[lora_name] = {
        "base": base,
        "hash": hash,
        "triggers": triggers,
        "url": url
        }
    save_json(db_path, db)

    print(f"[Flow Control] {lora_name} : Lora info saved.")
    
    return (base, hash, triggers, url)

@PromptServer.instance.routes.post("/load_lora_info")
async def load_ckpt_preset(request):
    body = await request.json()
    lora_name = body.get("loraName")

    (base, hash, triggers, url) = load_lora_info(lora_name)

    return web.json_response({
        "base": base,
        "hash": hash,
        "triggers": triggers,
        "url": url
        })

@PromptServer.instance.routes.post("/save_lora_info")
async def save_ckpt_preset(request):
    body = await request.json()
    lora_name = body.get("loraName")
    base = body.get("base")
    triggers = body.get("triggers")
    url = body.get("url")
    
    (base, hash, triggers, url) = save_lora_info(lora_name, base, triggers, url)

    return web.json_response({
        "base": base,
        "hash": hash,
        "triggers": triggers,
        "url": url
        })

@PromptServer.instance.routes.post("/get_loras")
async def get_ckpts(request):
    return web.json_response(folder_paths.get_filename_list("loras"))

class FlowLoraLoader:
    def __init__(self):
        self.loaded_lora = None

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "gen_info": ("GENINFO",),
                "bypass": (['Yes', 'No'], { "default": 'No' }),
                "filter": (["All", "Pony", "SDXL", "SD15"], { "default": "All" }),
                "lora_name": (folder_paths.get_filename_list("loras"), ),
                "strength_model": ("FLOAT", {"default": 1.0, "min": -100.0, "max": 100.0, "step": 0.01}),
                "strength_clip": ("FLOAT", {"default": 1.0, "min": -100.0, "max": 100.0, "step": 0.01}),
                "base": (["", "Pony", "SDXL", "SD15"], { "default": "" }),
                "hash": ("STRING", {"default": ""}),
                "triggers": ("STRING", { "multiline": True }),
                "url": ("STRING", {"default": ""}),
            }
        }
    RETURN_TYPES = ("MODEL", "CLIP", "GENINFO", )
    RETURN_NAMES = ("model", "clip", "gen_info", )
    FUNCTION = "load_lora"

    CATEGORY = "Flow/inputs"

    def load_lora(self, model, clip, gen_info, bypass, filter, lora_name, strength_model, strength_clip, base, hash, triggers, url):
        if bypass == "Yes":
            print(f"[Flow Control] {lora_name} : Bypass.")
            return (model, clip, gen_info)

        if not isinstance(gen_info, dict):
            print(f"[Flow Control] {lora_name} : Invalid generate information type.")
            return (model, clip, gen_info)

        if strength_model == 0 and strength_clip == 0:
            print(f"[Flow Control] {lora_name} : Skip, lora strength is zero.")
            return (model, clip, gen_info)
    
        ckpt_base = gen_info.get("base", "none")
        if ((base == "SDXL" or base == "Pony") and (ckpt_base == "SDXL" or ckpt_base == "Pony")) or ckpt_base == base:
            print(f"[Flow Control] {lora_name} : Loading...")
        else:
            print(f"[Flow Control] {lora_name} : Skip, checkpoint base is {ckpt_base}.")
            return (model, clip, gen_info)

        loras = gen_info.get("loras", {})
        lora_name_without_ext = get_file_name_without_extension(lora_name)
        loras[lora_name_without_ext] = hash[:10]
        gen_info["loras"] = loras

        lora_path = folder_paths.get_full_path("loras", lora_name)
        lora = None
        if self.loaded_lora is not None:
            if self.loaded_lora[0] == lora_path:
                lora = self.loaded_lora[1]
            else:
                temp = self.loaded_lora
                self.loaded_lora = None
                del temp

        if lora is None:
            lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
            self.loaded_lora = (lora_path, lora)

        model_lora, clip_lora = comfy.sd.load_lora_for_models(model, clip, lora, strength_model, strength_clip)
        return (model_lora, clip_lora, gen_info)

class FlowLoraLoaderModelOnly:
    def __init__(self):
        self.loaded_lora = None

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL",),
                "gen_info": ("GENINFO",),
                "bypass": (['Yes', 'No'], { "default": 'No' }),
                "filter": (["All", "Flux", "Pony", "SDXL", "SD15"], { "default": "All" }),
                "lora_name": (folder_paths.get_filename_list("loras"), ),
                "strength_model": ("FLOAT", {"default": 1.0, "min": -100.0, "max": 100.0, "step": 0.01}),
                "base": (["", "Flux", "Pony", "SDXL", "SD15"], { "default": "" }),
                "hash": ("STRING", {"default": ""}),
                "triggers": ("STRING", { "multiline": True }),
                "url": ("STRING", {"default": ""}),
            }
        }
    RETURN_TYPES = ("MODEL", "GENINFO", )
    RETURN_NAMES = ("model", "gen_info", )
    FUNCTION = "load_lora"

    CATEGORY = "Flow/inputs"

    def load_lora(self, model, gen_info, bypass, filter, lora_name, strength_model, base, hash, triggers, url):
        if bypass == "Yes":
            print(f"[Flow Control] {lora_name} : Bypass.")
            return (model, gen_info)

        if not isinstance(gen_info, dict):
            print(f"[Flow Control] {lora_name} : Invalid generate information type.")
            return (model, gen_info)

        if strength_model == 0:
            print(f"[Flow Control] {lora_name} : Skip, lora strength is zero.")
            return (model, gen_info)
    
        ckpt_base = gen_info.get("base", "none")
        if ((base == "SDXL" or base == "Pony") and (ckpt_base == "SDXL" or ckpt_base == "Pony")) or ckpt_base == base:
            print(f"[Flow Control] {lora_name} : Loading...")
        else:
            print(f"[Flow Control] {lora_name} : Skip, checkpoint base is {ckpt_base}.")
            return (model, gen_info)

        loras = gen_info.get("loras", {})
        lora_name_without_ext = get_file_name_without_extension(lora_name)
        loras[lora_name_without_ext] = hash[:10]
        gen_info["loras"] = loras

        lora_path = folder_paths.get_full_path("loras", lora_name)
        lora = None
        if self.loaded_lora is not None:
            if self.loaded_lora[0] == lora_path:
                lora = self.loaded_lora[1]
            else:
                temp = self.loaded_lora
                self.loaded_lora = None
                del temp

        if lora is None:
            lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
            self.loaded_lora = (lora_path, lora)

        model_lora, _ = comfy.sd.load_lora_for_models(model, None, lora, strength_model, 0)
        return (model_lora, gen_info)
