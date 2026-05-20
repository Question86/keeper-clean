#!/usr/bin/env python3
"""Tests for TASK_0137 external knowledge connectors."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.external_knowledge_importer import (
    ExternalKnowledgeImporter,
    GitHubConnector,
    WikipediaConnector,
    WebScrapingConnector,
)


class _FakeResponse:
    def __init__(self, payload=None, text: str = "", status_code: int = 200):
        self._payload = payload or {}
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, routes):
        self.routes = routes
        self.headers = {}
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        key = (url, json.dumps(params, sort_keys=True) if params else "")
        if key in self.routes:
            return self.routes[key]
        if (url, "") in self.routes:
            return self.routes[(url, "")]
        return _FakeResponse({}, "", 404)


def test_github_connector_fetch():
    routes = {
        (
            "https://api.github.com/search/repositories",
            json.dumps({"q": "token optimization", "per_page": 3, "sort": "stars", "order": "desc"}, sort_keys=True),
        ): _FakeResponse(
            {
                "items": [
                    {
                        "full_name": "org/repo",
                        "html_url": "https://github.com/org/repo",
                        "description": "Token optimization toolkit",
                        "stargazers_count": 42,
                        "language": "Python",
                        "topics": ["tokens"],
                    }
                ]
            }
        )
    }
    session = _FakeSession(routes)
    c = GitHubConnector(token=None, session=session)
    out = c.fetch("token optimization", ["token", "optimization"], max_results=3)
    assert len(out) == 1
    assert out[0].source == "github"
    assert out[0].relevance_score > 0


def test_wikipedia_connector_fetch():
    routes = {
        (
            "https://en.wikipedia.org/w/api.php",
            json.dumps(
                {
                    "action": "query",
                    "list": "search",
                    "format": "json",
                    "srlimit": 2,
                    "srsearch": "machine learning",
                },
                sort_keys=True,
            ),
        ): _FakeResponse({"query": {"search": [{"title": "Machine learning"}]}}),
        ("https://en.wikipedia.org/api/rest_v1/page/summary/Machine_learning", ""): _FakeResponse(
            {"extract": "Machine learning is a field of AI."}
        ),
    }
    session = _FakeSession(routes)
    c = WikipediaConnector(session=session)
    out = c.fetch("machine learning", ["machine", "learning"], max_results=2)
    assert len(out) == 1
    assert out[0].source == "wikipedia"
    assert "AI" in out[0].content


def test_web_scraping_connector_domain_filter():
    routes = {
        ("https://example.com/page", ""): _FakeResponse({}, "<html><body>token budget guidance</body></html>")
    }
    session = _FakeSession(routes)
    c = WebScrapingConnector(allowed_domains=["example.com"], session=session)
    out = c.fetch(["https://example.com/page"], ["token", "budget"])
    assert len(out) == 1
    assert out[0].source == "web"
    assert out[0].relevance_score > 0


def test_external_importer_integration(tmp_path: Path):
    (tmp_path / "reports").mkdir()
    importer = ExternalKnowledgeImporter(tmp_path)

    # Stub network calls for deterministic test.
    importer.github.fetch = lambda q, k, max_results=5: []
    importer.wikipedia.fetch = lambda q, k, max_results=5: []
    importer.web.fetch = lambda urls, keywords: []

    payload = importer.import_for_milestone(
        milestone_id=None,
        query="knowledge pipeline",
        include_github=True,
        include_wikipedia=True,
        include_web=True,
        web_urls=["https://example.com/page"],
    )
    assert "queries" in payload
    assert "items" in payload
    out = importer.save(payload)
    assert out.exists()
