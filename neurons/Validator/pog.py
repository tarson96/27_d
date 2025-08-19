import paramiko
import hashlib
import struct
import numpy as np
import os
import time
import secrets
import json
import tempfile
import yaml
import bittensor as bt

MASK32 = 0xFFFF_FFFF
MIX32  = 0x45D9F3B

# --- Sybil PRNG and Merkle functions ---

def xs32(x):
    """
    Sybil 32-bit PRNG core step.
    """
    x &= MASK32
    x ^= (x << 13) & MASK32
    x ^= (x >> 17)
    x ^= (x << 5)  & MASK32
    return x & MASK32

def prng(seed, i, j):
    """
    Sybil-style deterministic PRNG for matrix elements.
    """
    s = (seed + (i & MASK32) + j) & MASK32
    for _ in range(10):
        s = xs32(s)
    return s / float(MASK32)

def row_hash32_np(row: np.ndarray) -> int:
    """
    Hash a row as a single 32-bit int, Sybil style, for Merkle leaf construction.
    """
    words = np.ascontiguousarray(row, dtype=np.float32).view(np.uint32)
    while words.size > 1:
        if words.size & 1:
            words = np.append(words, words[-1])
        words = words[0::2] ^ words[1::2]
        words = (words.astype(np.uint64) * MIX32) & MASK32
        words ^= words >> np.uint64(16)
        words = words.astype(np.uint32)
    return int(words[0])

def leaf_digest(row: np.ndarray) -> bytes:
    """
    Sybil Merkle leaf: SHA256 of row's 32-bit hash.
    """
    return hashlib.sha256(struct.pack("<I", row_hash32_np(row))).digest()

def verify_merkle_proof_row(row, proof, root_hash, index, total_leaves, hash_func=hashlib.sha256):
    """
    Verifies a Merkle proof for a given row using Sybil-style leaf construction.
    """
    computed_hash = leaf_digest(row)
    idx = index
    for sibling_hash in proof:
        if idx % 2 == 0:
            computed_hash = hash_func(computed_hash + sibling_hash).digest()
        else:
            computed_hash = hash_func(sibling_hash + computed_hash).digest()
        idx //= 2
    return computed_hash == root_hash

def load_yaml_config(file_path):
    """
    Load GPU performance data from a YAML file.
    """
    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
        return data
    except FileNotFoundError:
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    except yaml.YAMLError as e:
        raise ValueError(f"Error decoding YAML file {file_path}: {e}")

def identify_gpu(fp16_tflops, fp32_tflops, estimated_avram, gpu_data, reported_name=None, tolerance_pairs=None):
    """
    Identify GPU based on TFLOPS and AVRAM with a tolerance check for GPUs with similar fingerprints.
    """
    tolerance_pairs = tolerance_pairs or {}
    GPU_TFLOPS_FP16 = gpu_data["GPU_TFLOPS_FP16"]
    GPU_TFLOPS_FP32 = gpu_data["GPU_TFLOPS_FP32"]
    GPU_AVRAM = gpu_data["GPU_AVRAM"]

    combined_scores = []
    for gpu in GPU_TFLOPS_FP16.keys():
        fp16_theoretical = GPU_TFLOPS_FP16[gpu]
        fp32_theoretical = GPU_TFLOPS_FP32[gpu]
        avram_theoretical = GPU_AVRAM[gpu]
        fp16_deviation = abs(fp16_tflops - fp16_theoretical) / fp16_theoretical
        fp32_deviation = abs(fp32_tflops - fp32_theoretical) / fp32_theoretical
        avram_deviation = abs(estimated_avram - avram_theoretical) / avram_theoretical
        combined_score = (fp16_deviation + fp32_deviation + avram_deviation) / 3
        combined_scores.append((gpu, combined_score))
    identified_gpu = sorted(combined_scores, key=lambda x: x[1])[0][0]
    if reported_name:
        if identified_gpu in tolerance_pairs and reported_name == tolerance_pairs.get(identified_gpu):
            bt.logging.trace(f"[Tolerance Adjustment] Detected GPU {identified_gpu} matches reported GPU {reported_name}.")
            identified_gpu = reported_name
        elif reported_name in tolerance_pairs and identified_gpu == tolerance_pairs.get(reported_name):
            bt.logging.trace(f"[Tolerance Adjustment] Reported GPU {reported_name} matches detected GPU {identified_gpu}.")
            identified_gpu = reported_name
    return identified_gpu

