import folder_paths
from server import PromptServer
from aiohttp import web
import os
from ..node_tools import get_flow_path, delete_file, load_json, save_json, calculate_sha256, get_model_info, map_base

checkpoints_db_path = get_flow_path("db/checkpoints.json")
loras_db_path = get_flow_path("db/loras.json")

def get_preset(db, config_name):
    if config_name in db:
        preset = db[config_name]
        del db[config_name]
        return preset
    
    return None

def move_model(file_name, model_path, base):
    prefix = base.lower()
    config_name = os.path.basename(file_name)
    model_dir = os.path.dirname(model_path)
    if model_dir.endswith(prefix) == False:
        model_dir = f"{model_dir}/{prefix}"

    target_model_path = f"{model_dir}/{config_name}"

    if model_path != target_model_path:
        if os.path.isfile(target_model_path) == True:
            delete_file(target_model_path)

        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
            print(f"[Flow Control] {model_dir} : Directory created.")

        os.rename(model_path, target_model_path)
        print(f"[Flow Control] {file_name} -> {prefix}/{config_name}")

def auto_arrange(type, fetch_model):
    print(f"[Flow Control] {type} : Auto Arrange, Fetch Model = {fetch_model}")
    type = type.lower()
    fetch_model = fetch_model.lower()
    file_names = folder_paths.get_filename_list(type)
    count = 0
    db = dict()
    old_db = None

    if type == "checkpoints":
        db_path = checkpoints_db_path
        old_db = load_json(db_path)
        delete_file(db_path)
    elif type == "loras":
        db_path = loras_db_path
        old_db = load_json(db_path)
        delete_file(db_path)

    for file_name in file_names:
        model_path = folder_paths.get_full_path(type, file_name)  
        config_name = os.path.basename(file_name)
        preset = get_preset(old_db, config_name)

        if preset is None or fetch_model == "all":
            print(f"[Flow Control] {file_name} : Fetch model information.")
            sha256 = calculate_sha256(model_path)
            model_info = get_model_info(sha256)
            base = map_base(model_info.get("baseModel", ""))
            modelID = model_info.get("modelId", "")
            if model_info.get("trainedWords", None) is None:
                triggers = ""
            else:
                triggers = ",".join(model_info.get("trainedWords"))
            url = f"https://civitai.com/models/{modelID}"

            if base != "":
                move_model(file_name, model_path, base)

                if type == "checkpoints":
                    if preset is not None:
                        steps = preset["steps"]
                        cfg = preset["cfg"]
                        clip_skip = preset["clip_skip"]
                        sampler_name = preset["sampler_name"]
                        scheduler = preset["scheduler"]
                    else:
                        steps = 20
                        cfg = 7
                        clip_skip = 2
                        sampler_name = "dpmpp_2m"
                        scheduler = "karras"

                    db[config_name] = {
                        "vae_name": "embedded",
                        "base": base,
                        "hash": sha256,
                        "steps": steps,
                        "cfg": cfg,
                        "clip_skip": clip_skip,
                        "sampler_name": sampler_name,
                        "scheduler": scheduler,
                        "url": url
                        }
                elif type == "loras":
                    db[config_name] = {
                        "base": base,
                        "hash": sha256,
                        "triggers": triggers,
                        "url": url
                        }
            else:
                print(f"[Flow Control] {file_name} : No information.")
        else:
            print(f"[Flow Control] {file_name} : Skip fetching model.")

            if preset is not None:
                base = preset.get("base", "")
                move_model(file_name, model_path, base)

                db[config_name] = preset

    if old_db is not None:
        db.update(old_db)

    save_json(db_path, db)
    print(f"[Flow Control] {db_path} : Saved.")

    return count

@PromptServer.instance.routes.post("/model_auto_arrange")
async def model_auto_arrange(request):
    body = await request.json()
    type = body.get("type")
    fetch_model = body.get("fetchModel")

    count = auto_arrange(type, fetch_model)

    return web.json_response({
        "count": count
        })

class FlowModelManager:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "type": (['Checkpoints', 'Loras'], { "default": 'Checkpoints' }),
                "fetch_model": (['All', 'New'], { "default": 'New' }),
            }
        }
    RETURN_TYPES = ()
    RETURN_NAMES = ()
    FUNCTION = "execute"

    CATEGORY = "Flow"

    def execute(self, type):
        return ()