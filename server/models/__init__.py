import server.models.model
from server.models.db import db
from server.models.proxy import ModelProxy

# The imports below are order sensitive
from server.models.model.GradingTask import GradingTask
from server.models.model.User import User
from server.models.model.Enrollment import Enrollment
from server.models.model.Message import Message
from server.models.model.Backup import Backup
from server.models.model.Version import Version
from server.models.model.Course import Course
from server.models.model.Score import Score
from server.models.model.Comment import Comment
from server.models.model.GroupAction import GroupAction
from server.models.model.GroupMember import GroupMember
from server.models.model.Group import Group
from server.models.model.Assignment import Assignment
from server.models.model.CanvasCourse import CanvasCourse
from server.models.model.CanvasAssignment import CanvasAssignment
from server.models.model.Client import Client
from server.models.model.Grant import Grant
from server.models.model.Token import Token
from server.models.model.Job import Job
