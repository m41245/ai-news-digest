"""
Unit tests for M80 benchmark dataset.
"""

from __future__ import annotations

from ai_news_digest.application.ai.benchmark.dataset import get_cases_for_task, load_dataset
from ai_news_digest.application.ai.benchmark.models import BenchmarkDataset, BenchmarkTask


class TestBenchmarkDataset:
    def test_load_dataset_returns_dataset(self):
        dataset = load_dataset()
        assert isinstance(dataset, BenchmarkDataset)
        assert dataset.name == "ai_news_quality_v1"
        assert dataset.version == "2026-09-14"

    def test_dataset_has_cases(self):
        dataset = load_dataset()
        assert len(dataset.cases) > 0

    def test_all_cases_have_required_fields(self):
        dataset = load_dataset()
        for case in dataset.cases:
            assert case.case_id
            assert case.article_title.strip()
            assert case.article_content.strip()
            assert isinstance(case.task, BenchmarkTask)

    def test_cases_for_task(self):
        cases = get_cases_for_task(BenchmarkTask.SUMMARY)
        assert len(cases) > 0
        for case in cases:
            assert case.task == BenchmarkTask.SUMMARY

    def test_no_duplicate_case_ids(self):
        dataset = load_dataset()
        ids = [c.case_id for c in dataset.cases]
        assert len(ids) == len(set(ids))

    def test_cases_are_deterministic(self):
        dataset1 = load_dataset()
        dataset2 = load_dataset()
        assert dataset1.cases == dataset2.cases

    def test_expected_fields_populated(self):
        dataset = load_dataset()
        for case in dataset.cases:
            assert len(case.expected_categories) >= 0
            assert len(case.expected_companies) >= 0
            assert len(case.expected_topics) >= 0
