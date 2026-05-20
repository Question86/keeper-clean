#!/usr/bin/env python3
"""
SKL Publisher - Multi-Format Content Publishing System
Generates HTML, JSON-LD, and SEO-optimized outputs for SKL documents
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone
from urllib.parse import quote
import re

from skl_simple import SKLFramework, SKLDocument

class SKLPublisher:
    """Multi-format publisher for SKL documents"""

    def __init__(self, workspace_path: Path, output_dir: str = "skl_publish"):
        self.workspace = workspace_path
        self.output_dir = workspace_path / output_dir
        self.output_dir.mkdir(exist_ok=True)

        # Create subdirectories
        self.html_dir = self.output_dir / "html"
        self.jsonld_dir = self.output_dir / "jsonld"
        self.assets_dir = self.output_dir / "assets"

        for dir_path in [self.html_dir, self.jsonld_dir, self.assets_dir]:
            dir_path.mkdir(exist_ok=True)

        self.framework = SKLFramework(workspace_path)

    def publish_all(self) -> Dict:
        """Publish all documents in multiple formats"""
        report = {
            "total_processed": 0,
            "html_generated": 0,
            "jsonld_generated": 0,
            "errors": [],
            "sitemap_entries": []
        }

        # Generate automatic summaries first (Phase 3)
        try:
            from skl_summarizer import SKLSummarizer, SKLSummaryPublisher
            print("📋 Generating automatic summaries...")
            summary_report = self._generate_summaries()
            report["summaries_generated"] = summary_report.get("summary_files_generated", 0)
            if summary_report.get("errors"):
                report["errors"].extend([f"Summary: {err}" for err in summary_report["errors"]])
        except ImportError:
            print("⚠️  SKL Summarizer not available, skipping summaries")
        except Exception as e:
            report["errors"].append(f"Summary generation failed: {str(e)}")

        for md_file in self.workspace.glob("*.md"):
            if md_file.name.startswith('_'):
                continue

            report["total_processed"] += 1

            try:
                doc = SKLDocument.from_markdown(md_file)

                # Generate HTML
                html_path = self._publish_html(doc)
                if html_path:
                    report["html_generated"] += 1
                    report["sitemap_entries"].append({
                        "url": f"/html/{quote(doc.id)}.html",
                        "lastmod": doc.metadata.get('modified', datetime.now(timezone.utc).isoformat()),
                        "priority": "0.8"
                    })

                # Generate JSON-LD
                jsonld_path = self._publish_jsonld(doc)
                if jsonld_path:
                    report["jsonld_generated"] += 1

            except Exception as e:
                report["errors"].append(f"{md_file.name}: {str(e)}")

        # Generate sitemap
        self._generate_sitemap(report["sitemap_entries"])

        # Generate robots.txt
        self._generate_robots_txt()

        # Generate index page
        self._generate_index_page()

        return report

    def _publish_html(self, doc: SKLDocument) -> Optional[Path]:
        """Generate SEO-optimized HTML with semantic markup"""
        try:
            html_content = self._generate_html(doc)
            html_path = self.html_dir / f"{doc.id}.html"
            html_path.write_text(html_content, encoding='utf-8')
            return html_path
        except Exception:
            return None

    def _publish_jsonld(self, doc: SKLDocument) -> Optional[Path]:
        """Generate JSON-LD structured data"""
        try:
            jsonld_data = self._generate_jsonld(doc)
            jsonld_path = self.jsonld_dir / f"{doc.id}.jsonld"
            jsonld_path.write_text(json.dumps(jsonld_data, indent=2, ensure_ascii=False), encoding='utf-8')
            return jsonld_path
        except Exception:
            return None

    def _generate_html(self, doc: SKLDocument) -> str:
        """Generate complete HTML page with semantic markup"""
        # Convert markdown content to HTML
        html_body = self._markdown_to_html(doc.content)

        # Generate meta tags
        meta_tags = self._generate_meta_tags(doc)

        # Generate structured data
        jsonld_script = f"""
        <script type="application/ld+json">
        {json.dumps(self._generate_jsonld(doc), indent=2)}
        </script>
        """

        # Generate HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{doc.title} - SKL Knowledge Base</title>
    {meta_tags}
    <link rel="stylesheet" href="../assets/skl.css">
    <link rel="canonical" href="/html/{quote(doc.id)}.html">
    {jsonld_script}
</head>
<body>
    <header class="skl-header">
        <nav class="skl-nav">
            <a href="../index.html">SKL Home</a> |
            <a href="/jsonld/{quote(doc.id)}.jsonld">JSON-LD</a> |
            <a href="/tags.html">Tags</a>
        </nav>
        <h1 class="skl-title">{doc.title}</h1>
        {self._generate_tag_badges(doc.tags)}
    </header>

    <main class="skl-content">
        {self._generate_summary_section(doc)}
        {html_body}
    </main>

    <footer class="skl-footer">
        <div class="skl-meta">
            <p><strong>ID:</strong> {doc.id}</p>
            <p><strong>Version:</strong> {doc.metadata.get('version', '1.0')}</p>
            <p><strong>Created:</strong> {doc.metadata.get('created', 'Unknown')}</p>
            <p><strong>Modified:</strong> {doc.metadata.get('modified', 'Unknown')}</p>
        </div>
        <div class="skl-references">
            {self._generate_references_html(doc.references)}
        </div>
    </footer>
</body>
</html>"""
        return html

    def _generate_jsonld(self, doc: SKLDocument) -> Dict:
        """Generate comprehensive JSON-LD structured data"""
        base_url = "https://skl.example.com"  # Configurable base URL

        # Build main entity
        jsonld = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": doc.title,
            "description": doc.metadata.get('summary', doc.title),
            "url": f"{base_url}/html/{doc.id}.html",
            "datePublished": doc.metadata.get('created', datetime.now(timezone.utc).isoformat()),
            "dateModified": doc.metadata.get('modified', datetime.now(timezone.utc).isoformat()),
            "author": {
                "@type": "Organization",
                "name": "SKL Framework",
                "url": base_url
            },
            "publisher": {
                "@type": "Organization",
                "name": "Semantic Knowledge Lattice",
                "url": base_url
            },
            "identifier": doc.id,
            "version": doc.metadata.get('version', '1.0'),
            "about": [
                {
                    "@type": "Thing",
                    "name": tag,
                    "identifier": f"tag:{tag}"
                } for tag in doc.tags
            ],
            "mentions": [
                {
                    "@type": "Thing",
                    "name": ref,
                    "url": f"{base_url}/html/{ref.replace('.md', '')}.html"
                } for ref in doc.references
            ]
        }

        # Add additional metadata if available
        if 'keywords' in doc.metadata:
            jsonld["keywords"] = doc.metadata['keywords']

        if 'category' in doc.metadata:
            jsonld["articleSection"] = doc.metadata['category']

        return jsonld

    def _markdown_to_html(self, content: str) -> str:
        """Convert markdown to HTML (enhanced version)"""
        # Headers
        content = re.sub(r'^### (.*)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
        content = re.sub(r'^## (.*)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
        content = re.sub(r'^# (.*)$', r'<h1>\1</h1>', content, flags=re.MULTILINE)

        # Code blocks (must come before inline code)
        content = re.sub(r'```(\w+)?\n(.*?)\n```', r'<pre><code class="language-\1">\2</code></pre>', content, flags=re.DOTALL)

        # Inline code
        content = re.sub(r'`([^`]+)`', r'<code>\1</code>', content)

        # Bold and italic
        content = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', content)
        content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
        content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)

        # Links
        content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', content)

        # Lists - process before paragraphs to avoid conflicts
        lines = content.split('\n')
        processed_lines = []
        in_list = False
        list_items = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('* ') or stripped.startswith('- ') or re.match(r'^\d+\.\s', stripped):
                # List item
                if not in_list:
                    in_list = True
                    list_items = []
                # Extract list content
                if stripped.startswith('* '):
                    item_content = stripped[2:]
                elif stripped.startswith('- '):
                    item_content = stripped[2:]
                else:
                    item_content = re.sub(r'^\d+\.\s', '', stripped)
                list_items.append(f'<li>{item_content}</li>')
            else:
                # End of list or regular content
                if in_list:
                    # Close the list
                    processed_lines.append('<ul>')
                    processed_lines.extend(list_items)
                    processed_lines.append('</ul>')
                    in_list = False
                    list_items = []

                if stripped:
                    processed_lines.append(f'<p>{line}</p>')
                else:
                    processed_lines.append('')

        # Handle any remaining list
        if in_list:
            processed_lines.append('<ul>')
            processed_lines.extend(list_items)
            processed_lines.append('</ul>')

        content = '\n'.join(processed_lines)

        # Blockquotes
        content = re.sub(r'^> (.*)$', r'<blockquote>\1</blockquote>', content, flags=re.MULTILINE)

        return content

    def _generate_meta_tags(self, doc: SKLDocument) -> str:
        """Generate SEO meta tags"""
        meta = []

        # Basic meta tags
        meta.append('<meta name="description" content="' + (doc.metadata.get('summary', doc.title)[:160]) + '">')
        meta.append('<meta name="keywords" content="' + ', '.join(doc.tags) + '">')
        meta.append('<meta name="author" content="SKL Framework">')

        # Open Graph tags
        meta.append('<meta property="og:title" content="' + doc.title + '">')
        meta.append('<meta property="og:description" content="' + (doc.metadata.get('summary', doc.title)[:200]) + '">')
        meta.append('<meta property="og:type" content="article">')
        meta.append('<meta property="og:url" content="/html/' + quote(doc.id) + '.html">')

        # Twitter Card tags
        meta.append('<meta name="twitter:card" content="summary">')
        meta.append('<meta name="twitter:title" content="' + doc.title + '">')
        meta.append('<meta name="twitter:description" content="' + (doc.metadata.get('summary', doc.title)[:200]) + '">')

        return '\n    '.join(meta)

    def _generate_tag_badges(self, tags: List[str]) -> str:
        """Generate HTML for tag badges"""
        if not tags:
            return ""

        badges = []
        for tag in tags:
            badges.append(f'<span class="skl-tag">{tag}</span>')

        return '<div class="skl-tags">' + ' '.join(badges) + '</div>'

    def _generate_references_html(self, references: List[str]) -> str:
        """Generate HTML for references section"""
        if not references:
            return "<p>No references</p>"

        ref_links = []
        for ref in references:
            ref_id = ref.replace('.md', '')
            ref_links.append(f'<a href="{quote(ref_id)}.html">{ref_id}</a>')

        return '<p><strong>References:</strong> ' + ' | '.join(ref_links) + '</p>'

    def _generate_sitemap(self, entries: List[Dict]) -> None:
        """Generate XML sitemap"""
        base_url = "https://skl.example.com"  # Configurable

        sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
"""

        for entry in entries:
            sitemap_content += f"""  <url>
    <loc>{base_url}{entry['url']}</loc>
    <lastmod>{entry['lastmod'][:10]}</lastmod>
    <priority>{entry['priority']}</priority>
  </url>
"""

        sitemap_content += "</urlset>"

        sitemap_path = self.output_dir / "sitemap.xml"
        sitemap_path.write_text(sitemap_content, encoding='utf-8')

    def _generate_robots_txt(self) -> None:
        """Generate robots.txt"""
        robots_content = """User-agent: *
Allow: /

Sitemap: https://skl.example.com/sitemap.xml

# SKL Framework - Semantic Knowledge Lattice
# Generated automatically - do not edit manually
"""

        robots_path = self.output_dir / "robots.txt"
        robots_path.write_text(robots_content, encoding='utf-8')

    def _generate_index_page(self) -> None:
        """Generate main index page"""
        # Get workspace analysis
        analysis = self.framework.analyze_workspace()

        # Generate tag cloud
        tag_counts = analysis.get('tags_summary', {})
        tag_cloud = self._generate_tag_cloud(tag_counts)

        # Generate recent documents
        recent_docs = sorted(
            analysis.get('documents', []),
            key=lambda x: x.get('title', ''),
            reverse=False
        )[:20]  # Show 20 most recent

        recent_html = ""
        for doc in recent_docs:
            tags_str = ' '.join([f'<span class="skl-tag-mini">{tag}</span>' for tag in doc.get('tags', [])])
            recent_html += f"""
            <div class="skl-doc-item">
                <h3><a href="html/{quote(doc['id'])}.html">{doc['title']}</a></h3>
                <div class="skl-doc-meta">
                    {tags_str}
                    <span class="skl-refs">{doc.get('references', 0)} refs</span>
                </div>
            </div>"""

        index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SKL Knowledge Base - Semantic Knowledge Lattice</title>
    <meta name="description" content="AI-independent knowledge base with semantic markup and structured data">
    <link rel="stylesheet" href="assets/skl.css">
    <link rel="sitemap" type="application/xml" href="sitemap.xml">
</head>
<body>
    <header class="skl-header">
        <h1 class="skl-main-title">Semantic Knowledge Lattice</h1>
        <p class="skl-subtitle">AI-Independent Knowledge Base</p>
        <nav class="skl-nav">
            <a href="#tags">Tags</a> |
            <a href="#documents">Documents</a> |
            <a href="sitemap.xml">Sitemap</a>
        </nav>
    </header>

    <main class="skl-main">
        <section class="skl-stats">
            <div class="skl-stat">
                <span class="skl-stat-number">{analysis.get('total_files', 0)}</span>
                <span class="skl-stat-label">Documents</span>
            </div>
            <div class="skl-stat">
                <span class="skl-stat-number">{len(tag_counts)}</span>
                <span class="skl-stat-label">Tags</span>
            </div>
            <div class="skl-stat">
                <span class="skl-stat-number">{analysis.get('issues_found', 0)}</span>
                <span class="skl-stat-label">Issues</span>
            </div>
        </section>

        <section id="tags" class="skl-section">
            <h2>Tag Cloud</h2>
            {tag_cloud}
        </section>

        <section id="documents" class="skl-section">
            <h2>Recent Documents</h2>
            <div class="skl-doc-list">
                {recent_html}
            </div>
        </section>
    </main>

    <footer class="skl-footer">
        <p>Generated by SKL Framework | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    </footer>
</body>
</html>"""

        index_path = self.output_dir / "index.html"
        index_path.write_text(index_html, encoding='utf-8')

    def _generate_tag_cloud(self, tag_counts: Dict[str, int]) -> str:
        """Generate HTML tag cloud"""
        if not tag_counts:
            return "<p>No tags found</p>"

        # Calculate font sizes (simple linear scaling)
        max_count = max(tag_counts.values())
        min_count = min(tag_counts.values())

        if max_count == min_count:
            # All tags have same count
            font_sizes = {tag: 14 for tag in tag_counts}
        else:
            # Scale between 12px and 24px
            font_sizes = {}
            for tag, count in tag_counts.items():
                size = 12 + (count - min_count) * (24 - 12) / (max_count - min_count)
                font_sizes[tag] = round(size)

        # Generate HTML
        tag_links = []
        for tag in sorted(tag_counts.keys()):
            count = tag_counts[tag]
            size = font_sizes[tag]
            tag_links.append(f'<a href="tags/{quote(tag)}.html" class="skl-tag-cloud-item" style="font-size: {size}px;" title="{count} documents">{tag}</a>')

        return '<div class="skl-tag-cloud">' + ' '.join(tag_links) + '</div>'

    def _generate_summary_section(self, doc: SKLDocument) -> str:
        """Generate summary section if summary exists"""
        summary_path = self.output_dir / "summaries" / f"{doc.id}_summary.json"
        if not summary_path.exists():
            return ""

        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)

            summary_html = f"""
            <section class="skl-summary">
                <h2>📋 Automatic Summary</h2>
                <div class="skl-summary-content">
                    <p>{summary_data['summary_text']}</p>
            """

            if summary_data.get('key_points'):
                summary_html += '<h3>Key Points:</h3><ul>'
                for point in summary_data['key_points'][:5]:
                    summary_html += f'<li>{point}</li>'
                summary_html += '</ul>'

            summary_html += f"""
                    <div class="skl-summary-meta">
                        <span class="skl-confidence">Confidence: {summary_data['confidence_score']:.1%}</span>
                        <span class="skl-word-count">{summary_data['word_count']} words</span>
                    </div>
                </div>
            </section>
            """

            return summary_html

        except Exception:
            return ""

    def _generate_summaries(self) -> Dict:
        """Generate automatic summaries for all documents (Phase 3)"""
        try:
            from skl_summarizer import SKLSummarizer, SKLSummaryPublisher
        except ImportError:
            return {"error": "SKL Summarizer not available"}

        # Collect all documents
        documents = []
        for md_file in self.workspace.glob("*.md"):
            if md_file.name.startswith('_'):
                continue
            try:
                doc = SKLDocument.from_markdown(md_file)
                documents.append(doc)
            except Exception:
                continue  # Skip problematic documents

        # Generate summaries
        summarizer = SKLSummarizer()
        workspace_summary = summarizer.generate_workspace_summary(documents)

        # Publish summaries
        summary_publisher = SKLSummaryPublisher(self.output_dir)
        return summary_publisher.publish_summaries(workspace_summary)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SKL Multi-Format Publisher")
    parser.add_argument("--publish", action="store_true", help="Publish all documents")
    parser.add_argument("--workspace", type=str, default=".", help="Workspace path")
    parser.add_argument("--output", type=str, default="skl_publish", help="Output directory")

    args = parser.parse_args()

    workspace_path = Path(args.workspace)
    publisher = SKLPublisher(workspace_path, args.output)

    if args.publish:
        print("🚀 Publishing SKL documents...")
        report = publisher.publish_all()

        print("📊 Publishing Complete:")
        print(f"   Processed: {report['total_processed']} documents")
        print(f"   HTML generated: {report['html_generated']}")
        print(f"   JSON-LD generated: {report['jsonld_generated']}")
        print(f"   Sitemap entries: {len(report['sitemap_entries'])}")
        print(f"   Errors: {len(report['errors'])}")

        if report['errors']:
            print("   Errors encountered:")
            for error in report['errors'][:3]:
                print(f"     - {error}")

        print(f"\n📁 Output directory: {publisher.output_dir}")
        print("   ├── index.html (main page)")
        print("   ├── sitemap.xml (SEO sitemap)")
        print("   ├── robots.txt (crawler instructions)")
        print("   ├── html/ (SEO-optimized HTML pages)")
        print("   ├── jsonld/ (structured data)")
        print("   └── assets/ (stylesheets, etc.)")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()