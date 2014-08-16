from models import core
import grading
import unlock
import utils

class ConceptTestCase(grading.GradedTestCase, unlock.UnlockTestCase):

    @property
    def answer(self):
        return self._outputs[0].answer

    def on_grade(self, logger, verbose, interact):
        if verbose:
            utils.underline('Concept question', line='-')
            print(self._input_str)
            print('A: ' + self.answer)
            print()
        return False

    def on_unlock(self, interact_fn):
        """Runs an unlocking session for a conceptual TestCase."""
        print(self._input_str)
        # TODO(albert): needs verify_fn.
        answer = interact_fn(self.answer)
        return [core.TestCaseAnswer(answer)]

