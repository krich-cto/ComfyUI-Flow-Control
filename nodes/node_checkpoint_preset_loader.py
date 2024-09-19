import comfy.sd
import comfy.samplers
import folder_paths
from server import PromptServer
from aiohttp import web
import os
from ..node_tools import get_file_name_without_extension, get_flow_path, load_json, save_json, calculate_sha256, get_model_info, map_base

db_path = get_flow_path("db/checkpoints.json")
print(f"[Flow Control] Checkpoint presets database : {db_path}")

def load_preset(ckpt_name):
    db = load_json(db_path)
    ckpt_info = db.get(ckpt_name, {})

    if isinstance(ckpt_info, str):
        ckpt_info = {}
    
    vae_name = ckpt_info.get("vae_name", "embedded")
    base = ckpt_info.get("base", "")
    hash = ckpt_info.get("hash", "")
    steps = ckpt_info.get("steps", 20)
    cfg = ckpt_info.get("cfg", 7)
    clip_skip = ckpt_info.get("clip_skip", 2)
    sampler_name = ckpt_info.get("sampler_name", "dpmpp_2m")
    scheduler = ckpt_info.get("scheduler", "karras")
    url = ckpt_info.get("url", "")

    if base == "":
        print(f"[Flow Control] {ckpt_name} : Fetch checkpoint information.")
        ckpt_path = folder_paths.get_full_path("checkpoints", ckpt_name)
        sha256 = calculate_sha256(ckpt_path)
        model_info = get_model_info(sha256)
        base = map_base(model_info.get("baseModel", ""))
        modelID = model_info.get("modelId", "")
        hash = sha256
        url = f"https://civitai.com/models/{modelID}"

        db[ckpt_name] = {
            "vae_name": vae_name,
            "base": base,
            "hash": hash,
            "steps": steps,
            "cfg": cfg,
            "clip_skip": clip_skip,
            "sampler_name": sampler_name,
            "scheduler": scheduler,
            "url": url
            }
        save_json(db_path, db)

    print(f"[Flow Control] {ckpt_name} : Preset loaded.")   
    
    return (vae_name, base, hash, steps, cfg, clip_skip, sampler_name, scheduler, url)

def save_preset(ckpt_name, vae_name, base, steps, cfg, clip_skip, sampler_name, scheduler, url):
    db = load_json(db_path)

    ckpt_info = db.get(ckpt_name, {})

    if isinstance(ckpt_info, str):
        ckpt_info = {}
    
    if base == "":
        base = ckpt_info.get("base", "")

    hash = ckpt_info.get("hash", "")

    if base == "" or hash == "":
        print(f"[Flow Control] {ckpt_name} : Fetch checkpoint information.")
        ckpt_path = folder_paths.get_full_path("checkpoints", ckpt_name)
        sha256 = calculate_sha256(ckpt_path)
        model_info = get_model_info(sha256)
        base = map_base(model_info.get("baseModel", ""))
        modelID = model_info.get("modelId", "")
        hash = sha256
        url = f"https://civitai.com/models/{modelID}"

    db[ckpt_name] = {
        "vae_name": vae_name,
        "base": base,
        "hash": hash,
        "steps": steps,
        "cfg": cfg,
        "clip_skip": clip_skip,
        "sampler_name": sampler_name,
        "scheduler": scheduler,
        "url": url
        }
    save_json(db_path, db)
    print(f"[Flow Control] {ckpt_name} : Preset saved.")
    
    return (vae_name, base, hash, steps, cfg, clip_skip, sampler_name, scheduler, url)

def get_checkpoints_list():
    filter_files = []
    files = folder_paths.get_filename_list("checkpoints")
    for file in files:
        ckpt_path = folder_paths.get_full_path("checkpoints", file)
        size = os.path.getsize(ckpt_path)
        if size > 1048576:
            filter_files.append(file)
    
    return filter_files

@PromptServer.instance.routes.post("/load_ckpt_preset")
async def load_ckpt_preset(request):
    body = await request.json()
    ckpt_name = body.get("ckptName")

    (vae_name, base, hash, steps, cfg, clip_skip, sampler_name, scheduler, url) = load_preset(ckpt_name)

    return web.json_response({
        "vaeName": vae_name,
        "base": base,
        "hash": hash,
        "steps": steps,
        "cfg": cfg,
        "clipSkip": clip_skip,
        "samplerName": sampler_name,
        "scheduler": scheduler,
        "url": url
        })

@PromptServer.instance.routes.post("/save_ckpt_preset")
async def save_ckpt_preset(request):
    body = await request.json()
    ckpt_name = body.get("ckptName")
    vae_name = body.get("vaeName")
    base = body.get("base")
    steps = body.get("steps")
    cfg = body.get("cfg")
    clip_skip = body.get("clipSkip")
    sampler_name = body.get("samplerName")
    scheduler = body.get("scheduler")
    url = body.get("url")
    
    (vae_name, base, hash, steps, cfg, clip_skip, sampler_name, scheduler, url) = save_preset(ckpt_name, vae_name, base, steps, cfg, clip_skip, sampler_name, scheduler, url)

    return web.json_response({
        "vaeName": vae_name,
        "base": base,
        "hash": hash,
        "steps": steps,
        "cfg": cfg,
        "clipSkip": clip_skip,
        "samplerName": sampler_name,
        "scheduler": scheduler,
        "url": url
        })

@PromptServer.instance.routes.post("/get_ckpts")
async def get_ckpts(request):
    return web.json_response(get_checkpoints_list())

