# Nirikshan API Backend

Backend for Nirikshan, a Legal Metrology label compliance checker under LMPC Rules 2011.

## Local Setup & Development (Venv Only)

The primary and recommended deployment target is the multi-stage Docker container (`docker build -t nirikshan .`).

If running locally outside Docker, you **MUST** use a Python virtual environment (`.venv`). Do **NOT** rely on global site-packages or set `PYTHONPATH` hacks manually.

### Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn main:app --reload --port 8000
```

### Linux / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn main:app --reload --port 8000
```
