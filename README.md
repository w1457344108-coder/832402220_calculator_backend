# 832402220 计算器后端

[简体中文](README.md) | [English](README.en.md)

本项目是前后端分离计算器的 FastAPI 后端。浏览器将表达式或换算参数发送到 API，由后端完成校验、科学计算、进制转换或单位换算，并将成功结果保存到 PostgreSQL。前端和后端分别存放在独立的公开 GitHub 仓库中。

## 在线服务

- API 地址：[Render 后端](https://eight32402220-calculator-backend.onrender.com)
- 健康检查：[GET /api/health](https://eight32402220-calculator-backend.onrender.com/api/health)
- 接口文档：[FastAPI /docs](https://eight32402220-calculator-backend.onrender.com/docs)
- 前端：[Vercel 计算器](https://832402220-calculator-frontend.vercel.app)
- 前端仓库：[832402220_calculator_frontend](https://github.com/w1457344108-coder/832402220_calculator_frontend)
- 后端仓库：[832402220_calculator_backend](https://github.com/w1457344108-coder/832402220_calculator_backend)
- 代码规范：[codestyle.md](codestyle.md)

后端部署在 Render，数据库使用 Neon PostgreSQL。Render 免费服务闲置后可能休眠，因此长时间未访问后的首次请求可能需要较长时间唤醒服务。SQLAlchemy 在复用连接前检查连接状态；如果 Neon 已关闭空闲连接，后端会替换连接后再执行查询。

## 系统架构

```text
Vue 3 + Vite（Vercel）
          │ HTTPS / JSON
          ▼
FastAPI（Render）
          │ SQLAlchemy + psycopg
          ▼
Neon PostgreSQL
```

前端不直接连接 PostgreSQL。后端负责表达式解析、计算与换算、请求校验、CORS 和持久化。科学计算、进制转换和单位换算的成功记录共用 `calculation_history` 表，可以通过相同的历史查询和删除接口访问；重新加载页面后，前端从 API 获取数据库中保存的历史。

## 功能与精度

### 算术和科学计算

支持十进制数、小数、科学记数法（例如 `1.2e-3`）、空白字符、括号、一元正负号，以及二元 `+ - * / ^`。乘方 `^` 使用右结合规则，例如 `2^3^2` 按 `2^(3^2)` 计算。支持常量 `pi`、`π` 和 `e`，以及以下固定单参数函数：

| 函数 | 含义 | 输入要求 |
| --- | --- | --- |
| `sin(x)` | 正弦 | 弧度 |
| `cos(x)` | 余弦 | 弧度 |
| `tan(x)` | 正切 | 弧度，拒绝接近极点的数值区域 |
| `sqrt(x)` | 平方根 | `x >= 0` |
| `ln(x)` | 自然对数 | `x > 0` |
| `log10(x)` | 常用对数 | `x > 0` |
| `exp(x)` | 自然指数 | 在受保护的数值范围内 |

前端显示的 `×` 和 `÷` 在提交给 API 前转换为 `*` 和 `/`。函数名称使用表中列出的形式，函数参数需要括号；不支持隐式乘法、多参数函数或任意函数调用。

解析器限制表达式最多 500 个字符，共享结构递归预算为 32。非零数字、运算中间值和结果的十进制调整后指数 `Decimal.adjusted()` 必须在 `[-10000, 10000]` 内；零可以使用。科学记数法字面量中 `e` / `E` 后的指数绝对值也不超过 10000，零同样受此限制。乘方的指数绝对值不超过 10000。`0^0` 和负底数的非整数次幂属于定义域错误；零的负次幂属于除零错误。

普通算术、平方根、对数和指数函数使用 50 位有效数字的 Decimal 上下文。三角函数使用 binary64 浮点近似，输出约 15 位有效数字，角度绝对值限制为 `1e6`；不能安全表示的极小三角参数或结果会被拒绝。`tan(x)` 在 `abs(cos(x)) <= 1e-9` 的近极点区域返回定义域错误。`exp(x)` 的参数绝对值限制为 23025，并继续检查结果范围。

结果以字符串返回。定点形式不超过 200 个字符时保留定点输出，更长的值使用紧凑科学记数法，最终结果不超过 200 个字符。科学计算的舍入结果不使用单位换算专属的 `≈` 标记。

### 进制转换

支持二、八、十、十六进制之间的整数转换。输入允许一个前导 `+` 或 `-`、首尾空白和前导零；十六进制字母大小写均可，输出使用大写 `A–F`。转换使用 Python 整数运算，避免经过浮点数造成的大整数精度损失。

不接受 `0b`、`0o`、`0x` 前缀、小数、科学记数法、下划线、内部空格或非 ASCII 数字。原始输入最多 400 个字符，转换结果最多 200 个字符。例如十进制 `255` 转为十六进制得到 `FF`，二进制 `11111111` 转为八进制得到 `377`。

### 单位换算

支持长度、质量、面积、体积、时间和温度六类共 28 种单位，只能在同一类别内换算。下表中的单位 ID 用于 API，符号用于界面显示。

| 类别 | 单位 ID | 符号 | 名称 |
| --- | --- | --- | --- |
| 长度 `length` | `nm` | nm | 纳米 |
| 长度 `length` | `um` | μm | 微米 |
| 长度 `length` | `mm` | mm | 毫米 |
| 长度 `length` | `cm` | cm | 厘米 |
| 长度 `length` | `m` | m | 米 |
| 长度 `length` | `km` | km | 千米 |
| 质量 `mass` | `mg` | mg | 毫克 |
| 质量 `mass` | `g` | g | 克 |
| 质量 `mass` | `kg` | kg | 千克 |
| 质量 `mass` | `t` | t | 公吨 |
| 面积 `area` | `mm2` | mm² | 平方毫米 |
| 面积 `area` | `cm2` | cm² | 平方厘米 |
| 面积 `area` | `m2` | m² | 平方米 |
| 面积 `area` | `ha` | ha | 公顷 |
| 面积 `area` | `km2` | km² | 平方千米 |
| 体积 `volume` | `ml` | mL | 毫升 |
| 体积 `volume` | `cm3` | cm³ | 立方厘米 |
| 体积 `volume` | `l` | L | 升 |
| 体积 `volume` | `dm3` | dm³ | 立方分米 |
| 体积 `volume` | `m3` | m³ | 立方米 |
| 时间 `time` | `ms` | ms | 毫秒 |
| 时间 `time` | `s` | s | 秒 |
| 时间 `time` | `min` | min | 分钟 |
| 时间 `time` | `h` | h | 小时 |
| 时间 `time` | `d` | d | 天 |
| 温度 `temperature` | `c` | °C | 摄氏度 |
| 温度 `temperature` | `f` | °F | 华氏度 |
| 温度 `temperature` | `k` | K | 开尔文 |

单位数值必须以字符串提交，接受 ASCII 十进制数和科学记数法，例如 `0.1`、`.5`、`1.2e-3`；不接受算术表达式、`NaN` 或 `Infinity`。输入最多 100 个字符，去除首尾零后最多 50 位有效数字；科学记数法指数的绝对值不超过 10000，非零输入和结果的调整后指数必须在 `[-10000, 10000]` 内。

后端先将 Decimal 输入转换为 Fraction，通过精确有理数完成比例和温度偏移换算，最后只舍入一次到 50 位有效数字，使用 `ROUND_HALF_EVEN`。如果舍入损失精度，结果前添加 `≈`；例如 `1 s` 转为分钟得到 `≈0.016666666666666666666666666666666666666666666666667`。定点数值长度不超过 80 时保留定点输出，否则使用科学记数法；整个结果最多 200 个字符。

温度使用开尔文作为参考值，低于绝对零度的输入会被拒绝。边界分别为 `-273.15 °C`、`-459.67 °F` 和 `0 K`。单位名称、换算关系和温度下限来自同一份后端目录，通过选项接口提供给前端。

## 目录说明

| 路径 | 作用 |
| --- | --- |
| `app/main.py` | FastAPI 应用、CORS、接口处理、统一历史保存和启动建表 |
| `app/calculator.py` | 受限科学表达式的递归下降解析器 |
| `app/conversions.py` | 进制转换、单位目录、精确单位换算和结果格式化 |
| `app/database.py` | SQLAlchemy 引擎、会话与 PostgreSQL URL 规范化 |
| `app/models.py` | `calculation_history` 数据模型 |
| `app/init_db.py` | 单独创建数据库表的命令 |
| `tests/` | 解析器、换算、数据库和 API 测试 |
| `.env.example` | 本地配置模板，复制为 `.env` 后填写实际值 |
| `codestyle.md` | Python 代码规范 |

## 运行环境

- Python 3.11 或更新版本。
- `pip`。
- 本地正式运行使用 PostgreSQL，也可以连接 Neon。

测试使用内存 SQLite；未配置 `DATABASE_URL` 时应用回退到本地 SQLite 文件，便于快速测试。线上部署使用 PostgreSQL。

## 本地 PostgreSQL 配置与启动

以下命令均从本后端仓库根目录执行。

1. 安装并启动 PostgreSQL。在使用 Homebrew 的 macOS 上，常见命令为 `brew install postgresql@16` 和 `brew services start postgresql@16`；Ubuntu/Debian 可安装 `postgresql` 软件包并启动对应系统服务。其他系统请使用相应的 PostgreSQL 安装方式。

2. 创建数据库和用户，例如由 `calculator_user` 拥有的 `calculator` 数据库。打开管理员会话：Homebrew 环境通常使用 `psql -d postgres`，Ubuntu/Debian 通常使用 `sudo -u postgres psql`。如果 Homebrew 的 `psql` 不在 `PATH` 中，使用安装目录中的程序。选择自己的密码后执行：

   ```sql
   CREATE USER calculator_user WITH PASSWORD 'replace-this-password';
   CREATE DATABASE calculator OWNER calculator_user;
   ```

3. 创建虚拟环境并安装依赖：

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. 创建环境文件：

   ```bash
   cp .env.example .env
   ```

5. 使用第 2 步选择的密码填写实际 PostgreSQL URL。`postgresql://...` 和 `postgresql+psycopg://...` 均可，应用会将前者转换为 psycopg 3 方言。`CORS_ORIGINS` 是以逗号分隔的前端来源：

   ```dotenv
   DATABASE_URL='postgresql+psycopg://calculator_user:password@localhost:5432/calculator'
   CORS_ORIGINS='http://localhost:5173'
   ```

6. 可显式初始化数据表。`python -m app.init_db` 从进程环境读取 `DATABASE_URL`，因此需要先导出自己 `.env` 中的变量。URL 中可能包含 `&`，请保留上述引号：

   ```bash
   set -a
   source .env
   set +a
   python -m app.init_db
   ```

7. 启动 API；Uvicorn 为应用进程加载 `.env`：

   ```bash
   uvicorn --env-file .env app.main:app --reload
   ```

API 默认地址为 [http://localhost:8000](http://localhost:8000)，交互式接口文档位于 [http://localhost:8000/docs](http://localhost:8000/docs)。应用启动时也会创建缺失的数据表。仅进行快速测试且未设置 `DATABASE_URL` 时，代码使用本地 `calculator.db`；这不能替代部署时的 PostgreSQL 配置。

## API 契约

请求和响应均使用 JSON。以下 `id` 和时间仅用于展示格式，实际值由数据库生成。计算和转换成功返回 `200 OK`，并保存一条历史；失败请求不会保存历史。

### `GET /api/health`

无需请求体。服务正常时返回 `200 OK`：

```json
{"status":"ok"}
```

### `POST /api/calculate`

`expression` 是非空字符串，最多 500 个字符。请求示例：

```json
{"expression":"(1+2)*3"}
```

成功响应：

```json
{
  "success": true,
  "id": 1,
  "expression": "(1+2)*3",
  "result": "9",
  "created_at": "2026-10-06T10:00:00+00:00"
}
```

也可以提交科学表达式，例如 `sqrt(9)+2^3`、`sin(pi/2)`、`ln(e)`。

### `GET /api/convert/options`

无需请求体。返回 `200 OK`，包含 `bases` 和 `categories`。进制选项提供 ID、合法数字与示例；类别和单位名称包含 `zh`、`en`，单位还包含显示符号、换算关系和温度下限。下面只展示一个类别中的一个单位；实际响应包含上表全部六个类别和 28 种单位：

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

该接口不创建历史记录。非温度单位的 `minimum` 为 `null`；温度单位提供对应绝对零度的数值字符串。

### `POST /api/convert/base`

`value` 必须是非空字符串，最多 400 个字符；`from_base` 和 `to_base` 必须是整数，支持 `2`、`8`、`10`、`16`。请求示例：

```json
{"value":"255","from_base":10,"to_base":16}
```

成功响应：

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

`category` 为 `length`、`mass`、`area`、`volume`、`time` 或 `temperature`；`value` 为最多 100 个字符的非空字符串。`from_unit`、`to_unit` 为对应类别中的单位 ID，各最多 8 个字符。请求示例：

```json
{"category":"length","value":"100","from_unit":"cm","to_unit":"m"}
```

成功响应：

```json
{
  "success": true,
  "id": 3,
  "expression": "UNIT 100 cm → m",
  "result": "1",
  "created_at": "2026-10-06T10:02:00+00:00"
}
```

`result` 可能带有 `≈`，前端和使用者应将它作为格式化结果字符串显示。

### `GET /api/history`

无需请求体。返回 `200 OK` 和已保存记录数组，按 `created_at` 降序、`id` 降序排列：

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

没有记录时返回 `[]`。接口返回完整历史，当前没有服务端分页、搜索或用户隔离。

### `DELETE /api/history/{id}`

例如 `DELETE /api/history/3`，无需请求体。删除成功返回 `204 No Content`。记录不存在时返回 `404`：

```json
{
  "success": false,
  "code": "NOT_FOUND",
  "message": {"zh":"记录不存在","en":"Record not found"}
}
```

### 错误响应

业务校验失败返回 `400`，响应包含稳定错误码和中英文消息。例如非法表达式：

```json
{
  "success": false,
  "code": "INVALID_EXPRESSION",
  "message": {"zh":"表达式无效","en":"Invalid expression"}
}
```

| 错误码 | 含义 |
| --- | --- |
| `INVALID_EXPRESSION` | 不支持的字符、未知名称、语法错误或结构深度超限 |
| `DIVISION_BY_ZERO` | 除数为零，或零的负次幂 |
| `DOMAIN_ERROR` | 超出函数或乘方定义域，例如 `sqrt(-1)`、`ln(0)`、`0^0` |
| `RESULT_OUT_OF_RANGE` | 数值、中间值、参数或输出长度超过保护范围 |
| `INVALID_BASE_NUMBER` | 不合法的进制整数或不支持的进制 |
| `INVALID_UNIT_VALUE` | 单位数值格式错误或超过有效数字限制 |
| `INVALID_UNIT_PAIR` | 源或目标单位不属于指定类别 |
| `TEMPERATURE_BELOW_ABSOLUTE_ZERO` | 温度低于绝对零度 |

缺少字段、字段类型错误、空字符串、字段过长或无效的类别值由 FastAPI/Pydantic 返回 `422` 和标准 `detail` 校验响应。转换数值严格使用字符串，进制严格使用整数，不接受布尔值或字符串进制 ID。删除不存在的记录返回 `404 NOT_FOUND`。所有上述失败均不会产生新的历史记录。

## 表达式安全与使用限制

服务使用手写解析器和固定白名单，不调用 `eval`、不执行 shell，也不解释任意 Python。属性访问、字符串、逗号、导入语句、未知名称和其他不支持的字符会被拒绝。所有结果以字符串返回，避免 JSON 浮点数丢失表示精度。

本课程项目没有登录和用户隔离功能：所有访问者共享同一份历史，并可以删除记录。CORS 控制允许发起请求的浏览器来源，不是用户身份认证。

## 数据库设计与 Neon 配置

`calculation_history` 是计算和换算共用的数据表：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `Integer` | 主键 |
| `expression` | `String(500)` | 表达式或带 `BASE` / `UNIT` 前缀的换算描述，非空 |
| `result` | `String(200)` | 字符串结果，非空 |
| `created_at` | `DateTime(timezone=True)` | 默认创建 UTC 时间，非空 |

1. 创建 Neon 项目，选择数据库和数据库用户。
2. 从 Neon 的 Connect 面板复制 PostgreSQL 连接串，保留 `sslmode=require` 等 SSL 选项，不要使用 HTTP 控制台链接代替。
3. 将完整连接串设置为 Render 的 `DATABASE_URL`。应用接受 Neon 的 `postgresql://` 前缀，并转换为 SQLAlchemy 的 psycopg 方言。
4. 本地连接 Neon 时，将连接串作为带引号的值放入 `.env`，使用前面的初始化和启动命令。

## Render 部署

创建连接本后端仓库的 Render Web Service。`requirements.txt` 和 `app/` 位于仓库根目录，因此 Root Directory 留空。

- Build command：`pip install -r requirements.txt`
- Start command：`uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- `DATABASE_URL`：Neon PostgreSQL 完整连接串。
- `CORS_ORIGINS`：`https://832402220-calculator-frontend.vercel.app`。

Render 提供 `$PORT`。应用启动时创建缺失的数据表，免费服务不需要使用服务 shell 初始化；若要手动初始化，在本地虚拟环境导出 Neon `DATABASE_URL` 后执行：

```bash
python -m app.init_db
```

不要提交 `.env` 或数据库凭据，仓库仅保留安全模板 `.env.example`。本作业前后端仓库保持分离且公开，以便教师检查源码、README 和 `codestyle.md`。

## 测试

在虚拟环境激活后执行：

```bash
pytest
```

测试覆盖优先级、括号、一元符号、小数与科学计算、固定科学函数、语法错误、定义域与范围错误、除零、进制转换、单位目录与换算、绝对零度、舍入与 `≈` 标记、数据库 URL 规范化、空闲连接恢复，以及健康检查、计算、换算、历史查询和删除 API 流程。

API 测试使用内存 SQLite；连接恢复测试使用临时 SQLite 文件。测试不修改本地或线上 PostgreSQL 数据库。

## 作业验收检查

- `GET /api/health` 返回 `200` 和 `{"status":"ok"}`。
- 前端提交 `1+2*3` 后显示 `7`，提交 `sqrt(9)+2^3` 后显示 `11`。
- 十进制 `255` 转十六进制得到 `FF`，`100 cm` 转米得到 `1`。
- 成功的计算与换算出现在历史接口中，刷新页面仍可加载，并能删除指定记录。
- `1/0`、`sqrt(-1)`、非法进制数字和低于绝对零度的温度显示可控错误。
- `__import__("os")` 等任意代码输入被解析器拒绝。
- 前端来源包含在 `CORS_ORIGINS` 中。
- 服务长时间闲置后，等待健康检查响应，再重试请求。
- 两个公开仓库分别包含 README 和 `codestyle.md`，不包含密钥或 `.env`。
