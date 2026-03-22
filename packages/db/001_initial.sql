-- Data Palestine — Initial Database Schema
-- PostgreSQL 16 + TimescaleDB + PostGIS
-- Run after: CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- GEOGRAPHIC HIERARCHY
-- Palestine → Territory (West Bank / Gaza Strip) → Governorate → Locality
-- Aligned with PCBS P-codes and OCHA COD-AB administrative boundaries
-- ============================================================================

CREATE TABLE geographies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code            VARCHAR(20) UNIQUE NOT NULL,       -- P-code: PS, PS-WBK, PS-GZA, PS-JEN, etc.
    name_en         VARCHAR(255) NOT NULL,
    name_ar         VARCHAR(255) NOT NULL,
    level           VARCHAR(20) NOT NULL CHECK (level IN ('country', 'territory', 'governorate', 'locality')),
    parent_id       UUID REFERENCES geographies(id),
    iso_3166_2      VARCHAR(10),                       -- ISO code where applicable
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    geometry        GEOMETRY(MultiPolygon, 4326),       -- PostGIS boundary
    population      INTEGER,                           -- Latest known population
    population_year SMALLINT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_geographies_parent ON geographies(parent_id);
CREATE INDEX idx_geographies_level ON geographies(level);
CREATE INDEX idx_geographies_code ON geographies(code);
CREATE INDEX idx_geographies_geometry ON geographies USING GIST(geometry);


-- ============================================================================
-- DATA SOURCES
-- Provenance tracking: every piece of data traces back to a source document
-- ============================================================================

CREATE TABLE sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(500) NOT NULL,              -- "PCBS Labor Force Survey Q3 2024"
    organization    VARCHAR(255) NOT NULL,              -- "Palestinian Central Bureau of Statistics"
    url             TEXT,                               -- Original URL
    document_type   VARCHAR(50) CHECK (document_type IN ('webpage', 'pdf', 'excel', 'csv', 'api', 'report', 'database')),
    publication_date DATE,
    access_date     DATE NOT NULL,                      -- When we accessed/downloaded it
    language        VARCHAR(5) DEFAULT 'en',            -- 'en', 'ar', 'both'
    license         VARCHAR(255),                       -- Data license if known
    notes           TEXT,
    file_hash       VARCHAR(64),                        -- SHA-256 of the original file
    archived_path   TEXT,                               -- Path to our archived copy
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sources_organization ON sources(organization);
CREATE INDEX idx_sources_publication_date ON sources(publication_date);


-- ============================================================================
-- CATEGORIES
-- Thematic groupings: Economy, Health, Education, Demographics, etc.
-- ============================================================================

CREATE TABLE categories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            VARCHAR(100) UNIQUE NOT NULL,       -- "economy", "health", "education"
    name_en         VARCHAR(255) NOT NULL,
    name_ar         VARCHAR(255) NOT NULL,
    description_en  TEXT,
    description_ar  TEXT,
    icon            VARCHAR(50),                        -- Icon identifier for UI
    display_order   INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ============================================================================
-- DATASETS
-- A dataset is a named collection of related indicators from a specific source
-- Example: "Palestinian Labor Force Survey", "Consumer Price Index"
-- ============================================================================

CREATE TABLE datasets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            VARCHAR(200) UNIQUE NOT NULL,       -- URL-friendly identifier
    name_en         VARCHAR(500) NOT NULL,
    name_ar         VARCHAR(500) NOT NULL,
    description_en  TEXT,
    description_ar  TEXT,
    category_id     UUID NOT NULL REFERENCES categories(id),
    primary_source_id UUID REFERENCES sources(id),      -- Main source organization
    methodology_en  TEXT,                               -- How this data was collected
    methodology_ar  TEXT,
    update_frequency VARCHAR(50) CHECK (update_frequency IN (
        'daily', 'weekly', 'monthly', 'quarterly', 'annually', 'irregular', 'one-time'
    )),
    temporal_coverage_start DATE,
    temporal_coverage_end   DATE,
    geographic_coverage     VARCHAR(50) DEFAULT 'national' CHECK (geographic_coverage IN (
        'national', 'territory', 'governorate', 'locality'
    )),
    status          VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'archived', 'draft')),
    tags            TEXT[],                             -- Freeform tags for search
    metadata        JSONB DEFAULT '{}',
    last_updated    TIMESTAMPTZ,                        -- When data was last refreshed
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_datasets_slug ON datasets(slug);
CREATE INDEX idx_datasets_category ON datasets(category_id);
CREATE INDEX idx_datasets_status ON datasets(status);
CREATE INDEX idx_datasets_tags ON datasets USING GIN(tags);


-- ============================================================================
-- INDICATORS
-- A measurable variable within a dataset
-- Example: "Unemployment rate", "Population total", "CPI all items"
-- Indicators have dimensions that define what subgroups they measure
-- ============================================================================

