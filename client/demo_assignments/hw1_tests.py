"""Tests for hw1 demo assignment."""

assignment = {
  'name': 'hw1',
  'imports': ['from hw1 import *'],
  'src_files': ['hw1.py'],
  'version': '1.0',

  # Specify tests that should not be locked
  'no_lock': {
  },

  'tests': [
    # Test square
    {
      # The first name is the "official" name.
      'name': ['Q1', 'q1', '1'],
      # No explicit point value -- each test suite counts as 1 point
      'suites': [
        [
          {
            'type': 'code',     # Code question.
            'input': 'square(4)',
            'output': ['16'],   # List of outputs, even if only one
          },
          {
            'type': 'concept',  # Concept question.
            'input': """
            What type of input does the square function take?
            """,
            'output': [
              # Denote multiple choice with a list, rather than
              # a string.
              [
                'number',         # Correct choice comes first.
                'string',
                'None',
              ]
            ],
          },
          {
            # If type is omitted, default type is 'code'.
            'input': """
            x = -5
            square(-5)
            """,
            # Last line in a multiline input is used as the prompt.
            'output': ['25'],
            # Additional statuses can be included here.
            'status': {
              'lock': False,
            }
          },
        ],
      ],
    },
    # Test double
    {
      'name': ['Q2', 'q2', '2'],
      # Point value specified -- points are partitioned evenly across
      # suites.
      'points': 4,
      'suites': [
        [
          {
            'input': 'double(4)',
            'output': ['8'],
          }
        ],
        [
          {
            # Cases with multiple outputs: lines with expected output
            # are denoted by '$ '.
            'input': """
            x = double(4)
            $ x
            $ double(x)
            """,
            'output': ['8', '16']
          },
          {
            'input': """
            x = double(2)
            $ x
            $ square(x)
            """,
            'output': ['4', '16'],
          },
        ],
      ],
    },
  ],
}
