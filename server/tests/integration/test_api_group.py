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


class GroupAPITest(APITest, APIBaseTestCase):
	model = models.Group
	name = 'group'
	num = 1
	access_token = 'dummy_admin'

	def setUp(self):
		super(GroupAPITest, self).setUp()
		self.course = make_fake_course(self.user)
		self.course.put()
		self.assignment = make_fake_assignment(self.course, self.user)
		self.assignment.put()
		for student_name in [a for a in self.accounts if 'student' in a]:
			s = self.accounts[student_name]
			models.Participant.add_role(s, self.course, constants.STUDENT_ROLE)

	def get_basic_instance(self, mutate=True):
		return self.model(
			assignment=self.assignment.key,
			member=[
				self.accounts['dummy_student2'].key,
				self.accounts['dummy_student3'].key])

	def test_assignment_group(self):
		self.user = self.accounts['dummy_student2']
		inst = self.get_basic_instance()
		inst.put()

		self.get('/assignment/{}/group'.format(self.assignment.key.id()))
		self.assertEqual(self.response_json['id'], inst.key.id())

  def test_index_arguments(self):
    self.user = self.accounts['dummy_student2']
    self.partner = self.accounts['dummy_student3']
    inst = self.get_basic_instance()
    inst.put()

    self.get_index(assignment=self.assignment.key.id(), member=self.user.key.id())
    self.assertEqual(self.response_json[0]['id'], inst.key.id())

    self.get_index(member=self.partner.key.id())
    self.assertEqual(self.response_json[0]['id'], inst.key.id())


	def test_assignment_invite(self):
		self.user = self.accounts['dummy_student2']
		inst = self.get_basic_instance()
		inst.put()

		invited = self.accounts['dummy_student']
		invited.put()

		self.post_json(
			'/assignment/{}/invite'.format(self.assignment.key.id()),
			data={'email': invited.email[0]})

		self.assertEqual(inst.invited, [invited.key])

		# Check audit log
		audit_logs = models.AuditLog.query().fetch()
		self.assertEqual(len(audit_logs), 1)
		log = audit_logs[0]
		self.assertEqual(log.user, self.user.key)
		self.assertEqual('Group.invite', log.event_type)
		self.assertIn(invited.email[0], log.description)

	def test_invite(self):
		self.user = self.accounts['dummy_student2']
		inst = self.get_basic_instance()
		inst.put()
		invited = self.accounts['dummy_student']

		self.post_json(
			'/{}/{}/add_member'.format(self.name, inst.key.id()),
			data={'email': invited.email[0]})

		self.assertEqual(inst.invited, [invited.key])

	def test_accept(self):
		self.user = self.accounts['dummy_student']
		inst = self.get_basic_instance()
		inst.invited.append(self.user.key)
		inst.put()

		self.post_json('/{}/{}/accept'.format(self.name, inst.key.id()))

		self.assertEqual(inst.invited, [])
		self.assertIn(self.user.key, inst.member)

	def test_exit_invited(self):
		self.user = self.accounts['dummy_student']
		inst = self.get_basic_instance()
		inst.invited.append(self.user.key)
		inst.put()

		self.post_json('/{}/{}/decline'.format(self.name, inst.key.id()))

		self.assertEqual(inst.invited, [])
		self.assertNotIn(self.user.key, inst.member)

	def test_exit_member(self):
		self.user = self.accounts['dummy_student']
		inst = self.get_basic_instance()
		inst.member.append(self.user.key)
		inst.put()

		self.post_json(
			'/{}/{}/remove_member'.format(self.name, inst.key.id()),
			data={'email': self.user.email[0]})

		self.assertNotIn(self.user.key, inst.member)

	def test_invite_someone_in_a_group(self):
		self.user = self.accounts['dummy_student2']
		inst = self.get_basic_instance()
		inst.put()

		# Place dummy_student in another group
		invited = self.accounts['dummy_student']
		self.model(
			assignment=self.assignment.key,
			member=[invited.key, self.accounts['dummy_staff'].key]
		).put()

		self.post_json(
			'/{}/{}/add_member'.format(self.name, inst.key.id()),
			data={'email': invited.email[0]})

		self.assertStatusCode(400)
		self.assertEqual(inst.invited, [])

	def test_remove_from_two_member_group(self):
		self.user = self.accounts['dummy_student']
		inst = self.model(assignment=self.assignment.key,
		                  member=[self.user.key, self.accounts['dummy_student2'].key])
		inst.put()

		self.post_json(
			'/{}/{}/remove_member'.format(self.name, inst.key.id()),
			data={'email': self.user.email[0]})

		self.assertStatusCode(200)
		self.assertEqual(inst.key.get(), None)

	def test_decline_invite_from_two_member_group(self):
		self.user = self.accounts['dummy_student']

		members = [self.accounts['dummy_student2'].key]
		inst = self.model(assignment=self.assignment.key, member=members,
		                  invited=[self.user.key])
		inst.put()

		self.post_json(
			'/{}/{}/decline'.format(self.name, inst.key.id()),
			data={'email': self.user.email[0]})

		self.assertStatusCode(200)
		self.assertEqual(inst.key.get(), None)

	def test_create_two_entities(self):
		pass # No creation

	def test_entity_create_basic(self):
		pass # No creation
