class Protocol(object):
    """A Protocol encapsulates a single aspect of ok.py functionality."""
    name = None # Override in sub-class.

    def __init__(self, cmd_line_args, assignment, logger):
        """Constructor.

        PARAMETERS:
        cmd_line_args -- Namespace; parsed command line arguments.
                         command line, as parsed by argparse.
        assignment    -- dict; general information about the assignment.
        logger        -- OutputLogger; used to control output
                         destination, as well as capturing output from
                         an autograder session.
        """
        self.args = cmd_line_args
        self.assignment = assignment
        self.logger = logger

    def on_start(self):
        """Called when ok.py starts. Returns an object to be sent to server."""

    def on_interact(self):
        """Called to execute an interactive or output-intensive session."""


