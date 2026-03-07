import unittest
from unittest.mock import MagicMock, patch
from chatterbot.conversation import Statement
from onto_adapter import OntoAdapter

class TestOntoAdapter(unittest.TestCase):

    @patch('onto_adapter.OntoAdapter.load_schema')
    def setUp(self, mock_load_schema):
        self.mock_chatbot = MagicMock()
        self.adapter = OntoAdapter(self.mock_chatbot)

    def test_parse_input_valid(self):
        text = "Alice is a Person"
        result = self.adapter.parse_input(text)
        self.assertEqual(result, {"instance": "Alice", "object": "Person"})

    def test_parse_input_invalid(self):
        text = "This is some random text"
        result = self.adapter.parse_input(text)
        self.assertIsNone(result)

    def test_can_process_valid(self):
        statement = Statement(text="Bob is a Doctor")
        self.assertTrue(self.adapter.can_process(statement))

    def test_can_process_invalid(self):
        statement = Statement(text="Hello world")
        self.assertFalse(self.adapter.can_process(statement))

    def test_get_label(self):
        self.assertEqual(self.adapter.get_label("someVariableName"), "some variable name")
        self.assertEqual(self.adapter.get_label("AnotherVariable"), "another variable")

if __name__ == '__main__':
    unittest.main()
