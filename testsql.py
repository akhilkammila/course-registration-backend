from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://akhilkammila:@localhost/course_registration'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Users(db.Model):
    email = db.Column(db.String(255), primary_key=True)
    password = db.Column(db.String(255))

with app.app_context():
    new_user = Users(email="test@gmail.com", password="test")
    db.session.add(new_user)
    db.session.commit()