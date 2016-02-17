import unittest
from jsonschema import SchemaError
from minibus import MiniBusClient

class SyntaxTest(unittest.TestCase):
    def setUp(self):
        self.client = MiniBusClient()

    def callback(self):
        pass

    def callback2(self):
        pass

    def test_sub_good(self):
        self.client.subscribe("test_sub_good", {'type': "number"}, self.callback)

    def test_sub_bad_schema(self):
        self.assertRaises(SchemaError, self.client.subscribe, 
                "test_sub_bad_schema", {"type": "orange"}, self.callback)

    def test_sub_schema_mismatch(self):
        self.client.subscribe("test_sub_schema_mismatch", {"type": "number"}, self.callback)
        self.assertRaises(Exception, self.client.subscribe,
                "test_sub_schema_mismatch", {"type": "string"}, self.callback2)

    def test_sub_schema_dupcallback(self):
        self.client.subscribe("test_sub_schema_dupcallback", {"type": "number"}, self.callback)
        self.assertRaises(Exception, self.client.subscribe,
                "test_sub_schema_dupcallback", {"type": "number"}, self.callback)

if __name__ == "__main__":
    unittest.main()
