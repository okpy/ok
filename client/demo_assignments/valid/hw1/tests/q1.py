test = {
  'name': 'q1',
  'params': {
    'doctest': {
      'cache': """
      # Cache code for doctest-style TestCases. This code is only
      # evaluated once, before any test cases are evaluated.
      """,
      'setup': """
      # Setup code for doctest-style TestCases. This setup code is
      # evaluated before every doctest testcase.
      """,
      'teardown': """
      # Teardown code for doctest-style TestCases. This code is
      # evaluated after every doctest testcase, even ones that fail.
      """
    }
  },
  'points': 3,
  'suites': [
    [
      {
        'answer': 'Domain is numbers. Range is numbers',
        'choices': [
          'Domain is numbers. Range is numbers',
          'Domain is numbers. Range is strings',
          'Domain is strings. Range is numbers',
          'Domain is strings. Range is strings'
        ],
        'locked': False,
        'question': 'What is the domain and range of the square function?',
        'type': 'concept'
      },
      {
        'locked': False,
        'test': """
        >>> square(3)
        9
        """,
        'type': 'doctest'
      }
    ],
    [
      {
        'locked': False,
        'test': """
        >>> square(-2)
        4
        # explanation: Squaring a negative number
        # choice: -4
        # choice: 4
        # choice: 2
        # choice: None
        """,
        'type': 'doctest'
      },
      {
        'locked': False,
        'teardown': """
        print('Optional Teardown code for the testcase goes here')
        """,
        'test': """
        >>> square(0)
        0
        # explanation: Squaring zero
        """,
        'type': 'doctest'
      }
    ]
  ]
}
