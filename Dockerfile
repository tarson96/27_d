# Multi-stage build for SN27 Miner
FROM nvidia/cuda:12.8-devel-ubuntu22.04 as base

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
    python3.10-venv \
    git \
    openssh-server \
    build-essential \
    curl \
    wget \
    software-properties-common \
    ocl-icd-libopencl1 \
    pocl-opencl-icd \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.10 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 \
    && update-alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3 1

# Create a non-root user for running the miner
RUN useradd -m -u 1000 -s /bin/bash miner && \
    usermod -aG sudo miner

# Create required directories
RUN mkdir -p /tmp/miner_allocations /var/run/sshd && \
    chown -R miner:miner /tmp/miner_allocations && \
    chmod 755 /tmp/miner_allocations

# Production stage
FROM base as production

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app/

# Install Python dependencies
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install -e . -r requirements.txt

# Create logging directory
RUN mkdir -p /app/logs && chown -R miner:miner /app/logs

# Switch to miner user
USER miner

# Create necessary directories for miner operation
RUN mkdir -p ~/.bittensor/wallets

# Expose required ports
# 8091 - Axon port (Bittensor communication)
# 4444 - SSH port for validator access
# 27015 - External fixed port for client use
EXPOSE 8091 4444 27015

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import bittensor as bt; print('healthy')" || exit 1

# Default command
CMD ["python3", "neurons/miner.py", "--netuid", "27", "--subtensor.network", "finney", "--axon.port", "8091", "--ssh.port", "4444", "--external.fixed-port", "27015", "--logging.debug"]