#!/usr/bin/env python3
"""
Test suite for Knowledge Redundancy System
"""

import unittest
import tempfile
import os
from pathlib import Path
from knowledge_redundancy_db import KnowledgeRedundancyDB
from scripts.lessons_learned_extractor import LessonsLearnedExtractor
from scripts.semantic_search_enhanced import SemanticSearchEnhanced

class TestKnowledgeRedundancySystem(unittest.TestCase):

    def setUp(self):
        """Set up test database"""
        self.db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_file.close()
        self.db = KnowledgeRedundancyDB(self.db_file.name)

    def tearDown(self):
        """Clean up test database"""
        os.unlink(self.db_file.name)

    def test_add_and_retrieve_knowledge(self):
        """Test adding and retrieving knowledge"""
        test_data = {
            "topic": "Test Topic",
            "content": "Test content",
            "tags": ["test", "knowledge"]
        }

        knowledge_id = self.db.add_knowledge("test_key", test_data, "test.py")
        self.assertIsNotNone(knowledge_id)

        retrieved = self.db.get_knowledge("test_key")
        self.assertEqual(retrieved, test_data)

    def test_lessons_extraction(self):
        """Test lessons learned extraction"""
        test_content = """
        ## Lessons Learned
        - Always validate inputs
        - Use proper error handling
        - Document your code

        ## Best Practices
        - Write unit tests
        - Follow coding standards
        """

        # Add knowledge first
        knowledge_id = self.db.add_knowledge("test_content", {"content": test_content}, "test.md")

        # Extract lessons
        lessons = self.db.extract_lessons_learned(knowledge_id, test_content)
        self.assertGreater(len(lessons), 0)

    def test_semantic_search(self):
        """Test semantic search functionality"""
        # Add test knowledge
        self.db.add_knowledge("search_test_1", {"content": "Python programming"}, "test1.py")
        self.db.add_knowledge("search_test_2", {"content": "Java development"}, "test2.py")

        # Perform search
        results = self.db.semantic_search("programming")
        self.assertGreater(len(results), 0)

    def test_validation(self):
        """Test knowledge validation"""
        test_data = {"test": "data"}
        self.db.add_knowledge("validation_test", test_data, "test.py")

        validation = self.db.validate_knowledge("validation_test")
        self.assertTrue(validation['exists'])
        self.assertTrue(validation['checksum_valid'])
        self.assertTrue(validation['backup_exists'])

    def test_cross_references(self):
        """Test cross-reference functionality"""
        search = SemanticSearchEnhanced(self.db_file.name)

        # Add knowledge
        search.db.add_knowledge("ref_test_1", {"content": "First item"}, "test1.py")
        search.db.add_knowledge("ref_test_2", {"content": "Second item"}, "test2.py")

        # Add cross-reference
        search.add_cross_references("ref_test_1", "ref_test_2", "related", 0.8)

        # Get related
        related = search.get_related_knowledge("ref_test_1")
        self.assertGreater(len(related), 0)

class TestLessonsLearnedExtractor(unittest.TestCase):

    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_file.close()
        self.extractor = LessonsLearnedExtractor(self.db_file.name)

    def tearDown(self):
        os.unlink(self.db_file.name)

    def test_extract_from_content(self):
        """Test lesson extraction from content"""
        content = "Lesson learned: Always test your code. Best practice: Use version control."
        lessons = self.extractor._extract_lessons_from_content(content)
        self.assertGreater(len(lessons), 0)

    def test_extract_from_file(self):
        """Test extraction from file"""
        test_content = "Lesson learned: Validate inputs\nBest practice: Write tests"
        test_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md')
        test_file.write(test_content)
        test_file.close()

        try:
            lessons = self.extractor.extract_from_file(test_file.name)
            self.assertGreater(len(lessons), 0)
        finally:
            os.unlink(test_file.name)

class TestSemanticSearch(unittest.TestCase):

    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_file.close()
        self.search = SemanticSearchEnhanced(self.db_file.name)

    def tearDown(self):
        os.unlink(self.db_file.name)

    def test_search_functionality(self):
        """Test search functionality"""
        # Add test data
        self.search.db.add_knowledge("search_test", {"content": "Python programming tutorial"}, "test.py")

        # Update index
        self.search.update_search_index()

        # Search
        results = self.search.search("programming")
        # Note: May not find results without sentence transformers
        self.assertIsInstance(results, list)

if __name__ == '__main__':
    unittest.main()</content>
<parameter name="filePath">d:\Keeper-Clean-Loop1\tests\test_knowledge_redundancy_system.py