"""Tests for PCBS population pipeline."""

import pytest

from pipeline.sources.pcbs_population import PCBSPopulationPipeline


def test_pipeline_name():
    """Test pipeline has correct name."""
    pipeline = PCBSPopulationPipeline()
    assert pipeline.name == "pcbs_population"


def test_pipeline_source_url():
    """Test pipeline has correct source URL."""
    pipeline = PCBSPopulationPipeline()
    assert "pcbs.gov.ps" in pipeline.source_url
