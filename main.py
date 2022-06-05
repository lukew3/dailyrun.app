from flask import Flask, render_template, request, make_response, redirect
from flask_sqlalchemy import SQLAlchemy
import json
import requests
import datetime

with open('config.json', 'r') as config_file:
    cfg = json.load(config_file)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = cfg['SQLALCHEMY_DATABASE_URI']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String)
    lastname = db.Column(db.String)
    cur_streak = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=db.func.now())
    # Strava data
    strava_id = db.Column(db.Integer, nullable=False, unique=True)
    refresh_token = db.Column(db.String)
    access_token = db.Column(db.String)
    access_token_exp_date = db.Column(db.DateTime)

db.create_all()

def get_oauth_url():
    return f"http://www.strava.com/oauth/authorize?client_id={cfg['CLIENT_ID']}&response_type=code&redirect_uri=https://{cfg['DOMAIN']}/exchange_token&approval_prompt=force&scope=read"

@app.route('/')
def home():
    strava_id = request.cookies.get('strava_id')
    if strava_id:
        user = User.query.filter_by(strava_id=int(strava_id)).first()
        return render_template('home.html', fullname=user.firstname + ' ' + user.lastname)
    else:
        return render_template('landing.html', authLink=get_oauth_url())

@app.route('/exchange_token')
def exchange_token():
    state = request.args.get('state')
    code = request.args.get('code')
    scope = request.args.get('scope')
    # Get user tokens and setup user
    res = requests.post('https://www.strava.com/oauth/token', params={
            'client_id': cfg['CLIENT_ID'],
            'client_secret': cfg['CLIENT_SECRET'],
            'code': code,
            'grant_type': 'authorization_code'
        })
    user_data = json.loads(res.content)
    if User.query.filter_by(strava_id=user_data['athlete']['id']).first(): 
        response = make_response(redirect('/'))
        response.set_cookie('strava_id', str(user_data['athlete']['id']).encode())
        return response
    new_user = User(firstname=user_data['athlete']['firstname'],
            lastname=user_data['athlete']['lastname'],
            strava_id=user_data['athlete']['id'],
            refresh_token=user_data['refresh_token'],
            access_token=user_data['access_token'],
            access_token_exp_date=datetime.datetime.fromtimestamp(user_data['expires_at'])
        )
    db.session.add(new_user)
    db.session.commit()
    response = make_response(redirect('/'))
    response.set_cookie('strava_id', str(new_user.strava_id).encode())
    return response

if __name__ == '__main__':
    app.run(port=5000, debug=True)
