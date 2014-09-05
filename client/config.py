import models.concept_case
import models.doctest_case
import protocols.grading
import protocols.unlock
import protocols.protocol
import protocols.file_contents
import protocols.analytics

from collections import OrderedDict


cases = { 
    'concept' : models.concept_case.ConceptCase,
    'doctest' : models.doctest_case.DoctestCase
}

protocols = OrderedDict([
    ('protocol', protocols.protocol.Protocol),
    ('file_contents', protocols.file_contents.FileContents),
    ('unlock', protocols.unlock.UnlockProtocol),
    ('lock', protocols.unlock.LockProtocol),
    ('grading', protocols.grading.GradingProtocol),
    ('analytics', protocols.analytics.AnalyticsProtocol)
])
