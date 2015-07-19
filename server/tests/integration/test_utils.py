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
		fn = utils.make_zip_filename(user)
		
		assert fn.split('.')[1] == 'zip'
		assert '@' not in fn
		assert ' ' not in fn
		
	def test_add_subm_to_zip(self):
		""" Test that submission contents added to zip """
		results = api.SearchAPI.results({
			'query': ''
		})
		for result in results:
			subm = api.SubmissionAPI()
			zipfile_str, zipfile = utils.start_zip()
			zipfile = utils.add_subm_to_zip(subm, result.__class__, zipfile, result)
			assert zipfile is None or len(zipfile.infolist()) > 0
		
	def test_start_zip_basic(self):
		""" Test that a zip is started properly """
		zipfile_str, zipfile = utils.start_zip()
		assert zipfile_str is not None
		assert zipfile is not None
		return zipfile_str, zipfile
	
	def test_start_zip_filecontents(self):
		""" Test that zip is initialized with file contents dict properly """
		file_contents = dict(a='file a contents', b='file b contents')
		zipfile_str, zipfile = utils.start_zip(file_contents)
		zipinfo = zipfile.infolist()
		zipnames = [z.filename for z in zipinfo]
		assert 'a' in zipnames
		assert 'b' in zipnames
		return zipfile_str, zipfile
		
	def test_start_zip_dir(self):
		""" Test that files are saved under specified directory """
		file_contents, dir = dict(a='file a contents', b='file b contents'), 'dir'
		zipfile_str, zipfile = utils.start_zip(file_contents, dir)
		zipinfo = zipfile.infolist()
		zipnames = [z.filename for z in zipinfo]
		assert 'dir/a' in zipnames
		assert 'dir/b' in zipnames
		return zipfile_str, zipfile
		
	def test_add_to_zip_basic(self):
		""" Test that a zip is added to properly """
		zipfile_str, zipfile = self.test_start_zip_basic()
		zipfile = utils.add_to_zip(zipfile, dict(filename='file contents'))
		assert len(zipfile.infolist()) == 1
		return zipfile_str, zipfile

	def test_add_to_zip_filecontents(self):
		""" Test that zip is initialized with file contents dict properly """
		zipfile_str, zipfile = self.test_start_zip_filecontents()
		file_contents = dict(c='file c contents', d='file d contents')
		zipfile = utils.add_to_zip(zipfile, file_contents)
		zipinfo = zipfile.infolist()
		zipnames = [z.filename for z in zipinfo]
		assert 'c' in zipnames
		assert 'c' in zipnames

	def test_add_to_zip_dir(self):
		""" Test that files are saved under specified directory """
		zipfile_str, zipfile = self.test_start_zip_dir()
		file_contents, dir = dict(c='file c contents', d='file d contents'), 'dir'
		zipfile = utils.add_to_zip(zipfile, file_contents, dir)
		zipinfo = zipfile.infolist()
		zipnames = [z.filename for z in zipinfo]
		assert 'dir/c' in zipnames
		assert 'dir/d' in zipnames
		
	def test_finish_zip_basic(self):
		""" Test that zip is ready to go """
		zipfile_str, zipfile = self.test_add_to_zip_basic()
		assert utils.finish_zip(zipfile_str, zipfile) is not None
		
	###########################
	# TEST OK-GCS ABSTRACTION #
	###########################