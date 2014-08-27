"""TestCase for conceptual tests.

ConceptTestCases are designed to be natural language tests that help
students understand high-level understanding. As such, these test cases
focus mainly on unlocking. When used in the grading protocol,
ConceptTestCases simply display the answer if already unlocked.
"""

from models import core
from protocols import grading
from protocols import unlock
import utils

class ConceptTestCase(grading.GradedTestCase, unlock.UnlockTestCase):
    """TestCase for conceptual questions."""

    @property
    def answer(self):
        """Returns the answer of the test case. If the test case has
        not been unlocked, the answer will remain in locked form.
        """
        return self._outputs[0].answer

    @property
    def type(self):
        return 'concept'

    ######################################
    # Protocol interface implementations #
    ######################################

    def on_grade(self, logger, verbose, interact):
        """Implements the GradedTestCase interface."""
        if verbose:
            utils.underline('Concept question', line='-')
            print(self._input_str)
            print('A: ' + self.answer)
            print()
        return False

    def on_unlock(self, logger, interact_fn):
        """Implements the UnlockTestCase interface."""
        print(self._input_str)
        hash_key = self.info['hash_key'].encode('utf-8')
        verify_fn = lambda x, y: hmac.new(hash_key, x.encode('utf-8')).digest() == y
        answer = interact_fn(self.answer, self.verify_fn)
        return [core.TestCaseAnswer(answer)]

