#!/bin/bash

# SN27 Miner Containerized Startup Script
# This script handles wallet setup and runs the miner in Docker container mode

set -e

# Configuration
MINER_NAME="sn27-miner"
DEFAULT_NETWORK="finney"
DEFAULT_NETUID="27"
DEFAULT_AXON_PORT="8091"
DEFAULT_SSH_PORT="4444"
DEFAULT_EXTERNAL_PORT="27015"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_colored() {
    echo -e "${2}${1}${NC}"
}

print_header() {
    echo
    print_colored "===============================================" $BLUE
    print_colored "        SN27 Miner Container Setup           " $BLUE
    print_colored "===============================================" $BLUE
    echo
}

print_step() {
    print_colored "→ $1" $YELLOW
}

print_success() {
    print_colored "✓ $1" $GREEN
}

print_error() {
    print_colored "✗ $1" $RED
}

# Function to check if Docker is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! docker info &> /dev/null; then
        print_error "Docker is not running or accessible. Please start Docker or check permissions."
        exit 1
    fi

    print_success "Docker is available"
}

# Function to check if NVIDIA Docker is available (if GPU is needed)
check_nvidia_docker() {
    if docker run --rm --gpus all nvidia/cuda:12.8-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        print_success "NVIDIA Docker support is available"
        return 0
    else
        print_colored "Warning: NVIDIA Docker support not available. GPU mining will not work." $YELLOW
        return 1
    fi
}

# Function to setup wallet directories
setup_wallets() {
    print_step "Setting up wallet directories..."

    mkdir -p wallets
    mkdir -p logs

    if [ ! -d "wallets" ] || [ -z "$(ls -A wallets)" ]; then
        print_colored "Wallet directory is empty. You'll need to:" $YELLOW
        echo "  1. Copy your existing wallet files to ./wallets/"
        echo "  2. Or create new wallets using btcli"
        echo
        echo "To create new wallets:"
        echo "  docker run -it --rm -v \$(pwd)/wallets:/home/miner/.bittensor/wallets bittensor/bittensor:latest btcli wallet new_coldkey"
        echo "  docker run -it --rm -v \$(pwd)/wallets:/home/miner/.bittensor/wallets bittensor/bittensor:latest btcli wallet new_hotkey"
        echo
        read -p "Press Enter to continue once wallets are ready..."
    fi

    print_success "Wallet directories prepared"
}

# Function to setup environment
setup_environment() {
    print_step "Setting up environment..."

    if [ ! -f ".env" ]; then
        if [ -f ".env.miner" ]; then
            cp .env.miner .env
            print_success "Copied .env.miner to .env"
        else
            print_colored "Warning: No .env file found. Creating minimal configuration." $YELLOW
            cat > .env << EOF
# SN27 Miner Configuration
# Add your WandB API key here if you have one
# WANDB_API_KEY=your_api_key_here
EOF
        fi
    fi

    print_success "Environment configured"
}

# Function to build Docker image
build_image() {
    print_step "Building Docker image..."

    if docker build -t sn27-miner .; then
        print_success "Docker image built successfully"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
}

