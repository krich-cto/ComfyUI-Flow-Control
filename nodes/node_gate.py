class FlowGate:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "output": (['Single', 'Multiple'], { "default": 'Single' }),
                "gate_1": ("STRING", {"default": ""})
            },
            "optional": {
                "gate_2": ("STRING", {"default": ""}),
                "gate_3": ("STRING", {"default": ""}),
                "gate_4": ("STRING", {"default": ""}),
                "gate_5": ("STRING", {"default": ""}),
                "gate_6": ("STRING", {"default": ""}),
                "gate_7": ("STRING", {"default": ""}),
                "gate_8": ("STRING", {"default": ""}),
                "gate_9": ("STRING", {"default": ""})
            }
        }

    RETURN_TYPES = ("STRING", )
    RETURN_NAMES = ("gates", )

    FUNCTION = "execute"
    CATEGORY = "Flow/conditions"

    def execute(self, **args):
        values = []
        for key, value in args.items():
            if key.startswith("gate_"):
                trim_value = value.strip()
                if len(trim_value) > 0:
                    values.append(trim_value)

        result = ','.join(values)
        return (result, )
