"""
Integration test for LTX-2.3 video generation via ComfyUI API.

This test submits a real workflow to ComfyUI, waits for completion,
and validates that a video output is produced. It can be compared
directly to the e2e orchestrator workflow in test_e2e_wordpress.py.

Requirements:
- ComfyUI running and reachable at COMFYUI_URL (default: http://127.0.0.1:8188)
- LTX-2.3 checkpoint installed in ComfyUI at the path specified by LTX_CHECKPOINT_PATH
  (default: /models/ltx-video/ltxv_2.3.safetensors)

Run with:
    pytest orchestrator/tests/test_ltx23_video_generation.py -v
"""

import os
import time
import pytest
import pathlib
import importlib.util
from dotenv import load_dotenv


ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_module(path, name):
    """Dynamically load a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Test data - loaded from ltx23-prompts.txt
# ---------------------------------------------------------------------------

def _load_prompts():
    """Load test prompts from the prompts file."""
    prompts_file = ROOT / "orchestrator" / "tests" / "ltx23-prompts.txt"
    
    positive_prompts = []
    negative_prompts = []
    
    if prompts_file.exists():
        with open(prompts_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("positive_prompt_"):
                    _, prompt = line.split("|", 1)
                    positive_prompts.append(prompt)
                elif line.startswith("negative_prompt_"):
                    _, prompt = line.split("|", 1)
                    negative_prompts.append(prompt)
    
    # Fallback prompts if file is empty or missing
    if not positive_prompts:
        positive_prompts = [
            "A cinematic wide shot of a misty forest at dawn, golden light filtering through the trees",
            "Ocean waves crashing on rocky cliffs, dramatic sky with clouds moving",
            "Smooth flowing liquid metal morphing shapes, iridescent colors, macro close-up",
        ]
    if not negative_prompts:
        negative_prompts = [
            "blurry, low quality, distorted, deformed",
            "static, flat lighting, artificial",
            "jagged edges, noise, grainy",
        ]
    
    return {
        "cinematic": {
            "positive": positive_prompts[0] if len(positive_prompts) > 0 else positive_prompts[-1],
            "negative": negative_prompts[0] if len(negative_prompts) > 0 else negative_prompts[-1],
        },
        "racer": {
            "positive": positive_prompts[1] if len(positive_prompts) > 1 else positive_prompts[0],
            "negative": negative_prompts[1] if len(negative_prompts) > 1 else negative_prompts[0],
        },
        "warrior": {
            "positive": positive_prompts[2] if len(positive_prompts) > 2 else positive_prompts[0],
            "negative": negative_prompts[2] if len(negative_prompts) > 2 else negative_prompts[0],
        },
    }


TEST_PROMPTS = _load_prompts()

# Default test config (override via environment variables)
DEFAULT_CONFIG = {
    "checkpoint_path": os.getenv("LTX_CHECKPOINT_PATH", "/models/ltx-video/ltxv_2.3.safetensors"),
    "resolution_x": int(os.getenv("LTX_RESOLUTION_X", "768")),
    "resolution_y": int(os.getenv("LTX_RESOLUTION_Y", "512")),
    "num_frames": int(os.getenv("LTX_NUM_FRAMES", "97")),
    "fps": int(os.getenv("LTX_FPS", "25")),
    "steps": int(os.getenv("LTX_STEPS", "32")),
    "cfg_scale": float(os.getenv("LTX_CFG", "4.5")),
    "seed": int(os.getenv("LTX_SEED", "42")),
    "lora_enabled": os.getenv("LORA_ENABLED", "false").lower() == "true",
    "lora_path": os.getenv("LORA_PATH", ""),
    "lora_weight": float(os.getenv("LORA_WEIGHT", "1.0")),
}


def _build_ltx23_workflow(post_id: int, prompt_key: str = "cinematic") -> dict:
    """Build a complete LTX-2.3 video generation workflow for testing."""
    prompts = TEST_PROMPTS.get(prompt_key, TEST_PROMPTS["cinematic"])

    nodes = {
        # Node 1: Positive prompt encoding
        "1": {
            "inputs": {
                "text": prompts["positive"],
            },
            "class_type": "CLIPTextEncode",
        },
        # Node 2: Negative prompt encoding
        "2": {
            "inputs": {
                "text": prompts["negative"],
            },
            "class_type": "CLIPTextEncode",
        },
        # Node 3: Load LTX-2.3 checkpoint
        "3": {
            "inputs": {
                "ckpt_name": DEFAULT_CONFIG["checkpoint_path"],
            },
            "class_type": "CheckpointLoaderSimple",
        },
        # Node 4: Empty latent video (LTX-2.3 specific)
        "4": {
            "inputs": {
                "width": DEFAULT_CONFIG["resolution_x"],
                "height": DEFAULT_CONFIG["resolution_y"],
                "length": DEFAULT_CONFIG["num_frames"],
                "latents_size": "LTX-2.3",
                "batch_size": 1,
            },
            "class_type": "EmptyLTXVLatentVideo",
        },
        # Node 5: KSampler for video generation
        "5": {
            "inputs": {
                "seed": DEFAULT_CONFIG["seed"],
                "steps": DEFAULT_CONFIG["steps"],
                "cfg": DEFAULT_CONFIG["cfg_scale"],
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["3", 0],
                "positive": ["1", 0],
                "negative": ["2", 0],
                "latent_image": ["4", 0],
            },
            "class_type": "KSampler",
        },
        # Node 6: VAE Decode
        "6": {
            "inputs": {
                "samples": ["5", 0],
                "vae": ["3", 1],
            },
            "class_type": "VAEDecode",
        },
        # Node 7: Save video output
        "7": {
            "inputs": {
                "images": ["6", 0],
                "fps": DEFAULT_CONFIG["fps"],
                "format": "video/h264-mp4",
                "method": "secure",
                "filename_prefix": f"test_ltx23_{prompt_key}_{post_id}",
            },
            "class_type": "SaveImage",
        },
    }

    # Add LoRA node if enabled
    if DEFAULT_CONFIG["lora_enabled"] and DEFAULT_CONFIG["lora_path"]:
        lora_node_id = "8"
        nodes[lora_node_id] = {
            "inputs": {
                "lora_name": DEFAULT_CONFIG["lora_path"],
                "strength_model": DEFAULT_CONFIG["lora_weight"],
                "strength_clip": DEFAULT_CONFIG["lora_weight"],
            },
            "class_type": "LoadLoRAModel",
        }
        # Update model reference in KSampler to use LoRA output
        nodes["5"]["inputs"]["model"] = [lora_node_id, 0]

    return {"prompt": nodes}


def _wait_for_completion(prompt_id: str, timeout: int = 600) -> dict:
    """Poll ComfyUI history until the prompt completes or times out."""
    import requests

    url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
    start_time = time.time()

    while time.time() - start_time < timeout:
        resp = requests.get(f"{url}/history/{prompt_id}", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if prompt_id in data and "outputs" in data[prompt_id]:
                return data[prompt_id]
        time.sleep(3)

    raise TimeoutError(f"ComfyUI generation timed out after {timeout}s for prompt {prompt_id}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLTX23VideoGeneration:
    """Test suite for LTX-2.3 video generation via ComfyUI API."""

    @pytest.fixture(autouse=True)
    def _load_env(self):
        """Load environment variables from .env file."""
        load_dotenv(ROOT / ".env")

    @pytest.fixture(scope="class")
    def comfyui_reachable(self):
        """Check if ComfyUI is reachable before running tests."""
        import requests

        url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
        try:
            r = requests.get(url + "/", timeout=5)
            r.raise_for_status()
            return True
        except Exception as e:
            pytest.skip(f"ComfyUI not reachable at {url}: {e}")

    def test_01_submit_workflow_returns_prompt_id(self, comfyui_reachable):
        """Test that submitting an LTX-2.3 workflow returns a valid prompt_id."""
        tasks = load_module(ROOT / "orchestrator" / "tasks.py", "orchestrator.tasks")

        # Override config for this test
        original_checkpoint = tasks.LTX_CHECKPOINT_PATH
        tasks.LTX_CHECKPOINT_PATH = DEFAULT_CONFIG["checkpoint_path"]

        try:
            prompt_id = tasks.submit_workflow(post_id=1)
            assert isinstance(prompt_id, str), f"Expected string prompt_id, got {type(prompt_id)}"
            assert len(prompt_id) > 0, "prompt_id should not be empty"
        finally:
            tasks.LTX_CHECKPOINT_PATH = original_checkpoint

    def test_02_generate_cinematic_video(self, comfyui_reachable):
        """Generate a cinematic video using LTX-2.3 and validate output."""
        import requests

        url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")

        # Build workflow
        workflow = _build_ltx23_workflow(post_id=100, prompt_key="cinematic")

        # Submit
        resp = requests.post(f"{url}/prompt", json=workflow, timeout=10)
        assert resp.status_code == 200, f"Failed to submit workflow: {resp.text}"
        prompt_id = resp.json()["prompt_id"]
        assert prompt_id

        print(f"\n[INFO] Prompt ID: {prompt_id}")
        print(f"[INFO] Waiting for LTX-2.3 video generation (cinematic)...")

        # Wait for completion
        outputs = _wait_for_completion(prompt_id, timeout=600)

        # Validate output structure
        assert "7" in outputs, f"Expected node '7' (SaveImage) in outputs, got: {list(outputs.keys())}"
        save_image_output = outputs["7"]
        assert len(save_image_output) > 0, "SaveImage output should contain at least one image"

        # Validate video file exists
        video_info = save_image_output[0]
        filename = video_info.get("filename", "")
        subfolder = video_info.get("subfolder", "")
        file_type = video_info.get("type", "output")

        assert filename, "Video filename should not be empty"
        assert file_type in ("output", "temp"), f"Expected file type 'output' or 'temp', got '{file_type}'"

        # Construct full path and verify file exists
        if subfolder:
            full_path = os.path.join(url.split(":")[-1].replace("/", ""), subfolder, filename)
        else:
            full_path = filename

        print(f"[INFO] Video generated: {filename}")
        print(f"[INFO] Subfolder: {subfolder}")
        print(f"[INFO] File type: {file_type}")

    def test_03_generate_nature_video(self, comfyui_reachable):
        """Generate a nature video using LTX-2.3 and validate output."""
        import requests

        url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")

        workflow = _build_ltx23_workflow(post_id=101, prompt_key="nature")

        resp = requests.post(f"{url}/prompt", json=workflow, timeout=10)
        assert resp.status_code == 200, f"Failed to submit workflow: {resp.text}"
        prompt_id = resp.json()["prompt_id"]

        print(f"\n[INFO] Prompt ID: {prompt_id}")
        print(f"[INFO] Waiting for LTX-2.3 video generation (nature)...")

        outputs = _wait_for_completion(prompt_id, timeout=600)

        assert "7" in outputs, f"Expected node '7' (SaveImage) in outputs, got: {list(outputs.keys())}"
        video_info = outputs["7"][0]
        assert video_info.get("filename"), "Video filename should not be empty"

        print(f"[INFO] Video generated: {video_info['filename']}")

    def test_04_compare_with_orchestrator_workflow(self, comfyui_reachable):
        """Compare the direct API workflow with the orchestrator's submit_workflow function."""
        import requests

        url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
        tasks = load_module(ROOT / "orchestrator" / "tasks.py", "orchestrator.tasks")

        # Get workflow from orchestrator
        orchestrator_prompt_id = tasks.submit_workflow(post_id=200)
        assert orchestrator_prompt_id

        print(f"\n[INFO] Orchestrator prompt ID: {orchestrator_prompt_id}")
        print(f"[INFO] Waiting for orchestrator-generated video...")

        orchestrator_outputs = _wait_for_completion(orchestrator_prompt_id, timeout=600)
        assert "7" in orchestrator_outputs, f"Orchestrator workflow missing SaveImage output: {list(orchestrator_outputs.keys())}"

        # Get workflow from our test builder
        test_workflow = _build_ltx23_workflow(post_id=201, prompt_key="cinematic")
        resp = requests.post(f"{url}/prompt", json=test_workflow, timeout=10)
        assert resp.status_code == 200
        test_prompt_id = resp.json()["prompt_id"]

        print(f"[INFO] Test workflow prompt ID: {test_prompt_id}")
        print(f"[INFO] Waiting for test-generated video...")

        test_outputs = _wait_for_completion(test_prompt_id, timeout=600)
        assert "7" in test_outputs, f"Test workflow missing SaveImage output: {list(test_outputs.keys())}"

        # Both should produce valid outputs
        orchestrator_video = orchestrator_outputs["7"][0].get("filename")
        test_video = test_outputs["7"][0].get("filename")

        assert orchestrator_video, "Orchestrator workflow should produce a video"
        assert test_video, "Test workflow should produce a video"

        print(f"\n[INFO] === Comparison Results ===")
        print(f"[INFO] Orchestrator video: {orchestrator_video}")
        print(f"[INFO] Test workflow video: {test_video}")
        print(f"[INFO] Both workflows completed successfully!")

    def test_05_lora_enabled_workflow(self, comfyui_reachable):
        """Test LTX-2.3 generation with LoRA enabled."""
        import requests

        if not DEFAULT_CONFIG["lora_enabled"] or not DEFAULT_CONFIG["lora_path"]:
            pytest.skip("LoRA not enabled in config (set LORA_ENABLED=true and LORA_PATH)")

        url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")

        # Temporarily enable LoRA for this test
        tasks = load_module(ROOT / "orchestrator" / "tasks.py", "orchestrator.tasks")
        original_lora_enabled = tasks.LORA_ENABLED
        original_lora_path = tasks.LORA_PATH
        original_lora_weight = tasks.LORA_WEIGHT

        try:
            tasks.LORA_ENABLED = True
            tasks.LORA_PATH = DEFAULT_CONFIG["lora_path"]
            tasks.LORA_WEIGHT = DEFAULT_CONFIG["lora_weight"]

            prompt_id = tasks.submit_workflow(post_id=300)
            assert prompt_id

            print(f"\n[INFO] LoRA-enabled prompt ID: {prompt_id}")
            print(f"[INFO] Waiting for LTX-2.3 + LoRA video generation...")

            outputs = _wait_for_completion(prompt_id, timeout=600)
            assert "7" in outputs, f"Expected SaveImage output with LoRA, got: {list(outputs.keys())}"

            video_info = outputs["7"][0]
            assert video_info.get("filename"), "LoRA workflow should produce a video"

            print(f"[INFO] LoRA video generated: {video_info['filename']}")
        finally:
            tasks.LORA_ENABLED = original_lora_enabled
            tasks.LORA_PATH = original_lora_path
            tasks.LORA_WEIGHT = original_lora_weight


