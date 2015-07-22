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

import datetime
from test_base import APIBaseTestCase, unittest, api #pylint: disable=relative-import
from test_base import make_fake_assignment, make_fake_course, make_fake_backup, make_fake_submission, make_fake_finalsubmission #pylint: disable=relative-import
from google.appengine.ext import ndb
from app import models, constants, utils
from ddt import ddt, data, unpack
from app.exceptions import *
from integration.test_api_base import APITest


class SubmissionAPITest(APIBaseTestCase):

	API = api.SubmissionAPI

	def setUp(self):
		super(SubmissionAPITest, self).setUp()
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
		self._finalsubmission = make_fake_finalsubmission(self._submission, self._assign, self.user2)
		self._score = models.Score(score=2).put()
		self._submission.score = [self._score.get()]
		self._submission.put()

	def get_accounts(self):
		return APITest().get_accounts()

	def test_data_for_zip_no_contents(self):
		""" Tests that no file_contents raises BadValueError """
		with self.assertRaises(BadValueError):
			self.API().data_for_zip(self.obj().set(
				submitter=self.obj().set(get=lambda: self.obj().set(email=['dummy@admin.com'])),
				created='created',
				get_messages=lambda: {}))
			
	def test_data_for_zip_del_submit(self):
		""" Tests that submit entry is deleted """
		name, file_contents = self.API().data_for_zip(self.obj().set(
			submitter=self.obj().set(get=lambda: self.obj().set(email=['dummy@admin.com'])),
			created='created',
			get_messages=lambda: {'file_contents': {'submit': 'hello'}}))
		self.assertNotIn('submit', file_contents)
		
	def test_data_for_zip_without_email(self):
		""" Tests that user without email is okay """
		self.API().data_for_zip(self.obj().set(
			submitter=self.obj().set(get=lambda: self.obj().set(email=[])),
			created='created',
			get_messages=lambda: {'file_contents': {'gup.py': 'import yo'}}))
		
	def test_data_for_zip_name(self):
		""" Test that the filename is valid """
		info = {'gup.py': 'import yo'}
		name, file_contents = self.API().data_for_zip(self.obj().set(
			submitter=self.obj().set(get=lambda: self.obj().set(email=[])),
			created='created',
			get_messages=lambda: {'file_contents': info}))
		self.assertEqual(info, file_contents)
		self.assertNotIn('.', name)
		self.assertNotIn(' ', name)
		
	def test_data_for_zip_unencodable(self):
		""" Tests that non-encodable keys are okay """
		info = {'gup.py': 1}
		self.API().data_for_zip(self.obj().set(
			submitter=self.obj().set(get=lambda: self.obj().set(email=[])),
			created='created',
			get_messages=lambda: {'file_contents': info}))
		self.assertEqual(info['gup.py'], '1')
		
	def test_zip(self):
		""" Tests that zip does not crash """
		obj = self.obj().set(
			submitter=self.obj().set(get=lambda: self.obj().set(email=[])),
			created='created',
			get_messages=lambda: {'file_contents': {'gup.py': 1}})
		self.API().zip(obj, self.accounts['dummy_admin'], {})
		
	def test_zip_files(self):
		""" Tests that zip_files does not crash """
		name, file_contents = 'yolo', {'gup.py': 'import fish'}
		name2, zipfile = self.API().zip_files(name, file_contents)
		self.assertEqual(name, name2)
		return name, zipfile
		
	def test_make_zip_response(self):
		""" Check zipfile response headers """
		with self.app.test_request_context('/api/v2'):
			response = self.API().make_zip_response(*self.test_zip_files())
			self.assertIn('attachment;', response.headers['Content-Disposition'])
			self.assertEqual('application/zip', response.headers['Content-Type'])
		
	def test_download(self):
		""" Check that download completes successfully """
		with self.app.test_request_context('/api/v2'):
			user, obj = self.accounts['dummy_admin'], self.obj().set(
				submitter=self.obj().set(get=lambda: self.obj().set(email=[])),
				created='created',
				get_messages=lambda: {'file_contents': {'gup.py': 1}})
			self.API().download(obj, user, {})
		
	def test_diff_empty(self):
		""" Tests that diff does not accept empty file_Contents """
		with self.assertRaises(BadValueError):
			obj = self.obj().set(get_messages=lambda: {})
			self.API().diff(obj, self.accounts['dummy_admin'], {})
			
	def test_diff_remove_submit(self):
		""" Tests that diff removes submit key """
		with self.assertRaises(AttributeError):  # AttributeError because fake obj has no assignment... means it passed
			file_contents = {'submit': 'yo'}
			key = ndb.Key(models.User, 1)
			obj = self.obj().set(
				get_messages=lambda: {'file_contents': file_contents},
				key=key)
			self.API().diff(obj, self.accounts['dummy_admin'], {})
			self.assertNotIn('submit', file_contents)
		
	def test_diff_non_encodable(self):
		""" Tests against keys that are nonencodable """
		with self.assertRaises(AttributeError):
			file_contents = {'gup.py': True}
			obj = self.obj().set(get_messages=lambda: {'file_contents': file_contents})
			self.API().diff(obj, self.accounts['dummy_admin'], {})
			self.assertEqual(file_contents['gup.py'], 'True')
		
	def test_diff_obj(self):
		""" Tests that existing diff is just returned """
		api, fake = self.API(), True
		file_contents = {'gup.py': True}
		self.mock(api.diff_model, 'get_by_id').using(staticmethod(lambda keyId: fake))
		key = ndb.Key(models.User, 1)
		obj = self.obj().set(
			get_messages=lambda: {'file_contents': file_contents},
			key=key,
			file_contents=file_contents)
		diff = api.diff(obj, self.accounts['dummy_admin'], {})
		self.assertEqual(fake, diff)
		return obj
	
	def test_diff_no_templates(self):
		""" Test diff with no template """
		api = self.API()
		file_contents = {'gup.py': True}
		self.mock(api.diff_model, 'get_by_id').using(staticmethod(lambda keyId: False))
		key = ndb.Key(models.User, 1)
		obj = self.obj().set(
			get_messages=lambda: {'file_contents': file_contents},
			key=key)
		obj.assignment = self._assign
		obj.assignment.get = lambda: self.obj().set(templates=None)
		templates = obj.assignment.get().templates
		self.assertFalse(api.diff_model.get_by_id(obj.key.id()))
		self.assertTrue(not templates or templates == {})
		with self.assertRaises(BadValueError):
			api.diff(obj, self.accounts['dummy_admin'], {})
			
	def test_diff_fn_notin_templates(self):
		""" Tests filename not in templates """
		obj = self.test_diff_obj()
		obj.assignment = self._assign
		obj.templates = {}
		self._assign.get = lambda: self.obj().set(templates='{"a":"adsf"}')
		obj.get_messages = lambda: {'file_contents': {'b': "adsf"}}
		self.API().diff(obj, self.accounts['dummy_admin'], {})
		return obj

	def test_diff_fn_in_templates(self):
		""" Tests filename not in templates """
		obj = self.test_diff_obj()
		obj.assignment = self._assign
		obj.templates = {}
		self._assign.get = lambda: self.obj().set(templates='{"a":"adsf"}')
		obj.get_messages = lambda: {'file_contents': {'a': "asdf", 'b': "asdf"}}
		self.API().diff(obj, self.accounts['dummy_admin'], {})
		return obj
		
	def test_diff_template_as_list(self):
		""" Test that a template list is okay """
		obj = self.test_diff_fn_in_templates()
		obj.assignment.get = lambda: self.obj().set(templates='{"a":["asdf"]}')
		self.API().diff(obj, self.accounts['dummy_admin'], {})
		return obj
	
	def test_diff_returned(self):
		""" Test that a diff object is returned """
		obj = self.test_diff_template_as_list()
		obj.assignment.get().templates = '["a"]'
		self.mock(models.Diff, 'get_by_id').using(staticmethod(lambda keyId: False))
		diff = self.API().diff(obj, self.accounts['dummy_admin'], {})
		self.assertEqual(diff.key.id(), obj.key.id())
		
	def test_add_comment(self):
		""" Tests that comment cannot be added to nonexistent diff """
		self.mock(models.Diff, 'get_by_id').using(staticmethod(lambda keyId: False))
		with self.assertRaises(BadValueError):
			self.API().add_comment(self.accounts['dummy_admin'], None, None)
			
	def test_add_empty_comment(self):
		""" Test that empty comment not allowed """
		data = {
			'index': '',
		    'message': '    ',
		    'file': ''
		}
		self.mock(models.Diff, 'get_by_id').using(staticmethod(lambda keyId: True))
		with self.assertRaises(BadValueError):
			self.API().add_comment(self.accounts['dummy_admin'], None, data)
			
	def test_add_comment_normal(self):
		""" Tests that coment can be added normally """
		data = {
			'index': 32,
			'message': 'Some unhelpful message',
			'file': ''
		}
		diff_obj = models.Diff(id=1).put().get()
		comment = self.API().add_comment(diff_obj, self.accounts['dummy_admin'], data)
		self.assertNotEqual(None, comment)
		
	def test_delete_comment_diff_dne(self):
		""" Tests comment cant be added to nonexsitent diff """
		self.mock(models.Diff, 'get_by_id').using(staticmethod(lambda keyId: False))
		with self.assertRaises(BadValueError):
			self.API().delete_comment(self.accounts['dummy_admin'], None, None)
			
	def test_delete_comment_dne(self):
		""" Tests that nonexistent comment cant be removed """
		self.mock(models.Diff, 'get_by_id').using(staticmethod(lambda keyId: self.accounts['dummy_admin']))
		self.mock(models.Comment, 'get_by_id').using(staticmethod(lambda *args, **kwargs: None))
		with self.assertRaises(BadKeyError):
			self.API().delete_comment(self.accounts['dummy_admin'], None, {
				'comment': self.accounts['dummy_admin'].key
			})

	def test_delete_comment_check(self):
		""" Tests that permissions are checked """
		self.mock(models.Diff, 'get_by_id').using(staticmethod(lambda keyId: 
			self.accounts['dummy_admin']))
		self.mock(models.Comment, 'get_by_id').using(staticmethod(lambda *args, **kwargs:
			self.accounts['dummy_admin']))
		with self.assertRaises(PermissionError):
			self.API().delete_comment(self.accounts['dummy_student3'], self.accounts['dummy_student2'], {
				'comment': self.accounts['dummy_student'].key
			})
			
	def test_delete_comment_normal(self):
		""" Test that the comment is actually deleted (kind of) """
		self.mock(models.Diff, 'get_by_id').using(staticmethod(lambda keyId:
			self.accounts['dummy_admin']))
		self.mock(models.Comment, 'get_by_id').using(staticmethod(lambda *args, **kwargs:
			self.accounts['dummy_admin']))
		self.API().delete_comment(self.accounts['dummy_admin'], self.accounts['dummy_admin'], {
			'comment': self.accounts['dummy_student'].key
		})
	
	# def test_add_tag_dup(self):
	# 	""" Tests that duplicate tag cannot beadded """
	# 	obj = self.obj().set(tags=['a', 'b', 'c'])
	# 	user = self.accounts['dummy_student3']
	# 	data = {'tag': 'a'}
	# 	with self.assertRaises(BadValueError):
	# 		self.API().add_tag(obj, user, data)
	#
	# def test_add_tag_not_submitted(self):
	# 	""" Tests "normal" (not SUBMITTED_TAG) and not duplicated tag is added """
	# 	obj = self.obj().set(tags=[], put=lambda: '_')
	# 	user = self.accounts['dummy_student3']
	# 	data = {'tag': 'a'}
	# 	with self.assertRaises(BadValueError):
	# 		self.API().add_tag(obj, user, data)
	# 		self.assertIn('a', obj.tags)
	#
	# def test_add_tag_submitted(self):
	# 	""" Tests SUBMITTED_TAG works """
	# 	obj = self._submission
	# 	user = self.accounts['dummy_student3']
	# 	data = {'tag': 'submitted'}
	# 	self.mock(api.SubmissionAPI, 'SUBMITED_TAG').using('submitted')
	# 	with self.assertRaises(BadValueError):
	# 		models.Submission(
	# 			models.Submission.assignment == self._assign.key,
	# 			models.Submission.submitter == self.accounts['dummy_student3'].key,
	# 		    models.Submission.tags == 'submitted'
	# 		).put()
	# 		self.API().add_tag(obj, user, data)
	
	def test_score_check(self):
		""" Tests that permissinos are chcekd """
		with self.assertRaises(PermissionError):
			self.API().score(self._submission, self.accounts['dummy_student'], {'submission': self._submission.key})

	def test_score_no_subm_backup_match(self):
		""" Tests that ubmission and backup are matched """
		with self.assertRaises(ValueError):
			self.API().score(self._submission, self.accounts['dummy_admin'], {'submission': self._submission.key})
		
	def test_score_nrmally(self):
		""" Test score normal """
		self.API().score(self._backup, self.accounts['dummy_admin'], {
			'submission': self._submission.key,
			'key': 'tag',
		    'score': 10,
		    'message': 'YO'
		})
	
	def test_get_assignment(self):
		""" Tests the get_assignment will whine on multiple assignments """
		models.Assignment(name=self.assignment_name).put()
		with self.assertRaises(BadValueError):
			self.API().get_assignment(self.assignment_name)

	def test_submit_late_revision(self):
		""" Tests that late assignment, revision allowed """
		user = submitter = self.accounts['dummy_student2']
		assignment = self.assignment_name
		self._assign.lock_date = datetime.datetime.now() - datetime.timedelta(hours=9)
		self._assign.revision = True
		self._assign.put()
		messages, submit = {'analytics': False}, True
		status_code, message, data = self.API().submit(user, assignment, messages, submit, submitter)
		vassign = self.API().get_assignment(assignment)
		fs = user.get_final_submission(vassign)
		late_flag = vassign.lock_date and datetime.datetime.now() >= vassign.lock_date
		revision = vassign.revision
		self.assertTrue(submit and late_flag)
		self.assertTrue(revision)
		self.assertFalse(fs is None or fs.submission.get().score == [])
		self.assertEqual(status_code, 201)

	def test_submit_late_revision_notallowed(self):
		""" Tests that late assignment without finalsubm not allowed """
		user = submitter = self.accounts['dummy_student3']
		assignment = self.assignment_name
		self._assign.lock_date = datetime.datetime.now() - datetime.timedelta(hours=9)
		self._assign.put()
		messages, submit = None, True
		status_code, message, data = self.API().submit(user, assignment, messages, submit, submitter)
		self.assertEqual(status_code, 403)
		self.assertEqual(message, 'late')
	
	def test_submit_late_period(self):
		""" Tests that late submissions are not allowed """
		user = submitter = self.accounts['dummy_student3']
		assignment = self.assignment_name
		self._assign.lock_date = datetime.datetime.now() - datetime.timedelta(hours=9)
		self._assign.revision = True
		self._assign.put()
		messages, submit = None, True
		status_code, message, data = self.API().submit(user, assignment, messages, submit, submitter)
		self.assertEqual(status_code, 403)
		self.assertNotEqual(message, 'late')

	def test_backup_late_period(self):
		""" Tests that late backups are allowed """
		user = submitter = self.accounts['dummy_student3']
		assignment = self.assignment_name
		messages, submit = {'analytics': False}, False
		status_code, message, data = self.API().submit(user, assignment, messages, submit, submitter)
		self.assertEqual(status_code, 201)
		self.assertNotEqual(message, 'late')
		

	def test_mark_as_final(self):
		""" Tests that marking works, at the basic level """
		self._submission.mark_as_final()
	
		assert models.FinalSubmission.query(
			models.FinalSubmission.submission==self._submission.key
		).get() is not None