"""Implements the GradingProtocol, which runs all specified tests
associated with an assignment.

The GradedTestCase interface should be implemented by TestCases that
are compatible with the GradingProtocol.
"""

from models import core
from protocols import protocol
import utils
from datetime import datetime

#####################
# Testing Mechanism #
#####################


class AnalyticsProtocol(protocol.Protocol):
    """A Protocol that analyzes how much students are using the autograder.
    """
    name = 'analytics'

    def on_start():
        """
        Returns some analytics about this autograder run.
        """
        statistics = {}
        statistics['time'] = datetime.now()
        statistics['unlock'] = False

        if self.args.question:
            statistics['question'] = self.args.question

        if self.args.unlock:
            statistics['unlock'] = True

        statistics['log'] = self.logger.log

        return statistics
