# Contributing to Data Palestine

Thank you for your interest in contributing to Data Palestine! This project is open source and we welcome contributions from everyone.

## How to Contribute

### Reporting Issues
- **Data accuracy**: Use the [Data Correction template](https://github.com/datapalestine/data-palestine/issues/new?template=data-correction.md)
- **Bugs**: Use the [Bug Report template](https://github.com/datapalestine/data-palestine/issues/new?template=bug-report.md)
- **Features**: Use the [Feature Request template](https://github.com/datapalestine/data-palestine/issues/new?template=feature-request.md)

### Code Contributions
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Run tests: `cd apps/api && pytest` and `cd apps/web && npm run lint`
5. Commit with a clear message: `git commit -m "feat: add labor force dataset pipeline"`
6. Push and open a pull request

### Commit Message Convention
We follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` new feature
- `fix:` bug fix
- `data:` data pipeline additions or corrections
- `docs:` documentation changes
- `style:` formatting, no code change
- `refactor:` code restructuring
- `test:` adding tests
- `chore:` maintenance tasks

### Adding a New Data Pipeline
1. Create a new file in `packages/pipeline/pipeline/sources/` (follow `worldbank.py` or `techforpalestine.py`)
2. Every observation must link to a `source_document` with the original URL
3. Use the existing database schema, don't modify tables
4. Test locally and run `python scripts/verify_accuracy.py` to confirm data integrity
5. Document the data source in `docs/DATA_SOURCES.md`

### Translation Contributions
- Translation files are in `apps/web/messages/`
- We currently support English (`en.json`) and Arabic (`ar.json`)
- All user-facing text must be in both languages

## Code Standards

### Python (API + Pipelines)
- Python 3.11+
- Formatted with `ruff format`
- Linted with `ruff check`
- Type hints on all function signatures
- Async by default for I/O operations

### TypeScript (Frontend)
- TypeScript strict mode
- ESLint + Prettier
- Functional components with hooks
- Server Components by default, Client Components only when needed

## Data Standards

- **Attribution**: Every data point must link to its original source
- **No editorializing**: We present data, not opinions
- **Transparency**: Document methodology, limitations, and known issues
- **Privacy**: Never include personally identifiable information without explicit ethical review

## Code of Conduct

Be respectful, constructive, and inclusive. We are building a tool that serves all people who care about accurate Palestinian data. Discrimination, harassment, and bad-faith engagement will not be tolerated.

## Questions?

Open an issue or email info@datapalestine.org.
