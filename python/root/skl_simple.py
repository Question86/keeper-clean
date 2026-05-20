#!/usr/bin/env python3
"""
SKL Framework Prototype - Enhanced Version with Tags Support
Demonstrates core concepts of the Semantic Knowledge Lattice with metadata tags
"""

import json
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import re

@dataclass
class SKLDocument:
    """Core document structure with tags support"""
    id: str
    title: str
    content: str = ""
    tags: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)

    @classmethod
    def from_markdown(cls, file_path: Path) -> 'SKLDocument':
        """Parse markdown file with metadata and tags support"""
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            content = file_path.read_text(encoding='latin-1')

        # Extract YAML frontmatter
        metadata = {}
        body_content = content
        if content.startswith('---'):
            try:
                lines = content.split('\n')
                end_idx = -1
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() == '---':
                        end_idx = i
                        break
                if end_idx > 0:
                    frontmatter = '\n'.join(lines[1:end_idx])
                    metadata = yaml.safe_load(frontmatter) or {}
                    body_content = '\n'.join(lines[end_idx+1:])
            except Exception:
                pass  # If YAML parsing fails, continue without metadata

        # Extract title (prioritize YAML frontmatter, fallback to H1, then filename)
        title = file_path.stem.replace('_', ' ').title()
        if 'title' in metadata and metadata['title']:
            title = metadata['title']
        else:
            title_match = re.search(r'^#\s+(.+)$', body_content, re.MULTILINE)
            if title_match:
                title = title_match.group(1).strip()

        # Extract tags from metadata
        tags = []
        if 'tags' in metadata:
            if isinstance(metadata['tags'], list):
                tags = metadata['tags']
            elif isinstance(metadata['tags'], str):
                tags = [tag.strip() for tag in metadata['tags'].split(',')]
        elif 'categories' in metadata:
            # Also check for categories as alternative
            if isinstance(metadata['categories'], list):
                tags = metadata['categories']
            elif isinstance(metadata['categories'], str):
                tags = [tag.strip() for tag in metadata['categories'].split(',')]

        # Extract references
        references = []
        ref_pattern = r'\[ref:([^\]]+)\]'
        for match in re.finditer(ref_pattern, body_content):
            ref_str = match.group(1)
            # Parse reference format: path|v:version|tags:tag1,tag2|src:source
            ref_parts = {}
            for part in ref_str.split('|'):
                if ':' in part:
                    key, value = part.split(':', 1)
                    ref_parts[key.strip()] = value.strip()
            if 'path' in ref_parts:
                references.append(ref_parts['path'])

        return cls(
            id=file_path.stem,
            title=title,
            content=body_content,
            tags=tags,
            references=references,
            metadata=metadata
        )

