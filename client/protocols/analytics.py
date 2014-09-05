"""Implements the AnalyticsProtocol, which keeps track of configuration
for the ok grading session.
"""

from protocols import protocol
from datetime import datetime

class AnalyticsProtocol(protocol.Protocol):
    """A Protocol that analyzes how much students are using the autograder.
    """
    name = 'analytics'

    def on_start(self):
        """
        Returns some analytics about this autograder run.
        """
        statistics = {}
        statistics['time'] = datetime.now()
        statistics['unlock'] = self.args.unlock is not None

        if self.args.question:
            statistics['question'] = self.args.question

        return statistics
