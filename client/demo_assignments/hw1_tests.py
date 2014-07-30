"""Tests for hw1 demo assignment."""

TEST_INFO = {
    'assignment': 'hw1',
    'imports': ['from hw1 import *'],
}

TESTS = [

    # Test square
    {
        'name': ('Q1', 'q1', '1'),
        'suites': [
            [
                ['square(4)', '16'],
                ['square(-5)', '25'],
            ],
        ],
    },


    # Test double
    {
        'name': ('Q2', 'q2', '2'),
        'suites': [
            [
                ['double(4)', '8'],
                ['double(-5)', '-10'],
            ],
        ],
    },

]
