# 832402220 Calculator Backend

FastAPI backend for the separated calculator assignment. The browser sends an arithmetic expression to this service; the service evaluates it, stores the successful calculation in PostgreSQL, and returns the result and history.

## Online service

- API base URL: <https://eight32402220-calculator-backend.onrender.com>
- Health check: <https://eight32402220-calculator-backend.onrender.com/api/health>
- Frontend: <https://832402220-calculator-frontend.vercel.app>

The backend is deployed on Render and uses a Neon PostgreSQL database. The free Render service may sleep when it is idle, so the first request after a period of inactivity can take longer while the service wakes up.

## Architecture

```text
Vue 3 + Vite (Vercel)
          │ HTTPS / JSON
          ▼
FastAPI (Render)
          │ SQLAlchemy + psycopg
          ▼
Neon PostgreSQL
```

The frontend never connects directly to PostgreSQL. It calls the backend endpoints, and the backend owns expression evaluation, validation, CORS, and persistence.

## Directory guide

| Path | Role |
| --- | --- |
| `app/main.py` | FastAPI application, CORS configuration, endpoint handlers, and startup table creation |
| `app/calculator.py` | Small recursive-descent arithmetic parser |
| `app/database.py` | SQLAlchemy engine/session setup and PostgreSQL URL normalization |
| `app/models.py` | `calculation_history` SQLAlchemy model |
| `app/init_db.py` | One-shot command that creates the database tables |
| `tests/` | Parser and API tests |
| `.env.example` | Safe local configuration template; copy it to `.env` and fill in local values |

## Requirements

- Python 3.11 or newer
- A running PostgreSQL database for local production-like use (Neon is also suitable)
- `pip`

The test suite can use SQLite in memory, but the deployed application is configured with PostgreSQL.

## Local setup with PostgreSQL

Run the Python commands below from this backend repository's root directory.

1. Install and start PostgreSQL if it is not already running. On macOS with Homebrew, the typical commands are `brew install postgresql@16` and `brew services start postgresql@16`; on Ubuntu/Debian, install the `postgresql` package and start its system service. Use your operating system's PostgreSQL package manager when these examples do not apply.

2. Create a local PostgreSQL database and user, for example a database named `calculator` owned by `calculator_user`.

   Open an administrator session, for example `psql -d postgres` after a Homebrew installation or `sudo -u postgres psql` on Ubuntu/Debian. If Homebrew's `psql` is not on `PATH`, use the binary in its PostgreSQL installation directory. Run the following after choosing your own password:

   ```sql
   CREATE USER calculator_user WITH PASSWORD 'replace-this-password';
   CREATE DATABASE calculator OWNER calculator_user;
   ```

3. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. Create the environment file:

   ```bash
   cp .env.example .env
   ```

5. Edit `.env` with a real local PostgreSQL URL, using the password selected in step 2. Both `postgresql://...` and `postgresql+psycopg://...` are accepted; the application normalizes the first form for psycopg 3. Set `CORS_ORIGINS` to the frontend origin(s), separated by commas.

   ```dotenv
   DATABASE_URL='postgresql+psycopg://calculator_user:password@localhost:5432/calculator'
   CORS_ORIGINS='http://localhost:5173'
   ```

6. Initialize the table. `python -m app.init_db` reads `DATABASE_URL` from the process environment, so export the values from your own `.env` for this one-shot command. Keep values quoted as above, especially if a URL contains `&`:

   ```bash
   set -a
   source .env
   set +a
   python -m app.init_db
   ```

7. Start the API. Uvicorn loads `.env` for the application process:

   ```bash
   uvicorn --env-file .env app.main:app --reload
   ```

The API is then available at `http://localhost:8000`. Opening `http://localhost:8000/docs` shows FastAPI's interactive documentation.

For a quick test-only run without PostgreSQL, omit `DATABASE_URL`; the code falls back to a local SQLite file. This fallback is useful for tests and does not replace PostgreSQL for deployment.

## API contract

### `GET /api/health`

Returns `200 OK` when the service is running:

```json
{"status":"ok"}
```

### `POST /api/calculate`

Request body:

```json
{"expression":"(1+2)*3"}
```

On success, returns `200 OK` and writes one history row:

