from test_base import auth, BaseTestCase, models

from app.exceptions import PermissionError, IncorrectVersionError


class ExceptionsTestCase(BaseTestCase):
	"""
	Testing exceptions
	"""

	sv = '1.0'
	cv = '1.1'
	dl = 'http://ok.py'

	def test_permissions_error(self):
		""" Test PermissionsError """
		need = lambda: 'get'
		message = 'exception'
		need.get_exception_message = lambda: message
		perm = PermissionError(need)
		assert perm.need is need
		assert perm.message == message

	def test_incorrect_version_error_basic(self):
		self.supplied_version = self.sv
		self.correct_version = cv = lambda: '_'
		cv.current_version = self.cv
		cv.download_link = lambda: self.dl
		ive = IncorrectVersionError(self.supplied_version, self.correct_version)
		assert ive.supplied_version == self.sv
		assert ive.correct_version.current_version == self.cv
		return ive

	def test_incorrect_version_error(self):
		""" Test IncorrectVersionError """
		ive = self.test_incorrect_version_error_basic()
		data = ive.data
		self.assertEqual(data['supplied'], self.supplied_version)
		self.assertEqual(data['correct'], self.correct_version.current_version)
		self.assertEqual(data['download_link'], self.correct_version.download_link())
		self.assertEqual(ive.message, ("Incorrect client version. Supplied version was {}. "
		                              "Correct version is {}.".format(self.supplied_version,
		                                                              self.correct_version.current_version)))
