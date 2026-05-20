#!/usr/bin/env python3
"""
Semantic Knowledge Lattice (SKL) - Core Framework Prototype

This prototype demonstrates the key concepts of the SKL framework:
1. AI-independent base structure
2. Multi-format publishing (Markdown, HTML, JSON-LD)
3. Self-healing validation
4. Intelligent indexing
5. Complexity management

Usage:
    python skl_framework.py --analyze
    python skl_framework.py --migrate
    python skl_framework.py --publish
"""

import json
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import yaml

@dataclass
class SKLDocument:
    """Core document structure for SKL"""
    id: str
    title: str
    content: str
    metadata: Dict[str, Any]
    references: List[Dict[str, str]]
    version: str
    created: str
    modified: str
    checksum: str

    @classmethod
    def from_markdown(cls, file_path: Path) -> 'SKLDocument':
        """Parse markdown file into SKL document"""
        content = file_path.read_text(encoding='utf-8')

        # Extract metadata from frontmatter
        metadata = {}
        if content.startswith('---'):
            try:
                lines = content.split('\n')
                end_idx = lines[1:].index('---') + 1
                frontmatter = '\n'.join(lines[1:end_idx])
                metadata = yaml.safe_load(frontmatter)
                content = '\n'.join(lines[end_idx+1:])
            except:
                pass

        # Extract title
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else file_path.stem

        # Extract references
        references = []
        ref_pattern = r'\[ref:([^\]]+)\]'
        for match in re.finditer(ref_pattern, content):
            ref_str = match.group(1)
            ref_parts = dict(part.split(':') for part in ref_str.split('|'))
            references.append(ref_parts)

        # Generate checksum
        checksum = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Timestamps
        now = datetime.now(timezone.utc).isoformat()

        return cls(
            id=file_path.stem,
            title=title,
            content=content,
            metadata=metadata or {},
            references=references,
            version=metadata.get('version', '1.0'),
            created=metadata.get('created', now),
            modified=now,
            checksum=checksum
        )

class SKLValidator:
    """Self-healing validation system"""

    def __init__(self, workspace_path: Path):
        self.workspace = workspace_path
        self.issues = []

    def validate_document(self, doc: SKLDocument) -> List[str]:
        """Validate single document and return issues"""
        issues = []

        # Check required metadata
        required_fields = ['version', 'created', 'modified']
        for field in required_fields:
            if field not in doc.metadata:
                issues.append(f"Missing metadata field: {field}")

        # Validate references
        for ref in doc.references:
            if 'path' not in ref:
                issues.append(f"Reference missing path: {ref}")
            elif not (self.workspace / ref['path']).exists():
                issues.append(f"Broken reference: {ref['path']}")

        # Check content integrity
        if not doc.content.strip():
            issues.append("Empty document content")

        return issues

    def heal_document(self, doc: SKLDocument) -> SKLDocument:
        """Attempt to automatically fix document issues"""
        # Add missing metadata
        if 'version' not in doc.metadata:
            doc.metadata['version'] = '1.0'
        if 'created' not in doc.metadata:
            doc.metadata['created'] = doc.created
        if 'modified' not in doc.metadata:
            doc.metadata['modified'] = doc.modified

        # Fix reference format issues
        for ref in doc.references:
            if 'path' in ref and 'v' not in ref:
                ref['v'] = 'latest'

        return doc

