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
        # TODO(albert): needs verify_fn.
        answer = interact_fn(self.answer)
        return [core.TestCaseAnswer(answer)]

