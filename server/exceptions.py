class APIException(Exception):
    code = 400
    data = None


class IncorrectVersionError(APIException):
    code = 403

    def __init__(self, supplied_version, correct_version):
        self.supplied_version = supplied_version
        self.correct_version = correct_version

    @property
    def message(self):
        return ("Incorrect client version. Supplied version was {}. " +
                "Correct version is {}.".format(
                    self.supplied_version,
                    self.correct_version.current_version))

    @property
    def data(self):
        return {
            'supplied': self.supplied_version,
            'correct': self.correct_version.current_version,
            'download_link': self.correct_version.download_link
        }
