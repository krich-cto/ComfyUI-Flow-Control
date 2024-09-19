import json
import shutil
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from datetime import datetime
import numpy as np
import os
import re
from ..node_tools import calculate_sha256, format_date_time
import folder_paths

class FlowSaveImage:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                        "images": ("IMAGE", ),
                        "path": ("STRING", {"default": "", "multiline": False}),
                        "filename": ("STRING", {"default": f"%date_%model_%counter", "multiline": False}),
                        "extension": (["png", "jpg", "jpeg", "gif", "tiff", "webp", "bmp"],),
                        "counter_digits": ("INT", {"default": 4, "min": 0, "max": 0xffffffffffffffff }),
                        "time_format": ("STRING", {"default": "%Y-%m-%d-%H%M%S", "multiline": False}),
                        "dpi": ("INT", {"default": 300, "min": 1, "max": 2400, "step": 1}),
                        "quality": ("INT", {"default": 100, "min": 1, "max": 100}),
                        "optimize": ("BOOLEAN", {"default": False}),
                        "webp_lossless": ("BOOLEAN", {"default": True}),
                        "workflow_embedded": ("BOOLEAN", {"default": True}),
                        "show_previews": ("BOOLEAN", {"default": True}),
                    },
                "optional": {
                        "gen_info": ("GENINFO", ),
                    },
                "hidden": {
                        "prompt": "PROMPT",
                        "extra_pnginfo": "EXTRA_PNGINFO"
                    },
                }

    RETURN_TYPES = ("IMAGE", "STRING", )
    RETURN_NAMES = ("images", "files", )
    FUNCTION = "save"

    OUTPUT_NODE = True

    CATEGORY = "Flow/outputs"

    def __init__(self):
        self.civitai_sampler_map = {
            "euler_ancestral": "Euler a",
            "euler": "Euler",
            "lms": "LMS",
            "heun": "Heun",
            "dpm_2": "DPM2",
            "dpm_2_ancestral": "DPM2 a",
            "dpmpp_2s_ancestral": "DPM++ 2S a",
            "dpmpp_2m": "DPM++ 2M",
            "dpmpp_sde": "DPM++ SDE",
            "dpmpp_2m_sde": "DPM++ 2M SDE",
            "dpmpp_3m_sde": "DPM++ 3M SDE",
            "dpm_fast": "DPM fast",
            "dpm_adaptive": "DPM adaptive",
            "ddim": "DDIM",
            "plms": "PLMS",
            "uni_pc_bh2": "UniPC",
            "uni_pc": "UniPC",
            "lcm": "LCM",
        }

    def get_civitai_sampler_name(self, sampler_name, scheduler):
        # based on: https://github.com/civitai/civitai/blob/main/src/server/common/constants.ts#L122
        if sampler_name in self.civitai_sampler_map:
            civitai_name = self.civitai_sampler_map[sampler_name]

            if scheduler == "karras":
                civitai_name += " Karras"
            elif scheduler == "exponential":
                civitai_name += " Exponential"

            return civitai_name
        else:
            if scheduler != "normal":
                return f"{sampler_name}_{scheduler}"
            else:
                return sampler_name

    def format_text(self, format, counter, counter_digits, time_format, gen_info):
        output = format.replace("%date", format_date_time("%Y-%m-%d"))
        output = output.replace("%time", format_date_time(time_format))

        if counter != None:
            output = output.replace("%counter", f"{counter:0{counter_digits}}")
        
        if gen_info is not None:
            output = output.replace("%model", gen_info.get("ckpt_name", ""))
            output = output.replace("%seed", str(gen_info.get("seed", "")))
            output = output.replace("%sampler_name", str(gen_info.get("sampler_name", "")))
            output = output.replace("%steps", str(gen_info.get("steps", "")))
            output = output.replace("%guidance", str(gen_info.get("guidance", "")))
            output = output.replace("%cfg", str(gen_info.get("cfg", "")))
            output = output.replace("%scheduler", str(gen_info.get("scheduler", "")))
            output = output.replace("%denoise", str(gen_info.get("denoise", "")))
        else:
            output = output.replace("%model", "")
            output = output.replace("%seed", "")
            output = output.replace("%sampler_name", "")
            output = output.replace("%steps", "")
            output = output.replace("%guidance", "")
            output = output.replace("%cfg", "")
            output = output.replace("%scheduler", "")
            output = output.replace("%denoise", "")

        return output

    def format_prompt(self, string: str):
        return string.strip().replace("\n", " ").replace("\r", " ").replace("\t", " ").replace("  ", " ")

    def get_embedding_path(self, embedding: str):
        matching_embedding = next((x for x in folder_paths.get_filename_list("embeddings") if x.startswith(embedding)), None)
        if matching_embedding == None:
            return None
        return folder_paths.get_full_path("embeddings", matching_embedding)
    
    def extract_embeddings(self, prompt):
        output = {}
        embeddings = re.findall(r'embedding:([^,\s\(\)\:]+)', prompt, re.IGNORECASE | re.MULTILINE)
        for embedding in embeddings:
            embedding_name = f'embed:{embedding}'
            embedding_path = self.get_embedding_path(embedding)
            if embedding_path == None:
                return
            
            hash = calculate_sha256(embedding_path)
            # Based on https://github.com/civitai/sd_civitai_extension/blob/2008ba9126ddbb448f23267029b07e4610dffc15/scripts/gen_hashing.py#L53
            output[embedding_name] = hash[:10]
        return output

    def get_lora_path(self, lora: str):
        # Find the position of the last dot
        last_dot_position = lora.rfind('.')
        # Get the extension including the dot
        extension = lora[last_dot_position:] if last_dot_position != -1 else ""
        # Check if the extension is supported, if not, add .safetensors
        if extension not in folder_paths.supported_pt_extensions:
            lora += ".safetensors"

        # Find the matching lora path
        matching_lora = next((x for x in folder_paths.get_filename_list("loras") if x.endswith(lora)), None)
        if matching_lora is None:
            return None
        
        return folder_paths.get_full_path("loras", matching_lora)
    
    def extract_loras(self, prompt):
        output = {}
        loras = re.findall(r'<lora:([^>:]+)(?::[^>]+)?>', prompt, re.IGNORECASE | re.MULTILINE)
        for lora in loras:
            lora_name = f'LORA:{lora}'
            lora_path = self.get_lora_path(lora)
            if lora_path == None:
                continue
            
            hash = calculate_sha256(lora_path)
            # Based on https://github.com/civitai/sd_civitai_extension/blob/2008ba9126ddbb448f23267029b07e4610dffc15/scripts/gen_hashing.py#L53
            output[lora_name] = hash[:10]
        
        return output
    
    def format_gen_parameters(self, gen_info):
        if gen_info is None:
            return None

        base = gen_info.get("base", "")
        positive_prompt = gen_info.get("positive_prompt", "")
        negative_prompt = gen_info.get("negative_prompt", "")
        steps = gen_info.get("steps", "")
        sampler_name = gen_info.get("sampler_name", "")
        seed = gen_info.get("seed", "")
        cfg = gen_info.get("cfg", "")
        clip_skip = gen_info.get("clip_skip", "")
        width = gen_info.get("width", "")
        height = gen_info.get("height", "")
        ckpt_hash = gen_info.get("ckpt_hash", "")
        ckpt_name = gen_info.get("ckpt_name", "")
        scheduler = gen_info.get("scheduler", "")
        loras = gen_info.get("loras", {})
        civitai_sampler_name = self.get_civitai_sampler_name(sampler_name, scheduler)

        positive_embeddings = self.extract_embeddings(positive_prompt)
        positive_loras = self.extract_loras(positive_prompt)
        positive_prompt = self.format_prompt(positive_prompt)
        negative_embeddings = self.extract_embeddings(negative_prompt)
        negative_loras = self.extract_loras(negative_prompt)
        negative_prompt = f"\nNegative prompt: {self.format_prompt(negative_prompt)}"
        hashes = json.dumps(positive_embeddings | negative_embeddings | positive_loras | negative_loras | loras | { "model": ckpt_hash })

        if base == "Flux":
            return f"{positive_prompt}{negative_prompt}\nSteps: {steps}, Sampler: {civitai_sampler_name}, CFG scale: {cfg}, Seed: {seed}, Size: {width}x{height}, Model hash: {ckpt_hash}, Model: {ckpt_name}, Hashes: {hashes}, Version: ComfyUI"

        return f"{positive_prompt}{negative_prompt}\nSteps: {steps}, Sampler: {civitai_sampler_name}, CFG scale: {cfg}, Clip skip: {clip_skip}, Seed: {seed}, Size: {width}x{height}, Model hash: {ckpt_hash}, Model: {ckpt_name}, Hashes: {hashes}, Version: ComfyUI"

    def save(self, images, path, filename, extension, counter_digits, time_format, dpi, quality, optimize, webp_lossless, workflow_embedded, show_previews, gen_info = None, prompt = None, extra_pnginfo = None):
        if gen_info is not None:
            print(f"[Flow Control] Gen Info : {gen_info}")

        # Format output path.
        if path in [None, "", "none", "."]:
            output_path = folder_paths.get_output_directory()
        else:
            output_path = self.format_text(path, None, counter_digits, time_format, gen_info)
            output_path = output_path.strip()
            if output_path.startswith("~/"):
                home_path = os.path.expanduser("~/")
                output_path = os.path.join(home_path, output_path[2:])
            elif not os.path.isabs(output_path):
                output_path = os.path.join(folder_paths.get_output_directory(), output_path)

        print(f"[Flow Control] Output path : {output_path}")

        # Create output path is not exists.
        if not os.path.exists(output_path):
            print(f"[Flow Control] {output_path} : Directory created.")
            os.makedirs(output_path, exist_ok=True)

        if filename in [None, ""]:
            filename = f"%date_%model_%counter"

        # Get lastest counter
        counter_index = filename.find("%counter")
        if counter_index >= 0:
            filename_before = filename[:counter_index]
            filename_after = filename[counter_index + len("%counter"):]
            filename_after = filename_after.replace("%counter", "")
            before_counter = self.format_text(filename_before, None, counter_digits, time_format, gen_info)
            after_counter = self.format_text(filename_after, None, counter_digits, time_format, gen_info)
            if len(before_counter) == 0:
                pattern = f"(\\d+){re.escape(after_counter)}"
            elif len(after_counter) == 0:
                pattern = f"{re.escape(before_counter)}(\\d+)"
            else:
                pattern = f"{re.escape(before_counter)}(\\d+){re.escape(after_counter)}"
                
            existing_counters = [
                int(re.search(pattern, filename).group(1))
                for filename in os.listdir(output_path)
                if re.match(pattern, os.path.basename(filename))
            ]
            existing_counters.sort(reverse=True)

            if existing_counters:
                counter = existing_counters[0] + 1
            else:
                counter = 1

            # Format output file name.
            filename = f"{before_counter}%counter{after_counter}.{extension}"
        else:
            filename = f"{filename}.{extension}"

        gen_parameters = self.format_gen_parameters(gen_info)
        output_files = list()
        results = list()
        for image in images:
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))

            # Delegate metadata/pnginfo
            if extension in ["jpg", "jpeg", "webp", "tiff"]:
                # https://exiftool.org/TagNames/EXIF.html
                img_exif = img.getexif()

                if gen_parameters is not None:
                    img_exif[0x9286] = gen_parameters

                if workflow_embedded == True:
                    workflow_metadata = ""
                    prompt_str = ""
                    if prompt is not None:
                        prompt_str = json.dumps(prompt)
                        img_exif[0x010f] = "Prompt:" + prompt_str
                    if extra_pnginfo is not None:
                        for x in extra_pnginfo:
                            workflow_metadata += json.dumps(extra_pnginfo[x])
                    img_exif[0x010e] = "Workflow:" + workflow_metadata
                exif_data = img_exif.tobytes()
            else:
                png_info = PngInfo()

                if gen_parameters is not None:
                    png_info.add_text("parameters", gen_parameters)

                if workflow_embedded == True:
                    if prompt is not None:
                        png_info.add_text("prompt", json.dumps(prompt))
                    if extra_pnginfo is not None:
                        for x in extra_pnginfo:
                            png_info.add_text(x, json.dumps(extra_pnginfo[x]))
                exif_data = png_info

            while True:
                output_filename = self.format_text(filename, counter, counter_digits, time_format, gen_info)
                if os.path.exists(os.path.join(output_path, output_filename)):
                    counter += 1
                else:
                    break

            # Save the images
            try:
                output_file = os.path.abspath(os.path.join(output_path, output_filename))
                if extension in ["jpg", "jpeg"]:
                    img.save(output_file, quality=quality, optimize=optimize, dpi=(dpi, dpi), exif=exif_data)
                elif extension == "webp":
                    img.save(output_file, quality=quality, lossless=webp_lossless, exif=exif_data)
                elif extension == "png":
                    img.save(output_file, pnginfo=exif_data, optimize=optimize)
                elif extension == "bmp":
                    img.save(output_file)
                elif extension == "tiff":
                    img.save(output_file, quality=quality, optimize=optimize, exif=exif_data)
                else: # gif
                    img.save(output_file, optimize=optimize)

                counter += 1

                print(f"[Flow Control] {output_file} : Saved.")

                output_files.append(output_file)

                if show_previews == True:
                    preview_filename = f"flow_preview.{extension}"
                    preview_file = os.path.join(folder_paths.get_output_directory(), preview_filename)
                    shutil.copy(output_file, preview_file)
                    results.append({
                        "filename": preview_filename,
                        "subfolder": "",
                        "type": "output"
                    })
            except OSError as e:
                print(f"[Flow Control] {output_file} : OS Error.")
                print(e)
            except Exception as e:
                print(f"[Flow Control] {output_file} : Exception.")
                print(e)

        if show_previews == True:
            return {"ui": {"images": results, "files": output_files}, "result": (images, output_files,)}
        else:
            return {"ui": {"images": []}, "result": (images, output_files,)}
