#!/usr/bin/env python
# encoding: utf-8
#pylint: disable=no-member, no-init, too-many-public-methods
#pylint: disable=attribute-defined-outside-init
# This disable is because the tests need to be name such that
# you can understand what the test is doing from the method name.
#pylint: disable=missing-docstring
"""
tests.py

"""

from test_base import APIBaseTestCase
from test_base import utils, api
from integration.test_api_base import APITest
from test_base import make_fake_assignment, make_fake_course, make_fake_backup, make_fake_submission, make_fake_finalsubmission #pylint: disable=relative-import
import contextlib
import datetime
import zipfile as zf

try:
	from cStringIO import StringIO
except:
	from StringIO import StringIO

class UtilsTestCase(APIBaseTestCase):

	def setUp(self):
		super(UtilsTestCase, self).setUp()
		self.user = self.accounts['dummy_admin']
		self.user1 = self.accounts['dummy_student']
		self.user2 = self.accounts['dummy_student2']
		self.user3 = self.accounts['dummy_student3']
		self.assignment_name = 'Hog Project'
		self._course = make_fake_course(self.user)
		self._course.put()
		self._assign = make_fake_assignment(self._course, self.user)
		self._assign.name = self._assign.display_name = self.assignment_name
		self._assign.put()
		self._backup = make_fake_backup(self._assign, self.user2)
		self._submission = make_fake_submission(self._backup)

	def get_accounts(self):
		return APITest().get_accounts()

	##########################
	# TEST ZIP FUNCTIONALITY #
	##########################

	def test_zip_filename_purified(self):
		""" Test that filename doesn't contain weird chars """
		user = lambda: '_'
		user.email = ['test@example.com']
		fn = utils.make_zip_filename(user, datetime.datetime.now())

		assert fn.split('.')[1] == 'zip'
		assert '@' not in fn
		assert ' ' not in fn

	def test_add_to_zip(self):
		""" Test that a zip is added to properly """
		files = {
			'c': 'file c contents',
			'd': 'file d contents'
		}
		directory = 'dir'
		zip_contents = {directory + '/' + name: contents
			for name, contents in files.iteritems()}
		with contextlib.closing(StringIO()) as contents:
			with zf.ZipFile(contents, 'w') as zipfile:
				utils.add_to_zip(zipfile, files, directory)
				self.assertEquals(set(zip_contents.keys()), set(zipfile.namelist()))
				for filename, content in zip_contents.iteritems():
					self.assertEquals(content, zipfile.read(filename))

	###########################
	# TEST OK-GCS ABSTRACTION #
	###########################
