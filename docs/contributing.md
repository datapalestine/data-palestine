# Contributing to Data Palestine

Thank you for your interest in contributing to Data Palestine! This guide will help you get started.

## Ways to Contribute

### Data Pipelines
The highest-impact contribution is adding new data sources. Each pipeline lives in `packages/pipeline/sources/` and follows the collect → extract → transform → load pattern defined in `pipeline/base.py`.

To add a new data source:
1. Create a new file in `packages/pipeline/sources/`
2. Implement the `BasePipeline` interface
3. Add test fixtures in `packages/pipeline/tests/fixtures/`
4. Write tests for each pipeline stage
5. Document the source in the methodology page

### Translations
Our Arabic translations are in `apps/web/messages/ar.json`. If you spot errors or can improve the translations, please submit a PR.

### Visualizations
We use D3.js for charts and Mapbox GL JS for maps. New chart types or improved visualizations are welcome — see `apps/web/components/data/` for existing components.

### Bug Reports & Feature Requests
Open an issue on GitHub. For bugs, include: steps to reproduce, expected behavior, actual behavior, and screenshots if applicable.

## Development Setup

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- Node.js 20+

### Getting Started

```bash
# Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/data-palestine.git
cd data-palestine

# Copy environment variables
cp .env.example .env

# Start infrastructure
docker compose up -d

# API setup
cd apps/api
pip install -e ".[dev]"
uvicorn app.main:app --reload

# Frontend setup (separate terminal)
cd apps/web
npm install
npm run dev
```

### Running Tests

```bash
# API tests
cd apps/api && pytest -v

# Pipeline tests
cd packages/pipeline && pytest -v

# Frontend type check
cd apps/web && npx tsc --noEmit
```

### Linting

```bash
# Python
ruff check . && ruff format .

# TypeScript
npx biome check .
```

## Git Workflow

1. Create a branch from `main`: `feat/add-health-pipeline`, `fix/chart-rtl-bug`, etc.
2. Use conventional commits: `feat:`, `fix:`, `data:`, `docs:`, `chore:`
3. Keep PRs focused — one feature or fix per PR
4. Include tests for new functionality
5. Update documentation if needed

## Code of Conduct

Be respectful, constructive, and collaborative. We are building a tool to serve the Palestinian people — approach this work with the seriousness and care it deserves.

## Data Ethics

When contributing data pipelines or handling data:
- **Always attribute sources** — Every data point must link to its original source
- **Never fabricate data** — If data is unavailable, mark it as missing
- **Handle sensitive data carefully** — Casualty and conflict data represents human lives
- **Protect privacy** — Never include personally identifiable information
- **Be transparent about limitations** — Document what the data does and does not show

## Questions?

- Open a GitHub Discussion for general questions
- Email info@datapalestine.org for partnership inquiries
