# Data Palestine

**The open data platform for Palestinian statistical, humanitarian, and socioeconomic data.**

[![License: MIT](https://img.shields.io/badge/Code-MIT-green.svg)](LICENSE)
[![License: CC BY 4.0](https://img.shields.io/badge/Data-CC%20BY%204.0-blue.svg)](https://creativecommons.org/licenses/by/4.0/)

---

Data Palestine aggregates and modernizes data from PCBS, OCHA, UNRWA, World Bank, B'Tselem, and other sources. Transforming scattered PDFs, outdated interfaces, and siloed databases into a unified, searchable, API-driven platform.

## Links

- **Website:** [datapalestine.org](https://datapalestine.org)
- **API:** [datapalestine.org/api/v1](https://datapalestine.org/api/v1)
- **API Docs:** [datapalestine.org/en/developers](https://datapalestine.org/en/developers)

## Features

- **Comprehensive Data Catalog**: Population, economy, labor, education, health, conflict, displacement, and more
- **Modern REST API**: Programmatic access to all data with filtering, pagination, and bulk export
- **Bilingual**: Full Arabic (RTL) and English support
- **Interactive Visualizations**: Time-series charts, geographic maps, and data tables
- **Open Source**: All code, pipelines, and methodology publicly available
- **Source Transparency**: Every data point traces back to its original source

## Architecture

```
apps/api          → FastAPI (Python) backend serving the REST API
apps/web          → Next.js frontend with bilingual support
packages/db       → PostgreSQL schema with TimescaleDB + PostGIS
packages/pipeline → Data ingestion pipelines (scrapers, transformers)
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- Node.js 20+

### Setup

```bash
# Clone the repository
git clone https://github.com/datapalestine/data-palestine.git
cd data-palestine

# Copy environment variables
cp .env.example .env

# Start infrastructure (PostgreSQL, Redis, Meilisearch, MinIO)
docker compose up -d

# Set up the API
cd apps/api
pip install -e ".[dev]"
uvicorn app.main:app --reload

# Set up the frontend (in another terminal)
cd apps/web
npm install
npm run dev
```

The API will be available at `http://localhost:8000` and the website at `http://localhost:3000`.

## Data Sources

| Source | Coverage | Status |
|--------|----------|--------|
| PCBS | Population, economy, labor, education, health | ✅ Active |
| OCHA oPt | Humanitarian situation, displacement, conflict | ✅ Active |
| World Bank | GDP, poverty, economic indicators | ✅ Active |
| B'Tselem | Casualties, demolitions, prisoner data | ✅ Active |
| UNRWA | Refugee demographics, education, health | 🔄 Planned |
| WHO | Health indicators | 🔄 Planned |

## Contributing

We welcome contributions! See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

Priority areas for contribution:
- **Data pipelines**: Add new data sources or improve existing scrapers
- **Translations**: Improve Arabic translations
- **Visualizations**: Build new chart types and map layers
- **Documentation**: Improve API docs and methodology pages

## License

- **Code:** [MIT License](LICENSE)
- **Data:** [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/) - Data is sourced from publicly available sources. Original data ownership belongs to the respective sources (PCBS, OCHA, etc.). Attribution is required.

## Contact

- **Email:** info@datapalestine.org
- **Twitter/X:** [@DataPalestine](https://twitter.com/DataPalestine)

---

<p align="center">
  <strong>بيانات مفتوحة لفلسطين. مجانية. شفافة. سهلة الوصول.</strong>
<br>
  Open data for Palestine. Free. Transparent. Accessible 
</p>
