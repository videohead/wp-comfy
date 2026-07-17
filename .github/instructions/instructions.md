WordPress (Post + SCF fields)
        ↓ REST API: /generate (fast, returns immediately)
Python Orchestrator (FastAPI)
        ↓ Celery Task Queue (Redis or RabbitMQ)
Celery Worker(s)
        ↓ ComfyUI API (GPU workflow)
ComfyUI (Docker + GPU)
        ↓ Output file
Celery Worker
        ↓ WordPress REST API (media upload + post update)
WordPress (final video embedded)