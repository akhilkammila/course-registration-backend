from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
import requests
import json
import os
from postmarkcreds import api_key
from flask_cors import CORS

uri = os.getenv('SQLALCHEMY_DATABASE_URI')
if not uri: uri = 'postgresql://akhilkammila:@localhost/course_registration'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

webpageBaseUrl = os.getenv('webpageBaseUrl')
if not webpageBaseUrl: webpageBaseUrl = "*"
print(webpageBaseUrl)
CORS(app, resources={r"/*": {"origins": [webpageBaseUrl]}})

"""
0. Schema and helpers
"""

class Users(db.Model):
    email = db.Column(db.String(255), primary_key=True)
    password = db.Column(db.String(255))
    verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(255), unique=True)
    reset_token = db.Column(db.String(255), unique=True, nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)

    first_time = db.Column(db.Boolean, default=True)

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
    notifications = db.Column(db.Boolean, default=False)

def send_email(user_email, base_url, link_endpoint, token):
    link = f"{base_url}/{link_endpoint}/{token}"
    postmark_token = api_key
    sender_email = 'notifier@gtregistration.com'
    subject = '[GT Registration] Verify your account'
    text_body = f'Please click on the link to {link_endpoint}: {link}'
    html_body = f'<html><body><strong>Please click on the link to {link_endpoint}:</strong> <a href="{link}">{link}</a></body></html>'

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Postmark-Server-Token': postmark_token
    }
    payload = {
        'From': sender_email,
        'To': user_email,
        'Subject': subject,
        'TextBody': text_body,
        'HtmlBody': html_body,
        'MessageStream': 'outbound'
    }
    response = requests.post('https://api.postmarkapp.com/email', headers=headers, data=json.dumps(payload))
    return response

"""
1. Account creation endpoints
    /create_account: adds account to database, but with verified set to false. sends email with link to verify
    /verify_account: get endpoint that is visited through email link. verification token is matched to user in database
"""
@app.route('/create_account', methods=['POST'])
def create_account():
    data = request.json
    hashed_password = generate_password_hash(data['password'])
    existing_user = Users.query.filter_by(email=data['email']).first()

    if existing_user and not existing_user.verified:
        existing_user.password = hashed_password
        existing_user.generate_verification_token()
        send_email(data['email'], webpageBaseUrl, "verify_account", existing_user.verification_token)
        db.session.commit()
        return jsonify({'message': 'Existing unverified account found. Verification email resent.'}), 200

    if existing_user:
        return jsonify({'message': 'Email already exists.'}), 400

    new_user = Users(email=data['email'], password=hashed_password)
    new_user.generate_verification_token()
    db.session.add(new_user)
    db.session.commit()
    send_email(data['email'], webpageBaseUrl, "verify_account", new_user.verification_token)
    return jsonify({'message': 'Verification email sent.'}), 201

@app.route('/verify_account/<token>', methods=['GET'])
def verify_account(token):
    user = Users.query.filter_by(verification_token=token).first()
    if user:
        user.verified = True
        db.session.commit()
        return jsonify({'message': 'Account verified successfully.'}), 200
    return jsonify({'message': 'Invalid or expired token.'}), 400

"""
2. Reset password endpoints
    /request_reset: generates reset token, sends email
    /reset_password/token/: get endpoint based on link sent to email, 
"""
@app.route('/request_reset', methods=['POST'])
def request_reset():
    data = request.json
    user = Users.query.filter_by(email=data['email']).first()

    if user:
        user.generate_reset_token()
        db.session.commit()
        send_email(data['email'], webpageBaseUrl, "reset_password", user.reset_token)

    # Always return the same message to avoid revealing which emails are registered
    return jsonify({'message': 'If the email is registered, a reset link has been sent.'}), 200

@app.route('/reset_password/<token>', methods=['POST'])
def reset_password(token):
    user = Users.query.filter(Users.reset_token == token, Users.reset_token_expires > datetime.utcnow()).first()
    if not user:
        return jsonify({'message': 'Invalid or expired token.'}), 400

    data = request.json
    user.password = generate_password_hash(data['password'])
    user.reset_token = None  # Invalidate the token
    user.reset_token_expires = None
    db.session.commit()
    
    return jsonify({'message': 'Password reset successfully.'}), 200

"""
3. Sign In
"""
@app.route('/sign_in', methods=['POST'])
def sign_in():
    data = request.json
    user = Users.query.filter_by(email=data['email']).first()

    if user and check_password_hash(user.password, data['password']):
        if user.verified:
            return jsonify({'message': 'Successfully logged in.'}), 200
        else:
            return jsonify({'message': 'Account not verified.'}), 403
    return jsonify({'message': 'Login failed.'}), 401

"""
4. Managing Classes and Relations
"""
@app.route('/update_classes', methods=['POST'])
def update_classes():
    data = request.json
    user_id = data['accountName']
    new_classes = data['rows']

    user = Users.query.get(user_id)
    if user:
        # Need to clear classes that are only referenced once
        user.first_time = True
        user.classes.clear()
        db.session.commit()

        for class_info in new_classes:
            class_id = class_info['crn']
            notes = class_info.get('notes', '')
            notifications = class_info.get('notifications', False)

            class_obj = Class.query.get(class_id)
            if not class_obj:
                class_obj = Class(crn=class_id)
                db.session.add(class_obj)

            # Create a new user-class relation
            user_class = UserClass(user_email=user.email, class_crn=class_obj.crn, notes=notes, notifications=notifications)
            db.session.add(user_class)

        db.session.commit()
        return jsonify({'message': 'Classes updated successfully.'}), 200
    return jsonify({'message': 'User not found.'}), 404

"""
5. Bot queries
"""
@app.route('/get_user_classes', methods=['GET'])
def get_user_classes():
    # Constructing the query
    query = (db.session.query(
                Users.email, 
                Users.first_time, 
                Class.crn, 
                UserClass.notes, 
                Class.status
            )
            .join(UserClass, Users.email == UserClass.user_email)
            .join(Class, UserClass.class_crn == Class.crn)
            .filter(Users.verified == True, UserClass.notifications == True)
        )

    # Executing the query
    result = query.all()

    # Set all users' first time to false
    db.session.query(Users).update({Users.first_time: False})
    db.session.commit()

    # Formatting the results into the desired structure
    formatted_result = {}
    for email, first_time, crn, note, status in result:
        if email not in formatted_result:
            formatted_result[email] = {'first_time': first_time, 'courses': []}
        formatted_result[email]['courses'].append({'crn': crn, 'note': note, 'status': status})
    return formatted_result

@app.route('/update_class_statuses', methods=['POST'])
def update_class_statuses():
    data = request.json
    if not data:
        return jsonify({'message': 'No data provided'}), 400

    for crn, status in data.items():
        class_to_update = Class.query.get(crn)
        if class_to_update:
            class_to_update.status = status
        else:
            return jsonify({'message': f'Class with CRN {crn} not found'}), 404

    db.session.commit()
    return jsonify({'message': 'Class statuses updated successfully'}), 200

"""
Test Endpoint
"""
@app.route('/get_example', methods=['GET'])
def get_example():
    return jsonify({'message': 'This is a GET endpoint for testing.'}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)