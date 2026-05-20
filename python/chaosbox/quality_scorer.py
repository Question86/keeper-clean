#!/usr/bin/env python3
"""
Quality Scorer - Automated Evaluation and Prioritization of Seed Ideas

Scores seed ideas based on multiple dimensions:
- Technical feasibility
- Business value
- Implementation complexity
- Resource requirements
- Strategic alignment
"""

import re
from typing import Dict, List, Any
from chaosbox.chaosbox_manager import SeedIdea
import os
from pathlib import Path

class QualityScorer:
    """Automated quality scoring system for seed ideas."""

    def __init__(self):
        # Scoring weights (must sum to 1.0)
        self.weights = {
            'technical_feasibility': 0.25,
            'business_value': 0.25,
            'implementation_complexity': 0.20,
            'resource_requirements': 0.15,
            'strategic_alignment': 0.15
        }

        # Technical feasibility keywords
        self.technical_keywords = {
            'high': ['api', 'integration', 'automation', 'algorithm', 'framework', 'library'],
            'medium': ['database', 'testing', 'validation', 'monitoring', 'documentation'],
            'low': ['research', 'analysis', 'design', 'planning']
        }

        # Business value indicators
        self.business_value_keywords = {
            'high': ['efficiency', 'productivity', 'automation', 'optimization', 'performance'],
            'medium': ['quality', 'reliability', 'usability', 'maintainability'],
            'low': ['analysis', 'reporting', 'monitoring', 'documentation']
        }

        # Strategic alignment keywords
        self.strategic_keywords = [
            'ai', 'machine learning', 'automation', 'integration', 'scalability',
            'security', 'performance', 'reliability', 'innovation', 'development'
        ]

        # Research quality indicators
        self.research_indicators = [
            'mathematical', 'theorem', 'proof', 'algorithm', 'stability', 'convergence',
            'optimization', 'analysis', 'framework', 'architecture', 'model', 'training',
            'validation', 'testing', 'evaluation', 'benchmark', 'performance', 'accuracy'
        ]

    def _extract_file_paths(self, text: str) -> List[str]:
        """Extract file and directory paths from idea text."""
        paths = []
        
        # Match quoted paths like "D:\path\to\file.md"
        quoted_paths = re.findall(r'"([^"]*\.[^"]*)"', text)
        paths.extend(quoted_paths)
        
        # Match directory paths in parentheses
        dir_paths = re.findall(r'\("([^"]*)"\)', text)
        paths.extend(dir_paths)
        
        return paths

    def _analyze_linked_content(self, file_paths: List[str]) -> Dict[str, Any]:
        """Analyze content of referenced files and directories."""
        analysis = {
            'total_files': 0,
            'code_files': 0,
            'research_docs': 0,
            'test_files': 0,
            'mathematical_content': 0,
            'research_depth_score': 0.0,
            'technical_maturity': 0.0
        }
        
        workspace_root = Path(__file__).resolve().parent.parent
        
        for path_str in file_paths:
            try:
                # Convert to Path object
                if path_str.startswith('D:'):
                    # Absolute Windows path
                    path = Path(path_str)
                else:
                    # Relative path
                    path = workspace_root / path_str
                
                if path.exists():
                    if path.is_file():
                        analysis['total_files'] += 1
                        content = self._analyze_file_content(path)
                        analysis.update(content)
                    elif path.is_dir():
                        dir_analysis = self._analyze_directory(path)
                        for key, value in dir_analysis.items():
                            if isinstance(value, (int, float)):
                                analysis[key] += value
                            else:
                                analysis[key] = value
                                
            except Exception as e:
                # Skip invalid paths
                continue
                
        return analysis

    def _analyze_file_content(self, file_path: Path) -> Dict[str, Any]:
        """Analyze content of a single file."""
        analysis = {
            'code_files': 0,
            'research_docs': 0,
            'mathematical_content': 0,
            'research_depth_score': 0.0
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().lower()
                
            # Check file type
            if file_path.suffix in ['.py', '.js', '.java', '.cpp', '.c']:
                analysis['code_files'] = 1
            elif file_path.suffix in ['.md', '.txt', '.doc']:
                analysis['research_docs'] = 1
            
            # Analyze content depth
            math_indicators = sum(1 for indicator in self.research_indicators if indicator in content)
            analysis['mathematical_content'] = min(math_indicators, 10)  # Cap at 10
            
            # Research depth based on content length and complexity
            content_length = len(content)
            complexity_score = math_indicators * 0.1 + (content_length / 10000) * 0.1
            analysis['research_depth_score'] = min(complexity_score, 1.0)
            
        except Exception:
            pass
            
        return analysis

    def _analyze_directory(self, dir_path: Path) -> Dict[str, Any]:
        """Analyze content of a directory."""
        analysis = {
            'total_files': 0,
            'code_files': 0,
            'research_docs': 0,
            'test_files': 0,
            'mathematical_content': 0,
            'research_depth_score': 0.0,
            'technical_maturity': 0.0
        }
        
        try:
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    file_analysis = self._analyze_file_content(file_path)
                    analysis['total_files'] += 1
                    
                    for key, value in file_analysis.items():
                        if key in analysis and isinstance(value, (int, float)):
                            analysis[key] += value
                    
                    # Check for test files
                    if 'test' in file_path.name.lower():
                        analysis['test_files'] += 1
                        
        except Exception:
            pass
            
        # Calculate technical maturity based on file diversity
        if analysis['total_files'] > 0:
            maturity = (
                analysis['code_files'] * 0.4 +
                analysis['research_docs'] * 0.3 +
                analysis['test_files'] * 0.3
            ) / analysis['total_files']
            analysis['technical_maturity'] = min(maturity, 1.0)
            
        return analysis

    def score_idea(self, idea: SeedIdea) -> Dict[str, Any]:
        """
        Calculate comprehensive quality score for a seed idea.

        Args:
            idea: The seed idea to score

        Returns:
            Scoring results with individual dimensions and composite score
        """
        text = f"{idea.title} {idea.description}".lower()

        # Extract and analyze linked content
        file_paths = self._extract_file_paths(f"{idea.title} {idea.description}")
        linked_content = self._analyze_linked_content(file_paths)

        # Calculate individual dimension scores
        technical_score = self._score_technical_feasibility(text)
        business_score = self._score_business_value(text)
        complexity_score = self._score_implementation_complexity(text)
        resource_score = self._score_resource_requirements(text)
        strategic_score = self._score_strategic_alignment(text, idea.tags)

        # Boost scores based on linked content analysis
        if linked_content['total_files'] > 0:
            # Boost strategic alignment based on research depth and technical maturity
            research_boost = linked_content['research_depth_score'] * 0.3
            maturity_boost = linked_content['technical_maturity'] * 0.2
            strategic_score = min(1.0, strategic_score + research_boost + maturity_boost)
            
            # Boost business value based on mathematical content and code quality
            math_boost = min(linked_content['mathematical_content'] * 0.05, 0.2)
            code_boost = linked_content['code_files'] * 0.1
            business_score = min(1.0, business_score + math_boost + code_boost)
            
            # Boost technical feasibility based on existing code and tests
            if linked_content['code_files'] > 0:
                technical_score = min(1.0, technical_score + 0.2)
            if linked_content['test_files'] > 0:
                technical_score = min(1.0, technical_score + 0.1)

        # Calculate weighted composite score
        composite_score = (
            technical_score * self.weights['technical_feasibility'] +
            business_score * self.weights['business_value'] +
            complexity_score * self.weights['implementation_complexity'] +
            resource_score * self.weights['resource_requirements'] +
            strategic_score * self.weights['strategic_alignment']
        )

        # Determine quality tier
        if composite_score >= 0.8:
            tier = "EXCELLENT"
        elif composite_score >= 0.7:
            tier = "GOOD"
        elif composite_score >= 0.6:
            tier = "FAIR"
        elif composite_score >= 0.5:
            tier = "POOR"
        else:
            tier = "UNACCEPTABLE"

        return {
            'composite_score': round(composite_score, 3),
            'tier': tier,
            'dimensions': {
                'technical_feasibility': round(technical_score, 3),
                'business_value': round(business_score, 3),
                'implementation_complexity': round(complexity_score, 3),
                'resource_requirements': round(resource_score, 3),
                'strategic_alignment': round(strategic_score, 3)
            },
            'linked_content_analysis': linked_content,
            'recommendation': self._generate_recommendation(composite_score, {
                'technical_feasibility': technical_score,
                'business_value': business_score,
                'implementation_complexity': complexity_score,
                'resource_requirements': resource_score,
                'strategic_alignment': strategic_score
            })
        }

    def _score_technical_feasibility(self, text: str) -> float:
        """Score technical feasibility (0-1)."""
        score = 0.5  # Base score

        # Count keyword matches
        high_matches = sum(1 for kw in self.technical_keywords['high'] if kw in text)
        medium_matches = sum(1 for kw in self.technical_keywords['medium'] if kw in text)
        low_matches = sum(1 for kw in self.technical_keywords['low'] if kw in text)

        # Adjust score based on matches
        if high_matches > 0:
            score += 0.2 * min(high_matches, 3)  # Cap at 3 matches
        if medium_matches > 0:
            score += 0.1 * min(medium_matches, 5)
        if low_matches > 2:  # Too many low-value terms reduce score
            score -= 0.1

        # Check for specific technical indicators
        if re.search(r'\b(api|endpoint|database|algorithm)\b', text):
            score += 0.1
        if re.search(r'\b(integrat|connect|interface)\b', text):
            score += 0.1

        return min(1.0, max(0.0, score))

    def _score_business_value(self, text: str) -> float:
        """Score business value (0-1)."""
        score = 0.5  # Base score

        # Count keyword matches
        high_matches = sum(1 for kw in self.business_value_keywords['high'] if kw in text)
        medium_matches = sum(1 for kw in self.business_value_keywords['medium'] if kw in text)

        # Adjust score based on matches
        if high_matches > 0:
            score += 0.15 * min(high_matches, 4)
        if medium_matches > 0:
            score += 0.1 * min(medium_matches, 4)

        # Check for quantifiable benefits
        if re.search(r'\b(\d+%|percent|times|hours|days|cost|save)\b', text):
            score += 0.1

        # Check for user impact
        if re.search(r'\b(user|customer|client|developer|team)\b', text):
            score += 0.1

        return min(1.0, max(0.0, score))

    def _score_implementation_complexity(self, text: str) -> float:
        """
        Score implementation complexity (0-1).
        Note: Lower complexity = higher score (easier to implement)
        """
        complexity_indicators = [
            'complex', 'difficult', 'challenging', 'advanced', 'sophisticated',
            'multiple', 'integration', 'architecture', 'framework', 'algorithm',
            'security', 'performance', 'scalability', 'distributed'
        ]

        word_count = len(text.split())
        sentence_count = len(re.split(r'[.!?]+', text))

        # Base complexity from text length and structure
        base_complexity = min(1.0, (word_count / 500) + (sentence_count / 20))

        # Add complexity from indicators
        indicator_matches = sum(1 for indicator in complexity_indicators if indicator in text)
        indicator_complexity = min(0.5, indicator_matches * 0.1)

        total_complexity = base_complexity + indicator_complexity

        # Return inverse (lower complexity = higher score)
        return 1.0 - min(0.8, total_complexity)

    def _score_resource_requirements(self, text: str) -> float:
        """
        Score resource requirements (0-1).
        Note: Lower resource requirements = higher score (easier to resource)
        """
        resource_indicators = [
            'extensive', 'significant', 'substantial', 'major', 'large',
            'team', 'multiple', 'specialized', 'expert', 'training',
            'infrastructure', 'hardware', 'third.party', 'vendor'
        ]

        # Base resource score (assume minimal resources)
        resource_score = 0.2

        # Add resource requirements from indicators
        indicator_matches = sum(1 for indicator in resource_indicators if indicator in text)
        resource_score += min(0.6, indicator_matches * 0.15)

        # Check for specific resource mentions
        if re.search(r'\b(team|multiple|specialized|expert)\b', text):
            resource_score += 0.2

        # Return inverse (lower resources = higher score)
        return 1.0 - min(0.9, resource_score)

    def _score_strategic_alignment(self, text: str, tags: List[str]) -> float:
        """Score strategic alignment with project goals (0-1)."""
        score = 0.3  # Base score

        # Check keyword matches
        keyword_matches = sum(1 for kw in self.strategic_keywords if kw in text)
        score += min(0.4, keyword_matches * 0.1)

        # Check tag alignment
        strategic_tags = ['ai', 'automation', 'integration', 'performance', 'security', 'quality']
        tag_matches = sum(1 for tag in tags if tag.lower() in strategic_tags)
        score += min(0.3, tag_matches * 0.15)

        return min(1.0, max(0.0, score))

    def _generate_recommendation(self, composite_score: float, dimensions: Dict[str, float]) -> str:
        """Generate a recommendation based on scoring results."""
        if composite_score >= 0.8:
            return "HIGH PRIORITY: Excellent quality idea, proceed with implementation."

        if composite_score >= 0.7:
            return "APPROVE: Good quality idea with strong technical and business merit."

        if composite_score >= 0.6:
            return "CONDITIONAL: Fair quality, may proceed with refinements or additional analysis."

        if composite_score >= 0.5:
            return "REVIEW: Poor quality, requires significant improvements before consideration."

        # Find weakest dimensions
        weakest = min(dimensions.items(), key=lambda x: x[1])
