test = {
  'name': 'q2',
  'points': 1,
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
        'question': 'What is the domain and range of the double function?',
        'type': 'concept'
      }
    ],
    [
      {
        'test': """
        >>> double(3)
        6
        """,
        'type': 'doctest'
      },
      {
        'test': """
        >>> double(-2)
        -4
        # explanation: Doubling a negative number
        # choice: 4
        # choice: 2
        # choice: None
        """,
        'type': 'doctest'
      },
      {
        'teardown': """
        print('Optional Teardown code for the testcase goes here')
        """,
        'test': """
        >>> double(0)
        0
        # explanation: Doubling zero
        """,
        'type': 'doctest'
      }
    ]
  ]
}