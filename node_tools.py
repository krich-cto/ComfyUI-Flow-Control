from datetime import datetime
import hashlib
import requests
import json
import os

def get_file_name(file_path):
    return os.path.basename(file_path)

def get_file_name_without_extension(file_path):
    return os.path.splitext(os.path.basename(file_path))[0]

def get_flow_path(file_name):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), file_name)

def delete_file(file_path):
    try:
        os.remove(file_path)
        print(f"[Flow Control] {file_path} : Removed.")
    except FileNotFoundError:
        print(f"[Flow Control] Delete File : File not found: {file_path}")

def load_json(file_path):
    try:
        with open(file_path, 'r') as json_file:
            data = json.load(json_file)
            return data
    except FileNotFoundError:
        print(f"[Flow Control] Load JSON : File not found: {file_path}")
        return {}
    except json.JSONDecodeError:
        print(f"[Flow Control] Load JSON : Error decoding JSON in file: {file_path}")
        return {}

def save_json(file_path, data):
    try:
        with open(file_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)
    except Exception as e:
        print(f"[Flow Control] Save JSON : Error saving JSON to file: {e}")
    
def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def get_model_info(hash_value):
    try:
        api_url = f"https://civitai.com/api/v1/model-versions/by-hash/{hash_value}"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {}
    except requests.exceptions.Timeout:
        print(f"[Flow Control] Get model info [{hash_value}] : Timeout")
        return {}

base_dict = {
    "Pony": "Pony",
    "pony": "Pony",
    "Illustrious": "Illustrious",
    "illustrious": "Illustrious",
    "NoobAI": "NoobAI",
    "noobai": "NoobAI",
    "SDXL": "SDXL",
    "SDXL Turbo": "SDXL",
    "SDXL 1.0": "SDXL",
    "sdxl": "SDXL",
    "SD 1.5": "SD15",
    "SD1.5": "SD15",
    "sd15": "SD15",
    "Flux": "Flux",
    "Flux.1 D": "Flux",
    "Flux.1 S": "Flux",
}

def map_base(base):
    return base_dict.get(base, "")

def format_date_time(format):
    now = datetime.now()
    try:
        date_time = now.strftime(format)
    except:
        date_time = ""

    return date_time
