# label-check

Lightweight image scanning web application with a FastAPI Python backend and React Vite frontend.

## Local Setup & Run Commands

### Backend
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment (optional):
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the backend server on port 8000:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### Frontend
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the frontend dev server on port 5173:
   ```bash
   npm run dev
   ```
