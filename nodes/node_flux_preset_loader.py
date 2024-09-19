import comfy.sd
import comfy.samplers
import folder_paths
from server import PromptServer
from aiohttp import web
import os
from ..node_tools import get_file_name_without_extension, get_flow_path, load_json, save_json, calculate_sha256, get_model_info, map_base
from .gguf.ops import GGMLTensor, GGMLOps, move_patch_to_device
from .gguf.dequant import is_quantized, is_torch_compatible
from .gguf.nodes import gguf_sd_loader, GGUFModelPatcher

db_path = get_flow_path("db/flux_checkpoints.json")
print(f"[Flow Control] Flux presets database : {db_path}")

# Add a custom keys for files ending in .gguf
orig = folder_paths.folder_names_and_paths.get("diffusion_models", folder_paths.folder_names_and_paths.get("unet", [[], set()]))
folder_paths.folder_names_and_paths["diffusion_models"] = (orig[0], {".gguf"})

def load_preset(unet_name):
    db = load_json(db_path)
    ckpt_info = db.get(unet_name, {})

    if isinstance(ckpt_info, str):
        ckpt_info = {}
    
    vae_name = ckpt_info.get("vae_name", "")
    clip_name1 = ckpt_info.get("clip_name1", "")
    clip_name2 = ckpt_info.get("clip_name2", "")
    base = ckpt_info.get("base", "")
    hash = ckpt_info.get("hash", "")
    steps = ckpt_info.get("steps", 20)
    guidance = ckpt_info.get("guidance", 3.5)
    sampler_name = ckpt_info.get("sampler_name", "euler")
    scheduler = ckpt_info.get("scheduler", "simple")
    url = ckpt_info.get("url", "")

    if base == "":
        print(f"[Flow Control] {unet_name} : Fetch checkpoint information.")
        ckpt_path = folder_paths.get_full_path("diffusion_models", unet_name)
        sha256 = calculate_sha256(ckpt_path)
        model_info = get_model_info(sha256)
        base = map_base(model_info.get("baseModel", ""))
        modelID = model_info.get("modelId", "")
        hash = sha256
        url = f"https://civitai.com/models/{modelID}"

        if base == "":
            base = "Flux"

        db[unet_name] = {
            "vae_name": vae_name,
            "clip_name1": clip_name1,
            "clip_name2": clip_name2,
            "base": base,
            "hash": hash,
            "steps": steps,
            "guidance": guidance,
            "sampler_name": sampler_name,
            "scheduler": scheduler,
            "url": url
            }
        save_json(db_path, db)

    print(f"[Flow Control] {unet_name} : Preset loaded.")   
    
    return (vae_name, clip_name1, clip_name2, base, hash, steps, guidance, sampler_name, scheduler, url)

def save_preset(unet_name, vae_name, clip_name1, clip_name2, base, steps, guidance, sampler_name, scheduler, url):
    db = load_json(db_path)

    ckpt_info = db.get(unet_name, {})

    if isinstance(ckpt_info, str):
        ckpt_info = {}
    
    if base == "":
        base = ckpt_info.get("base", "")

    hash = ckpt_info.get("hash", "")

    if base == "" or hash == "":
        print(f"[Flow Control] {unet_name} : Fetch checkpoint information.")
        ckpt_path = folder_paths.get_full_path("diffusion_models", unet_name)
        sha256 = calculate_sha256(ckpt_path)
        model_info = get_model_info(sha256)
        base = map_base(model_info.get("baseModel", ""))
        modelID = model_info.get("modelId", "")
        hash = sha256
        url = f"https://civitai.com/models/{modelID}"

    db[unet_name] = {
        "vae_name": vae_name,
        "clip_name1": clip_name1,
        "clip_name2": clip_name2,
        "base": base,
        "hash": hash,
        "steps": steps,
        "guidance": guidance,
        "sampler_name": sampler_name,
        "scheduler": scheduler,
        "url": url
        }
    save_json(db_path, db)
    print(f"[Flow Control] {unet_name} : Preset saved.")
    
    return (vae_name, clip_name1, clip_name2, base, hash, steps, guidance, sampler_name, scheduler, url)

def get_checkpoints_list():
    filter_files = []
    unet_files = folder_paths.get_filename_list("diffusion_models")
    for file in unet_files:
        ckpt_path = folder_paths.get_full_path("diffusion_models", file)
        size = os.path.getsize(ckpt_path)
        if size > 1048576:
            filter_files.append(file)

    return filter_files

def load_unet(unet_name, weight_dtype):
    model_options = {}
    if weight_dtype == "fp8_e4m3fn":
        model_options["dtype"] = torch.float8_e4m3fn
    elif weight_dtype == "fp8_e4m3fn_fast":
        model_options["dtype"] = torch.float8_e4m3fn
        model_options["fp8_optimizations"] = True
    elif weight_dtype == "fp8_e5m2":
        model_options["dtype"] = torch.float8_e5m2

    unet_path = folder_paths.get_full_path_or_raise("diffusion_models", unet_name)
    model = comfy.sd.load_diffusion_model(unet_path, model_options=model_options)
    return model

