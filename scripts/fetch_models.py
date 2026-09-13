import os
import sys
import urllib.request
import hashlib

MODELS = [
    {
        "url": "https://huggingface.co/SWHL/RapidOCR/resolve/main/PP-OCRv3/en_PP-OCRv3_rec_infer.onnx",
        "path": "backend/models/en_PP-OCRv3_rec_infer.onnx",
        "sha256": "ef7abd8bd3629ae57ea2c28b425c1bd258a871b93fd2fe7c433946ade9b5d9ea",
    },
    {
        "url": "https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/main/ppocr/utils/en_dict.txt",
        "path": "backend/models/en_dict.txt",
        "sha256": "5662df9d2d03f0e8ca0d3b0649d6acbab904b6a14b3d3521463c71c37c668ce3",
    },
]


def fetch_models(base_dir: str = "."):
    for m in MODELS:
        dest_path = os.path.join(base_dir, m["path"])
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        if os.path.exists(dest_path):
            with open(dest_path, "rb") as f:
                content = f.read()
            actual_sha = hashlib.sha256(content).hexdigest()
            if actual_sha == m["sha256"]:
                print(f"Model file {dest_path} exists and SHA-256 matches.")
                continue
            else:
                print(f"SHA-256 mismatch for {dest_path}. Re-downloading...")

        print(f"Downloading {m['url']} to {dest_path}...")
        req = urllib.request.Request(m["url"], headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp:
            content = resp.read()

        actual_sha = hashlib.sha256(content).hexdigest()
        if actual_sha != m["sha256"]:
            print(f"ERROR: Downloaded file {dest_path} SHA-256 mismatch!\nExpected: {m['sha256']}\nGot: {actual_sha}", file=sys.stderr)
            sys.exit(1)

        with open(dest_path, "wb") as f:
            f.write(content)
        print(f"Successfully downloaded and verified {dest_path}.")


if __name__ == "__main__":
    fetch_models()
