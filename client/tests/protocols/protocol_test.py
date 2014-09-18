"""Tests the GradingProtocol."""

from protocols import protocol
from unittest import mock
import unittest
import utils
import exceptions

class GetProtocolTest(unittest.TestCase):
    def calls_get_protocols(self, names, expected_classes):
        classes = protocol.get_protocols(names)
        self.assertEqual(expected_classes, classes)

    def testNoNames(self):
        self.calls_get_protocols([], [])

    def testSingleName(self):
        self.calls_get_protocols([ProtocolA.name], [ProtocolA])

    def testMultipleNames(self):
        protocols = [ProtocolA, ProtocolC, ProtocolB]
        self.calls_get_protocols([p.name for p in protocols], protocols)

    def testNonexistentName(self):
        self.assertRaises(exceptions.OkException, protocol.get_protocols,
                ['bogus'])

    def testDuplicateName(self):
        self.calls_get_protocols([ProtocolA.name, ProtocolA.name],
                                 [ProtocolA, ProtocolA])

###################
# Dummy Protocols #
###################

class ProtocolA(protocol.Protocol):
    name = 'A'

class ProtocolB(protocol.Protocol):
    name = 'B'

class ProtocolC(protocol.Protocol):
    name = 'C'
