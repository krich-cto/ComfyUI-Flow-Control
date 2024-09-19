import latent_preview
import gc
import torch
import comfy.sample
import comfy.samplers
import comfy.utils
import node_helpers
from nodes import common_ksampler
from comfy_extras.nodes_custom_sampler import Noise_RandomNoise, Guider_Basic

def get_sigmas(model, scheduler, steps, denoise):
    total_steps = steps
    if denoise < 1.0:
        if denoise <= 0.0:
            return torch.FloatTensor([])
        total_steps = int(steps/denoise)

    sigmas = comfy.samplers.calculate_sigmas(model.get_model_object("model_sampling"), scheduler, total_steps).cpu()
    sigmas = sigmas[-(steps + 1):]
    return sigmas

def flux_sampler(model, conditioning, seed, steps, guidance, denoise, sampler_name, scheduler, latent_image):
    print(f"[Flow Control] FluxSampler : Noise_RandomNoise")
    # Noise_RandomNoise
    noise = Noise_RandomNoise(seed)

    print(f"[Flow Control] FluxSampler : FluxGuidance")
    # FluxGuidance
    conditioning = node_helpers.conditioning_set_values(conditioning, {"guidance": guidance})

    print(f"[Flow Control] FluxSampler : BasicGuider")
    # BasicGuider
    guider = Guider_Basic(model)
    guider.set_conds(conditioning)

    print(f"[Flow Control] FluxSampler : BasicScheduler")
    # BasicScheduler
    sigmas = get_sigmas(model, scheduler, steps, denoise)
    
    print(f"[Flow Control] FluxSampler : KSamplerSelect")
    # KSamplerSelect
    sampler = comfy.samplers.sampler_object(sampler_name)

    print(f"[Flow Control] FluxSampler : SamplerCustomAdvanced")
    # SamplerCustomAdvanced
    latent = latent_image
    latent_image = latent["samples"]
    latent = latent.copy()
    latent_image = comfy.sample.fix_empty_latent_channels(guider.model_patcher, latent_image)
    latent["samples"] = latent_image

    noise_mask = None
    if "noise_mask" in latent:
        noise_mask = latent["noise_mask"]

    x0_output = {}
    callback = latent_preview.prepare_callback(guider.model_patcher, sigmas.shape[-1] - 1, x0_output)

    disable_pbar = not comfy.utils.PROGRESS_BAR_ENABLED
    samples = guider.sample(noise.generate_noise(latent), latent_image, sampler, sigmas, denoise_mask=noise_mask, callback=callback, disable_pbar=disable_pbar, seed=noise.seed)
    samples = samples.to(comfy.model_management.intermediate_device())

    out = latent.copy()
    out["samples"] = samples

    return (out, )

class FlowKSampler:
    @classmethod
    def INPUT_TYPES(s):
        return {"required":
                    {
                    "basic_pipe" : ("BASIC_PIPE", ),
                    "gen_info": ("GENINFO", ),
                    "latent_image": ("LATENT", ),
                    "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                    "denoise": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),    
                     }
                }

    RETURN_TYPES = ("LATENT", "BASIC_PIPE", "GENINFO", )
    RETURN_NAMES = ("latent", "basic_pipe", "gen_info", )
    FUNCTION = "sample"

    CATEGORY = "Flow/Sampler"

    def sample(self, basic_pipe, gen_info, latent_image, seed, denoise=1.0):
        if not isinstance(gen_info, dict):
            print(f"[Flow Control] KSampler : Invalid generate information type.")
            return (latent_image, gen_info)

        base = gen_info.get("base", "")
        steps = gen_info.get("steps", 20)
        cfg = gen_info.get("cfg", 7)
        sampler_name = gen_info.get("sampler_name", "dpmpp_2m")
        scheduler = gen_info.get("scheduler", "karras")
        gen_info["seed"] = seed
        gen_info["denoise"] = denoise

        model, _, _, positive, negative = basic_pipe
        if base == "Flux":
            print(f"[Flow Control] KSampler Preset : Steps = {steps}, Guidance = {cfg}, Sampler = {sampler_name}, Scheduler = {scheduler}, Seed = {seed}, Denoise = {denoise}")
            samples = flux_sampler(model, positive, seed, steps, cfg, denoise, sampler_name, scheduler, latent_image)
        else:  
            print(f"[Flow Control] KSampler Preset : Steps = {steps}, Cfg = {cfg}, Sampler = {sampler_name}, Scheduler = {scheduler}, Seed = {seed}, Denoise = {denoise}")
            samples = common_ksampler(model, seed, steps, cfg, sampler_name, scheduler, positive, negative, latent_image, denoise=denoise)

        samples += (basic_pipe, gen_info, )
        return samples
