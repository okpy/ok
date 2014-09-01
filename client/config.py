import models.concept_case
import models.doctest_case

cases = { 
          'concept' : models.concept_case.ConceptTestCase,
          'python' : models.doctest_case.PythonTestCase
        }

protocols = [ 'grading', 'unlock' ]
