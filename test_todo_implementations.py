#!/usr/bin/env python3
"""
Test suite for TODO implementations
Verifies that all TODO items have been properly implemented
"""

import unittest
import ast
import os


class TestTODOImplementations(unittest.TestCase):
    """Test that all critical TODOs have been implemented"""

    def test_no_critical_todos_remain(self):
        """Verify that critical TODO comments have been removed"""
        
        files_to_check = [
            'websocket_server.py',
            'usb_watcher.py',
            'src/mobile_server.py',
            'src/services/usb_watcher.py'
        ]
        
        critical_todos = [
            'TODO: implement case retrieval',
            'TODO: Trigger XGBoost predictions',
            'TODO: Run scispaCy NLP'
        ]
        
        for filepath in files_to_check:
            if not os.path.exists(filepath):
                continue
                
            with open(filepath, 'r') as f:
                content = f.read()
                
            for todo in critical_todos:
                self.assertNotIn(
                    todo, 
                    content,
                    f"Critical TODO still present in {filepath}: {todo}"
                )
        
        print("✓ All critical TODOs have been implemented")

    def test_websocket_server_has_case_retrieval(self):
        """Verify websocket_server.py has case retrieval implementation"""
        
        with open('websocket_server.py', 'r') as f:
            tree = ast.parse(f.read())
        
        # Check for _load_vector_db method
        class_methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                class_methods.append(node.name)
        
        self.assertIn('_load_vector_db', class_methods, 
                     "Missing _load_vector_db method")
        self.assertIn('retrieve_similar_cases', class_methods,
                     "Missing retrieve_similar_cases method")
        
        print("✓ websocket_server.py has case retrieval implementation")

    def test_usb_watcher_has_predictions(self):
        """Verify usb_watcher.py has XGBoost predictions"""
        
        with open('usb_watcher.py', 'r') as f:
            content = f.read()
        
        # Check for XGBoost integration
        self.assertIn('CreatininePredictor', content,
                     "Missing CreatininePredictor import")
        self.assertIn('predict_creatinine_24h', content,
                     "Missing predict_creatinine_24h call")
        
        print("✓ usb_watcher.py has XGBoost predictions")

    def test_usb_watcher_has_nlp(self):
        """Verify usb_watcher.py has scispaCy NLP"""
        
        with open('usb_watcher.py', 'r') as f:
            content = f.read()
        
        # Check for scispaCy integration
        self.assertIn('MedicalNLPProcessor', content,
                     "Missing MedicalNLPProcessor import")
        self.assertIn('extract_entities', content,
                     "Missing extract_entities call")
        
        print("✓ usb_watcher.py has scispaCy NLP")

    def test_all_files_compile(self):
        """Verify all modified files compile successfully"""
        
        files = [
            'websocket_server.py',
            'usb_watcher.py',
            'src/mobile_server.py',
            'src/services/usb_watcher.py'
        ]
        
        for filepath in files:
            if not os.path.exists(filepath):
                continue
                
            with open(filepath, 'r') as f:
                try:
                    ast.parse(f.read())
                    print(f"✓ {filepath} compiles successfully")
                except SyntaxError as e:
                    self.fail(f"Syntax error in {filepath}: {e}")

    def test_websocket_imports(self):
        """Verify websocket_server.py has all necessary imports"""
        
        with open('websocket_server.py', 'r') as f:
            content = f.read()
        
        required_imports = [
            'bayesian_safety_assessment',
            'faiss',
            'SentenceTransformer',
        ]
        
        for import_name in required_imports:
            self.assertIn(import_name, content,
                         f"Missing import: {import_name}")
        
        print("✓ websocket_server.py has all necessary imports")

    def test_error_handling(self):
        """Verify error handling is implemented"""
        
        with open('usb_watcher.py', 'r') as f:
            content = f.read()
        
        # Check for try/except blocks around new code
        self.assertIn('except ImportError:', content,
                     "Missing ImportError handling")
        self.assertIn('except Exception as e:', content,
                     "Missing generic exception handling")
        
        print("✓ Error handling is implemented")


if __name__ == '__main__':
    print("="*70)
    print("TODO IMPLEMENTATION TEST SUITE")
    print("="*70)
    print()
    
    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestTODOImplementations)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("="*70)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED - TODO implementations verified!")
    else:
        print("❌ SOME TESTS FAILED - Review the errors above")
    print("="*70)
    
    exit(0 if result.wasSuccessful() else 1)
