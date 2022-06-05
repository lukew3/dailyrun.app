from flask import Flask, render_template, request, make_response, redirect
from flask_sqlalchemy import SQLAlchemy
import json
import requests
import datetime
import pytz

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
    return f"http://www.strava.com/oauth/authorize?client_id={cfg['CLIENT_ID']}&response_type=code&redirect_uri=https://{cfg['DOMAIN']}/exchange_token&approval_prompt=force&scope=activity:read"

@app.route('/')
def home():
    strava_id = request.cookies.get('strava_id')
    if strava_id:
        user = User.query.filter_by(strava_id=int(strava_id)).first()
        if user:
            return render_template('home.html', fullname=user.firstname + ' ' + user.lastname, streak=user.cur_streak)
    return render_template('landing.html', authLink=get_oauth_url())

def streak_from_activities(user_strava_id):
    user = User.query.filter_by(strava_id=user_strava_id).first()
    r = requests.get('https://www.strava.com/api/v3/athlete/activities', headers={
            'Authorization': f'Bearer {user.access_token}'
        }, params={
            'page': 1,
            'per_page': 50
        })
    data = json.loads(r.content)
    streak = 0
    recent_time = datetime.datetime.now(tz=pytz.timezone(data[0]['timezone'].split()[1])) # the time of the last processed activity
    for activity in data:
        prev_time = datetime.datetime.fromisoformat(activity['start_date_local'][:-1]) # the time of the activity being processed now
        if (recent_time - datetime.timedelta(hours=24)).date() == prev_time.date():
            streak += 1
            recent_time = prev_time
        elif recent_time.date() == prev_time.date():
            # Don't increment streak if 2+ activities recorded in the same day
            recent_time = prev_time
        else:
            break
    user.cur_streak = streak
    db.session.commit()
    print(streak)

@app.route('/invalid_permissions')
def invalid_permissions():
    return render_template('invalid_permissions.html')

@app.route('/exchange_token')
def exchange_token():
    if request.args.get('scope') != 'read,activity:read':
        return redirect('/invalid_permissions')
    # Get user tokens and setup user
    r = requests.post('https://www.strava.com/oauth/token', params={
            'client_id': cfg['CLIENT_ID'],
            'client_secret': cfg['CLIENT_SECRET'],
            'code': request.args.get('code'),
            'grant_type': 'authorization_code'
        })
    user_data = json.loads(r.content)
    if not User.query.filter_by(strava_id=user_data['athlete']['id']).first(): 
        # Create user if not already existing
        new_user = User(firstname=user_data['athlete']['firstname'],
                lastname=user_data['athlete']['lastname'],
                strava_id=user_data['athlete']['id'],
                refresh_token=user_data['refresh_token'],
                access_token=user_data['access_token'],
                access_token_exp_date=datetime.datetime.fromtimestamp(user_data['expires_at'])
            )
        db.session.add(new_user)
        db.session.commit()
        streak_from_activities(new_user.strava_id)
    response = make_response(redirect('/'))
    response.set_cookie('strava_id', str(user_data['athlete']['id']).encode())
    return response

if __name__ == '__main__':
    app.run(port=5000, debug=True)
