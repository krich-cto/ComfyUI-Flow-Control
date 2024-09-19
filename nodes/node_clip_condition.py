class FlowClipCondition:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "clip": ("CLIP",),
                "base": ("BASE",),
             }
        }

    RETURN_TYPES = ("CLIP", "CLIP", )
    RETURN_NAMES = ("SD15 clip", "SDXL clip", )

    FUNCTION = "execute"
    CATEGORY = "Flow/begin-conditions"

    def execute(self, clip, base):
        return (clip, clip)
