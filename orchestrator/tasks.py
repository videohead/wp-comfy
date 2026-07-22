import os
import time
import requests
from celery import Celery

# ---------------------------------------------------------
# Environment variables
# ---------------------------------------------------------
WORDPRESS_URL = os.getenv("WORDPRESS_URL", "http://10.0.0.34")
WORDPRESS_USER = os.getenv("WORDPRESS_USER")
WORDPRESS_APP_PASSWORD = os.getenv("WORDPRESS_APP_PASSWORD")
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://comfyui:8188")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# ---------------------------------------------------------
# LTX-2.3 Configuration
# ---------------------------------------------------------
LTX_CHECKPOINT_PATH = os.getenv(
    "LTX_CHECKPOINT_PATH",
    "/models/ltx-video/ltxv_2.3.safetensors"
)
LTX_RESOLUTION_X = int(os.getenv("LTX_RESOLUTION_X", "768"))
LTX_RESOLUTION_Y = int(os.getenv("LTX_RESOLUTION_Y", "512"))
LTX_NUM_FRAMES = int(os.getenv("LTX_NUM_FRAMES", "97"))
LTX_FPS = int(os.getenv("LTX_FPS", "25"))
LTX_STEPS = int(os.getenv("LTX_STEPS", "32"))
LTX_CFG = float(os.getenv("LTX_CFG", "4.5"))
LTX_SEED = int(os.getenv("LTX_SEED", "42"))

# ---------------------------------------------------------
# LTX-2.3 LoRA Configuration
# ---------------------------------------------------------
LORA_ENABLED = os.getenv("LORA_ENABLED", "false").lower() == "true"
LORA_NAME = os.getenv("LORA_NAME", "")  # e.g., "motion_blur_ltx23"
LORA_PATH = os.getenv(
    "LORA_PATH",
    f"/models/loras/{LORA_NAME}.safetensors" if LORA_NAME else ""
)
LORA_WEIGHT = float(os.getenv("LORA_WEIGHT", "1.0"))

# ---------------------------------------------------------
# Celery app
# ---------------------------------------------------------
celery_app = Celery("tasks")
celery_app.conf.broker_url = REDIS_URL
celery_app.conf.result_backend = REDIS_URL

# ---------------------------------------------------------
# WordPress helpers
# ---------------------------------------------------------
def wp_auth():
    return (WORDPRESS_USER, WORDPRESS_APP_PASSWORD)

def upload_media_to_wordpress(filepath: str, filename: str):
    url = f"{WORDPRESS_URL}/wp-json/wp/v2/media"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}

    with open(filepath, "rb") as f:
        resp = requests.post(url, headers=headers, data=f, auth=wp_auth())
        resp.raise_for_status()
        return resp.json()

# ---------------------------------------------------------
# ComfyUI helpers
# ---------------------------------------------------------
def submit_workflow(post_id: int):
    """Submit an LTX-2.3 video generation workflow for a WordPress post."""
    
    # Build base nodes
    nodes = {
        "1": {
            "inputs": {
                "text": f"Generate a video for WordPress post {post_id}"
            },
            "class_type": "CLIPTextEncode"
        },
        "2": {
            "inputs": {
                "text": ""
            },
            "class_type": "CLIPTextEncode"
        },
        "3": {
            "inputs": {
                "ckpt_name": LTX_CHECKPOINT_PATH
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "4": {
            "inputs": {
                "seed": LTX_SEED,
                "steps": LTX_STEPS,
                "cfg": LTX_CFG,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["3", 0],
                "positive": ["1", 0],
                "negative": ["2", 0],
                "latent_image": ["6", 0]
            },
            "class_type": "KSampler"
        },
        "5": {
            "inputs": {
                "width": LTX_RESOLUTION_X,
                "height": LTX_RESOLUTION_Y,
                "latents_size": "LTX-2.3",
                "batch_size": 1
            },
            "class_type": "EmptyLTXVLatentVideo"
        },
        "6": {
            "inputs": {
                "samples": ["4", 0],
                "vae": ["3", 1]
            },
            "class_type": "VAEDecode"
        },
        "7": {
            "inputs": {
                "images": ["6", 0],
                "fps": LTX_FPS,
                "format": "video/h264-mp4",
                "method": "secure",
                "filename_prefix": f"ltx23_post_{post_id}"
            },
            "class_type": "SaveImage"
        }
    }
    
    # Add LoRA nodes if enabled
    node_id = 8
    model_ref = ["3", 0]
    
    if LORA_ENABLED and LORA_PATH:
        lora_node_id = str(node_id)
        nodes[lora_node_id] = {
            "inputs": {
                "lora_name": LORA_PATH,
                "strength_model": LORA_WEIGHT,
                "strength_clip": LORA_WEIGHT
            },
            "class_type": "LoadLoRAModel"
        }
        model_ref = [lora_node_id, 0]
        node_id += 1
        
        # Update KSampler to use LoRA-applied model
        nodes["4"]["inputs"]["model"] = model_ref
    
    # Build final workflow with updated model reference
    workflow = {
        "prompt": {
            **nodes
        }
    }

    resp = requests.post(f"{COMFYUI_URL}/prompt", json=workflow)
    resp.raise_for_status()
    return resp.json()["prompt_id"]

def poll_comfyui(prompt_id: str):
    while True:
        resp = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
        if resp.status_code == 200:
            data = resp.json()
            if "outputs" in data:
                return data["outputs"]
        time.sleep(2)

# ---------------------------------------------------------
# Celery task
# ---------------------------------------------------------
@celery_app.task(bind=True, name="tasks.generate_video_task")
def generate_video_task(self, post_id: int):
    self.update_state(state="PROGRESS", meta={"message": "Submitting LTX-2.3 workflow..."})

    prompt_id = submit_workflow(post_id)

    self.update_state(state="PROGRESS", meta={"message": "Waiting for ComfyUI (LTX-2.3 video generation)..."})
    outputs = poll_comfyui(prompt_id)

    # Get the generated video from SaveImage output
    video_info = list(outputs.values())[0][0]
    video_path = video_info["filename"]

    self.update_state(state="PROGRESS", meta={"message": "Uploading to WordPress..."})
    wp_media = upload_media_to_wordpress(video_path, os.path.basename(video_path))

    return {
        "message": "Completed",
        "result": wp_media
    }
