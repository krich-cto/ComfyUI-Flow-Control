class FlowLatentCondition:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "latent": ("LATENT",),
                "gates": ("STRING", {"forceInput": True}),
             }
        }

    RETURN_TYPES = ("LATENT", "LATENT", "LATENT", "LATENT", "LATENT", "LATENT", "LATENT", "LATENT", "LATENT", )
    RETURN_NAMES = ("gate_1", "gate_2", "gate_3", "gate_4", "gate_5", "gate_6", "gate_7", "gate_8", "gate_9", )

    FUNCTION = "execute"
    CATEGORY = "Flow/begin-conditions"

    def execute(self, latent, gates):
        condition_values = gates.split(",")

        result = []
        for x in range(len(condition_values)):
            result.append(latent)

        return tuple(result)
