from nodes import common_ksampler

class FlowCLIPTextEncode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "dynamicPrompts": True, "tooltip": "The text to be encoded."}), 
                "clip": ("CLIP", {"tooltip": "The CLIP model used for encoding the text."}),
                "type": (["Positive", "Negative"], { "default": "Positive" }),
                "gen_info": ("GENINFO", ),
            }
        }
    RETURN_TYPES = ("CONDITIONING", "GENINFO", )
    OUTPUT_TOOLTIPS = ("A conditioning containing the embedded text used to guide the diffusion model.",)
    FUNCTION = "encode"

    CATEGORY = "conditioning"
    DESCRIPTION = "Encodes a text prompt using a CLIP model into an embedding that can be used to guide the diffusion model towards generating specific images."

    def encode(self, text, clip, type, gen_info):
        print(f"[Flow Control] CLIP Text {type} : {text[:20]}")

        tokens = clip.tokenize(text)

        if gen_info["base"] == "Flux":
            tokens["t5xxl"] = clip.tokenize(text)["t5xxl"]

        output = clip.encode_from_tokens(tokens, return_pooled=True, return_dict=True)
        cond = output.pop("cond")

        if type == "Positive":
            gen_info["positive_prompt"] = text
        else:
            gen_info["negative_prompt"] = text

        return ([[cond, output]], gen_info, )
