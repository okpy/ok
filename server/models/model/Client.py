from server.models.db import db, Model, StringList

class Client(Model):
    """ OAuth Clients.
    See: https://flask-oauthlib.readthedocs.io/en/latest/oauth2.html
    """
    name = db.Column(db.String(40))

    # human readable description, not required
    description = db.Column(db.String(400))

    # creator of the client, not required
    user_id = db.Column(db.ForeignKey('user.id'))
    # required if you need to support client credential
    user = db.relationship('User')

    client_id = db.Column(db.String(40), primary_key=True)
    client_secret = db.Column(db.String(55), unique=True, index=True,
                              nullable=False)

    is_confidential = db.Column(db.Boolean, nullable=False)

    redirect_uris = db.Column(StringList, nullable=False)
    default_scopes = db.Column(StringList, nullable=False)

    @property
    def default_redirect_uri(self):
        return self.redirect_uris[0]