class SKLPublisher:
    """Multi-format publishing system"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)

    def publish_html(self, doc: SKLDocument) -> Path:
        """Generate SEO-optimized HTML"""
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{doc.title}</title>
    <meta name="description" content="{doc.metadata.get('summary', doc.title)}">
    <script type="application/ld+json">
    {json.dumps(self._generate_jsonld(doc), indent=2)}
    </script>
</head>
<body>
    <article>
        <h1>{doc.title}</h1>
        <div class="metadata">
            <p>Version: {doc.version} | Created: {doc.created} | Modified: {doc.modified}</p>
        </div>
        <div class="content">
            {self._markdown_to_html(doc.content)}
        </div>
    </article>
</body>
</html>"""
        output_path = self.output_dir / f"{doc.id}.html"
        output_path.write_text(html_content, encoding='utf-8')
        return output_path

    def publish_jsonld(self, doc: SKLDocument) -> Path:
        """Generate JSON-LD structured data"""
        jsonld = self._generate_jsonld(doc)
        output_path = self.output_dir / f"{doc.id}.jsonld"
        output_path.write_text(json.dumps(jsonld, indent=2), encoding='utf-8')
        return output_path

    def _generate_jsonld(self, doc: SKLDocument) -> Dict:
        """Generate JSON-LD structured data"""
        return {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": doc.title,
            "description": doc.metadata.get('summary', doc.title),
            "datePublished": doc.created,
            "dateModified": doc.modified,
            "version": doc.version,
            "identifier": doc.id,
            "about": doc.metadata.get('tags', []),
            "mentions": [
                {"@type": "Thing", "name": ref.get('path', '')}
                for ref in doc.references
            ]
        }

    def _markdown_to_html(self, content: str) -> str:
        """Simple markdown to HTML converter (basic implementation)"""
        # Headers
        content = re.sub(r'^### (.*)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
        content = re.sub(r'^## (.*)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
        content = re.sub(r'^# (.*)$', r'<h1>\1</h1>', content, flags=re.MULTILINE)

        # Bold
        content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)

        # Italic
        content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)

        # Paragraphs
        content = re.sub(r'\n\n([^<\n])', r'\n\n<p>\1</p>\n\n', content)
        content = re.sub(r'<p>\n*([^<]+)\n*</p>', r'<p>\1</p>', content)

        return content

class SKLIndexer:
    """Intelligent indexing system"""

    def __init__(self, index_file: Path):
        self.index_file = index_file
        self.index = self._load_index()

    def _load_index(self) -> Dict:
        """Load existing index or create new one"""
        if self.index_file.exists():
            return json.loads(self.index_file.read_text(encoding='utf-8'))
        return {"documents": {}, "references": {}, "tags": {}}

    def index_document(self, doc: SKLDocument):
        """Add document to index"""
        # Document index
        self.index["documents"][doc.id] = {
            "title": doc.title,
            "version": doc.version,
            "tags": doc.metadata.get('tags', []),
            "references": [ref.get('path', '') for ref in doc.references],
            "checksum": doc.checksum
        }

        # Reference index
        for ref in doc.references:
            ref_path = ref.get('path', '')
            if ref_path not in self.index["references"]:
                self.index["references"][ref_path] = []
            if doc.id not in self.index["references"][ref_path]:
                self.index["references"][ref_path].append(doc.id)

        # Tag index
        for tag in doc.metadata.get('tags', []):
            if tag not in self.index["tags"]:
                self.index["tags"][tag] = []
            if doc.id not in self.index["tags"][tag]:
                self.index["tags"][tag].append(doc.id)

    def save_index(self):
        """Save index to disk"""
        self.index_file.write_text(json.dumps(self.index, indent=2), encoding='utf-8')

    def search(self, query: str) -> List[str]:
        """Simple search implementation"""
        results = []
        query_lower = query.lower()

        for doc_id, doc_data in self.index["documents"].items():
            if (query_lower in doc_data["title"].lower() or
                any(query_lower in tag.lower() for tag in doc_data["tags"])):
                results.append(doc_id)

        return results

