import models.concept_case
import models.doctest_case
import protocols.grading
import protocols.unlock

cases = { 
          'concept' : models.concept_case.ConceptCase,
          'python' : models.doctest_case.DoctestCase
        }

protocols = {
    'grading': protocols.grading.GradingProtocol,
    'unlock': protocols.unlock.UnlockProtocol,
}
