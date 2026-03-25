# Data Palestine — API Reference

Base URL: `https://datapalestine.org/api/v1`

All responses follow this envelope:

```json
{
  "data": <T>,
  "meta": {
    "total": 150,
    "page": 1,
    "per_page": 20,
    "total_pages": 8
  }
}
```

Single-resource responses omit the `meta` field and return `{ "data": <T> }`.

Errors return:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Dataset not found",
    "detail": "No dataset with slug 'xyz' exists"
  }
}
```

---

## Datasets

### List Datasets

```
GET /datasets
```

**Query Parameters:**

| Param       | Type   | Description                                |
|-------------|--------|--------------------------------------------|
| category    | string | Filter by category slug (e.g., "economy")  |
| status      | string | "active", "archived", "draft". Default: "active" |
| search      | string | Full-text search across name + description |
| tag         | string | Filter by tag                              |
| page        | int    | Page number (default: 1)                   |
| per_page    | int    | Results per page (default: 20, max: 100)   |
| sort        | string | "name", "updated", "created". Default: "name" |
| order       | string | "asc" or "desc". Default: "asc"            |
| lang        | string | "en" or "ar". Determines which name/description fields. Default: "en" |

**Response:**

```json
{
  "data": [
    {
      "id": "uuid",
      "slug": "labor-force-survey",
      "name": "Palestinian Labor Force Survey",
      "description": "Quarterly survey covering employment, unemployment...",
      "category": {
        "slug": "economy",
        "name": "Economy & Labor"
      },
      "source": {
        "organization": "Palestinian Central Bureau of Statistics",
        "url": "https://www.pcbs.gov.ps/..."
      },
      "update_frequency": "quarterly",
      "temporal_coverage": {
        "start": "1995-01-01",
        "end": "2025-09-30"
      },
      "geographic_coverage": "governorate",
      "indicator_count": 48,
      "last_updated": "2025-12-15T00:00:00Z",
      "tags": ["employment", "unemployment", "labor", "wages"]
    }
  ],
  "meta": { "total": 23, "page": 1, "per_page": 20, "total_pages": 2 }
}
```

### Get Dataset

```
GET /datasets/{slug}
```

Returns full dataset record including methodology and all associated indicators.


---

## Indicators

### List Indicators

```
GET /indicators
```

**Query Parameters:**

| Param       | Type   | Description                                        |
|-------------|--------|----------------------------------------------------|
| dataset     | string | Filter by dataset slug                             |
| category    | string | Filter by category slug                            |
| geography   | string | Filter by geography code (e.g., "PS-GZA")          |
| search      | string | Full-text search                                   |
| unit        | string | Filter by unit ("percent", "USD", "persons", etc.) |
| dimension   | string | JSON filter on dimensions: `{"gender":"female"}`   |
| page        | int    | Page number                                        |
| per_page    | int    | Results per page                                   |
| lang        | string | "en" or "ar"                                       |

**Response:**

```json
{
  "data": [
    {
      "id": "uuid",
      "code": "LFS_UNEMP_RATE",
      "name": "Unemployment Rate",
      "description": "Share of labor force that is unemployed",
      "dataset": {
        "slug": "labor-force-survey",
        "name": "Palestinian Labor Force Survey"
      },
      "unit": "percent",
      "decimals": 1,
      "dimensions": {
        "gender": "both",
        "age_group": "15+"
      },
      "latest_value": {
        "value": 25.7,
        "time_period": "2025-07-01",
        "geography": "PS"
      }
    }
  ]
}
```

### Get Indicator

```
GET /indicators/{id}
```

Returns indicator with all observations (paginated).


---

## Observations

### Query Observations

The most powerful endpoint — multi-dimensional filtering of data points.

```
GET /observations
```

**Query Parameters:**

| Param         | Type   | Description                                    |
|---------------|--------|------------------------------------------------|
| indicator     | uuid   | Filter by indicator ID (required if no dataset)|
| dataset       | string | Filter by dataset slug                         |
| geography     | string | Geography code. Supports comma-separated: "PS-GZA,PS-WBK" |
| geo_level     | string | "country", "territory", "governorate"          |
| year_from     | int    | Start year (inclusive)                          |
| year_to       | int    | End year (inclusive)                            |
| date_from     | date   | Start date (ISO 8601)                          |
| date_to       | date   | End date (ISO 8601)                            |
| time_precision| string | "day", "month", "quarter", "year"              |
| value_status  | string | "final", "provisional", "estimated"            |
| page          | int    | Page number                                    |
| per_page      | int    | Results per page (max: 1000)                   |
| sort          | string | "time" (default), "value", "geography"         |
| order         | string | "asc" or "desc"                                |
| format        | string | "json" (default), "csv"                        |

**Response:**

```json
{
  "data": [
    {
      "id": "uuid",
      "indicator": {
        "id": "uuid",
        "code": "LFS_UNEMP_RATE",
        "name": "Unemployment Rate"
      },
      "geography": {
        "code": "PS-GZA",
        "name": "Gaza Strip"
      },
      "time_period": "2024-01-01",
      "time_precision": "quarter",
      "value": 45.3,
      "value_status": "final",
      "source": {
        "organization": "PCBS",
        "url": "https://www.pcbs.gov.ps/..."
      }
    }
  ]
}
```


---

## Geographies

### List Geographies

```
GET /geographies
```

**Query Parameters:**

| Param   | Type   | Description                                   |
|---------|--------|-----------------------------------------------|
| level   | string | "country", "territory", "governorate", "locality" |
| parent  | string | Parent geography code                         |
| lang    | string | "en" or "ar"                                  |

Returns a flat list or nested tree (use `?tree=true` for hierarchical response).


---

## Export

### Export Dataset

```
GET /export/{dataset_slug}
```

**Query Parameters:**

| Param    | Type   | Description                       |
|----------|--------|-----------------------------------|
| format   | string | "csv", "json", "xlsx". Default: "csv" |
| geography| string | Filter by geography code          |
| year_from| int    | Start year                        |
| year_to  | int    | End year                          |

Returns a downloadable file with all observations for the dataset. Sets `Content-Disposition` header for download.


---

## Search

### Search Everything

```
GET /search
```

**Query Parameters:**

| Param | Type   | Description                    |
|-------|--------|--------------------------------|
| q     | string | Search query (Arabic or English) |
| type  | string | "dataset", "indicator", "story". Omit for all. |
| limit | int    | Max results (default: 10)      |
| lang  | string | "en" or "ar"                   |

Powered by Meilisearch. Returns a mixed list of datasets, indicators, and stories ranked by relevance.


---

## Rate Limiting

| Tier            | Limit            |
|-----------------|------------------|
| Unauthenticated | 100 req/minute   |

Rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
