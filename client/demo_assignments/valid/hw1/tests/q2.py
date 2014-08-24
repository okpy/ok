"""Tests for Q2: double"""

test = {
  # Optional information for each type of test case to set up, specific
  # to this test (q2)
  'setup': {
    'doctest': """
    # Setup code for doctest-style TestCases. This setup code is only
    # run once, before any of the testcases are evaluated.
    """,
  },
  'cases': [
    {
      'type': 'concept',
      'question': """
      What is the domain and range of the double function?
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
      >>> double(3)
      6
      """,
    },
    {
      'type': 'doctest',
      'test': """
      >>> double(-2)
      -4
      # explanation: Doubling a negative number
      # choice: 4
      # choice: 2
      # choice: None
      """,
    },
    {
      'type': 'doctest',
      'test': """
      >>> double(0)
      0
      # explanation: Doubling zero
      """,
      'teardown': """
      print('Optional Teardown code for the testcase goes here')
      """
    },
  ]
}
