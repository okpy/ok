import models.concept_case
import models.doctest_case
import protocols.grading
import protocols.unlock
import protocols.protocol
import protocols.file_contents

from collections import OrderedDict


cases = { 
    'concept' : models.concept_case.ConceptCase,
    'doctest' : models.doctest_case.DoctestCase
}

protocols = OrderedDict([
    ('protocol', protocols.protocol.Protocol),
    ('file_contents', protocols.file_contents.FileContents),
    ('unlock', protocols.unlock.UnlockProtocol),
    ('grading', protocols.grading.GradingProtocol),
])
