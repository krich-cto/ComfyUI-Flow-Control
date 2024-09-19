import comfy.utils # type: ignore
import torch # type: ignore

class FlowImageAutoBatch:
  @classmethod
  def INPUT_TYPES(cls):  # pylint: disable = invalid-name, missing-function-docstring
    return {
      "required": {},
      "optional": {
        "image_1": ("IMAGE",),
      }
    }

  RETURN_TYPES = ("IMAGE",)
  RETURN_NAMES = ("image",)

  FUNCTION = "execute"
  CATEGORY = "Flow/end-conditions"

  def execute(self, **args):
    images = []
    for _, value in args.items():
      if value is not None:
        images.append(value)

    if len(images) > 0:
      result = images[0]
      base_image = images[0]
      for index in range(1, len(images), 1):
        image = images[index]
        if base_image.shape[1:] != image.shape[1:]:
          image = comfy.utils.common_upscale(image.movedim(-1,1), base_image.shape[2], base_image.shape[1], "bilinear", "center").movedim(1,-1)

        result = torch.cat((result, image), dim=0)
    
      return (result,)
    
    return ()