class SKLFramework:
    """Enhanced SKL framework with tags support"""

    def __init__(self, workspace_path: Path):
        self.workspace = workspace_path

    def analyze_workspace(self) -> Dict:
        """Analyze workspace for issues and extract tags"""
        report = {
            "total_files": 0,
            "issues_found": 0,
            "documents": [],
            "tags_summary": {},
            "untagged_documents": []
        }

        for md_file in self.workspace.glob("*.md"):
            if md_file.name.startswith('_'):
                continue

            report["total_files"] += 1

            try:
                doc = SKLDocument.from_markdown(md_file)
            except Exception as e:
                # Create basic document if parsing fails
                doc = SKLDocument(
                    id=md_file.stem,
                    title=md_file.stem.replace('_', ' ').title(),
                    issues=[f"Parse error: {str(e)}"]
                )

            # Analyze issues
            issues = []
            if len(doc.content.strip()) == 0:
                issues.append("Empty file")
            if not doc.references:
                issues.append("No references found")
            if not doc.tags:
                report["untagged_documents"].append(doc.id)

            doc.issues.extend(issues)

            # Update tags summary
            for tag in doc.tags:
                if tag not in report["tags_summary"]:
                    report["tags_summary"][tag] = 0
                report["tags_summary"][tag] += 1

            report["issues_found"] += len(doc.issues)
            report["documents"].append({
                "id": doc.id,
                "title": doc.title,
                "tags": doc.tags,
                "references": len(doc.references),
                "issues": len(doc.issues)
            })

        return report

    def add_tags_to_document(self, doc_id: str, tags: List[str]) -> bool:
        """Add tags to an existing document by updating its frontmatter"""
        md_file = self.workspace / f"{doc_id}.md"
        if not md_file.exists():
            return False

        try:
            doc = SKLDocument.from_markdown(md_file)

            # Add new tags to existing tags
            for tag in tags:
                if tag not in doc.tags:
                    doc.tags.append(tag)

            # Update metadata
            doc.metadata['tags'] = doc.tags

            # Reconstruct frontmatter
            frontmatter = yaml.dump(doc.metadata, default_flow_style=False, allow_unicode=True)
            new_content = f"---\n{frontmatter}---\n\n{doc.content}"

            # Write back to file
            md_file.write_text(new_content, encoding='utf-8')
            return True

        except Exception:
            return False

    def bulk_tag_documents(self, tag_rules: Dict[str, List[str]]) -> Dict:
        """Apply tagging rules to multiple documents"""
        results = {
            "processed": 0,
            "tagged": 0,
            "errors": []
        }

        for md_file in self.workspace.glob("*.md"):
            if md_file.name.startswith('_'):
                continue

            results["processed"] += 1

            try:
                doc = SKLDocument.from_markdown(md_file)
                new_tags = []

                # Apply rules based on content patterns
                for rule_name, patterns in tag_rules.items():
                    for pattern in patterns:
                        if pattern.lower() in doc.content.lower() or pattern.lower() in doc.title.lower():
                            if rule_name not in doc.tags:
                                new_tags.append(rule_name)
                            break

                if new_tags:
                    if self.add_tags_to_document(doc.id, new_tags):
                        results["tagged"] += 1
                    else:
                        results["errors"].append(f"Failed to tag {doc.id}")

            except Exception as e:
                results["errors"].append(f"Error processing {md_file.name}: {str(e)}")

        return results

    def generate_summaries(self, output_dir: str = "skl_summaries") -> Dict:
        """Generate automatic summaries for all documents (Phase 3 feature)"""
        # Import summarizer here to avoid circular imports
        try:
            from skl_summarizer import SKLSummarizer, SKLSummaryPublisher
        except ImportError:
            return {"error": "SKL Summarizer not available. Install required dependencies."}

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        report = {
            "total_processed": 0,
            "summaries_generated": 0,
            "errors": []
        }

        try:
            summarizer = SKLSummarizer()
            documents = []

            # Collect all documents
            for md_file in self.workspace.glob("*.md"):
                if md_file.name.startswith('_'):
                    continue

                try:
                    doc = SKLDocument.from_markdown(md_file)
                    documents.append(doc)
                    report["total_processed"] += 1
                except Exception as e:
                    report["errors"].append(f"Failed to parse {md_file.name}: {str(e)}")

            # Generate workspace summary
            workspace_summary = summarizer.generate_workspace_summary(documents)

            # Publish summaries
            publisher = SKLSummaryPublisher(Path(output_dir))
            publish_report = publisher.publish_summaries(workspace_summary)

            report["summaries_generated"] = publish_report["summary_files_generated"]
            report["errors"].extend(publish_report["errors"])

        except Exception as e:
            report["errors"].append(f"Summarization error: {str(e)}")

        return report

