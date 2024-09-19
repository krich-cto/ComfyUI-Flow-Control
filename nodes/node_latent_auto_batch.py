import comfy.utils # type: ignore
import torch # type: ignore

class FlowLatentAutoBatch:
  @classmethod
  def INPUT_TYPES(cls):  # pylint: disable = invalid-name, missing-function-docstring
    return {
      "required": {},
      "optional": {
        "latent_1": ("LATENT",),
      }
    }

  RETURN_TYPES = ("LATENT", )
  RETURN_NAMES = ("latent", )

  FUNCTION = "execute"
  CATEGORY = "Flow/end-conditions"

  def execute(self, **args):
    latents = []
    for _, value in args.items():
      if value is not None:
        latents.append(value)

    if len(latents) > 0:
      output = latents[0].copy()
      result_sample = latents[0]["samples"]
      result_batch_index = latents[0].get("batch_index", [x for x in range(0, result_sample.shape[0])])
      base_sample = latents[0]["samples"]
      for index in range(1, len(latents), 1):
        sample = latents[index]["samples"]
        if base_sample.shape[1:] != sample.shape[1:]:
          sample = comfy.utils.common_upscale(sample, base_sample.shape[3], base_sample.shape[2], "bilinear", "center")

        batch_index = latents[index].get("batch_index", [x for x in range(0, sample.shape[0])])

        result_sample = torch.cat((result_sample, sample), dim=0)
        result_batch_index = result_batch_index + batch_index
    
      output["samples"] = result_sample
      output["batch_index"] = result_batch_index
      return (output,)
    
    return ()


# class LatentBatch:
#     @classmethod
#     def INPUT_TYPES(s):
#         return {"required": { "samples1": ("LATENT",), "samples2": ("LATENT",)}}

#     RETURN_TYPES = ("LATENT",)
#     FUNCTION = "batch"

#     CATEGORY = "latent/batch"

#     def batch(self, samples1, samples2):
#         samples_out = samples1.copy()
#         s1 = samples1["samples"]
#         s2 = samples2["samples"]

#         if s1.shape[1:] != s2.shape[1:]:
#             s2 = comfy.utils.common_upscale(s2, s1.shape[3], s1.shape[2], "bilinear", "center")
#         s = torch.cat((s1, s2), dim=0)
#         samples_out["samples"] = s
#         samples_out["batch_index"] = samples1.get("batch_index", [x for x in range(0, s1.shape[0])]) + samples2.get("batch_index", [x for x in range(0, s2.shape[0])])
#         return (samples_out,)