class SKLFramework:
    """Main SKL framework orchestrator"""

    def __init__(self, workspace_path: Path):
        self.workspace = workspace_path
        self.validator = SKLValidator(workspace_path)
        self.publisher = SKLPublisher(workspace_path / "skl_output")
        self.indexer = SKLIndexer(workspace_path / "skl_index.json")

    def analyze_workspace(self) -> Dict:
        """Analyze entire workspace and return report"""
        report = {
            "total_files": 0,
            "valid_files": 0,
            "issues": [],
            "documents": []
        }

        for md_file in self.workspace.glob("*.md"):
            if md_file.name.startswith('_'):  # Skip system files
                continue

            report["total_files"] += 1
            try:
                doc = SKLDocument.from_markdown(md_file)
                issues = self.validator.validate_document(doc)

                if not issues:
                    report["valid_files"] += 1
                else:
                    report["issues"].extend([f"{md_file.name}: {issue}" for issue in issues])

                report["documents"].append({
                    "id": doc.id,
                    "title": doc.title,
                    "issues": len(issues),
                    "references": len(doc.references)
                })

            except Exception as e:
                report["issues"].append(f"{md_file.name}: Parse error - {str(e)}")

        return report

    def migrate_workspace(self) -> Dict:
        """Migrate and heal workspace documents"""
        migration_report = {
            "migrated": 0,
            "healed": 0,
            "errors": []
        }

        for md_file in self.workspace.glob("*.md"):
            if md_file.name.startswith('_'):
                continue

            try:
                doc = SKLDocument.from_markdown(md_file)
                original_issues = self.validator.validate_document(doc)

                if original_issues:
                    healed_doc = self.validator.heal_document(doc)
                    healed_issues = self.validator.validate_document(healed_doc)

                    if len(healed_issues) < len(original_issues):
                        migration_report["healed"] += 1
                        # In real implementation, would save healed document

                migration_report["migrated"] += 1

            except Exception as e:
                migration_report["errors"].append(f"{md_file.name}: {str(e)}")

        return migration_report

    def publish_workspace(self) -> Dict:
        """Publish workspace to all formats"""
        publish_report = {
            "published": 0,
            "indexed": 0,
            "errors": []
        }

        for md_file in self.workspace.glob("*.md"):
            if md_file.name.startswith('_'):
                continue

            try:
                doc = SKLDocument.from_markdown(md_file)

                # Publish formats
                self.publisher.publish_html(doc)
                self.publisher.publish_jsonld(doc)

                # Index document
                self.indexer.index_document(doc)

                publish_report["published"] += 1
                publish_report["indexed"] += 1

            except Exception as e:
                publish_report["errors"].append(f"{md_file.name}: {str(e)}")

        self.indexer.save_index()
        return publish_report

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Semantic Knowledge Lattice (SKL) Framework")
    parser.add_argument("--analyze", action="store_true", help="Analyze workspace")
    parser.add_argument("--migrate", action="store_true", help="Migrate and heal documents")
    parser.add_argument("--publish", action="store_true", help="Publish to all formats")
    parser.add_argument("--workspace", type=str, default=".", help="Workspace path")

    args = parser.parse_args()

    workspace_path = Path(args.workspace).resolve()
    skl = SKLFramework(workspace_path)

    if args.analyze:
        print("Analyzing workspace...")
        report = skl.analyze_workspace()
        print(f"Analysis Complete:")
        print(f"   Total files: {report['total_files']}")
        print(f"   Valid files: {report['valid_files']}")
        print(f"   Issues found: {len(report['issues'])}")
        if report['issues']:
            print("   Top issues:")
            for issue in report['issues'][:5]:
                print(f"     - {issue}")

    elif args.migrate:
        print("Migrating workspace...")
        report = skl.migrate_workspace()
        print(f"Migration Complete:")
        print(f"   Migrated: {report['migrated']}")
        print(f"   Healed: {report['healed']}")
        print(f"   Errors: {len(report['errors'])}")

    elif args.publish:
        print("Publishing workspace...")
        report = skl.publish_workspace()
        print(f"Publishing Complete:")
        print(f"   Published: {report['published']}")
        print(f"   Indexed: {report['indexed']}")
        print(f"   Errors: {len(report['errors'])}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()</content>
<parameter name="filePath">d:\Keeper-Clean-Loop1\skl_framework.py