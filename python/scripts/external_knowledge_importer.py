#!/usr/bin/env python3
"""
External Knowledge Importer (TASK_0137)

Provides real connector classes for:
- GitHub API (repository and topic discovery)
- Wikipedia API (concept discovery and summaries)
- Configurable web scraping (respectful, rate-limited fetches)

Integrates with:
- MilestoneKnowledgeIntegrator (priority context)
- TokenGovernor (budget-aware acquisition decisions)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# Allow running as `python scripts/external_knowledge_importer.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from milestone_knowledge_integration import MilestoneKnowledgeIntegrator
from output_safety import safe_print
from token_governor import TokenGovernor


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class ConnectorResult:
    source: str
    title: str
    url: str
    snippet: str
    content: str
    relevance_score: float
    fetched_at: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "content": self.content,
            "relevance_score": self.relevance_score,
            "fetched_at": self.fetched_at,
            "metadata": self.metadata,
        }


class RateLimiter:
    def __init__(self, calls_per_second: float = 1.0):
        self.interval = 1.0 / max(calls_per_second, 0.01)
        self._last_call = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        delta = now - self._last_call
        if delta < self.interval:
            time.sleep(self.interval - delta)
        self._last_call = time.monotonic()


class BaseConnector:
    source_name = "base"

    def __init__(self, session: Optional[requests.Session] = None, calls_per_second: float = 1.0):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": "Keeper-Loop/1.0 (Knowledge Import Agent)"})
        self.rate_limiter = RateLimiter(calls_per_second=calls_per_second)

    def relevance(self, text: str, keywords: List[str]) -> float:
        if not text:
            return 0.0
        if not keywords:
            return 0.5
        lowered = text.lower()
        matches = sum(1 for kw in keywords if kw.lower() in lowered)
        return min(1.0, matches / max(1, len(keywords)))


class GitHubConnector(BaseConnector):
    source_name = "github"

    def __init__(self, token: Optional[str] = None, session: Optional[requests.Session] = None):
        super().__init__(session=session, calls_per_second=1.2)
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def search_repositories(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        self.rate_limiter.wait()
        resp = self.session.get(
            "https://api.github.com/search/repositories",
            params={"q": query, "per_page": max(1, min(max_results, 20)), "sort": "stars", "order": "desc"},
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("items", [])

    def fetch(self, query: str, keywords: List[str], max_results: int = 5) -> List[ConnectorResult]:
        items = self.search_repositories(query, max_results=max_results)
        results: List[ConnectorResult] = []
        for item in items:
            snippet = item.get("description") or ""
            content = f"{item.get('full_name','')}: {snippet}"
            results.append(
                ConnectorResult(
                    source=self.source_name,
                    title=item.get("full_name", "unknown"),
                    url=item.get("html_url", ""),
                    snippet=snippet,
                    content=content[:5000],
                    relevance_score=self.relevance(content, keywords),
                    fetched_at=utc_now(),
                    metadata={
                        "stars": item.get("stargazers_count", 0),
                        "language": item.get("language"),
                        "topics": item.get("topics", []),
                    },
                )
            )
        return results


class WikipediaConnector(BaseConnector):
    source_name = "wikipedia"

    def __init__(self, session: Optional[requests.Session] = None):
        super().__init__(session=session, calls_per_second=1.0)

    def search(self, query: str, limit: int = 5) -> List[str]:
        self.rate_limiter.wait()
        resp = self.session.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "format": "json",
                "srlimit": max(1, min(limit, 20)),
                "srsearch": query,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return [x.get("title", "") for x in resp.json().get("query", {}).get("search", [])]

    def summary(self, title: str) -> str:
        self.rate_limiter.wait()
        safe_title = title.replace(" ", "_")
        resp = self.session.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe_title}",
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("extract", "")

    def fetch(self, query: str, keywords: List[str], max_results: int = 5) -> List[ConnectorResult]:
        titles = self.search(query, limit=max_results)
        results: List[ConnectorResult] = []
        for title in titles:
            extract = self.summary(title)
            results.append(
                ConnectorResult(
                    source=self.source_name,
                    title=title,
                    url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    snippet=extract[:300],
                    content=extract[:5000],
                    relevance_score=self.relevance(extract, keywords),
                    fetched_at=utc_now(),
                    metadata={},
                )
            )
        return results


class WebScrapingConnector(BaseConnector):
    source_name = "web"

    def __init__(self, allowed_domains: Optional[List[str]] = None, session: Optional[requests.Session] = None):
        super().__init__(session=session, calls_per_second=0.5)
        self.allowed_domains = [d.lower() for d in (allowed_domains or [])]

    def _is_allowed(self, url: str) -> bool:
        if not self.allowed_domains:
            return True
        from urllib.parse import urlparse

        host = (urlparse(url).hostname or "").lower()
        return any(host == dom or host.endswith(f".{dom}") for dom in self.allowed_domains)

    def fetch_url(self, url: str) -> str:
        if not self._is_allowed(url):
            raise ValueError(f"Domain not allowed: {url}")
        self.rate_limiter.wait()
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:5000]

    def fetch(self, urls: List[str], keywords: List[str]) -> List[ConnectorResult]:
        results: List[ConnectorResult] = []
        for url in urls:
            try:
                content = self.fetch_url(url)
                results.append(
                    ConnectorResult(
                        source=self.source_name,
                        title=url,
                        url=url,
                        snippet=content[:300],
                        content=content,
                        relevance_score=self.relevance(content, keywords),
                        fetched_at=utc_now(),
                        metadata={},
                    )
                )
            except Exception:
                continue
        return results


class ExternalKnowledgeImporter:
    """Coordinates connector execution with milestone and token-budget context."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root)
        self.token_governor = TokenGovernor(workspace_root=self.workspace_root)
        self.milestone_integrator = MilestoneKnowledgeIntegrator(workspace_root=self.workspace_root)

        token = os.getenv("GITHUB_TOKEN", "").strip() or None
        self.github = GitHubConnector(token=token)
        self.wikipedia = WikipediaConnector()
        self.web = WebScrapingConnector(
            allowed_domains=[d.strip() for d in os.getenv("EXTERNAL_WEB_ALLOWED_DOMAINS", "").split(",") if d.strip()]
        )

    def _can_spend(self, estimated_tokens: int) -> bool:
        metrics = self.token_governor.get_current_metrics()
        return metrics.remaining > max(500, estimated_tokens)

    def _build_queries(self, milestone_id: Optional[str], fallback_query: Optional[str]) -> List[str]:
        queries: List[str] = []
        if fallback_query:
            queries.append(fallback_query)
        if milestone_id:
            milestone_file = self.workspace_root / f"milestone_{milestone_id.lower().replace('m', '').zfill(2)}.json"
            if milestone_file.exists():
                try:
                    data = json.loads(milestone_file.read_text(encoding="utf-8"))
                    for goal in data.get("GOALS", []):
                        desc = (goal.get("description") or "").strip()
                        if desc:
                            queries.append(desc[:140])
                except Exception:
                    pass
        if not queries:
            queries = ["knowledge integration patterns", "token budget optimization"]
        return queries[:5]

    def import_for_milestone(
        self,
        milestone_id: Optional[str] = None,
        query: Optional[str] = None,
        max_results: int = 5,
        include_github: bool = True,
        include_wikipedia: bool = True,
        include_web: bool = False,
        web_urls: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        queries = self._build_queries(milestone_id=milestone_id, fallback_query=query)
        all_results: List[ConnectorResult] = []
        total_estimated_tokens = 0

        for q in queries:
            keywords = [w for w in re.split(r"[^a-zA-Z0-9_]+", q) if len(w) > 3][:12]
            if include_github and self._can_spend(1500):
                gh = self.github.fetch(q, keywords, max_results=max_results)
                all_results.extend(gh)
                total_estimated_tokens += sum(len(x.content) // 4 for x in gh)
            if include_wikipedia and self._can_spend(1500):
                wk = self.wikipedia.fetch(q, keywords, max_results=max_results)
                all_results.extend(wk)
                total_estimated_tokens += sum(len(x.content) // 4 for x in wk)

        if include_web and web_urls and self._can_spend(2000):
            base_keywords = [w for w in re.split(r"[^a-zA-Z0-9_]+", " ".join(queries)) if len(w) > 3][:20]
            wb = self.web.fetch(web_urls, base_keywords)
            all_results.extend(wb)
            total_estimated_tokens += sum(len(x.content) // 4 for x in wb)

        # Keep only useful items.
        all_results.sort(key=lambda x: x.relevance_score, reverse=True)
        filtered = [x for x in all_results if x.relevance_score >= 0.2][: max_results * 4]

        return {
            "milestone_id": milestone_id,
            "query_seed": query,
            "generated_at": utc_now(),
            "queries": queries,
            "estimated_tokens": total_estimated_tokens,
            "items": [x.to_dict() for x in filtered],
        }

    def save(self, payload: Dict[str, Any], output_path: Optional[Path] = None) -> Path:
        out = output_path or (
            self.workspace_root
            / "reports"
            / f"external_knowledge_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return out


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="External knowledge importer with milestone and token-governor awareness")
    p.add_argument("--milestone", default="", help="Milestone id (e.g., M01)")
    p.add_argument("--query", default="", help="Direct query seed")
    p.add_argument("--max-results", type=int, default=5, help="Max results per connector query")
    p.add_argument("--github", action="store_true", help="Enable GitHub connector")
    p.add_argument("--wikipedia", action="store_true", help="Enable Wikipedia connector")
    p.add_argument("--web", action="store_true", help="Enable web scraping connector")
    p.add_argument("--web-url", action="append", default=[], help="Web URL (repeatable)")
    p.add_argument("--dry-run", action="store_true", help="Print summary only; do not persist output")
    p.add_argument("--output", default="", help="Optional output JSON path")
    return p


def main() -> int:
    args = _build_parser().parse_args()
    workspace = Path(__file__).resolve().parent.parent
    importer = ExternalKnowledgeImporter(workspace)

    include_github = args.github or (not args.github and not args.wikipedia and not args.web)
    include_wikipedia = args.wikipedia or (not args.github and not args.wikipedia and not args.web)
    include_web = args.web

    payload = importer.import_for_milestone(
        milestone_id=args.milestone or None,
        query=args.query or None,
        max_results=args.max_results,
        include_github=include_github,
        include_wikipedia=include_wikipedia,
        include_web=include_web,
        web_urls=args.web_url or None,
    )

    if args.dry_run:
        safe_print(json.dumps({"queries": payload["queries"], "items": len(payload["items"])}, indent=2))
        return 0

    output = importer.save(payload, Path(args.output) if args.output else None)
    safe_print(f"saved={output}")
    safe_print(f"items={len(payload['items'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
