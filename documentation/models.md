# Ok v3 Models

See `models.py` for the most recent version of these models. This is intended as a reference.

## Model Ideas:
-  Do we need FinalSubmission:
  - Not really. If we have a "flagged" boolean on submissions - we can enforce that only one submission is flagged. (By default nothing will be flagged and we'll grade the most recent one).
    - This gets unweidly with groups.
    - Smaller searches with a FS table. (versus searching the entire Submission table) - maybe neglible with the proper indexes.
  - Still leaning towards having the FS table - but not presenting it as a "Concept" to users. Users will just see a checkmark ✅ next to their submission.

- Groups:
  -  We have a list of constraints for groups on the [Wiki](https://github.com/Cal-CS-61A-Staff/ok/wiki/Group-&-Submission-Consistency)
  -  What if we associate submissions & backups with groups?
    -   Makes it easier to get submissions (though not by much)
    -   Handling group transitions while maintaining the full list of constraints above will be hard.
  -   I'm open to changs here.

- Pondering the creation of a GroupMember table (to avoid have an array in the Group Table
  - Schema: KEY id, FK group id, FK assignment, FK user id, ENUM STRING status (invited|member)
  - Could index by assignment & user id (and place a constraint that there's only one record per combination)

## Models

### User
Introduced concepts of SID and Secondary (inst logins or github usernames)

`alt_email` is for the eventual merging of emails. The previous approach used an array of emails. The merging process still needs some thought

```python
class User(db.Model, UserMixin, TimestampMixin):
    id = db.Column(db.Integer(), primary_key=True)
    email = db.Column(db.String(), unique=True, nullable=False, index=True)
    is_admin = db.Column(db.Boolean(), default=False)
    sid = db.Column(db.String())  # SID or Login
    secondary = db.Column(db.String())  # Other usernames
    alt_email = db.Column(db.String())
    active = db.Column(db.Boolean(), default=True)

```

### Course:

```python
class Course(db.Model, TimestampMixin):
    id = db.Column(db.Integer(), primary_key=True)
    offering = db.Column(db.String(), unique=True, index=True)
    # offering - E.g., 'cal/cs61a/fa14
    institution = db.Column(db.String())  # E.g., 'UC Berkeley'
    display_name = db.Column(db.String())
    creator = db.Column(db.ForeignKey("user.id"))
    active = db.Column(db.Boolean(), default=True)
```

### Assignments
Assignments are specific to courses and have unique names.

Example:
name - cal/cs61a/fa14/proj1
display_name - Hog
due_date - DEADLINE (Publically displayed)
lock_date - DEADLINE+1 (Hard Deadline for submissions)
url - cs61a.org/proj/hog/hog.zip



```python

class Assignment(db.Model, TimestampMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(), index=True, unique=True)
    course = db.Column(db.ForeignKey("course.id"), index=True, nullable=False)
    display_name = db.Column(db.String(), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    lock_date = db.Column(db.DateTime, nullable=False)
    creator = db.Column(db.ForeignKey("user.id"))
    url = db.Column(db.String())
    max_group_size = db.Column(db.Integer(), default=1)
    revisions = db.Column(db.Boolean(), default=False)
    autograding_key = db.Column(db.String())

```

### Participant
This stores enrollment data (along with permissions level for course staff)

```python
class Participant(db.Model, TimestampMixin):
    id = db.Column(db.Integer(), primary_key=True)
    user = db.Column(db.ForeignKey("user.id"), index=True, nullable=False)
    course = db.Column(db.ForeignKey("course.id"), index=True, nullable=False)
    role = db.Column(db.Enum(*VALID_ROLES, name='role'), nullable=False)

```

### Messages
Messages are what the OK Client sends to the server according to the variety of protocols the client supports. The server must accept whatever the client sends and store it. The contents of the message is a serialized JSON object.

Example Messages from the ok-client:
> { "file\_contents": {"'ok.py: "import ok"}, "analytics": {'q1': []} }

```python
class Message(db.Model, TimestampMixin):
    id = db.Column(db.Integer(), primary_key=True)
    backup = db.Column(db.ForeignKey("backup.id"), index=True)
    contents = db.Column(pg.JSONB())
    kind = db.Column(db.String(), index=True)

```

### Backups

Backups are the primary model in which data about student code goes. It contains all the fields neccesary to use as a submission.

Client Time is the time on the Users machine

```python
class Backup(db.Model, TimestampMixin):
    id = db.Column(db.Integer(), primary_key=True)
    messages = db.relationship("Message")
    scores = db.relationship("Score")
    client_time = db.Column(db.DateTime())
    submitter = db.Column(db.ForeignKey("user.id"), nullable=False)
    assignment = db.Column(db.ForeignKey("assignment.id"), nullable=False)

    db.Index('idx_backAUser', 'assignment', 'submitter'),

```



### Submissions

Submissions are very similiar to backups but have the additional fields of queue (All queue entries will be submissions of some kind)

- Flagged Field (See Model Ideas)

```python
class Submission(db.Model, TimestampMixin):
    id = db.Column(db.Integer(), primary_key=True)
    backup = db.Column(db.ForeignKey("backup.id"), nullable=False)
    assignment = db.Column(db.ForeignKey("assignment.id"), nullable=False)
    submitter = db.Column(db.ForeignKey("user.id"), nullable=False)
    queue = db.Column(db.ForeignKey("queue.id"))
    revision = db.Column(db.ForeignKey("submission.id"))
```

### Final Submission

Determines which submission the student wants us to grade. Just a pointer to a submission. This model may not be needed. (See model ideas)

```python
class FinalSubmission(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    submission = db.Column(db.ForeignKey("submission.id"), nullable=False)
    assignment = db.Column(db.ForeignKey("assignment.id"), nullable=False)
```



## Other Models:

Eventual each model will have it's own section.

Notable:
- Groups: See Model Ideas
- Scores now are floats
- Version: Ok-Client Versioning for autoupgrading
- Diff/Comments: Link to backups. (this way it is possible to query for all comments on a backup)

```python
class Score(db.Model, TimestampMixin):
    id = db.Column(db.Integer(), primary_key=True)
    backup = db.Column(db.ForeignKey("backup.id"), nullable=False)
    grader = db.Column(db.ForeignKey("user.id"), nullable=False)
    tag = db.Column(db.String(), nullable=False)
    score = db.Column(db.Float())
    message = db.Column(db.Text())


class Version(db.Model, TimestampMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    versions = db.Column(pg.ARRAY(db.String()), nullable=False)
    current_version = db.Column(db.String(), nullable=False)
    base_url = db.Column(db.String())


class Diff(db.Model, TimestampMixin):
    """A diff between two versions of the same project, with comments.
    A diff has three types of lines: insertions, deletions, and matches.
    Every insertion line is associated with a diff line.
    If BEFORE is None, the BACKUP is diffed against the Assignment template.
    """
    id = db.Column(db.Integer(), primary_key=True)
    backup = db.Column(db.ForeignKey("backup.id"), nullable=False)
    assignment = db.Column(db.ForeignKey("assignment.id"), nullable=False)
    before = db.Column(db.ForeignKey("backup.id"))
    diff = db.Column(pg.JSONB())
    comments = db.relationship('Comment')
    updated = db.Column(db.DateTime, onupdate=db.func.now())


class Comment(db.Model, TimestampMixin):
    """A comment is part of a diff. The key has the diff as its parent.
    The diff a reference to the backup it was originated from.
    Line is the line # on the Diff Object.
    Submission_line is the closest line on the submitted file.
    """
    id = db.Column(db.Integer(), primary_key=True)
    diff = db.Column(db.ForeignKey("diff.id"), nullable=False)
    backup = db.Column(db.ForeignKey("backup.id"), nullable=False)
    author = db.Column(db.ForeignKey("user.id"), nullable=False)
    filename = db.Column(db.String(), nullable=False)
    line = db.Column(db.Integer(), nullable=False)
    submission_line = db.Column(db.Integer())
    message = db.Column(db.Text())  # Markdown


class Queue(db.Model, TimestampMixin):
    """A queue of submissions to grade."""
    id = db.Column(db.Integer(), primary_key=True)
    assignment = db.Column(db.ForeignKey("assignment.id"), nullable=False)
    course = db.Column(db.ForeignKey("course.id"), nullable=False)
    primary_owner = db.Column(db.ForeignKey("user.id"), nullable=False)
    description = db.Column(db.Text())


class Group(db.Model, TimestampMixin):
    """A group is a collection of users who are either members or invited.

    Members of a group can view each other's submissions.

    Specification:
    https://github.com/Cal-CS-61A-Staff/ok/wiki/Group-&-Submission-Consistency
    """
    id = db.Column(db.Integer(), primary_key=True)
    assignment = db.Column(db.ForeignKey("assignment.id"), nullable=False)
    members = db.Column(db.ForeignKey("user.id"), nullable=False)
    order = db.Column(db.String())

```
