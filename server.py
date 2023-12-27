from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://akhilkammila:@localhost/course_registration'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Users(db.Model):
    email = db.Column(db.String(255), primary_key=True)
    password = db.Column(db.String(255))

@app.route('/create_account', methods=['POST'])
def create_account():
    data = request.json
    hashed_password = generate_password_hash(data['password'])
    new_user = Users(email=data['email'], password=hashed_password)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'User created successfully.'}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'message': 'Email already exists.'}), 400


@app.route('/sign_in', methods=['POST'])
def sign_in():
    data = request.json
    user = Users.query.filter_by(email=data['email']).first()

    if user and check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Successfully logged in.'}), 200
    return jsonify({'message': 'Login failed.'}), 401

@app.route('/get_example', methods=['GET'])
def get_example():
    return jsonify({'message': 'This is a GET endpoint for testing.'}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)