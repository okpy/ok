import unittest
import argparse
from ok import PROTOCOLS, Protocol, parse_input, ok_main

class TestProtocol(Protocol):
    name = "test"
    called_start = 0
    called_interact = 0

    def __init__(self, cmd_line_args):
        Protocol.__init__(self, cmd_line_args)

    def on_start(self, buf):
        TestProtocol.called_start += 1

    def on_interact(self, buf):
        TestProtocol.called_interact += 1

class FrameworkTest(unittest.TestCase): #pylint: disable=too-many-public-methods
    def setUp(self):
        self.args = argparse.ArgumentParser().parse_args()
        del PROTOCOLS[:]
        PROTOCOLS.append(TestProtocol)

    def test_parser(self): #pylint: disable=no-self-use
        arguments = parse_input()
        assert arguments.mode == None

    def test_ok_main_no_args(self):
        initial_start = TestProtocol.called_start
        initial_interact = TestProtocol.called_interact
        self.args.mode = None
        ok_main(self.args)
        assert TestProtocol.called_start == initial_start + 1
        assert TestProtocol.called_interact == initial_interact

    def test_ok_main_mode_set(self):
        initial_start = TestProtocol.called_start
        initial_interact = TestProtocol.called_interact
        self.args.mode = "test"
        ok_main(self.args)
        assert TestProtocol.called_start == initial_start + 1
        assert TestProtocol.called_interact == initial_interact + 1
