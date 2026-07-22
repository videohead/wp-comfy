# wp-comfy Development & Testing Guide

## Lando Development Environment

The orchestrator runs inside a Lando Python 3.11 service (`app`). Use `lando ssh` to access it:

```bash
# SSH into the orchestrator container
lando ssh -s app

# Run pytest inside the container
lando ssh -s app "python -m pytest /app/orchestrator/tests/test_ltx23_video_generation.py -v"

# Install packages in the container
lando ssh -s app "pip install <package>"

# Check installed packages
lando ssh -s app "pip list | grep pytest"
```

### Important Paths Inside Lando Container
- Orchestrator code: `/app/orchestrator/` (mounted from host `/opt/wp-comfy/orchestrator/`)
- Test files: `/app/orchestrator/tests/`
- Prompts file: `/app/orchestrator/tests/ltx23-prompts.txt`

## LTX-2.3 Integration Tests

Location: `/app/orchestrator/tests/test_ltx23_video_generation.py`

### Test Suite (5 tests)
1. `test_01_submit_workflow_returns_prompt_id` — validates workflow submission to ComfyUI
2. `test_02_generate_cinematic_video` — full end-to-end video generation with cinematic prompt
3. `test_03_generate_nature_video` — generation with nature scene prompt
4. `test_04_compare_with_orchestrator_workflow` — compares direct API vs orchestrator workflow
5. `test_05_lora_enabled_workflow` — tests LoRA-enabled generation

### Prerequisites
- ComfyUI running and accessible at `COMFYUI_URL` (default `http://127.0.0.1:8188`)
- LTX-2.3 checkpoint installed at `/models/ltx-video/ltxv_2.3.safetensors` in ComfyUI
- Real prompts loaded from `ltx23-prompts.txt` (falls back to defaults if empty)

### Run Command
```bash
lando ssh -s app "python -m pytest /app/orchestrator/tests/test_ltx23_video_generation.py -v"
```

## Architecture Overview

```
WordPress (Post + SCF fields)
    ↓ REST API: POST /generate (fast, returns immediately)
Python Orchestrator (FastAPI) — /opt/wp-comfy/orchestrator/app.py
    ↓ Celery Task Queue (Redis)
Celery Worker(s) — /opt/wp-comfy/orchestrator/tasks.py
    ↓ ComfyUI API (GPU workflow)
ComfyUI (Docker + GPU)
    ↓ Output file
Celery Worker uploads media and updates WordPress via REST API
WordPress (final video embedded)
```

## Service Locations

| Service | Location/Path | Port |
|---------|---------------|------|
| Orchestrator app | `/opt/wp-comfy/orchestrator/app.py` | 8000 |
| Celery tasks | `/opt/wp-comfy/orchestrator/tasks.py` | - |
| WordPress | `/opt/wp-comfy/wordpress/` | 80 |
| Database | `/opt/wp-comfy/db-data/` | 3306 |
| Redis | (service) | 6379 |
| ComfyUI | (Docker + GPU) | 8188 |

## FastAPI Endpoints

### POST /generate
- Accepts: `{ "post_id": <int> }`
- Behavior: Calls `get_post(post_id)`, sends Celery task, updates post meta with `video_status=queued` and `video_job_id`
- Returns: `{ "job_id": <task.id>, "status": "queued" }`

### GET /status/{job_id}
- Queries Celery `AsyncResult`
- Returns: state, progress, message, result

## Key Functions to Test

| Function | File | Purpose |
|----------|------|---------|
| `submit_workflow(post_id)` | tasks.py | POSTs workflow JSON to ComfyUI `/prompt` |
| `poll_comfyui(prompt_id)` | tasks.py | Polls ComfyUI `/history/{prompt_id}` until completion |
| `upload_media_to_wordpress(filepath, filename)` | tasks.py | POSTs binary media to WordPress `/wp-json/wp/v2/media` |
| `generate_video_task(self, post_id)` | tasks.py | Celery task orchestrating the full workflow |

## Running Tests Locally

### Docker Compose Environment
```bash
# Install test dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r orchestrator/requirements.txt
pip install pytest pytest-mock responses
pytest orchestrator/tests -q
```

### Lando Environment (Recommended)
```bash
lando ssh -s app "python -m pytest /app/orchestrator/tests/ -v"
```

## Test Configuration Notes

- For Celery eager mode in tests: `tasks.celery_app.conf.task_always_eager = True`
- Mock `celery_app.send_task` to return a fake task with `id` attribute
- Use `pytest-mock` for mocking HTTP calls and Celery components

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WORDPRESS_URL` | `http://wordpress:80` | WordPress API URL |
| `WP_USERNAME` / `WORDPRESS_USER` | - | WordPress username |
| `WP_APP_PASSWORD` / `WORDPRESSAPPPASSWORD` | - | WordPress app password |
| `COMFYUI_URL` | `http://127.0.0.1:8188` | ComfyUI API URL |
| `REDIS_URL` | `redis://redis:6379/0` | Redis broker/backend URL |

## LTX-2.3 Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LTX_CHECKPOINT_PATH` | `/models/ltx-video/ltxv_2.3.safetensors` | Model checkpoint path |
| `LTX_RESOLUTION_X` | `768` | Video width |
| `LTX_RESOLUTION_Y` | `512` | Video height |
| `LTX_NUM_FRAMES` | `97` | Number of frames |
| `LTX_FPS` | `25` | Frames per second |
| `LTX_STEPS` | `32` | Generation steps |
| `LTX_CFG` | `4.5` | CFG scale |
| `LTX_SEED` | `42` | Random seed |

### LoRA Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LORA_ENABLED` | `false` | Enable LoRA support |
| `LORA_NAME` | `` | LoRA model name |
| `LORA_PATH` | `/models/loras/{name}.safetensors` | LoRA file path |
| `LORA_WEIGHT` | `1.0` | LoRA weight (0.0-2.0) |
