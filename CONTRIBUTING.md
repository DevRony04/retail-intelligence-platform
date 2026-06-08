# 🤝 Contributing to Retail Intelligence Platform

Thank you for contributing to the Retail Intelligence Platform! This guide provides all necessary instructions to set up your local development environment, run validation checks, write compliant git commits, and adhere to production safety guidelines.

---

## 🛠️ Local Environment Setup

### 1. Prerequisites
Ensure you have the following installed on your machine:
* Python `3.10` or `3.11` (or Python `3.13` as supported by dependencies)
* Git
* Docker & Docker Compose (optional, for containerized execution)

### 2. Clone the Repository
```bash
git clone https://github.com/DevRony04/retail-intelligence-platform.git
cd retail-intelligence-platform
```

### 3. Establish a Virtual Environment
Configure a python virtual environment to isolate project dependencies:
```bash
# Windows (Command Prompt / PowerShell)
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## ⚙️ Environment Configuration

The application reads configurations from environment variables. Create a local `.env` file in the repository root by copying the example:

```bash
cp .env.example .env
```

### Key Environment Variables

| Variable | Description | Recommended Local Value |
| :--- | :--- | :--- |
| `DATABASE_URL` | SQLAlchemy connection URI. Gracefully falls back to SQLite if empty or local. | `sqlite:///./store_intelligence.db` |
| `APP_ENV` | Running context environment. | `development` |
| `API_HOST` | FastAPI gateway binding address. | `0.0.0.0` |
| `API_PORT` | FastAPI gateway port. | `8000` |
| `API_URL` | Base API ingress URL resolved by dashboard and test assertions. | `http://localhost:8000` |

---

## 🚀 Running the Platform

Run and verify the platform components using the following command sequence:

### 1. Run the Computer Vision & Ingestion Pipeline
To process recorded video clips in `data/` or activate the high-fidelity mock stream generator:
```bash
python run_pipeline.py
```
This writes serialized telemetry events to `outputs/events.jsonl` and initiates database ingestion.

### 2. Launch the FastAPI Backend API
Start the FastAPI server in hot-reload mode for rapid local iteration:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
* **API Documentation:** Visit [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI) or [http://localhost:8000/redoc](http://localhost:8000/redoc) (ReDoc).

### 3. Start the Streamlit Dashboard
```bash
streamlit run dashboard/dashboard.py
```
* **Dashboard Interface:** Access the local control command center at [http://localhost:8501](http://localhost:8501).

---

## 🐳 Docker Workflow

To spin up the entire multi-container stack (PostgreSQL + FastAPI Backend + Streamlit Dashboard) inside Docker:

```bash
# 1. Build and run containers in daemon mode
docker compose up --build -d

# 2. Monitor execution logs
docker compose logs -f

# 3. Stop containers and preserve storage volumes
docker compose down
```

---

## 🧪 Testing & Validation Workflows

Every change must be validated before submitting a Pull Request.

### 1. Run Unit & Integration Tests
Execute the comprehensive test suite with `pytest`:
```bash
pytest -v
```
Ensure all tests in `tests/` pass successfully.

### 2. Execute Acceptance Gate Assertions
Verify endpoint compliance, batch schema processing, and idempotency guarantees using the e2e test suite:
```bash
python assertions.py
```
*If a local server is not active, this script degrades gracefully to run using the FastAPI `TestClient` class.*

---

## 🌿 Git Branch & Contribution Workflow

We enforce standard git branch naming patterns and commit formatting.

### 1. Branch Naming Strategy
Name development branches based on the work scope:
* `feature/` for new docs, tools, or CI setups (e.g., `feature/ci-validation-workflow`)
* `bugfix/` for resolving tests or configuration bugs (e.g., `bugfix/fix-assertions-client-import`)
* `hotfix/` for urgent production-grade patching (e.g., `hotfix/db-pool-leak-mitigation`)
* `docs/` for purely documentation improvements (e.g., `docs/add-contributing-guide`)

### 2. Conventional Commits
Write clean commit messages adhering to [Conventional Commits specifications](https://www.conventionalcommits.org/):

Format: `<type>(<scope>): <short description>`

Common Types:
* `feat`: Introduce a new feature (e.g., `feat(ci): add validation-only github actions workflow`)
* `fix`: Fix a bug or regression (e.g., `fix(tests): resolve deprecated pydantic validator warn`)
* `docs`: Update markdown documentation (e.g., `docs(readme): add contributing guide link`)
* `chore`: Maintenance tasks (e.g., `chore: update gitignore for python 3.13 cache`)

### 3. Pull Request Process
1. Create your branch from `main`.
2. Implement your changes, verifying that no production application logic or DB schemas are modified.
3. Verify that `pytest` and `python assertions.py` both pass locally with zero errors.
4. Push your branch and open a Pull Request against `main`.
5. Ensure the GitHub Actions CI validation workflow compiles successfully.
6. A repository administrator must review and approve the PR before merging.

---

## 🛡️ Production Safety & Security Guidelines

> [!WARNING]
> **Production Code Stability**
> The Retail Intelligence Platform is actively running in production. Modifying application logic, event schemas, API routers, database pool mechanisms, or docker run parameters is strictly forbidden. Limit changes strictly to developer tooling, documentation, and non-invasive CI.

* **No Credentials in Code:** Never commit `.env` files, database keys, or production access links to git.
* **Non-invasive CI:** The GitHub Actions workflow is strictly for validation and testing. Do not add steps that run database migrations, make remote api edits, or trigger automatic deployments.
