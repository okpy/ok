"""Tests for Q1: square"""

test = {
  # Optional information for each type of test case to set up, specific
  # to this test (q1)
  'params': {
    'doctest': {
      'setup': """
      # Setup code for doctest-style TestCases. This setup code is
      # evaluated before every doctest testcase.
      """,
      'teardown': """
      # Teardown code for doctest-style TestCases. This code is
      # evaluated after every doctest testcase, even ones that fail.
      """,
      'cache': """
      # Cache code for doctest-style TestCases. This code is only
      # evaluated once, before any test cases are evaluated.
      """,
    },
  },
  'suites': [
    [
      {
        'type': 'concept',
        'question': """
        What is the domain and range of the square function?
        """,
        'answer': """
        Domain is numbers. Range is numbers
        """,
        'choices': [
          'Domain is numbers. Range is strings',
          'Domain is strings. Range is numbers',
          'Domain is strings. Range is strings',
        ],
      },
      {
        'type': 'doctest',
        'test': """
        >>> square(3)
        9
        """,
      },
    ],
    [
      {
        'type': 'doctest',
        'test': """
        >>> square(-2)
        4
        # explanation: Squaring a negative number
        # choice: -4
        # choice: 2
        # choice: None
        """,
      },
      {
        'type': 'doctest',
        'test': """
        >>> square(0)
        0
        # explanation: Squaring zero
        """,
        'teardown': """
        print('Optional Teardown code for the testcase goes here')
        """
      },
    ],
  ],
}
