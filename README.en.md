# 832402220 Calculator Backend

[简体中文](README.md) | [English](README.en.md)

This is the FastAPI backend for a calculator with separate frontend and backend repositories. The browser sends expressions or conversion parameters to the API; the backend validates the request, performs scientific calculations, integer-base conversions, or unit conversions, and stores successful results in PostgreSQL. The frontend and backend are maintained in separate public GitHub repositories.

## Online service

- API base URL: [Render backend](https://eight32402220-calculator-backend.onrender.com)
- Health check: [GET /api/health](https://eight32402220-calculator-backend.onrender.com/api/health)
- Interactive API documentation: [FastAPI /docs](https://eight32402220-calculator-backend.onrender.com/docs)
- Frontend: [Vercel calculator](https://832402220-calculator-frontend.vercel.app)
- Frontend repository: [832402220_calculator_frontend](https://github.com/w1457344108-coder/832402220_calculator_frontend)
- Backend repository: [832402220_calculator_backend](https://github.com/w1457344108-coder/832402220_calculator_backend)
- Code style: [codestyle.md](codestyle.md)

The backend is deployed on Render and uses Neon PostgreSQL. The free Render service may sleep when idle, so the first request after a period of inactivity can take longer while the service wakes up. SQLAlchemy checks pooled connections before reusing them. If Neon has closed an idle connection, the backend replaces it before executing a database query.

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

The frontend never connects directly to PostgreSQL. The backend owns expression parsing, calculations and conversions, validation, CORS, and persistence. Successful scientific calculations, base conversions, and unit conversions share the `calculation_history` table and the same history query/delete endpoints. After a page reload, the frontend loads the saved database history through the API.

## Features and precision

### Arithmetic and scientific calculations

The calculator accepts decimal numbers, scientific notation such as `1.2e-3`, whitespace, parentheses, unary signs, and the binary operators `+ - * / ^`. Exponentiation is right-associative: `2^3^2` means `2^(3^2)`. The constants `pi`, `π`, and `e` and the following fixed single-argument functions are supported:

| Function | Meaning | Input requirement |
| --- | --- | --- |
| `sin(x)` | Sine | Radians |
| `cos(x)` | Cosine | Radians |
| `tan(x)` | Tangent | Radians; a numerical near-pole region is rejected |
| `sqrt(x)` | Square root | `x >= 0` |
| `ln(x)` | Natural logarithm | `x > 0` |
| `log10(x)` | Base-10 logarithm | `x > 0` |
| `exp(x)` | Natural exponential | Within the protected numerical range |

The frontend's display symbols `×` and `÷` are converted to `*` and `/` before submission. Function names must match the listed forms, and arguments require parentheses. Implicit multiplication, multiple-argument functions, and arbitrary function calls are not supported.

Expressions are limited to 500 characters and a shared structural recursion budget of 32. Nonzero literals, intermediate values, and results must have a decimal adjusted exponent, `Decimal.adjusted()`, in `[-10000, 10000]`; zero is allowed. The absolute exponent after `e` / `E` in a scientific-notation literal is also limited to 10000, including for zero. The absolute exponent for `^` is limited to 10000. `0^0` and a negative base raised to a non-integer exponent are domain errors; zero raised to a negative exponent is division by zero.

Arithmetic, square roots, logarithms, and exponentials use a 50-significant-digit Decimal context. Trigonometric functions use binary64 approximations formatted to about 15 significant digits, with arguments limited to an absolute value of `1e6`. Extremely small trigonometric arguments or results that cannot be represented safely are rejected. `tan(x)` returns a domain error in the near-pole region where `abs(cos(x)) <= 1e-9`. The absolute argument for `exp(x)` is limited to 23025, and its result is still checked against the numerical range.

Results are returned as strings. Fixed-point output is retained when it fits within 200 characters; longer values use compact scientific notation. The final result is limited to 200 characters. Rounded scientific-calculator results do not use the `≈` marker reserved for unit conversions.

### Integer-base conversion

The API supports conversions between bases 2, 8, 10, and 16. Inputs may contain one leading `+` or `-`, surrounding whitespace, and leading zeros. Hexadecimal input is case-insensitive; output uses uppercase `A–F`. Conversion uses Python integer arithmetic, avoiding floating-point precision loss for large integers.

The `0b`, `0o`, and `0x` prefixes, fractions, scientific notation, underscores, internal spaces, and non-ASCII digits are not accepted. The original input is limited to 400 characters, and the result is limited to 200 characters. For example, decimal `255` converts to hexadecimal `FF`, and binary `11111111` converts to octal `377`.

### Unit conversion

Unit conversion includes 28 units across six categories: length, mass, area, volume, time, and temperature. Source and target units must belong to the same category. Unit IDs are used in API requests; symbols are used for display.

| Category | Unit ID | Symbol | Name |
| --- | --- | --- | --- |
| Length `length` | `nm` | nm | Nanometre |
| Length `length` | `um` | μm | Micrometre |
| Length `length` | `mm` | mm | Millimetre |
| Length `length` | `cm` | cm | Centimetre |
| Length `length` | `m` | m | Metre |
| Length `length` | `km` | km | Kilometre |
| Mass `mass` | `mg` | mg | Milligram |
| Mass `mass` | `g` | g | Gram |
| Mass `mass` | `kg` | kg | Kilogram |
| Mass `mass` | `t` | t | Tonne |
| Area `area` | `mm2` | mm² | Square millimetre |
| Area `area` | `cm2` | cm² | Square centimetre |
| Area `area` | `m2` | m² | Square metre |
| Area `area` | `ha` | ha | Hectare |
| Area `area` | `km2` | km² | Square kilometre |
| Volume `volume` | `ml` | mL | Millilitre |
| Volume `volume` | `cm3` | cm³ | Cubic centimetre |
| Volume `volume` | `l` | L | Litre |
| Volume `volume` | `dm3` | dm³ | Cubic decimetre |
| Volume `volume` | `m3` | m³ | Cubic metre |
| Time `time` | `ms` | ms | Millisecond |
| Time `time` | `s` | s | Second |
| Time `time` | `min` | min | Minute |
| Time `time` | `h` | h | Hour |
| Time `time` | `d` | d | Day |
| Temperature `temperature` | `c` | °C | Celsius |
| Temperature `temperature` | `f` | °F | Fahrenheit |
| Temperature `temperature` | `k` | K | Kelvin |

Values must be sent as strings. ASCII decimal and scientific notation are accepted, including `0.1`, `.5`, and `1.2e-3`; arithmetic expressions, `NaN`, and `Infinity` are not accepted. Inputs are limited to 100 characters and 50 significant digits after removing leading and trailing zeros. The scientific-notation exponent is limited to an absolute value of 10000; nonzero inputs and results must have an adjusted exponent in `[-10000, 10000]`.

The backend converts Decimal input into a Fraction and performs exact rational scale and temperature-offset arithmetic. It rounds only once, at the end, to 50 significant digits using `ROUND_HALF_EVEN`. If rounding loses precision, the result starts with `≈`. For example, converting `1 s` to minutes returns `≈0.016666666666666666666666666666666666666666666666667`. Fixed-point numerical output is retained when its length is at most 80 characters; otherwise scientific notation is used. The complete result is limited to 200 characters.

Temperature uses Kelvin as its reference. Inputs below absolute zero are rejected: the boundaries are `-273.15 °C`, `-459.67 °F`, and `0 K`. Names, conversion relationships, and minimum temperatures come from the same backend catalog and are exposed to the frontend through the options endpoint.

## Directory guide

| Path | Role |
| --- | --- |
| `app/main.py` | FastAPI application, CORS, endpoint handlers, shared history saving, and startup table creation |
| `app/calculator.py` | Recursive-descent parser for bounded scientific expressions |
| `app/conversions.py` | Base conversion, unit catalog, exact unit conversion, and result formatting |
| `app/database.py` | SQLAlchemy engine/session setup and PostgreSQL URL normalization |
| `app/models.py` | `calculation_history` SQLAlchemy model |
| `app/init_db.py` | One-shot command that creates database tables |
| `tests/` | Parser, conversion, database, and API tests |
| `.env.example` | Safe local configuration template; copy it to `.env` and fill in actual values |
| `codestyle.md` | Python code style |

## Requirements

- Python 3.11 or newer.
- `pip`.
- A running PostgreSQL database for local production-like use; Neon is also suitable.

Tests use in-memory SQLite. When `DATABASE_URL` is not configured, the application falls back to a local SQLite file for quick testing. The deployed application uses PostgreSQL.

## Local setup with PostgreSQL

Run the following commands from this backend repository's root directory.

1. Install and start PostgreSQL. On macOS with Homebrew, typical commands are `brew install postgresql@16` and `brew services start postgresql@16`. On Ubuntu/Debian, install the `postgresql` package and start its system service. Use your operating system's PostgreSQL package manager when these examples do not apply.

2. Create a database and user, for example a database named `calculator` owned by `calculator_user`. Open an administrator session, for example `psql -d postgres` after a Homebrew installation or `sudo -u postgres psql` on Ubuntu/Debian. If Homebrew's `psql` is not on `PATH`, use the binary in its installation directory. Choose your own password and run:

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

5. Edit `.env` with an actual local PostgreSQL URL, using the password selected in step 2. Both `postgresql://...` and `postgresql+psycopg://...` are accepted; the application normalizes the first form for psycopg 3. Set `CORS_ORIGINS` to the frontend origins, separated by commas:

   ```dotenv
   DATABASE_URL='postgresql+psycopg://calculator_user:password@localhost:5432/calculator'
   CORS_ORIGINS='http://localhost:5173'
   ```

6. Optionally initialize the table explicitly. `python -m app.init_db` reads `DATABASE_URL` from the process environment, so export the values from your own `.env` first. Keep values quoted, especially if a URL contains `&`:

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

The API is available at [http://localhost:8000](http://localhost:8000). [http://localhost:8000/docs](http://localhost:8000/docs) provides FastAPI's interactive documentation. The application also creates missing tables during startup. For a quick test-only run without `DATABASE_URL`, the code uses a local `calculator.db` file; this fallback does not replace PostgreSQL for deployment.

## API contract

Requests and responses use JSON. IDs and timestamps below illustrate the format; actual values are generated by the database. A successful calculation or conversion returns `200 OK` and saves one history row. Failed requests do not save history.

### `GET /api/health`

No request body is needed. Returns `200 OK` when the service is running:

```json
{"status":"ok"}
```

### `POST /api/calculate`

`expression` must be a non-empty string of at most 500 characters. Example request:

```json
{"expression":"(1+2)*3"}
```

Successful response:

```json
{
  "success": true,
  "id": 1,
  "expression": "(1+2)*3",
  "result": "9",
  "created_at": "2026-10-06T10:00:00+00:00"
}
```

Scientific expressions such as `sqrt(9)+2^3`, `sin(pi/2)`, and `ln(e)` are also accepted.

### `GET /api/convert/options`

No request body is needed. Returns `200 OK` with `bases` and `categories`. Base options provide IDs, allowed digits, and examples. Category and unit names contain `zh` and `en`. Units also include a display symbol, conversion relationship, and minimum temperature. This excerpt shows one unit in one category; the actual response includes all six categories and all 28 units listed above:

```json
{
  "bases": [
    {"id": 2, "digits": "0–1", "example": "11111111"},
    {"id": 8, "digits": "0–7", "example": "377"},
    {"id": 10, "digits": "0–9", "example": "255"},
    {"id": 16, "digits": "0–9, A–F", "example": "FF"}
  ],
  "categories": [
    {
      "id": "length",
      "name": {"zh": "长度", "en": "Length"},
      "reference": "m",
      "units": [
        {
          "id": "m",
          "symbol": "m",
          "name": {"zh": "米", "en": "Metre"},
          "relation": "1 m = 1 m",
          "minimum": null
        }
      ]
    }
  ]
}
```

This endpoint does not create history records. `minimum` is `null` for non-temperature units; temperature units provide the absolute-zero boundary as a numerical string.

### `POST /api/convert/base`

`value` must be a non-empty string of at most 400 characters. `from_base` and `to_base` must be integers: `2`, `8`, `10`, or `16`. Example request:

```json
{"value":"255","from_base":10,"to_base":16}
```

Successful response:

```json
{
  "success": true,
  "id": 2,
  "expression": "BASE 255 (10) → (16)",
  "result": "FF",
  "created_at": "2026-10-06T10:01:00+00:00"
}
```

### `POST /api/convert/unit`

`category` is one of `length`, `mass`, `area`, `volume`, `time`, or `temperature`. `value` must be a non-empty string of at most 100 characters. `from_unit` and `to_unit` are unit IDs from that category, each at most 8 characters. Example request:

```json
{"category":"length","value":"100","from_unit":"cm","to_unit":"m"}
```

Successful response:

```json
{
  "success": true,
  "id": 3,
  "expression": "UNIT 100 cm → m",
  "result": "1",
  "created_at": "2026-10-06T10:02:00+00:00"
}
```

`result` may include `≈` and should be displayed as a formatted string.

### `GET /api/history`

No request body is needed. Returns `200 OK` and an array of saved records, ordered by `created_at` descending and then `id` descending:

```json
[
  {
    "id": 3,
    "expression": "UNIT 100 cm → m",
    "result": "1",
    "created_at": "2026-10-06T10:02:00+00:00"
  },
  {
    "id": 2,
    "expression": "BASE 255 (10) → (16)",
    "result": "FF",
    "created_at": "2026-10-06T10:01:00+00:00"
  },
  {
    "id": 1,
    "expression": "(1+2)*3",
    "result": "9",
    "created_at": "2026-10-06T10:00:00+00:00"
  }
]
```

An empty history returns `[]`. The endpoint returns the complete history; there is currently no server-side pagination, search, or user isolation.

### `DELETE /api/history/{id}`

For example, `DELETE /api/history/3` needs no request body. A successful deletion returns `204 No Content`. A missing record returns `404`:

```json
{
  "success": false,
  "code": "NOT_FOUND",
  "message": {"zh":"记录不存在","en":"Record not found"}
}
```

### Error responses

Business validation failures return `400` with a stable error code and bilingual message. For example, an invalid expression returns:

```json
{
  "success": false,
  "code": "INVALID_EXPRESSION",
  "message": {"zh":"表达式无效","en":"Invalid expression"}
}
```

| Error code | Meaning |
| --- | --- |
| `INVALID_EXPRESSION` | Unsupported characters, unknown names, malformed syntax, or excessive structural depth |
| `DIVISION_BY_ZERO` | A zero divisor or zero raised to a negative exponent |
| `DOMAIN_ERROR` | Outside a function or power domain, such as `sqrt(-1)`, `ln(0)`, or `0^0` |
| `RESULT_OUT_OF_RANGE` | A value, intermediate value, argument, or output length exceeds a protected limit |
| `INVALID_BASE_NUMBER` | An invalid base integer or unsupported base |
| `INVALID_UNIT_VALUE` | An invalid unit-value format or too many significant digits |
| `INVALID_UNIT_PAIR` | The source or target unit does not belong to the selected category |
| `TEMPERATURE_BELOW_ABSOLUTE_ZERO` | Temperature is below absolute zero |

Missing fields, invalid field types, empty strings, overlong fields, and invalid category values are rejected by FastAPI/Pydantic with `422` and its standard `detail` validation response. Conversion values strictly require strings, and base IDs strictly require integers; booleans and string base IDs are not accepted. Deleting a missing record returns `404 NOT_FOUND`. None of these failures create new history records.

## Expression safety and limitations

The service uses a hand-written parser and a fixed whitelist. It does not call `eval`, execute shell commands, or interpret arbitrary Python. Attribute access, strings, commas, imports, unknown names, and other unsupported characters are rejected. Results are normalized strings rather than JSON floating-point numbers, preserving their representation.

This course project has no login or user isolation: all visitors share the same history and can delete its records. CORS controls permitted browser origins; it is not user authentication.

## Database design and Neon configuration

Calculations and conversions share the `calculation_history` table:

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | `Integer` | Primary key |
| `expression` | `String(500)` | Non-null expression or conversion description prefixed with `BASE` / `UNIT` |
| `result` | `String(200)` | Non-null formatted result string |
| `created_at` | `DateTime(timezone=True)` | Non-null timestamp, defaulting to the UTC creation time |

1. Create a Neon project and select its database and database user.
2. Copy the PostgreSQL connection string from Neon's Connect panel. Preserve SSL options such as `sslmode=require`; do not use an HTTP dashboard URL instead.
3. Store the complete string as Render's `DATABASE_URL`. The code accepts Neon's `postgresql://` prefix and converts it to the SQLAlchemy psycopg dialect.
4. For a local run against Neon, put the connection string in `.env` as a quoted value and use the initialization/start commands above.

## Deploying the backend on Render

Create a Render Web Service connected to this backend repository. Leave the Root Directory empty because `requirements.txt` and `app/` are at the repository root.

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- `DATABASE_URL`: the complete Neon PostgreSQL connection string.
- `CORS_ORIGINS`: `https://832402220-calculator-frontend.vercel.app`.

Render provides `$PORT`. The application creates missing tables during startup, so the free service does not require a service shell to initialize the schema. To initialize it explicitly, export the Neon `DATABASE_URL` in a local virtual environment and run:

```bash
python -m app.init_db
```

Do not commit `.env` or database credentials. Only the safe `.env.example` template belongs in the repository. For this assignment, keep the frontend and backend repositories separate and public so the teacher can inspect the source, README, and `codestyle.md`.

## Tests

With the virtual environment active, run:

```bash
pytest
```

The tests cover precedence, parentheses, unary signs, decimal and scientific calculations, fixed scientific functions, malformed syntax, domain and range errors, division by zero, base conversions, the unit catalog and conversions, absolute zero, rounding and the `≈` marker, database URL normalization, reconnecting after an idle connection closes, and the health/calculate/conversion/history/delete API flow.

API tests use an in-memory SQLite database; the connection recovery test uses a temporary SQLite file. Tests do not change a local or deployed PostgreSQL database.

## Assignment acceptance checklist

- `GET /api/health` returns `200` and `{"status":"ok"}`.
- The frontend displays `7` for `1+2*3` and `11` for `sqrt(9)+2^3`.
- Decimal `255` converts to hexadecimal `FF`; `100 cm` converts to `1 m`.
- Successful calculations and conversions appear in history, remain available after a page reload, and can be deleted individually.
- `1/0`, `sqrt(-1)`, invalid base digits, and temperatures below absolute zero produce controlled errors.
- Arbitrary code input such as `__import__("os")` is rejected by the parser.
- The frontend origin is included in `CORS_ORIGINS`.
- After inactivity, wait for the health endpoint to respond, then retry the request.
- Both public repositories contain a README and `codestyle.md`, with no secrets or `.env` files.
