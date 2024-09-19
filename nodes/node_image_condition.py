class FlowImageCondition:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),
                "gates": ("STRING", {"forceInput": True}),
             }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE", )
    RETURN_NAMES = ("gate_1", "gate_2", "gate_3", "gate_4", "gate_5", "gate_6", "gate_7", "gate_8", "gate_9", )

    FUNCTION = "execute"
    CATEGORY = "Flow/begin-conditions"

    def execute(self, image, gates):
        condition_values = gates.split(",")

        result = []
        for x in range(len(condition_values)):
            result.append(image)

        return tuple(result)
