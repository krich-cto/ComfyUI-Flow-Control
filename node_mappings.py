

try:
    from .nodes.node_checkpoint_preset_loader import *
    from .nodes.node_conditioning_auto_switch import *
    from .nodes.node_clip_condition import *
    from .nodes.node_clip_text_encode import *
    from .nodes.node_flux_preset_loader import *
    from .nodes.node_gate import *
    from .nodes.node_image_auto_batch import *
    from .nodes.node_image_condition import *
    from .nodes.node_ksampler import *
    from .nodes.node_latent_auto_batch import *
    from .nodes.node_latent_condition import *
    from .nodes.node_lora_loader import *
    from .nodes.node_model_manager import *
    from .nodes.node_save_image import *
except ImportError as e:
    print("\033[34m[Flow Control]\033[0m : \033[92mFailed to load nodes.\033[0m")
    print(e)

NODE_CLASS_MAPPINGS = {
    "FlowCheckpointPresetLoader": FlowCheckpointPresetLoader,
    "FlowConditioningAutoSwitch": FlowConditioningAutoSwitch,
    "FlowClipCondition": FlowClipCondition,
    "FlowClipTextEncode": FlowCLIPTextEncode,
    "FlowFluxPresetLoader": FlowFluxPresetLoader,
    "FlowGate": FlowGate,
    "FlowImageCondition": FlowImageCondition,
    "FlowImageAutoBatch": FlowImageAutoBatch,
    "FlowKSampler": FlowKSampler,
    "FlowLatentCondition": FlowLatentCondition,
    "FlowLatentAutoBatch": FlowLatentAutoBatch,
    "FlowLoraLoader": FlowLoraLoader,
    "FlowLoraLoaderModelOnly": FlowLoraLoaderModelOnly,
    "FlowModelManager": FlowModelManager,
    "FlowSaveImage": FlowSaveImage,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "FlowCheckpointPresetLoader": "Flow - Checkpoint Preset Loader",
    "FlowConditioningAutoSwitch": "Flow - Conditioning Auto Switch",
    "FlowClipCondition": "Flow - Clip Condition",
    "FlowClipTextEncode": "Flow - CLIP Text Encode",
    "FlowFluxPresetLoader": "Flow - Flux Preset Loader",
    "FlowGate": "Flow - Gate",
    "FlowImageCondition": "Flow - Image Condition",
    "FlowImageAutoBatch": "Flow - Image Auto Batch",
    "FlowKSampler": "Flow - KSampler",
    "FlowLatentCondition": "Flow - Latent Condition",
    "FlowLatentAutoBatch": "Flow - Latent Auto Batch",
    "FlowLoraLoader": "Flow - Lora Loader",
    "FlowLoraLoaderModelOnly": "Flow - Lora Loader (Model Only)",
    "FlowModelManager": "Flow - Model Manager",
    "FlowSaveImage": "Flow - Save Image",
}
WEB_DIRECTORY = "./js"