```json
{
  "success": true,
  "id": 1,
  "expression": "(1+2)*3",
  "result": "9",
  "created_at": "2026-10-04T08:00:00+00:00"
}
```

`expression` must be a non-empty string of at most 500 characters. A syntactically valid request whose arithmetic cannot be parsed or evaluated returns `400` with a stable error code and bilingual message:

```json
{
  "success": false,
  "code": "INVALID_EXPRESSION",
  "message": {"zh":"表达式无效","en":"Invalid expression"}
}
```

Division by zero returns the same `400` shape with `code: "DIVISION_BY_ZERO"`; these errors do not create history records. Missing or structurally invalid request bodies, including an empty or over-500-character expression, are rejected by FastAPI with `422` and its standard `detail` validation response.

### `GET /api/history`

Returns `200 OK` and a JSON array of saved calculations, newest first:

```json
[
  {
    "id": 1,
    "expression": "(1+2)*3",
    "result": "9",
    "created_at": "2026-10-04T08:00:00+00:00"
  }
]
```

### `DELETE /api/history/{id}`

Deletes the row and returns `204 No Content` on success. A missing id returns `404`:

```json
{
  "success": false,
  "code": "NOT_FOUND",
  "message": {"zh":"记录不存在","en":"Record not found"}
}
```

## Expression safety

The service uses a hand-written parser and `Decimal` with a precision of 50 significant digits; it does not call `eval`, execute shell commands, or interpret arbitrary Python. Supported input is limited to decimal numbers, whitespace, parentheses, binary `+ - * /`, and unary `+` or `-`. Names, strings, commas, exponent notation, function calls, and other characters are rejected. Results are normalized decimal strings rather than JSON floating-point numbers.

This basic assignment has no login or user isolation: all visitors share the same history and can delete its records. CORS controls permitted browser origins; it is not user authentication.

## Tests

With the virtual environment active:

```bash
pytest
```

The tests cover precedence, parentheses, unary signs, decimal arithmetic, malformed expressions, division by zero, URL normalization, and the health/calculate/history/delete API flow. The API test module uses an in-memory SQLite database so it does not alter a local PostgreSQL database.

## Neon PostgreSQL configuration

1. Create a Neon project and select its database and database user.
2. Copy the PostgreSQL connection string from Neon's Connect panel. Preserve its SSL options, such as `sslmode=require`; do not replace it with an HTTP dashboard URL.
3. Store that complete string as Render's `DATABASE_URL`. The code accepts Neon's `postgresql://` prefix and converts it to the SQLAlchemy psycopg dialect.
4. For a local run against Neon, put the string in `.env` as a quoted value and use the same initialization/start commands above.

The database uses one `calculation_history` table with `id`, `expression`, `result`, and `created_at`. `id` is the primary key; results are stored as strings and timestamps are created in UTC.

## Deploying the backend on Render

Create a Render Web Service connected to this backend repository. Leave the Root Directory empty because `requirements.txt` and `app/` are at the repository root. Use:

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Environment variable `DATABASE_URL`: the Neon PostgreSQL connection string
- Environment variable `CORS_ORIGINS`: `https://832402220-calculator-frontend.vercel.app`

Render provides `$PORT`. The application creates missing tables during startup, so the free service does not require a service shell to initialize the schema. To initialize it explicitly, export the Neon `DATABASE_URL` in a local virtual environment and run:

```bash
python -m app.init_db
```

Do not commit `.env` or database credentials. Only `.env.example` belongs in the repository.

## Assignment acceptance checklist

- `GET /api/health` returns `200` and `{"status":"ok"}`.
- The frontend can calculate `1+2*3` and displays `7`.
- A successful calculation appears in `GET /api/history` and can be removed with the delete control.
- `1/0` shows a controlled error instead of a server traceback.
- Unsupported input such as `__import__("os")` is rejected by the parser.
- The frontend origin is present in `CORS_ORIGINS`.
- After inactivity, wait for the health URL to respond while Render/Neon wake on free plans, then retry a calculation.

The repositories can remain private. To let a teacher inspect the assignment, invite their GitHub account as a collaborator to each repository. A personal GitHub repository's collaborator role includes write access; an organization repository can instead grant the Read role. Do not publish `.env` files or secrets.
