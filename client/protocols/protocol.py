from client import exceptions

class Protocol(object):
    """A Protocol encapsulates a single aspect of ok.py functionality."""
    name = None # Override in sub-class.

    def __init__(self, cmd_line_args, assignment, output_logger, log=None):
        """Constructor.

        PARAMETERS:
        cmd_line_args -- Namespace; parsed command line arguments.
                         command line, as parsed by argparse.
        assignment    -- dict; general information about the assignment.
        logger        -- OutputLogger; used to control output
                         destination, as well as capturing output from
                         an autograder session.
        log           -- Logger; used for printing debugging messages.
        """
        self.args = cmd_line_args
        self.assignment = assignment
        self.logger = output_logger
        self.analytics = {}
        self.log = log

    def on_start(self):
        """Called when ok.py starts. Returns an object to be sent to server."""

    def on_interact(self):
        """Called to execute an interactive or output-intensive session."""

def get_protocols(names):
    mapping = {}
    subclasses = Protocol.__subclasses__()
    while subclasses:
        protocol = subclasses.pop()
        if protocol.name != Protocol.name:
            mapping[protocol.name] = protocol
        subclasses.extend(protocol.__subclasses__())
    try:
        return [mapping[name] for name in names]
    except KeyError as e:
        raise exceptions.OkException(str(e) + ' is not a protocol')
