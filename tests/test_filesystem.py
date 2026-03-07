import unittest
import os
import shutil
from filesystem.utils import makedirs, file_exists

class TestFilesystemUtils(unittest.TestCase):

    def setUp(self):
        self.test_dir = "test_data_dir"
        self.test_file = "test_data_file.txt"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_makedirs_creates_directory(self):
        self.assertFalse(os.path.exists(self.test_dir))
        makedirs(self.test_dir)
        self.assertTrue(os.path.exists(self.test_dir))

    def test_makedirs_does_not_raise_if_exists(self):
        os.makedirs(self.test_dir)
        try:
            makedirs(self.test_dir)
        except OSError:
            self.fail("makedirs() raised OSError unexpectedly!")

    def test_file_exists_returns_true_for_existing_file(self):
        with open(self.test_file, 'w') as f:
            f.write("test")
        self.assertTrue(file_exists(self.test_file))

    def test_file_exists_returns_false_for_missing_file(self):
        self.assertFalse(file_exists("nonexistent_file.txt"))

if __name__ == '__main__':
    unittest.main()
