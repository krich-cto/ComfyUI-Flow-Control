class FlowConditioningAutoSwitch:
  @classmethod
  def INPUT_TYPES(cls):  # pylint: disable = invalid-name, missing-function-docstring
    return {
      "required": {},
      "optional": {
        "conditioning_1": ("CONDITIONING",),
      }
    }

  RETURN_TYPES = ("CONDITIONING",)
  RETURN_NAMES = ("conditioning",)

  FUNCTION = "execute"
  CATEGORY = "Flow/clips"

  def execute(self, **args):
    for _, value in args.items():
      if value is not None:
        return (value,)
    
    return ()
