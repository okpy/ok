from server.models.db import db, Model, JsonBlob

class Message(Model):
    __tablename__ = 'message'
    __table_args__ = {'mysql_row_format': 'COMPRESSED'}

    id = db.Column(db.Integer, primary_key=True)
    backup_id = db.Column(db.ForeignKey("backup.id"), nullable=False,
                          index=True)
    contents = db.Column(JsonBlob, nullable=False)
    kind = db.Column(db.String(255), nullable=False, index=True)

    backup = db.relationship("Backup")
