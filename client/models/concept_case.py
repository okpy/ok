"""TestCase for conceptual tests.

ConceptTestCases are designed to be natural language tests that help
students understand high-level understanding. As such, these test cases
focus mainly on unlocking. When used in the grading protocol,
ConceptTestCases simply display the answer if already unlocked.
"""

from models import core
from models import serialize
from protocols import grading
from protocols import unlock
import utils

class ConceptCase(grading.GradedTestCase, unlock.UnlockTestCase):
    """TestCase for conceptual questions."""

    type = 'concept'

    REQUIRED = {
        'type': serialize.STR,
        'question': serialize.STR,
        'answer': serialize.STR,
    }
    OPTIONAL = {
        'locked': serialize.BOOL_FALSE,
        'choices': serialize.SerializeArray(serialize.STR),
        'never_lock': serialize.BOOL_FALSE,
    }

    def __init__(self, **fields):
        super().__init__(**fields)
        self['question'] = utils.dedent(self['question'])
        self['answer'] = utils.dedent(self['answer'])


    ######################################
    # Protocol interface implementations #
    ######################################

    def on_grade(self, logger, verbose, interact):
        """Implements the GradedTestCase interface."""
        print('Q: ' + self['question'])
        print('A: ' + self['answer'])
        print()
        return False

    def should_grade(self):
        return not self['locked']

    def on_unlock(self, logger, interact_fn):
        """Implements the UnlockTestCase interface."""
        print('Q: ' + self['question'])
        print()
        answer = interact_fn(self['answer'], self['choices'])
        self['answer'] = answer
        self['locked'] = False

    def on_lock(self, hash_fn):
        #TODO(soumya): Make this a call to normalize after it's moved to an appropriate place.
        if self['choices']:
            self['answer'] = hash_fn("".join(self['answer']))
        else:
            self['answer'] = hash_fn(self['answer'])
        self['locked'] = True

