import models.concept_case
import models.doctest_case

cases = { 
          'concept' : models.concept_case.ConceptCase,
          'python' : models.doctest_case.DoctestCase
        }

protocols = [ 'grading', 'unlock' ]