# Function to run the miner
run_miner() {
    local wallet_name="${1:-default}"
    local hotkey_name="${2:-default}"
    local network="${3:-$DEFAULT_NETWORK}"
    local netuid="${4:-$DEFAULT_NETUID}"

    print_step "Starting SN27 miner container..."

    # Stop existing container if running
    if docker ps -q -f name=$MINER_NAME | grep -q .; then
        print_step "Stopping existing miner container..."
        docker stop $MINER_NAME
        docker rm $MINER_NAME
    fi

    # Run the containerized miner
    docker run -d \
        --name $MINER_NAME \
        --restart unless-stopped \
        --gpus all \
        -p $DEFAULT_AXON_PORT:$DEFAULT_AXON_PORT \
        -p $DEFAULT_SSH_PORT:$DEFAULT_SSH_PORT \
        -p $DEFAULT_EXTERNAL_PORT:$DEFAULT_EXTERNAL_PORT \
        -v $(pwd)/wallets:/home/miner/.bittensor/wallets:rw \
        -v $(pwd)/logs:/app/logs:rw \
        -v $(pwd)/.env:/app/.env:ro \
        --cap-add SYS_ADMIN \
        --cap-add NET_ADMIN \
        --cap-add NET_BIND_SERVICE \
        sn27-miner \
        python3 neurons/miner_containerless.py \
        --netuid $netuid \
        --subtensor.network $network \
        --wallet.name $wallet_name \
        --wallet.hotkey $hotkey_name \
        --axon.port $DEFAULT_AXON_PORT \
        --ssh.port $DEFAULT_SSH_PORT \
        --external.fixed-port $DEFAULT_EXTERNAL_PORT \
        --logging.debug

    if [ $? -eq 0 ]; then
        print_success "Miner container started successfully!"
        echo
        print_colored "Container Name: $MINER_NAME" $BLUE
        print_colored "Axon Port: $DEFAULT_AXON_PORT" $BLUE
        print_colored "SSH Port: $DEFAULT_SSH_PORT" $BLUE
        print_colored "External Port: $DEFAULT_EXTERNAL_PORT" $BLUE
        echo
        print_colored "To view logs: docker logs -f $MINER_NAME" $YELLOW
        print_colored "To stop miner: docker stop $MINER_NAME" $YELLOW
        print_colored "To check status: docker ps" $YELLOW
    else
        print_error "Failed to start miner container"
        exit 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -w, --wallet NAME      Wallet name (default: default)"
    echo "  -k, --hotkey NAME      Hotkey name (default: default)"
    echo "  -n, --network NAME     Network (default: finney)"
    echo "  -u, --netuid ID        Network UID (default: 27)"
    echo "  --build-only           Only build the Docker image"
    echo "  --logs                 Show miner logs"
    echo "  --stop                 Stop the miner"
    echo "  --status               Show miner status"
    echo "  -h, --help             Show this help message"
    echo
    echo "Examples:"
    echo "  $0                                    # Run with defaults"
    echo "  $0 -w mywallet -k myhotkey           # Run with custom wallet"
    echo "  $0 -n test -u 15                     # Run on testnet"
    echo "  $0 --build-only                      # Just build the image"
    echo "  $0 --logs                            # View logs"
}

# Main execution
main() {
    local wallet_name="default"
    local hotkey_name="default"
    local network="$DEFAULT_NETWORK"
    local netuid="$DEFAULT_NETUID"
    local build_only=false
    local show_logs=false
    local stop_miner=false
    local show_status=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -w|--wallet)
                wallet_name="$2"
                shift 2
                ;;
            -k|--hotkey)
                hotkey_name="$2"
                shift 2
                ;;
            -n|--network)
                network="$2"
                shift 2
                ;;
            -u|--netuid)
                netuid="$2"
                shift 2
                ;;
            --build-only)
                build_only=true
                shift
                ;;
            --logs)
                show_logs=true
                shift
                ;;
            --stop)
                stop_miner=true
                shift
                ;;
            --status)
                show_status=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # Handle special commands
    if [ "$show_logs" = true ]; then
        docker logs -f $MINER_NAME
        exit 0
    fi

    if [ "$stop_miner" = true ]; then
        print_step "Stopping miner..."
        docker stop $MINER_NAME
        print_success "Miner stopped"
        exit 0
    fi

    if [ "$show_status" = true ]; then
        echo "Miner Status:"
        docker ps -f name=$MINER_NAME
        exit 0
    fi

    print_header

    # Prerequisites check
    check_docker
    check_nvidia_docker

    # Setup
    setup_wallets
    setup_environment
    build_image

    if [ "$build_only" = true ]; then
        print_success "Build completed successfully!"
        exit 0
    fi

    # Run miner
    run_miner "$wallet_name" "$hotkey_name" "$network" "$netuid"
}

# Run main function with all arguments
main "$@"