# Nirikshan OCR Models Documentation

## English Recognition Model

- **Model Name**: `en_PP-OCRv3_rec_infer.onnx`
- **Version**: PP-OCRv3 (PaddleOCR / RapidOCR dedicated English recognition model)
- **Model URL**: `https://huggingface.co/SWHL/RapidOCR/resolve/main/PP-OCRv3/en_PP-OCRv3_rec_infer.onnx`
- **SHA-256**: `ef7abd8bd3629ae57ea2c28b425c1bd258a871b93fd2fe7c433946ade9b5d9ea`
- **Reasoning**: PaddleOCR/RapidOCR published `en_PP-OCRv3_rec_infer.onnx` as their latest dedicated English text recognition model (PP-OCRv4 only published updated Chinese recognition models; no `en_PP-OCRv4_rec` was produced).

## English Dictionary

- **Dictionary Name**: `en_dict.txt`
- **Dictionary URL**: `https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/main/ppocr/utils/en_dict.txt`
- **SHA-256**: `5662df9d2d03f0e8ca0d3b0649d6acbab904b6a14b3d3521463c71c37c668ce3`

## Model Fetching & Verification

The script `scripts/fetch_models.py` downloads these models locally into `backend/models/` and verifies their SHA-256 hashes before runtime and during Docker container build.
