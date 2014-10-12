from client.utils import formatting
import unittest

class PrettyJsonTest(unittest.TestCase):
    def assertFormat(self, expect, json):
        self.assertEqual(formatting.dedent(expect),
                         formatting.prettyjson(json))

    def testInt(self):
        self.assertFormat('42', 42)

    def testFloat(self):
        self.assertFormat('3.14', 3.14)

    def testString_singleLine(self):
        self.assertFormat("'hello world'", 'hello world')

    def testString_multipleLines(self):
        self.assertFormat("""
        r\"\"\"
        hello
        world
        \"\"\"
        """, "hello\nworld")

    def testString_multipleLinesSurroundingNewlines(self):
        self.assertFormat("""
        r\"\"\"
        hello
        world
        \"\"\"
        """, "\nhello\nworld\n")

    def testString_rawStringSingleLine(self):
        self.assertFormat(r"""
        'hello \\ there'
        """, r"hello \ there")

    def testString_rawStringMultiLine(self):
        self.assertFormat("""
        r\"\"\"
        hello \\
            there
        \"\"\"
        """, r"""
        hello \
            there
        """)

    def testList_onlyPrimitives(self):
        self.assertFormat("""
        [
          42,
          3.14,
          'hello world',
          r\"\"\"
          hello
          world
          \"\"\"
        ]
        """, [
            42,
            3.14,
            'hello world',
            'hello\nworld'
        ])

    def testList_nestedLists(self):
        self.assertFormat("""
        [
          42,
          [
            3.14
          ]
        ]
        """, [
            42,
            [3.14]
        ])

    def testDict_onlyPrimitives(self):
        self.assertFormat("""
        {
          'answer': 'hello world',
          'multi': r\"\"\"
          answer
          here
          \"\"\",
          'secret': 42
        }
        """, {
            'answer': 'hello world',
            'multi': 'answer\nhere',
            'secret': 42,
        })

    def testDict_nestedDicts(self):
        self.assertFormat("""
        {
          'answer': {
            'test': 42
          },
          'solution': 3.14
        }
        """, {
            'answer': {
                'test': 42
            },
            'solution': 3.14,
        })

