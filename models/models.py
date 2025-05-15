from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Model for 'students' table
class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    school_id = db.Column(db.String(255), nullable=False, unique=True)
    name = db.Column(db.String(255), nullable=False)

# Model for 'settings' table
class Settings(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(255), nullable=False, unique=True)
    value = db.Column(db.String(255), nullable=False)

    # Define the unique constraint for the 'key' column
    __table_args__ = (db.UniqueConstraint('key', name='uq_settings_key'),)

