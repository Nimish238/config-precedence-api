# 12-Factor Config Precedence API

FastAPI implementation for the configuration-precedence assignment.

## Local run

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/effective-config`.

Test fresh CLI overrides:
`http://127.0.0.1:8000/effective-config?set=port=9000&set=debug=true`

## Deploy to Render

1. Push the contents of this folder to a GitHub repository.
2. In Render, create **New + → Blueprint** and select the repository (or create a Web Service with the settings below).
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. After deployment, open `https://YOUR-SERVICE.onrender.com/effective-config`.
6. Submit that base URL plus `/effective-config` in the assignment.

The endpoint reads configuration layers on each request, so query-string `set` overrides are not cached. API keys are always masked. CORS is enabled for browser-based grading.