def compute_script_hash(script_path):
    """
    Compute the SHA256 hash of the miner script for integrity verification.
    """
    with open(script_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def send_script_and_request_hash(ssh_client, script_path):
    """
    Upload the miner script and compute its hash remotely.
    """
    sftp = ssh_client.open_sftp()
    sftp.put(script_path, "/tmp/miner_script.py")
    sftp.close()
    hash_command = """
/opt/conda/bin/python -c "
import hashlib
with open('/tmp/miner_script.py', 'rb') as f:
    computed_hash = hashlib.sha256(f.read()).hexdigest()
print(computed_hash)
"
"""
    stdin, stdout, stderr = ssh_client.exec_command(hash_command)
    computed_hash = stdout.read().decode().strip().splitlines()[-1]
    hash_error = stderr.read().decode().strip()
    if hash_error:
        raise RuntimeError(f"Hash computation failed: {hash_error}")
    return computed_hash

def execute_script_on_miner(ssh_client, mode):
    """
    Execute the remote miner script in a given mode and capture the output.
    """
    execution_command = f"/opt/conda/bin/python /tmp/miner_script.py --mode {mode}"
    stdin, stdout, stderr = ssh_client.exec_command(execution_command)
    execution_output = stdout.read().decode().strip()
    execution_error = stderr.read().decode().strip()
    if execution_error:
        raise RuntimeError(f"Script execution failed: {execution_error}")
    return execution_output

def parse_benchmark_output(output):
    """
    Parse the output from benchmarking mode.
    """
    try:
        parts = output.strip().split()
        num_gpus = int(parts[0])
        vram = float(parts[1])
        size_fp16 = int(parts[2])
        time_fp16 = float(parts[3])
        size_fp32 = int(parts[4])
        time_fp32 = float(parts[5])
        return num_gpus, vram, size_fp16, time_fp16, size_fp32, time_fp32
    except (ValueError, IndexError) as e:
        raise ValueError(f"Failed to parse execution output: {output}") from e

def parse_merkle_output(output):
    """
    Parse the output from merkle (compute/proof) mode in Sybil-compatible style.
    """
    try:
        lines = output.strip().split('\n')
        root_hashes_line = None
        timings_line = None
        for line in lines:
            if line.startswith('ROOTS:'):
                root_hashes_line = line
            elif line.startswith('TIMINGS:'):
                timings_line = line
        if root_hashes_line is None or timings_line is None:
            raise ValueError("Output does not contain root hashes or timings")
        root_hashes = json.loads(root_hashes_line.split(':', 1)[1])
        gpu_timings = json.loads(timings_line.split(':', 1)[1])
        return root_hashes, gpu_timings
    except (ValueError, IndexError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to parse execution output: {output}") from e

def get_random_seeds(num_gpus):
    """
    Generate 32-bit seeds for each GPU.
    """
    seeds = {}
    for gpu_id in range(num_gpus):
        s_A = secrets.randbits(32)
        s_B = secrets.randbits(32)
        seeds[gpu_id] = (s_A, s_B)
    return seeds

def send_seeds(ssh_client, seeds, n):
    """
    Send matrix size and PRNG seeds to the remote miner via SFTP.
    """
    lines = [str(n)]
    for gpu_id in seeds.keys():
        s_A, s_B = seeds[gpu_id]
        line = f"{gpu_id} {s_A} {s_B}"
        lines.append(line)
    content = '\n'.join(lines)
    try:
        with ssh_client.open_sftp() as sftp:
            with sftp.file('/tmp/seeds.txt', 'w') as f:
                f.write(content)
    except Exception as e:
        raise RuntimeError(f"Failed to send seeds to remote miner: {e}")

def send_challenge_indices(ssh_client, indices):
    """
    Send challenge indices to the remote miner via SFTP.
    """
    lines = []
    for gpu_id in indices.keys():
        idx_list = indices[gpu_id]
        indices_str = ';'.join([f"{i},{j}" for i, j in idx_list])
        line = f"{gpu_id} {indices_str}"
        lines.append(line)
    content = '\n'.join(lines)
    try:
        with ssh_client.open_sftp() as sftp:
            with sftp.file('/tmp/challenge_indices.txt', 'w') as f:
                f.write(content)
    except Exception as e:
        raise RuntimeError(f"Failed to send challenge indices to remote miner: {e}")

def receive_responses(ssh_client, num_gpus):
    """
    Download response npy files from the miner and load as Python objects.
    """
    responses = {}
    try:
        with ssh_client.open_sftp() as sftp, tempfile.TemporaryDirectory() as temp_dir:
            for gpu_id in range(num_gpus):
                remote_path = f'/dev/shm/resp_{gpu_id}.npy'
                local_path = f'{temp_dir}/resp_{gpu_id}.npy'
                try:
                    sftp.get(remote_path, local_path)
                    response = np.load(local_path, allow_pickle=True)
                    responses[gpu_id] = response.item()
                except Exception as e:
                    print(f"Error processing GPU {gpu_id}: {e}")
                    responses[gpu_id] = None
    except Exception as e:
        print(f"SFTP connection error: {e}")
    return responses

def adjust_matrix_size(vram, element_size=2, buffer_factor=0.8):
    """
    Calculate the matrix size based on available VRAM.
    """
    usable_vram = vram * buffer_factor * 1e9
    max_size = int((usable_vram / (2 * element_size)) ** 0.5)
    aligned_size = (max_size // 32) * 32
    return aligned_size

def get_remote_gpu_info(ssh_client):
    """
    Execute the miner script in gpu_info mode to get GPU information from the remote miner.
    """
    command = "/opt/conda/bin/python /tmp/miner_script.py --mode gpu_info"
    stdin, stdout, stderr = ssh_client.exec_command(command)
    output = stdout.read().decode().strip()
    error = stderr.read().decode().strip()
    if error:
        raise RuntimeError(f"Failed to get GPU info: {error}")
    return json.loads(output)

def merkle_ok(row, proof, root, idx, total):
    h = leaf_digest(row)
    for sib in proof:
        h = hashlib.sha256(h + sib).digest() if idx % 2 == 0 \
            else hashlib.sha256(sib + h).digest()
        idx //= 2
    return h == root

def prng(seed, i, j):
    s = (seed + (i & MASK32) + j) & MASK32
    for _ in range(10):
        s = xs32(s)
    return s / float(MASK32)

def verify_responses(seeds, root_hashes, responses, indices, n):
    """
    Verifies the responses from GPUs by checking computed values and Merkle proofs (Sybil-style C1/C2 logic).
    """
    verification_passed = True
    failed_gpus = []
    num_gpus = len(root_hashes.keys())
    required_passes = num_gpus if num_gpus <= 4 else int(np.ceil(0.75 * num_gpus))
    for gpu_id in root_hashes.keys():
        s_A, s_B = seeds[gpu_id]
        gpu_indices = indices[gpu_id]
        response = responses[gpu_id]
        root_hash = bytes.fromhex(root_hashes[gpu_id])
        total_leaves = 2 * n  # Sybil: C1 and C2 stacked
        gpu_failed = False
        for idx, (i, j) in enumerate(gpu_indices):
            # Numeric check, Sybil style: C1 and C2
            if i < n:
                exp = sum(prng(s_A, i, k) * prng(s_B, k, j) for k in range(n))
            else:
                ir = i - n
                exp = sum(prng(s_B, ir, k) * prng(s_A, k, j) for k in range(n))
            value_validator = exp
            row_miner = response['rows'][idx]
            proof = response['proofs'][idx]
            value_miner = row_miner[j]
            if not np.isclose(value_miner, value_validator, atol=1e-4, rtol=1e-3):
                bt.logging.trace(f"[Verification] GPU {gpu_id}: Value mismatch at index ({i}, {j}).")
                gpu_failed = True
                break
            if not verify_merkle_proof_row(row_miner, proof, root_hash, i, total_leaves):
                bt.logging.trace(f"[Verification] GPU {gpu_id}: Invalid Merkle proof at index ({i}).")
                gpu_failed = True
                break
        if gpu_failed:
            failed_gpus.append(gpu_id)
            bt.logging.trace(f"[Verification] GPU {gpu_id} failed verification.")
        else:
            bt.logging.trace(f"[Verification] GPU {gpu_id} passed verification.")

    passed_gpus = num_gpus - len(failed_gpus)
    if passed_gpus >= required_passes:
        verification_passed = True
        bt.logging.trace(f"[Verification] SUCCESS: {passed_gpus} out of {num_gpus} GPUs passed verification.")
        if len(failed_gpus) > 0:
            bt.logging.trace(f"            Note: {len(failed_gpus)} GPU(s) failed verification but within allowed threshold.")
    else:
        verification_passed = False
        bt.logging.trace(f"[Verification] FAILURE: Only {passed_gpus} out of {num_gpus} GPUs passed verification.")
        if len(failed_gpus) > 0:
            bt.logging.trace(f"            {len(failed_gpus)} GPU(s) failed verification which exceeds the allowed threshold.")
    return verification_passed
