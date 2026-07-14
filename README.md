# Bathing Route

Find EU bathing spots (P9616) along a GPX route from GraphHopper, using Wikidata as the data source.

## Requirements

- Python 3.12
- Node.js 20+
- [uv](https://github.com/astral-sh/uv)
- [Just](https://github.com/casey/just)

## Install

```bash
just install
```

This installs backend dependencies with `uv sync --extra dev` and frontend dependencies with `npm install --legacy-peer-deps`.

## Start

Start both the API and frontend in separate terminals:

```bash
just api   # FastAPI server on http://localhost:8000
just vite  # Vite dev server on http://localhost:5173
```

## Development

### Linting

```bash
just be-lint   # Backend: ruff + mypy + file length check
just fe-lint   # Frontend: vue-tsc
```

### Testing

```bash
just test-all  # Run backend and frontend tests
just be-test   # Backend only (pytest, 80% coverage required)
just fe-test   # Frontend only (vitest)
```

## Architecture

```mermaid
flowchart TD
    subgraph Frontend["Frontend (Vue 3 + Vite)"]
        A[GPX Upload] --> B[POST /api/analyze]
        B --> C[GeoJSON Response]
        C --> D[Filter by Layer]
        D --> E[Display on Map - Leaflet CircleMarkers]
        E --> F[Click Marker]
        F --> G[Show Popup]
        G --> H[fetch /api/wikidata/Q12345/details]
        H --> I[fetch /api/commons-image for thumbnails]
    end

    subgraph Backend["Backend (FastAPI)"]
        B -->|parse GPX + buffer| J[Geo Service]
        J --> K[Filter Spots by Buffer]
        K --> L[Return GeoJSON - bathing_spots + route + buffer]

        H --> M[Check wikidata.db]
        M -->|miss| N[Wikidata REST API v1]
        N --> O[/v1/entities/items/id/labels/lang]
        N --> P[/v1/entities/items/id/statements property=P18]
        N --> Q[/v1/entities/items/id/sitelinks]
        M -->|hit| R[Return Cached]
        N --> S[wikidata.db 7-day TTL - label_cache wikidata_details_cache commons_cache]
        S --> R

        I --> T[Commons API Proxy]
        T --> U[wikidata.db commons_cache 7-day TTL]
    end

    subgraph Wikidata["Wikidata"]
        O & P & Q --> V[Wikidata REST API]
        V --> W[(SPARQL WDQS/QLever)]
        W --> X[sites.db 24h TTL - bathing_spot_cache]
    end

    X -.->|load_bathing_spots_all ENHANCED_QUERY| K
```

### Backend Details

- **Framework**: FastAPI + uvicorn
- **GPX parsing**: gpxpy
- **Geo buffering**: shapely + pyproj
- **SPARQL backends**: Wikidata Query Service (default) or QLever
- **Bathing spots cache**: SQLite (aiosqlite), 24h TTL, stored at `backend/sites.db`
- **Labels/details cache**: SQLite (aiosqlite), 7-day TTL, stored at `backend/wikidata.db`
- **Label source**: Wikidata REST API (labels never come from SPARQL)

### Frontend Details

- **Framework**: Vue 3 + Vite + TypeScript
- **Map**: Leaflet (native, not vue-leaflet)
- **UI**: Bootstrap 5 + vue-i18n (English / Swedish)
- **State**: Composables (`useRoute.ts`)
- **Image handling**: Commons images proxied through backend to avoid CORS

## Environment

No environment variables are required. The app is configured to work out of the box with the default WDQS backend.
