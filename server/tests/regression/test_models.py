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

from app import models, constants
from app.needs import Need
from app.exceptions import *
import json
from test_base import BaseTestCase, make_fake_course, make_fake_assignment, make_fake_group, make_fake_finalsubmission
import datetime
from mock import MagicMock
from google.appengine.ext import ndb


class ModelsTestCase(BaseTestCase):
	
	# Utilities

	def test_JSONEncoder(self):
		""" Tests that objects invokes to_json """
		user = models.User(email=['yo@yo.com']).put()
		assert isinstance(user, ndb.Key)
		models.JSONEncoder().default(user)
	
	def testBase_tojson(self):
		""" Tests that to_json returns a dict """
		user = models.User(email=['yo@yo.com']).put().get()
		assert isinstance(user.to_json(), dict)
		assert isinstance(user.to_json(True), dict)
		self.assertEqual(user.to_json(False), {})
		self.assertEqual(user.to_json({'email': ''}),
			{'email': ['yo@yo.com']})
		
		user.to_dict = MagicMock(returnvalue={'treasure': [user.key]})
		user.to_json({'treasure': True})
		
	def testBase_defaultPermission(self):
		""" Tests that default is False """
		self.assertFalse(models.Base._can(*([None]*4)))
		
	# UserModel
	
	def test_contains_files(self):
		""" Tests that contains_files works """
		backup_with = MagicMock()
		backup_with.get_messages.return_value = {
			'file_contents': 'HUEHUE'
		}
		backup_without = MagicMock()
		backup_without.get_messages.return_value = {}
		user = models.User()
		self.assertEqual({'file_contents': 'HUEHUE'}, 
		                 backup_with.get_messages())
		self.assertEqual(user._contains_files(backup_with), 'HUEHUE')
		self.assertEqual(user._contains_files(backup_without), None)
		
	def test_get_backups_helper_in_group(self):
		""" Test self not in group """
		user = models.User(email=['yo@yo.com']).put().get()
		user.get_group = MagicMock(
			return_value=MagicMock(
				member=[user.key]))
		user._get_backups_helper(None)

		user.get_group.assert_called_with(None)
		assert user.key in user.get_group(None).member
		
	def test_get_submissions_helper_in_group(self):
		""" Test self not in group """
		user = models.User(email=['yo@yo.com']).put().get()
		user.get_group = MagicMock(
			return_value=MagicMock(
				member=[user.key]))
		user._get_submissions_helper(None)

		user.get_group.assert_called_with(None)
		assert user.key in user.get_group(None).member
		
	def test_can_lookup(self):
		"""Tests that anyone can lookup"""
		user = models.User(email=['yo@yo.com']).put().get()
		need = Need('lookup')
		self.assertTrue(user._can(user, need, None, None))
		
	def test_can_get_not_user(self):
		"""Tests can get with invalid user"""
		user = models.User(email=['yo@yo.com']).put().get()
		need = Need('get')
		self.assertFalse(user._can(user, need, None, None))
		
	def test_can_index(self):
		"""Tests that index only works for user"""
		user = models.User(email=['yo@yo.com']).put().get()
		need = Need('index')
		self.assertTrue(user._can(user, need, None,
		                           MagicMock(filter=lambda *args: True)))
		
	def test_pre_put_hook(self):
		"""Tests that pre put hook for user works"""
		with self.assertRaises(BadValueError):
			models.User().put()
			
	def test_scores_forassign_wo_fs(self):
		"""Tests that missing fs doesn't crash method"""
		assign = models.Assignment().put().get()
		user = models.User(email=['yo@yo.com']).put().get()
		self.assertEqual(
			user.scores_for_assignment(assign),
			([[user.email[0], 0, None, None, None]], False))
		
	def test_scores_forassign_w_fs_wo_scores(self):
		"""Tests that fs scores are loaded"""
		assign = models.Assignment().put()
		user = models.User(email=['yo@yo.com']).put()
		backup = models.Backup(submitter=user, assignment=assign).put()
		subm = models.Submission(backup=backup).put()
		models.FinalSubmission(
			submitter=user, 
			assignment=assign, 
			submission=subm).put()
		
		user = user.get()
		self.assertNotEqual(user.get_final_submission(assign), None)
		self.assertFalse(user.scores_for_assignment(assign.get())[1])

	def test_scores_forassign_w_fs_w_scores(self):
		"""Tests that fs scores are loaded"""
		assign = models.Assignment().put()
		user = models.User(email=['yo@yo.com']).put()
		backup = models.Backup(submitter=user, assignment=assign).put()
		score = models.Score(score=10, grader=user)
		subm = models.Submission(
			backup=backup,
			score=[score]).put()
		models.FinalSubmission(
			submitter=user,
			assignment=assign,
			submission=subm).put()

		user = user.get()
		self.assertNotEqual(user.get_final_submission(assign), None)
		self.assertTrue(user.scores_for_assignment(assign.get())[1])
		
	##########
	# Course #
	##########
	
	def test_course_get_students_basic(self):
		"""Tests that get_students functions"""
		student_key = models.User(email=['yo@yo.com']).put()
		course = make_fake_course(student_key.get())
		students = course.get_students(student_key)
		self.assertTrue(isinstance(students, list))

	def test_course_get_students_function(self):
		"""Tests that get_students works"""
		student_key = models.User(email=['yo@yo.com']).put()
		course = make_fake_course(student_key.get())
		models.Participant.add_role(
			student_key, course.key, constants.STUDENT_ROLE)
		enrollment = course.get_students(student_key)
		self.assertTrue(isinstance(enrollment, list))
		students = [student.user for student in enrollment]
		self.assertIn(student_key, students)
		
	##############
	# Assignment #
	##############
	
	def test_assignment_can(self):
		"""Tests that index always returns"""
		index = Need('index')
		self.assertTrue(models.Assignment._can(None, index, None, True))

	def test_assignment_comparator(self):
		"""Tests that assignments can be compared like numbers... by due date"""
		creator_key = models.User(email=['yo@yo.com']).put()
		course = make_fake_course(creator_key.get())
		assignment1 = make_fake_assignment(course, creator_key.get())
		assignment2 = models.Assignment(
			name='hw1',
			points=3,
			display_name="CS 61A",
			templates="[]",
			course=course.key,
			creator=creator_key,
			max_group_size=4,
			due_date=datetime.datetime.now() + datetime.timedelta(days=3))
		self.assertTrue(assignment2 < assignment1)
		self.assertFalse(assignment1 < assignment2)
		
		lst = [assignment1, assignment2]
		lst = sorted(lst)
		self.assertEqual(lst, [assignment2, assignment1])
		
	###############
	# Participant #
	###############
	
	def test_participant_can(self):
		"""Tests that all users can get, and that only staff can index"""
		get = Need('get')
		self.assertTrue(models.Participant._can(None, get, None, None))
		
		need = Need('index')
		student = models.User(email=['yo@yo.com']).put().get()
		admin = models.User(email=['do@do.com']).put().get()
		
		course = make_fake_course(student)
		
		models.Participant.add_role(
			student.key, course.key, constants.STUDENT_ROLE)
		models.Participant.add_role(
			admin.key, course.key, constants.STAFF_ROLE)
		
		query = models.Participant.query()
		
		results = models.Participant._can(student, need, course, query).fetch()
		self.assertNotEqual(None, results)
		self.assertEqual(1, len(results))

		results = models.Participant._can(admin, need, course, query).fetch()
		self.assertNotEqual(None, results)
		self.assertEqual(2, len(results))
		
	def test_invalid_role_add(self):
		"""Test adding invalid role"""
		with self.assertRaises(BadValueError):
			models.Participant.add_role(None, None, 'yolo')

	def test_invalid_role_remove(self):
		"""Test adding invalid role"""
		with self.assertRaises(BadValueError):
			models.Participant.remove_role(None, None, 'yolo')
			
	def test_validate_message_empty_message(self):
		"""Tests that validate_msessages does not accept empty messages"""
		with self.assertRaises(BadValueError):
			models.validate_messages(None, None)
			
	def test_validate_invalid_messages_str(self):
		"""Tests that validate only accepts JSON dicts"""
		with self.assertRaises(BadValueError):
			models.validate_messages(None, '[]')

	def test_validate_invalid_json(self):
		"""Tests that validate raises BadValueError with invalid JSON"""
		with self.assertRaises(BadValueError):
			models.validate_messages(None, '#$@%P(@U#RP(QU@#P(UQ@# CP(U#P((____)')
			
	###########
	# Message #
	###########
		
	def test_message_can(self):
		"""Tests that messgea can always false"""
		index = Need('index')
		self.assertFalse(models.Message._can(None, index, None, None))
		
	##########
	# Backup #
	##########
	
	def test_backup_can_get(self):
		"""Tests that backup required"""
		with self.assertRaises(ValueError):
			get = Need('get')
			models.Backup._can(None, get, None, None)
	
	def test_backup_index(self):
		"""Tests permissions for backup"""
		admin = models.User(email=['do@do.com']).put().get()
		course = make_fake_course(admin)
		models.Participant.add_role(
			admin.key, course.key, constants.STAFF_ROLE)
		
		index = Need('index')
		assignment = make_fake_assignment(course, admin)
		backup = models.Backup(
			submitter=admin.key, assignment=assignment.key).put().get()
		query = models.Backup.query()
		self.assertNotEqual(
			False, models.Backup._can(admin, index, backup, query))
		
	##############
	# Submission #
	##############
	
	def test_get_final(self):
		"""Test get_final"""
		admin = models.User(email=['do@do.com']).put().get()
		student = models.User(email=['y@da.com']).put().get()
		course = make_fake_course(admin)
		assignment = make_fake_assignment(course, admin).put().get()

		backup = models.Backup(
			submitter=student.key, assignment=assignment.key).put()
		submission = models.Submission(backup=backup).put()
		fsubm = models.FinalSubmission(
			submitter=student.key,
			assignment=assignment.key,
		    group=make_fake_group(assignment, admin, student).key,
			submission=submission).put().get()
		self.assertEqual(fsubm, submission.get().get_final())

	def test_submission_can(self):
		"""Tests that mission submission raises valueerror"""
		grade = Need('grade')
		with self.assertRaises(ValueError):
			models.Submission._can(None, grade, None, None)

	def test_get_final_w_revision(self):
		""""""
		admin = models.User(email=['do@do.com']).put().get()
		student = models.User(email=['y@da.com']).put().get()
		course = make_fake_course(admin)
		assignment = make_fake_assignment(course, admin)
		assignment.revision = True
		assignment.put().get()

		backup = models.Backup(
			submitter=student.key, assignment=assignment.key).put()
		submission = models.Submission(backup=backup).put()
		models.FinalSubmission(
			submitter=student.key,
			assignment=assignment.key,
			group=make_fake_group(assignment, admin, student).key,
			submission=submission).put().get()
		
		self.assertEqual(submission.get().mark_as_final().get().revision,
		                 submission)

	def test_get_final_wo_final(self):
		""""""
		admin = models.User(email=['do@do.com']).put().get()
		student = models.User(email=['y@da.com']).put().get()
		course = make_fake_course(admin)
		assignment = make_fake_assignment(course, admin)
		assignment.revision = True
		assignment.put().get()
		
		group = make_fake_group(assignment, admin, student).put()

		backup = models.Backup(
			submitter=student.key, assignment=assignment.key).put()
		submission = models.Submission(backup=backup).put()
		
		self.assertEqual(submission.get().mark_as_final().get().group,
		                 group)


	########
	# Diff #
	########

	def test_diff_comments(self):
		"""Tests that comments returned successfully"""
		diff = models.Diff().put().get()
		self.assertIn('comments', diff.to_json().keys())

	###########
	# Comment #
	###########

	def test_comment_can(self):
		"""test commentp ermissions"""
		admin = models.User(email=['yo@yo.com'], is_admin=True).put().get()
		self.assertTrue(models.Comment._can(admin, None))
		weird = Need('weird')
		self.assertFalse(models.Comment._can(MagicMock(is_admin=False), weird))

	###########
	# Version #
	###########

	def test_version_download_link(self):
		"""Version download link"""
		version = models.Version()
		with self.assertRaises(BadValueError):
			version.download_link()
			
	def test_version_download_link_success(self):
		"""Tests that function works properly"""
		version = models.Version(
			versions=['1.1'],
			base_url='okpy',
			name='update')
		self.assertEqual(version.download_link('1.1'),
		                 'okpy/1.1/update')
		
	def test_version_to_json(self):
		"""Tests that to_json includes current version if applicable"""
		version = models.Version(
			versions=['1.1'],
			base_url='okpy',
		    current_version='1.1',
			name='update')
		self.assertIn('current_download_link', version.to_json().keys())
		
	def test_version_can(self):
		"""Tests that delete always forbidden"""
		need = Need('delete')
		self.assertFalse(models.Version._can(None, need))
		
	def test_from_dict(self):
		"""Tests that ValueError raised without value"""
		with self.assertRaises(ValueError):
			models.Version.from_dict({})
			
	#########
	# Group #
	#########
		
	def test_group_lookup_or_create(self):
		"""TEsts that group lookup_or_create works"""
		admin = models.User(email=['do@do.com']).put().get()
		student = models.User(email=['y@da.com']).put().get()
		course = make_fake_course(admin)
		assignment = make_fake_assignment(course, admin).put().get()
		models.Group._lookup_or_create(student.key, assignment.key)
		
	def test_group_lookup_by_assignment(self):
		"""Test lookup by assignment"""
		admin = models.User(email=['do@do.com']).put().get()
		student = models.User(email=['y@da.com']).put().get()
		course = make_fake_course(admin)
		assignment = make_fake_assignment(course, admin).put().get()
		group = make_fake_group(assignment, admin, student).put()
		groups = models.Group.lookup_by_assignment(assignment)
		self.assertIn(group, [g.key for g in groups])
		
	def test_group_invite(self):
		"""Tests group nitpicky invitation behavior"""
		admin = models.User(email=['do@do.com']).put().get()
		student = models.User(email=['y@da.com']).put().get()
		course = make_fake_course(admin).put().get()
		assignment = make_fake_assignment(course, admin).put().get()
		group = make_fake_group(assignment, admin, student).put().get()
		
		self.assertIn('is not a valid user', group.invite('asdf@asdf.com'))
		self.assertIn('is not enrolled in', group.invite(student.email[0]))
		
		group.invited = [student.key]
		models.Participant.add_role(student.key, course.key, constants.STUDENT_ROLE)
		self.assertIn('has already been invited', group.invite(student.email[0]))
		
		group.invited = []
		self.assertIn('is already in the group', group.invite(student.email[0]))
		
		assignment.max_group_size = 2
		assignment.put()
		student2 = models.User(email=['y@da2.com']).put().get()
		models.Participant.add_role(student2.key, course.key, constants.STUDENT_ROLE)
		self.assertEqual(2, group.assignment.get().max_group_size)
		self.assertEqual(2, len(group.member))
		self.assertEqual('The group is full', group.invite(student2.email[0]))