def main():
    import argparse

    parser = argparse.ArgumentParser(description="SKL Framework Prototype with Tags Support")
    parser.add_argument("--analyze", action="store_true", help="Analyze workspace")
    parser.add_argument("--tags", action="store_true", help="Show tags analysis")
    parser.add_argument("--export-tags", type=str, help="Export documents with specific tag to JSON")
    parser.add_argument("--add-tags", nargs=2, metavar=('DOC_ID', 'TAGS'), help="Add tags to a document (TAGS as comma-separated)")
    parser.add_argument("--bulk-tag", action="store_true", help="Apply automatic tagging rules to workspace")
    parser.add_argument("--summarize", action="store_true", help="Generate automatic summaries for all documents (Phase 3)")
    parser.add_argument("--output-dir", type=str, default="skl_output", help="Output directory for generated content")

    args = parser.parse_args()

    workspace_path = Path(".")
    skl = SKLFramework(workspace_path)

    if args.analyze:
        print("Analyzing workspace...")
        report = skl.analyze_workspace()
        print(f"Analysis Complete:")
        print(f"  Total files: {report['total_files']}")
        print(f"  Issues found: {report['issues_found']}")
        print(f"  Documents analyzed: {len(report['documents'])}")
        print(f"  Unique tags found: {len(report['tags_summary'])}")
        print(f"  Untagged documents: {len(report['untagged_documents'])}")

        if report['documents']:
            print("\nSample documents:")
            for doc in report['documents'][:3]:
                tags_str = f" [{', '.join(doc['tags'])}]" if doc['tags'] else ""
                print(f"  - {doc['title']}{tags_str} ({doc['issues']} issues, {doc['references']} refs)")

    elif args.tags:
        print("Tags Analysis...")
        report = skl.analyze_workspace()
        print(f"Tags Summary ({len(report['tags_summary'])} unique tags):")

        # Sort tags by frequency
        sorted_tags = sorted(report['tags_summary'].items(), key=lambda x: x[1], reverse=True)
        for tag, count in sorted_tags[:10]:  # Show top 10
            print(f"  {tag}: {count} documents")

        if report['untagged_documents']:
            print(f"\nUntagged documents ({len(report['untagged_documents'])}):")
            for doc_id in report['untagged_documents'][:5]:
                print(f"  - {doc_id}")

    elif args.export_tags:
        print(f"Exporting documents with tag '{args.export_tags}'...")
        report = skl.analyze_workspace()

        tagged_docs = [
            doc for doc in report['documents']
            if args.export_tags in doc['tags']
        ]

        if tagged_docs:
            export_data = {
                "tag": args.export_tags,
                "document_count": len(tagged_docs),
                "documents": tagged_docs
            }

            export_file = Path(f"documents_with_tag_{args.export_tags}.json")
            export_file.write_text(json.dumps(export_data, indent=2), encoding='utf-8')
            print(f"Exported {len(tagged_docs)} documents to {export_file}")
        else:
            print(f"No documents found with tag '{args.export_tags}'")

    elif args.add_tags:
        doc_id, tags_str = args.add_tags
        tags = [tag.strip() for tag in tags_str.split(',')]
        print(f"Adding tags {tags} to document {doc_id}...")

        if skl.add_tags_to_document(doc_id, tags):
            print("Tags added successfully")
        else:
            print("Failed to add tags. Document may not exist.")

    elif args.bulk_tag:
        print("Applying bulk tagging rules...")

        # Define tagging rules
        tag_rules = {
            "analysis": ["analysis", "audit", "review", "assessment"],
            "documentation": ["readme", "guide", "manual", "docs"],
            "framework": ["framework", "architecture", "system", "skl"],
            "code": ["python", "script", "function", "class", "module"],
            "configuration": ["config", "settings", "parameters", "setup"],
            "task": ["task", "todo", "objective", "goal"],
            "report": ["report", "summary", "findings", "results"],
            "learning": ["learning", "insight", "lesson", "knowledge"]
        }

        results = skl.bulk_tag_documents(tag_rules)
        print(f"Bulk tagging complete:")
        print(f"  Processed: {results['processed']} documents")
        print(f"  Tagged: {results['tagged']} documents")
        print(f"  Errors: {len(results['errors'])}")

        if results['errors']:
            print("Errors encountered:")
            for error in results['errors'][:3]:
                print(f"  - {error}")

    elif args.summarize:
        print("Generating automatic summaries (Phase 3)...")
        summary_report = skl.generate_summaries(args.output_dir)
        
        if "error" in summary_report:
            print(f"❌ Summarization failed: {summary_report['error']}")
        else:
            print("✅ Summarization complete:")
            print(f"  Documents processed: {summary_report['total_processed']}")
            print(f"  Summary files generated: {summary_report['summaries_generated']}")
            print(f"  Output directory: {args.output_dir}/summaries")
            
            if summary_report['errors']:
                print(f"  Errors: {len(summary_report['errors'])}")
                for error in summary_report['errors'][:3]:
                    print(f"    - {error}")

    else:
        parser.print_help()

    if args.analyze:
        print("Analyzing workspace...")
        report = skl.analyze_workspace()
        print(f"Analysis Complete:")
        print(f"  Total files: {report['total_files']}")
        print(f"  Issues found: {report['issues_found']}")
        print(f"  Documents analyzed: {len(report['documents'])}")
        print(f"  Unique tags found: {len(report['tags_summary'])}")
        print(f"  Untagged documents: {len(report['untagged_documents'])}")

        if report['documents']:
            print("\nSample documents:")
            for doc in report['documents'][:3]:
                tags_str = f" [{', '.join(doc['tags'])}]" if doc['tags'] else ""
                print(f"  - {doc['title']}{tags_str} ({doc['issues']} issues, {doc['references']} refs)")

    elif args.tags:
        print("Tags Analysis...")
        report = skl.analyze_workspace()
        print(f"Tags Summary ({len(report['tags_summary'])} unique tags):")

        # Sort tags by frequency
        sorted_tags = sorted(report['tags_summary'].items(), key=lambda x: x[1], reverse=True)
        for tag, count in sorted_tags[:10]:  # Show top 10
            print(f"  {tag}: {count} documents")

        if report['untagged_documents']:
            print(f"\nUntagged documents ({len(report['untagged_documents'])}):")
            for doc_id in report['untagged_documents'][:5]:
                print(f"  - {doc_id}")

    elif args.export_tags:
        print(f"Exporting documents with tag '{args.export_tags}'...")
        report = skl.analyze_workspace()

        tagged_docs = [
            doc for doc in report['documents']
            if args.export_tags in doc['tags']
        ]

        if tagged_docs:
            export_data = {
                "tag": args.export_tags,
                "document_count": len(tagged_docs),
                "documents": tagged_docs
            }

            export_file = f"skl_export_{args.export_tags}.json"
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            print(f"Exported {len(tagged_docs)} documents to {export_file}")
        else:
            print(f"No documents found with tag '{args.export_tags}'")

    elif args.add_tags:
        doc_id, tags_str = args.add_tags
        tags = [tag.strip() for tag in tags_str.split(',')]

        print(f"Adding tags {tags} to document '{doc_id}'...")
        if skl.add_tags_to_document(doc_id, tags):
            print("Tags added successfully!")
        else:
            print("Failed to add tags. Document may not exist.")

    elif args.bulk_tag:
        print("Applying bulk tagging rules...")

        # Define tagging rules
        tag_rules = {
            "analysis": ["analysis", "audit", "review", "assessment"],
            "documentation": ["readme", "guide", "manual", "docs"],
            "framework": ["framework", "architecture", "system", "skl"],
            "code": ["python", "script", "function", "class", "module"],
            "configuration": ["config", "settings", "parameters", "setup"],
            "task": ["task", "todo", "objective", "goal"],
            "report": ["report", "summary", "findings", "results"],
            "learning": ["learning", "insight", "lesson", "knowledge"]
        }

        results = skl.bulk_tag_documents(tag_rules)
        print(f"Bulk tagging complete:")
        print(f"  Processed: {results['processed']} documents")
        print(f"  Tagged: {results['tagged']} documents")
        print(f"  Errors: {len(results['errors'])}")

        if results['errors']:
            print("Errors encountered:")
            for error in results['errors'][:3]:
                print(f"  - {error}")

    elif args.summarize:
        print("Generating automatic summaries (Phase 3)...")
        summary_report = skl.generate_summaries(args.output_dir)
        
        if "error" in summary_report:
            print(f"❌ Summarization failed: {summary_report['error']}")
        else:
            print("✅ Summarization complete:")
            print(f"  Documents processed: {summary_report['total_processed']}")
            print(f"  Summary files generated: {summary_report['summaries_generated']}")
            print(f"  Output directory: {args.output_dir}/summaries")
            
            if summary_report['errors']:
                print(f"  Errors: {len(summary_report['errors'])}")
                for error in summary_report['errors'][:3]:
                    print(f"    - {error}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()