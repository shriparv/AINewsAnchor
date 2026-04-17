import torch
import sys
import subprocess
import os

def check_gpu():
    print("=== GPU Diagnostic ===")
    
    # 1. Torch Check
    print(f"\n1. PyTorch Status:")
    print(f"   - Torch version: {torch.__version__}")
    cuda_available = torch.cuda.is_available()
    print(f"   - CUDA Available: {'✅ YES' if cuda_available else '❌ NO'}")
    
    if cuda_available:
        print(f"   - GPU Device: {torch.cuda.get_device_name(0)}")
        print(f"   - CUDA Capability: {torch.cuda.get_device_capability(0)}")
    else:
        print("   ⚠️  Suggestion: You may have the CPU-only version of Torch.")
        print("      Run: pip install torch --index-url https://download.pytorch.org/whl/cu121")

    # 2. FFmpeg / NVENC Check
    print(f"\n2. Video Encoding (NVENC) Status:")
    try:
        # Check if ffmpeg has h264_nvenc encoder
        res = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
        if "h264_nvenc" in res.stdout:
            print(f"   - NVENC Encoder: ✅ FOUND")
        else:
            print(f"   - NVENC Encoder: ❌ NOT FOUND in FFmpeg")
            print("     ⚠️  Ensure you have an NVIDIA GPU and recent drivers installed.")
    except FileNotFoundError:
        print("   - FFmpeg Status: ❌ NOT FOUND in PATH")

    # 3. Environment Check
    print(f"\n3. Environment:")
    print(f"   - Python: {sys.version.split()[0]}")
    print(f"   - OS: {sys.platform}")

if __name__ == "__main__":
    check_gpu()
