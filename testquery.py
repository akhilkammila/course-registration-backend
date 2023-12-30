from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
import requests
import json
from postmarkcreds import api_key
from flask_cors import CORS

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://akhilkammila:@localhost/course_registration'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Users(db.Model):
    email = db.Column(db.String(255), primary_key=True)
    password = db.Column(db.String(255))
    verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(255), unique=True)
    reset_token = db.Column(db.String(255), unique=True, nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)

    first_time = db.Column(db.Boolean, default=True)
    bot_requested = db.Column(db.Boolean, default=False)

    def generate_verification_token(self):
        self.verification_token = str(uuid.uuid4())
    
    def generate_reset_token(self):
        self.reset_token = str(uuid.uuid4())
        self.reset_token_expires = datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour
    
    classes = db.relationship('Class', secondary='user_class', back_populates='users')

class Class(db.Model):
    crn = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Integer, default=0)
    users = db.relationship('Users', secondary='user_class', back_populates='classes')

class UserClass(db.Model):
    user_email = db.Column(db.String(255), db.ForeignKey('users.email'), primary_key=True)
    class_crn = db.Column(db.Integer, db.ForeignKey('class.crn'), primary_key=True)

    notes = db.Column(db.String(255))
    waitlist = db.Column(db.Boolean, default=False)
    open = db.Column(db.Boolean, default=False)

from sqlalchemy.orm import aliased

"""
Query start
"""

# Aliasing Class and UserClass for clarity in the join
ClassAlias = aliased(Class)
UserClassAlias = aliased(UserClass)

with app.app_context():
    # Constructing the query
    query = (db.session.query(
                Users.email, 
                Users.first_time, 
                ClassAlias.crn, 
                UserClassAlias.notes, 
                ClassAlias.status
            )
            .join(UserClassAlias, Users.email == UserClassAlias.user_email)
            .join(ClassAlias, UserClassAlias.class_crn == ClassAlias.crn)
            .filter(Users.verified == True)
        )

    # Executing the query
    result = query.all()

    # Formatting the results into the desired structure
    formatted_result = {}
    for email, first_time, crn, note, status in result:
        if email not in formatted_result:
            formatted_result[email] = {'first_time': first_time, 'courses': []}
        formatted_result[email]['courses'].append({'crn': crn, 'note': note, 'status': status})
    print(formatted_result)

# formatted_result will now contain the desired data structure
