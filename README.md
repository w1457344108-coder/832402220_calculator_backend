# 832402220 Calculator Backend

FastAPI backend for the front-end separated calculator assignment.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Set `DATABASE_URL` to the Neon PostgreSQL connection string and `CORS_ORIGINS` to the deployed frontend URL. The API creates the single `calculation_history` table on startup.

## API

- `GET /api/health`
- `POST /api/calculate` with `{ "expression": "(1+2)*3" }`
- `GET /api/history`
- `DELETE /api/history/{id}`

Expression evaluation is performed on the backend by a small hand-written parser. It accepts numbers, decimal points, parentheses, and `+ - * /`, including unary signs. It does not execute user input as code.
