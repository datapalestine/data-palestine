# API Guide

## Overview

The Data Palestine API provides free, open access to Palestinian statistical data. No authentication required for read access.

## Base URL

```
https://datapalestine.org/api/v1
```

## Endpoints

- `GET /datasets` — List all datasets
- `GET /datasets/:slug` — Single dataset
- `GET /indicators` — List indicators
- `GET /indicators/:id` — Single indicator
- `GET /observations` — Query observations
- `GET /geographies` — List geographies
- `GET /sources` — List data sources
- `GET /search?q=...` — Full-text search

## Query Parameters

- `page`, `per_page` — Pagination
- `geography` — Filter by geography code
- `from_date`, `to_date` — Time range
- `lang` — Response language (en/ar)

## Rate Limits

- 100 requests per minute per IP (unauthenticated)