CREATE TABLE indicators (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id      UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    code            VARCHAR(100),                       -- Source system code if available
    name_en         VARCHAR(500) NOT NULL,
    name_ar         VARCHAR(500) NOT NULL,
    description_en  TEXT,
    description_ar  TEXT,
    unit            VARCHAR(100),                       -- "percent", "USD", "persons", "index"
    unit_multiplier DOUBLE PRECISION DEFAULT 1,         -- e.g., 1000 if values are in thousands
    decimals        SMALLINT DEFAULT 2,                 -- Display precision
    dimensions      JSONB DEFAULT '{}',                 -- {"gender": "female", "age_group": "15-24"}
    aggregation_method VARCHAR(50),                     -- "sum", "average", "median", "latest"
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(dataset_id, code, dimensions)
);

CREATE INDEX idx_indicators_dataset ON indicators(dataset_id);
CREATE INDEX idx_indicators_code ON indicators(code);
CREATE INDEX idx_indicators_dimensions ON indicators USING GIN(dimensions);


-- ============================================================================
-- OBSERVATIONS
-- Individual data points: an indicator's value at a specific time and place
-- This is the core fact table — will be the largest table
-- ============================================================================

CREATE TABLE observations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    indicator_id    UUID NOT NULL REFERENCES indicators(id) ON DELETE CASCADE,
    geography_id    UUID NOT NULL REFERENCES geographies(id),
    source_id       UUID NOT NULL REFERENCES sources(id),
    time_period     DATE NOT NULL,                      -- The date this observation represents
    time_precision  VARCHAR(20) DEFAULT 'year' CHECK (time_precision IN (
        'day', 'week', 'month', 'quarter', 'year'
    )),
    value           DOUBLE PRECISION NOT NULL,
    value_status    VARCHAR(20) DEFAULT 'final' CHECK (value_status IN (
        'final', 'provisional', 'estimated', 'projected', 'revised'
    )),
    notes           TEXT,                               -- Any caveats about this specific value
    metadata        JSONB DEFAULT '{}',
    pipeline_run_id UUID,                               -- Which pipeline run created this
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(indicator_id, geography_id, time_period, source_id)
);

CREATE INDEX idx_observations_indicator ON observations(indicator_id);
CREATE INDEX idx_observations_geography ON observations(geography_id);
CREATE INDEX idx_observations_time ON observations(time_period);
CREATE INDEX idx_observations_indicator_time ON observations(indicator_id, time_period);
CREATE INDEX idx_observations_indicator_geo_time ON observations(indicator_id, geography_id, time_period);

-- Consider making this a TimescaleDB hypertable if observation volume is very high:
-- SELECT create_hypertable('observations', 'time_period');


-- ============================================================================
-- PIPELINE RUNS
-- Audit trail: every pipeline execution is logged
-- ============================================================================

CREATE TABLE pipeline_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_name   VARCHAR(200) NOT NULL,              -- "pcbs.population", "worldbank.indicators"
    status          VARCHAR(20) NOT NULL CHECK (status IN ('running', 'success', 'failed', 'partial')),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    records_created INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_skipped INTEGER DEFAULT 0,
    errors          JSONB DEFAULT '[]',                 -- Array of error objects
    config          JSONB DEFAULT '{}',                 -- Pipeline configuration used
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX idx_pipeline_runs_name ON pipeline_runs(pipeline_name);
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);


-- ============================================================================
-- DATA STORIES (Phase 2)
-- Long-form interactive articles using the platform's data
-- ============================================================================

CREATE TABLE stories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            VARCHAR(200) UNIQUE NOT NULL,
    title_en        VARCHAR(500) NOT NULL,
    title_ar        VARCHAR(500) NOT NULL,
    summary_en      TEXT,
    summary_ar      TEXT,
    content_en      TEXT,                               -- MDX content
    content_ar      TEXT,
    author_name     VARCHAR(255),
    cover_image     TEXT,                               -- Path or URL
    published_at    TIMESTAMPTZ,
    status          VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    featured        BOOLEAN DEFAULT false,
    tags            TEXT[],
    related_datasets UUID[],                            -- References to dataset IDs
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_stories_slug ON stories(slug);
CREATE INDEX idx_stories_status ON stories(status);
CREATE INDEX idx_stories_published ON stories(published_at);


-- ============================================================================
-- HELPER: Updated_at trigger
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_geographies_updated BEFORE UPDATE ON geographies FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_datasets_updated BEFORE UPDATE ON datasets FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_indicators_updated BEFORE UPDATE ON indicators FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_stories_updated BEFORE UPDATE ON stories FOR EACH ROW EXECUTE FUNCTION update_updated_at();
