# 💸 Expense Tracker API

A RESTful API for tracking personal finances — manage transactions, categories, budgets, and generate financial reports.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Database | [MongoDB](https://www.mongodb.com/) via PyMongo async client |
| Validation | [Pydantic v2](https://docs.pydantic.dev/) |
| Auth | JWT (PyJWT + Argon2 password hashing) |
| Package Manager | [uv](https://docs.astral.sh/uv/) |
| Testing | pytest + FastAPI TestClient |
| Docs | [Scalar](https://scalar.com/) (auto-generated) |

---

## Features

- **Authentication** — Register, login, JWT-protected routes
- **Categories** — Create and manage income/expense categories with icons and colors
- **Transactions** — Full CRUD with category-type validation and pagination
- **Budgets** — Set monthly spending limits per user
- **Reports** — Financial summaries including:
  - Total income, expenses, and net cash flow
  - Savings rate
  - Spending breakdown by category (with percentages)
  - Monthly cash flow trend
  - Top 5 transactions

---

## Project Structure

```
app/
├── auth/           # JWT dependencies
├── config/         # Settings (env vars)
├── database/       # MongoDB connection
├── models/         # Pydantic schemas
├── router/         # API route handlers
└── services/       # Business logic (report generation)
tests/              # 107 tests across all routers
```

---

## Setup

**1. Clone & install dependencies**
```bash
git clone <repo-url>
cd expense-tracker
uv sync
```

**2. Configure environment**

Create a `.env` file in the project root:
```env
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=expense_tracker
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**3. Run the server**
```bash
uv run uvicorn app.main:app --reload
```

**4. View API docs**

Open [http://localhost:8000/scalar](http://localhost:8000/scalar) in your browser.

---

## Running Tests

```bash
uv run pytest tests/ -v
```
