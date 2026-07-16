FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# ---------------------------------------------------------
# System dependencies
# ---------------------------------------------------------
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    git wget curl \
    libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# Create ComfyUI environment
# ---------------------------------------------------------
WORKDIR /opt/comfyui
RUN python3 -m venv comfyui-env
ENV PATH="/opt/comfyui/comfyui-env/bin:${PATH}"

# ---------------------------------------------------------
# Upgrade pip
# ---------------------------------------------------------
RUN pip install --upgrade pip

# ---------------------------------------------------------
# Install PyTorch with CUDA 13.0 (Blackwell / GB200)
# ---------------------------------------------------------
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130

# ---------------------------------------------------------
# Clone ComfyUI
# ---------------------------------------------------------
RUN git clone https://github.com/comfyanonymous/ComfyUI.git .

# ---------------------------------------------------------
# Install ComfyUI dependencies
# ---------------------------------------------------------
RUN pip install -r requirements.txt

# ---------------------------------------------------------
# Download Stable Diffusion 1.5 checkpoint
# ---------------------------------------------------------
RUN mkdir -p models/checkpoints
RUN wget -O models/checkpoints/v1-5-pruned-emaonly-fp16.safetensors \
    https://huggingface.co/Comfy-Org/stable-diffusion-v1-5-archive/resolve/main/v1-5-pruned-emaonly-fp16.safetensors

# ---------------------------------------------------------
# Expose ComfyUI port
# ---------------------------------------------------------
EXPOSE 8188

# ---------------------------------------------------------
# Run ComfyUI
# ---------------------------------------------------------
CMD ["python3", "main.py", "--listen", "0.0.0.0"]
