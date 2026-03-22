-- Data Palestine Core Schema
-- PostgreSQL 16 + TimescaleDB + PostGIS

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS postgis CASCADE;

-- ============================================================
-- ENUMS
-- ============================================================

CREATE TYPE dataset_status AS ENUM ('draft', 'published', 'archived');
CREATE TYPE update_frequency AS ENUM ('daily', 'weekly', 'monthly', 'quarterly', 'annual', 'irregular', 'one_time');
CREATE TYPE observation_status AS ENUM ('preliminary', 'revised', 'final');
CREATE TYPE geography_level AS ENUM ('national', 'territory', 'governorate', 'locality');
CREATE TYPE source_type AS ENUM ('government', 'international_org', 'ngo', 'academic', 'media', 'other');
CREATE TYPE file_type AS ENUM ('pdf', 'excel', 'csv', 'html', 'json', 'api', 'other');

-- ============================================================
-- GEOGRAPHIES
-- Hierarchical: Palestine > Territory > Governorate > Locality
-- Codes aligned with PCBS P-codes and OCHA COD-AB boundaries
-- ============================================================

CREATE TABLE geographies (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(20) NOT NULL UNIQUE,       -- e.g., 'PS', 'PS-WBK', 'PS-WBK-JEN'
    name_en         VARCHAR(255) NOT NULL,
    name_ar         VARCHAR(255) NOT NULL,
    level           geography_level NOT NULL,
    parent_code     VARCHAR(20) REFERENCES geographies(code),
    pcbs_code       VARCHAR(20),                       -- PCBS internal code if different
    iso_code        VARCHAR(10),                       -- ISO 3166-2 code where applicable
    latitude        DECIMAL(10, 7),
    longitude       DECIMAL(10, 7),
    geometry        GEOMETRY(MultiPolygon, 4326),      -- PostGIS boundary geometry
    population      INTEGER,                           -- Latest known population estimate
    population_year SMALLINT,                          -- Year of population estimate
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_geographies_level ON geographies(level);
CREATE INDEX idx_geographies_parent ON geographies(parent_code);
CREATE INDEX idx_geographies_geom ON geographies USING GIST(geometry);

-- ============================================================
-- SOURCES
-- Provenance tracking for every piece of data
-- ============================================================

CREATE TABLE sources (
    id              SERIAL PRIMARY KEY,
    slug            VARCHAR(100) NOT NULL UNIQUE,       -- e.g., 'pcbs', 'ocha-opt', 'btselem'
    name_en         VARCHAR(255) NOT NULL,
    name_ar         VARCHAR(255),
    description_en  TEXT,
    description_ar  TEXT,
    source_type     source_type NOT NULL,
    website_url     VARCHAR(500),
    logo_url        VARCHAR(500),
    methodology_en  TEXT,                               -- How this source collects data
    methodology_ar  TEXT,
    reliability     SMALLINT CHECK (reliability BETWEEN 1 AND 5),  -- 1=low, 5=highest
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SOURCE DOCUMENTS
-- Specific documents/files from which data was extracted
-- ============================================================

CREATE TABLE source_documents (
    id              SERIAL PRIMARY KEY,
    source_id       INTEGER NOT NULL REFERENCES sources(id),
    title_en        VARCHAR(500),
    title_ar        VARCHAR(500),
    document_url    VARCHAR(1000),                      -- Original URL
    archive_url     VARCHAR(1000),                      -- Our archived copy (MinIO)
    file_type       file_type NOT NULL,
    publication_date DATE,
    access_date     DATE NOT NULL,                      -- When we retrieved it
    page_numbers    VARCHAR(50),                        -- Relevant pages (e.g., '12-15')
    checksum_sha256 VARCHAR(64),                        -- File integrity verification
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_source_documents_source ON source_documents(source_id);

-- ============================================================
-- CATEGORIES
-- Topic-based grouping for datasets
-- ============================================================

CREATE TABLE categories (
    id              SERIAL PRIMARY KEY,
    slug            VARCHAR(100) NOT NULL UNIQUE,
    name_en         VARCHAR(255) NOT NULL,
    name_ar         VARCHAR(255) NOT NULL,
    description_en  TEXT,
    description_ar  TEXT,
    icon            VARCHAR(50),                        -- Icon identifier (e.g., 'population', 'economy')
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- DATASETS
-- Top-level containers for related indicators
-- ============================================================

CREATE TABLE datasets (
    id              SERIAL PRIMARY KEY,
    slug            VARCHAR(200) NOT NULL UNIQUE,       -- URL-friendly identifier
    name_en         VARCHAR(500) NOT NULL,
    name_ar         VARCHAR(500) NOT NULL,
    description_en  TEXT,
    description_ar  TEXT,
    category_id     INTEGER REFERENCES categories(id),
    primary_source_id INTEGER REFERENCES sources(id),
    status          dataset_status DEFAULT 'draft',
    update_frequency update_frequency,
    temporal_coverage_start DATE,                       -- Earliest data point
    temporal_coverage_end   DATE,                       -- Latest data point
    geographic_coverage     VARCHAR(20)[] DEFAULT ARRAY['PS'],  -- Geography codes covered
    methodology_en  TEXT,                               -- How we process this dataset
    methodology_ar  TEXT,
    license         VARCHAR(100) DEFAULT 'CC-BY-4.0',
    version         INTEGER DEFAULT 1,
    tags            VARCHAR(100)[] DEFAULT '{}',
    metadata        JSONB DEFAULT '{}',
    featured        BOOLEAN DEFAULT FALSE,              -- Show on homepage
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    published_at    TIMESTAMPTZ
);

CREATE INDEX idx_datasets_category ON datasets(category_id);
CREATE INDEX idx_datasets_status ON datasets(status);
CREATE INDEX idx_datasets_slug ON datasets(slug);
CREATE INDEX idx_datasets_tags ON datasets USING GIN(tags);

-- ============================================================
-- DATASET_SOURCES (many-to-many)
-- A dataset may draw from multiple sources
-- ============================================================

CREATE TABLE dataset_sources (
    dataset_id      INTEGER NOT NULL REFERENCES datasets(id),
    source_id       INTEGER NOT NULL REFERENCES sources(id),
    is_primary      BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (dataset_id, source_id)
);

-- ============================================================
-- INDICATORS
-- Individual measurable values within datasets
-- ============================================================

CREATE TABLE indicators (
    id              SERIAL PRIMARY KEY,
    dataset_id      INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    code            VARCHAR(100) NOT NULL,              -- Machine-readable code (e.g., 'unemployment_rate')
    name_en         VARCHAR(500) NOT NULL,
    name_ar         VARCHAR(500) NOT NULL,
    description_en  TEXT,
    description_ar  TEXT,
    unit_en         VARCHAR(100),                       -- e.g., 'percent', 'USD', 'persons'
    unit_ar         VARCHAR(100),
    unit_symbol     VARCHAR(20),                        -- e.g., '%', '$', ''
    decimals        SMALLINT DEFAULT 2,                 -- Display precision
    dimensions      JSONB DEFAULT '{}',                 -- Available disaggregations: {"gender": ["male", "female", "total"], "age_group": [...]}
    sdg_indicator   VARCHAR(50),                        -- SDG indicator code if applicable
    sort_order      INTEGER DEFAULT 0,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(dataset_id, code)
);

CREATE INDEX idx_indicators_dataset ON indicators(dataset_id);
CREATE INDEX idx_indicators_code ON indicators(code);

-- ============================================================
-- OBSERVATIONS
-- Individual data points: an indicator at a specific time/place
-- This is the core data table — will be the largest table
-- ============================================================

CREATE TABLE observations (
    id              BIGSERIAL,
    indicator_id    INTEGER NOT NULL REFERENCES indicators(id) ON DELETE CASCADE,
    geography_code  VARCHAR(20) NOT NULL REFERENCES geographies(code),
    time_period     DATE NOT NULL,                      -- Normalized to first day of period
    time_precision  VARCHAR(20) NOT NULL DEFAULT 'annual',  -- 'daily', 'monthly', 'quarterly', 'annual'
    value           DECIMAL(20, 6),                     -- The actual data value (NULL = missing)
    value_text      VARCHAR(255),                       -- For non-numeric observations
    dimensions      JSONB DEFAULT '{}',                 -- Disaggregation values: {"gender": "female", "age_group": "15-24"}
    status          observation_status DEFAULT 'final',
    source_document_id INTEGER REFERENCES source_documents(id),
    notes_en        TEXT,
    notes_ar        TEXT,
    data_version    INTEGER DEFAULT 1,                  -- Incremented when data is revised
    is_latest       BOOLEAN DEFAULT TRUE,               -- FALSE for superseded versions
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, time_period)                       -- Composite PK for TimescaleDB partitioning
);

-- Convert to TimescaleDB hypertable for time-series performance
SELECT create_hypertable('observations', 'time_period', migrate_data => true);

CREATE INDEX idx_observations_indicator ON observations(indicator_id);
CREATE INDEX idx_observations_geography ON observations(geography_code);
CREATE INDEX idx_observations_time ON observations(time_period DESC);
CREATE INDEX idx_observations_dimensions ON observations USING GIN(dimensions);
CREATE INDEX idx_observations_latest ON observations(indicator_id, geography_code, is_latest) WHERE is_latest = TRUE;

-- ============================================================
-- PIPELINE RUNS
-- Audit trail for every data ingestion
-- ============================================================

CREATE TABLE pipeline_runs (
    id              SERIAL PRIMARY KEY,
    pipeline_name   VARCHAR(200) NOT NULL,              -- e.g., 'pcbs_population'
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    status          VARCHAR(20) NOT NULL DEFAULT 'running',  -- 'running', 'success', 'failed', 'partial'
    records_processed INTEGER DEFAULT 0,
    records_inserted  INTEGER DEFAULT 0,
    records_updated   INTEGER DEFAULT 0,
    records_skipped   INTEGER DEFAULT 0,
    error_message   TEXT,
    metadata        JSONB DEFAULT '{}',                 -- Pipeline-specific metadata
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pipeline_runs_name ON pipeline_runs(pipeline_name);
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);

-- ============================================================
-- DATA STORIES (Phase 2, but schema ready)
-- Long-form interactive articles using platform data
-- ============================================================

CREATE TABLE data_stories (
    id              SERIAL PRIMARY KEY,
    slug            VARCHAR(200) NOT NULL UNIQUE,
    title_en        VARCHAR(500) NOT NULL,
    title_ar        VARCHAR(500),
    summary_en      TEXT,
    summary_ar      TEXT,
    content_en      TEXT,                               -- MDX or structured content
    content_ar      TEXT,
    author_name     VARCHAR(255),
    cover_image_url VARCHAR(500),
    indicator_ids   INTEGER[] DEFAULT '{}',             -- Related indicators
    status          VARCHAR(20) DEFAULT 'draft',
    published_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SEED DATA: Geographies
-- ============================================================

INSERT INTO geographies (code, name_en, name_ar, level, parent_code) VALUES
    ('PS', 'Palestine', 'فلسطين', 'national', NULL),
    ('PS-WBK', 'West Bank', 'الضفة الغربية', 'territory', 'PS'),
    ('PS-GZA', 'Gaza Strip', 'قطاع غزة', 'territory', 'PS'),
    -- West Bank Governorates
    ('PS-WBK-JEN', 'Jenin', 'جنين', 'governorate', 'PS-WBK'),
    ('PS-WBK-TBS', 'Tubas', 'طوباس', 'governorate', 'PS-WBK'),
    ('PS-WBK-TKM', 'Tulkarm', 'طولكرم', 'governorate', 'PS-WBK'),
    ('PS-WBK-NBS', 'Nablus', 'نابلس', 'governorate', 'PS-WBK'),
    ('PS-WBK-QQA', 'Qalqiliya', 'قلقيلية', 'governorate', 'PS-WBK'),
    ('PS-WBK-SLT', 'Salfit', 'سلفيت', 'governorate', 'PS-WBK'),
    ('PS-WBK-RBH', 'Ramallah & Al-Bireh', 'رام الله والبيرة', 'governorate', 'PS-WBK'),
    ('PS-WBK-JRH', 'Jericho & Al-Aghwar', 'أريحا والأغوار', 'governorate', 'PS-WBK'),
    ('PS-WBK-JEM', 'Jerusalem', 'القدس', 'governorate', 'PS-WBK'),
    ('PS-WBK-BTH', 'Bethlehem', 'بيت لحم', 'governorate', 'PS-WBK'),
    ('PS-WBK-HBN', 'Hebron', 'الخليل', 'governorate', 'PS-WBK'),
    -- Gaza Governorates
    ('PS-GZA-NGZ', 'North Gaza', 'شمال غزة', 'governorate', 'PS-GZA'),
    ('PS-GZA-GZA', 'Gaza', 'غزة', 'governorate', 'PS-GZA'),
    ('PS-GZA-DEB', 'Deir Al-Balah', 'دير البلح', 'governorate', 'PS-GZA'),
    ('PS-GZA-KYS', 'Khan Yunis', 'خان يونس', 'governorate', 'PS-GZA'),
    ('PS-GZA-RFH', 'Rafah', 'رفح', 'governorate', 'PS-GZA');

-- ============================================================
-- SEED DATA: Categories
-- ============================================================

INSERT INTO categories (slug, name_en, name_ar, icon, sort_order) VALUES
    ('population', 'Population & Demographics', 'السكان والتركيبة السكانية', 'users', 1),
    ('economy', 'Economy & Trade', 'الاقتصاد والتجارة', 'trending-up', 2),
    ('labor', 'Labor & Employment', 'العمل والتوظيف', 'briefcase', 3),
    ('education', 'Education', 'التعليم', 'book-open', 4),
    ('health', 'Health', 'الصحة', 'heart-pulse', 5),
    ('conflict', 'Conflict & Protection', 'النزاع والحماية', 'shield', 6),
    ('displacement', 'Displacement & Refugees', 'النزوح واللاجئين', 'map-pin', 7),
    ('infrastructure', 'Infrastructure & Water', 'البنية التحتية والمياه', 'droplet', 8),
    ('environment', 'Environment & Climate', 'البيئة والمناخ', 'leaf', 9),
    ('governance', 'Governance & Justice', 'الحوكمة والعدالة', 'scale', 10);

-- ============================================================
-- SEED DATA: Primary Sources
-- ============================================================

INSERT INTO sources (slug, name_en, name_ar, source_type, website_url, reliability) VALUES
    ('pcbs', 'Palestinian Central Bureau of Statistics', 'الجهاز المركزي للإحصاء الفلسطيني', 'government', 'https://www.pcbs.gov.ps', 5),
    ('ocha-opt', 'OCHA occupied Palestinian territory', 'مكتب الأمم المتحدة لتنسيق الشؤون الإنسانية', 'international_org', 'https://www.ochaopt.org', 5),
    ('unrwa', 'UNRWA', 'الأونروا', 'international_org', 'https://www.unrwa.org', 5),
    ('world-bank', 'World Bank', 'البنك الدولي', 'international_org', 'https://data.worldbank.org/country/west-bank-and-gaza', 5),
    ('btselem', 'B''Tselem', 'بتسيلم', 'ngo', 'https://www.btselem.org', 4),
    ('moh', 'Palestinian Ministry of Health', 'وزارة الصحة الفلسطينية', 'government', NULL, 4),
    ('unesco', 'UNESCO Institute for Statistics', 'معهد اليونسكو للإحصاء', 'international_org', 'https://uis.unesco.org', 5),
    ('who', 'World Health Organization', 'منظمة الصحة العالمية', 'international_org', 'https://www.who.int', 5),
    ('hdx', 'Humanitarian Data Exchange', 'منصة تبادل البيانات الإنسانية', 'international_org', 'https://data.humdata.org', 4),
    ('pwa', 'Palestinian Water Authority', 'سلطة المياه الفلسطينية', 'government', NULL, 4);

-- ============================================================
-- HELPER FUNCTIONS
-- ============================================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to relevant tables
CREATE TRIGGER set_updated_at BEFORE UPDATE ON geographies FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON sources FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON datasets FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON indicators FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON data_stories FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- VIEWS
-- ============================================================

-- Latest observations (excluding superseded versions)
CREATE VIEW latest_observations AS
SELECT o.*, i.code AS indicator_code, i.name_en AS indicator_name_en, i.name_ar AS indicator_name_ar,
       i.unit_en, i.unit_symbol, d.slug AS dataset_slug, d.name_en AS dataset_name_en,
       g.name_en AS geography_name_en, g.name_ar AS geography_name_ar, g.level AS geography_level
FROM observations o
JOIN indicators i ON o.indicator_id = i.id
JOIN datasets d ON i.dataset_id = d.id
JOIN geographies g ON o.geography_code = g.code
WHERE o.is_latest = TRUE;

-- Dataset summary (count of indicators and observations)
CREATE VIEW dataset_summary AS
SELECT d.id, d.slug, d.name_en, d.name_ar, d.status,
       COUNT(DISTINCT i.id) AS indicator_count,
       COUNT(DISTINCT o.id) AS observation_count,
       MIN(o.time_period) AS earliest_data,
       MAX(o.time_period) AS latest_data,
       d.updated_at
FROM datasets d
LEFT JOIN indicators i ON d.id = i.dataset_id
LEFT JOIN observations o ON i.id = o.indicator_id AND o.is_latest = TRUE
GROUP BY d.id;
