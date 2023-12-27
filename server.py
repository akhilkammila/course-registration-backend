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

CORS(app, resources={r"/*": {"origins": "*"}})  # This allows all domains. For security, list only the origins you trust.

apiBaseUrl = 'http://127.0.0.1:5000'
webpageBaseUrl = 'http://127.0.0.1:3000'

class Users(db.Model):
    email = db.Column(db.String(255), primary_key=True)
    password = db.Column(db.String(255))
    verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(255), unique=True)
    reset_token = db.Column(db.String(255), unique=True, nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)

    def generate_verification_token(self):
        self.verification_token = str(uuid.uuid4())
    
    def generate_reset_token(self):
        self.reset_token = str(uuid.uuid4())
        self.reset_token_expires = datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour

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
        send_email(data['email'], apiBaseUrl, "verify_account", existing_user.verification_token)
        db.session.commit()
        return jsonify({'message': 'Existing unverified account found. Verification email resent.'}), 200

    if existing_user:
        return jsonify({'message': 'Email already exists.'}), 400

    new_user = Users(email=data['email'], password=hashed_password)
    new_user.generate_verification_token()
    db.session.add(new_user)
    db.session.commit()
    send_email(data['email'], apiBaseUrl, "verify_account", new_user.verification_token)
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
Test Endpoint
"""
@app.route('/get_example', methods=['GET'])
def get_example():
    return jsonify({'message': 'This is a GET endpoint for testing.'}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)