class FlowCheckpointPresetLoader:
    @staticmethod
    def vae_list():
        vaes = ["embedded"]
        normal_vaes = folder_paths.get_filename_list("vae")
        approx_vaes = folder_paths.get_filename_list("vae_approx")
        sdxl_taesd_enc = False
        sdxl_taesd_dec = False
        sd1_taesd_enc = False
        sd1_taesd_dec = False
        sd3_taesd_enc = False
        sd3_taesd_dec = False
        f1_taesd_enc = False
        f1_taesd_dec = False

        for v in normal_vaes:
            vaes.append(v)

        for v in approx_vaes:
            if v.startswith("taesd_decoder."):
                sd1_taesd_dec = True
            elif v.startswith("taesd_encoder."):
                sd1_taesd_enc = True
            elif v.startswith("taesdxl_decoder."):
                sdxl_taesd_dec = True
            elif v.startswith("taesdxl_encoder."):
                sdxl_taesd_enc = True
            elif v.startswith("taesd3_decoder."):
                sd3_taesd_dec = True
            elif v.startswith("taesd3_encoder."):
                sd3_taesd_enc = True
            elif v.startswith("taef1_encoder."):
                f1_taesd_dec = True
            elif v.startswith("taef1_decoder."):
                f1_taesd_enc = True
        if sd1_taesd_dec and sd1_taesd_enc:
            vaes.append("taesd")
        if sdxl_taesd_dec and sdxl_taesd_enc:
            vaes.append("taesdxl")
        if sd3_taesd_dec and sd3_taesd_enc:
            vaes.append("taesd3")
        if f1_taesd_dec and f1_taesd_enc:
            vaes.append("taef1")
        return vaes
    
    @staticmethod
    def load_taesd(name):
        sd = {}
        approx_vaes = folder_paths.get_filename_list("vae_approx")

        encoder = next(filter(lambda a: a.startswith("{}_encoder.".format(name)), approx_vaes))
        decoder = next(filter(lambda a: a.startswith("{}_decoder.".format(name)), approx_vaes))

        enc = comfy.utils.load_torch_file(folder_paths.get_full_path("vae_approx", encoder))
        for k in enc:
            sd["taesd_encoder.{}".format(k)] = enc[k]

        dec = comfy.utils.load_torch_file(folder_paths.get_full_path("vae_approx", decoder))
        for k in dec:
            sd["taesd_decoder.{}".format(k)] = dec[k]

        if name == "taesd":
            sd["vae_scale"] = torch.tensor(0.18215)
            sd["vae_shift"] = torch.tensor(0.0)
        elif name == "taesdxl":
            sd["vae_scale"] = torch.tensor(0.13025)
            sd["vae_shift"] = torch.tensor(0.0)
        elif name == "taesd3":
            sd["vae_scale"] = torch.tensor(1.5305)
            sd["vae_shift"] = torch.tensor(0.0609)
        elif name == "taef1":
            sd["vae_scale"] = torch.tensor(0.3611)
            sd["vae_shift"] = torch.tensor(0.1159)
        return sd
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "filter": (["All", "Pony", "SDXL", "SD15"], { "default": "All" }),
                "ckpt_name": (get_checkpoints_list(), ),
                "vae_name": (s.vae_list(), ),
                "base": (["", "Pony", "SDXL", "SD15"], { "default": "" }),
                "hash": ("STRING", {"default": ""}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 10000}),
                "cfg": ("FLOAT", {"default": 8.0, "min": 0.0, "max": 100.0, "step":0.1, "round": 0.01}),
                "clip_skip": ("INT", {"default": 1, "min": 1, "max": 24, "step": 1}),
                "sampler_name": (comfy.samplers.KSampler.SAMPLERS, ),
                "scheduler": (comfy.samplers.KSampler.SCHEDULERS, ),
                "url": ("STRING", {"default": ""}),
            }
        }
    RETURN_TYPES = ("MODEL", "CLIP", "VAE", "GENINFO", )
    RETURN_NAMES = ("model", "clip", "vae", "gen_info", )
    FUNCTION = "load_checkpoint"

    CATEGORY = "Flow/inputs"

    def load_checkpoint(self, filter, ckpt_name, vae_name, base, hash, steps, cfg, clip_skip, sampler_name, scheduler, url):
        print(f"[Flow Control] {ckpt_name} : Loading...")

        ckpt_path = folder_paths.get_full_path("checkpoints", ckpt_name)
        model, clip, embedded_vae, _ = comfy.sd.load_checkpoint_guess_config(ckpt_path, output_vae=True, output_clip=True, embedding_directory=folder_paths.get_folder_paths("embeddings"))

        if vae_name == "embedded":
            vae = embedded_vae
        else:
            if vae_name in ["taesd", "taesdxl", "taesd3", "taef1"]:
                sd = self.load_taesd(vae_name)
            else:
                vae_path = folder_paths.get_full_path("vae", vae_name)
                sd = comfy.utils.load_torch_file(vae_path)
            vae = comfy.sd.VAE(sd=sd)

        if clip_skip > 0:
            clip = clip.clone()
            clip.clip_layer(-clip_skip)

        gen_info = {
            "base": base,
            "ckpt_name": get_file_name_without_extension(ckpt_name),
            "ckpt_hash": hash[:10],
            "loras": {},
            "positive_prompt": "",
            "negative_prompt": "",
            "seed": 0,
            "steps": steps,
            "cfg": cfg,
            "clip_skip": clip_skip,
            "sampler_name": sampler_name,
            "scheduler": scheduler,
            "width": 0,
            "height": 0,
            "denoise": 1.0
        }

        return (model, clip, vae, gen_info)