# ---------------------------------------------------------------------------
# Manual run helper
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    """Run this script directly for quick testing without pytest."""
    print("=" * 60)
    print("LTX-2.3 Video Generation Test (Direct Run)")
    print("=" * 60)

    load_dotenv(ROOT / ".env")
    url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")

    # Check ComfyUI reachability
    import requests
    try:
        r = requests.get(url + "/", timeout=5)
        r.raise_for_status()
        print(f"[OK] ComfyUI reachable at {url}")
    except Exception as e:
        print(f"[ERROR] ComfyUI not reachable: {e}")
        exit(1)

    # Build and submit workflow
    workflow = _build_ltx23_workflow(post_id=999, prompt_key="cinematic")
    resp = requests.post(f"{url}/prompt", json=workflow, timeout=10)

    if resp.status_code != 200:
        print(f"[ERROR] Failed to submit workflow: {resp.text}")
        exit(1)

    prompt_id = resp.json()["prompt_id"]
    print(f"\n[INFO] Prompt ID: {prompt_id}")
    print(f"[INFO] Waiting for video generation (this may take several minutes)...")

    # Wait for completion
    outputs = _wait_for_completion(prompt_id, timeout=600)

    if "7" in outputs and outputs["7"]:
        video_info = outputs["7"][0]
        print(f"\n[SUCCESS] Video generated!")
        print(f"[INFO] Filename: {video_info.get('filename')}")
        print(f"[INFO] Subfolder: {video_info.get('subfolder')}")
        print(f"[INFO] Type: {video_info.get('type')}")
    else:
        print(f"\n[ERROR] No video output found. Outputs: {outputs}")
        exit(1)
