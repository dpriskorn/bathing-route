set allow-duplicate-recipes

install:
    cd backend && uv sync --extra dev
    cd frontend && npm install --legacy-peer-deps

api:
    cd backend && PYTHONPATH=src uv run uvicorn bathing_route.main:app --reload --port 8000

vite:
    cd frontend && npm run dev

be-lint:
    cd backend && uv run ruff check src/bathing_route && uv run mypy src/bathing_route && python3 ../scripts/check_file_lengths.py

fe-lint:
    cd frontend && npx vue-tsc --noEmit

be-test:
    cd backend && PYTHONPATH=src uv run pytest --cov=src/bathing_route --cov-fail-under=80 -v -x

fe-test:
    cd frontend && npm run test:run

test-all: be-test fe-test