def load_unet_gguf(unet_name, dequant_dtype=None, patch_dtype=None, patch_on_device=None):
    ops = GGMLOps()

    if dequant_dtype in ("default", None):
        ops.Linear.dequant_dtype = None
    elif dequant_dtype in ["target"]:
        ops.Linear.dequant_dtype = dequant_dtype
    else:
        ops.Linear.dequant_dtype = getattr(torch, dequant_dtype)

    if patch_dtype in ("default", None):
        ops.Linear.patch_dtype = None
    elif patch_dtype in ["target"]:
        ops.Linear.patch_dtype = patch_dtype
    else:
        ops.Linear.patch_dtype = getattr(torch, patch_dtype)

    # init model
    unet_path = folder_paths.get_full_path("unet", unet_name)
    sd = gguf_sd_loader(unet_path)
    model = comfy.sd.load_diffusion_model_state_dict(
        sd, model_options={"custom_operations": ops}
    )
    if model is None:
        raise RuntimeError("ERROR: Could not detect model type of: {}".format(unet_path))
    
    model = GGUFModelPatcher.clone(model)
    model.patch_on_device = patch_on_device
    return model

@PromptServer.instance.routes.post("/load_flux_preset")
async def load_ckpt_preset(request):
    body = await request.json()
    unet_name = body.get("unetName")

    (vae_name, clip_name1, clip_name2, base, hash, steps, guidance, sampler_name, scheduler, url) = load_preset(unet_name)

    return web.json_response({
        "vaeName": vae_name,
        "clipName1": clip_name1,
        "clipName2": clip_name2,
        "base": base,
        "hash": hash,
        "steps": steps,
        "guidance": guidance,
        "samplerName": sampler_name,
        "scheduler": scheduler,
        "url": url
        })

@PromptServer.instance.routes.post("/save_flux_preset")
async def save_ckpt_preset(request):
    body = await request.json()
    unet_name = body.get("unetName")
    vae_name = body.get("vaeName")
    clip_name1 = body.get("clipName1")
    clip_name2 = body.get("clipName2")
    base = body.get("base")
    steps = body.get("steps")
    guidance = body.get("guidance")
    sampler_name = body.get("samplerName")
    scheduler = body.get("scheduler")
    url = body.get("url")
    
    (vae_name, clip_name1, clip_name2, base, hash, steps, guidance, sampler_name, scheduler, url) = save_preset(unet_name, vae_name, clip_name1, clip_name2, base, steps, guidance, sampler_name, scheduler, url)

    return web.json_response({
        "vaeName": vae_name,
        "clipName1": clip_name1,
        "clipName2": clip_name2,
        "base": base,
        "hash": hash,
        "steps": steps,
        "guidance": guidance,
        "samplerName": sampler_name,
        "scheduler": scheduler,
        "url": url
        })

@PromptServer.instance.routes.post("/get_fluxs")
async def get_ckpts(request):
    return web.json_response(get_checkpoints_list())

class FlowFluxPresetLoader:
    @staticmethod
    def vae_list():
        vaes = []
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
    def clip_list():
        clips = folder_paths.get_filename_list("text_encoders")
        return clips
    
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
                "unet_name": (get_checkpoints_list(), ),
                "weight_dtype": (["default", "fp8_e4m3fn", "fp8_e4m3fn_fast", "fp8_e5m2"],),
                "vae_name": (s.vae_list(), ),
                "clip_name1": (s.clip_list(), ),
                "clip_name2": (s.clip_list(), ),
                "base": (["", "Flux"], { "default": "" }),
                "hash": ("STRING", {"default": ""}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 10000}),
                "guidance": ("FLOAT", {"default": 3.5, "min": 0.0, "max": 100.0, "step": 0.1}),
                "sampler_name": (comfy.samplers.KSampler.SAMPLERS, ),
                "scheduler": (comfy.samplers.KSampler.SCHEDULERS, ),
                "url": ("STRING", {"default": ""}),
            }
        }
    RETURN_TYPES = ("MODEL", "CLIP", "VAE", "GENINFO", )
    RETURN_NAMES = ("model", "clip", "vae", "gen_info", )
    IS_CHANGED = True
    FUNCTION = "load_flux"

    CATEGORY = "Flow/inputs"
    
    def load_flux(self, unet_name, weight_dtype, vae_name, clip_name1, clip_name2, base, hash, steps, guidance, sampler_name, scheduler, url):
        print(f"[Flow Control] {unet_name} : Loading...")

        if unet_name.endswith(".gguf"):
            model = load_unet_gguf(unet_name)
        else:
            model = load_unet(unet_name, weight_dtype)

        clip_path1 = folder_paths.get_full_path_or_raise("text_encoders", clip_name1)
        clip_path2 = folder_paths.get_full_path_or_raise("text_encoders", clip_name2)
        clip = comfy.sd.load_clip(ckpt_paths=[clip_path1, clip_path2], embedding_directory=folder_paths.get_folder_paths("embeddings"), clip_type=comfy.sd.CLIPType.FLUX)

        if vae_name in ["taesd", "taesdxl", "taesd3", "taef1"]:
            sd = self.load_taesd(vae_name)
        else:
            vae_path = folder_paths.get_full_path("vae", vae_name)
            sd = comfy.utils.load_torch_file(vae_path)
        vae = comfy.sd.VAE(sd=sd)

        gen_info = {
            "base": base,
            "ckpt_name": get_file_name_without_extension(unet_name),
            "ckpt_hash": hash[:10],
            "loras": {},
            "positive_prompt": "",
            "negative_prompt": "",
            "seed": 0,
            "steps": steps,
            "cfg": guidance,
            "clip_skip": 0,
            "sampler_name": sampler_name,
            "scheduler": scheduler,
            "width": 0,
            "height": 0,
            "denoise": 1.0
        }

        return (model, clip, vae, gen_info)
