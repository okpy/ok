import functools
import json
import logging
import shlex

import pytz
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, types
from sqlalchemy.dialects import mysql
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.hybrid import hybrid_property

from server.constants import TIMEZONE

logger = logging.getLogger(__name__)

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)


def transaction(f):
    """ Decorator for database (session) transactions."""
    @functools.wraps(f)
    def wrapper(*args, **kwds):
        try:
            value = f(*args, **kwds)
            db.session.commit()
            return value
        except:
            db.session.rollback()
            raise
    return wrapper


class Json(types.TypeDecorator):
    impl = types.Text

    def process_bind_param(self, value, dialect):
        # Python -> SQL
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        # SQL -> Python
        return json.loads(value)


@compiles(mysql.MEDIUMBLOB, 'sqlite')
def ok_blob(element, compiler, **kw):
    return "BLOB"


@compiles(mysql.MEDIUMTEXT, 'sqlite')
def ok_text(element, compiler, **kw):
    return "TEXT"


class JsonBlob(types.TypeDecorator):
    impl = mysql.MEDIUMBLOB

    def process_bind_param(self, value, dialect):
        # Python -> SQL
        return json.dumps(value).encode('utf-8')

    def process_result_value(self, value, dialect):
        # SQL -> Python
        return json.loads(value.decode('utf-8'))


class Timezone(types.TypeDecorator):
    impl = types.String(255)

    def process_bind_param(self, value, dialect):
        # Python -> SQL
        if not hasattr(value, 'zone'):
            if value not in pytz.common_timezones_set:
                logger.warning('Unknown TZ: {}'.format(value))
                # Unknown TZ, use default instead
                return TIMEZONE
            return value
        return value.zone

    def process_result_value(self, value, dialect):
        # SQL -> Python
        return pytz.timezone(value)


class StringList(types.TypeDecorator):
    impl = types.Text

    def process_bind_param(self, string_list, dialect):
        # Python -> SQL
        items = []
        for item in string_list:
            if " " in item or not item:
                items.append('"{}"'.format(item))
            else:
                items.append(item)
        return ' '.join(items)

    def process_result_value(self, value, dialect):
        """ SQL -> Python
        Uses shlex.split to handle values with spaces.
        It's a fragile solution since it will break in some cases.
        For example if the last character is a backslash or otherwise meaningful
        to a shell.
        """
        values = []
        for val in shlex.split(value):
            if " " in val and '"' in val:
                values.append(val[1:-1])
            else:
                values.append(val)
        return values

class Model(db.Model):
    """ Timestamps all models, and serializes model objects."""
    __abstract__ = True

    created = db.Column(db.DateTime(timezone=True),
                        server_default=db.func.now(), nullable=False)

    def __repr__(self):
        if hasattr(self, 'id'):
            key_val = self.id
        else:
            pk = self.__mapper__.primary_key
            if type(pk) == tuple:
                key_val = pk[0].name
            else:
                key_val = self.__mapper__.primary_key._list[0].name
        return '<{0} {1}>'.format(self.__class__.__name__, key_val)

    @classmethod
    def can(cls, obj, user, action):
        if user.is_admin:
            return True
        return False

    @hybrid_property
    def export(self):
        """ CSV export data. """
        if not hasattr(self, 'export_items'):
            return {}
        return {k: v for k, v in self.as_dict().items() if k in self.export_items}

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def from_dict(self, dict):
        for c in self.__table__.columns:
            if c.name in dict:
                setattr(self, c.name, dict[c.name])
        return self
