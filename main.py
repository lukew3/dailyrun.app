from flask import Flask, render_template, request, make_response, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from turbo_flask import Turbo
import json
import requests
import datetime
import pytz

with open('config.json', 'r') as config_file:
    cfg = json.load(config_file)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = cfg['SQLALCHEMY_DATABASE_URI']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
turbo = Turbo(app)
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String)
    lastname = db.Column(db.String)
    profile_pic = db.Column(db.String)
    cur_streak = db.Column(db.Integer, default=0)
    streak_start_date = db.Column(db.DateTime, default=db.func.now())
    last_activity_date = db.Column(db.DateTime, default=db.func.now())
    timezone = db.Column(db.String, default="America/New_York")
    # Strava data
    strava_id = db.Column(db.Integer, nullable=False, unique=True)
    refresh_token = db.Column(db.String)
    access_token = db.Column(db.String)
    access_token_exp_date = db.Column(db.DateTime)

db.create_all()

def get_oauth_url():
    return f"http://www.strava.com/oauth/authorize?client_id={cfg['CLIENT_ID']}&response_type=code&redirect_uri=https://{cfg['DOMAIN']}/exchange_token&approval_prompt=force&scope=activity:read,activity:read_all"

@app.route('/')
def home():
    strava_id = request.cookies.get('strava_id')
    if strava_id:
        user = User.query.filter_by(strava_id=int(strava_id)).first()
        if user:
            now = datetime.datetime.now(tz=pytz.timezone(user.timezone))
            # Check if last_activity was before yesterday
            if user.last_activity_date.date() < (now - datetime.timedelta(hours=24)).date():
                user.cur_streak = 0
                user.streak_start_date = now
                db.session.commit()
            return render_template('home.html', fullname=user.firstname + ' ' + user.lastname, streak=user.cur_streak, pfp_url=user.profile_pic, start_date=user.streak_start_date.strftime('%b %d, %Y'))
    return render_template('landing.html', authLink=get_oauth_url())

@app.route('/logout')
def logout():
    response = make_response(redirect('/'))
    response.set_cookie('strava_id', '', expires=0)
    return response

def refresh_token(user_strava_id):
    user = User.query.filter_by(strava_id=user_strava_id).first()
    r = requests.post('https://www.strava.com/api/v3/oauth/token', params={
            'client_id': cfg['CLIENT_ID'],
            'client_secret': cfg['CLIENT_SECRET'],
            'grant_type': 'refresh_token',
            'refresh_token': user.refresh_token
        })
    if r.status_code != 200: return
    data = json.loads(r.content)
    user.access_token = data['access_token']
    user.refresh_token = data['refresh_token']
    user.access_token_exp_date = datetime.datetime.fromtimestamp(int(data['expires_at']))
    print(user.access_token_exp_date)
    db.session.commit()

def streak_from_activities(user_strava_id):
    user = User.query.filter_by(strava_id=user_strava_id).first()
    if not user: return;
    if datetime.datetime.now() > user.access_token_exp_date: refresh_token(user.strava_id)
    found_streak_end = False
    activities_page = 0
    streak = 0
    first_iteration = True
    last_time = datetime.datetime.now()
    while not found_streak_end:
        activities_page += 1
        r = requests.get('https://www.strava.com/api/v3/athlete/activities', headers={
                'Authorization': f'Bearer {user.access_token}'
            }, params={
                'page': activities_page,
                'per_page': 50
            })
        if r.status_code != 200: return # TODO: Add better handling here
        data = json.loads(r.content)
        if first_iteration:
            user.last_activity_date = datetime.datetime.fromisoformat(data[0]['start_date_local'][:-1])
            user.timezone = data[0]['timezone'].split()[1]
            last_time = datetime.datetime.now(tz=pytz.timezone(user.timezone))
            first_iteration = False
        i = 0
        while i < 50 and not found_streak_end:
            this_time = datetime.datetime.fromisoformat(data[i]['start_date_local'][:-1]) # the time of the activity being processed now
            if (last_time - datetime.timedelta(hours=24)).date() == this_time.date():
                streak += 1
                last_time = this_time
                user.streak_start_date = last_time
            elif last_time.date() == this_time.date():
                # Don't increment streak if 2+ activities recorded in the same day
                last_time = this_time
            else:
                found_streak_end = True 
            i += 1
    user.cur_streak = streak
    db.session.commit()

@app.route('/force_recheck')
def force_recheck():
    strava_id = request.cookies.get('strava_id')
    if not strava_id: return redirect('/')
    user = User.query.filter_by(strava_id=int(strava_id)).first()
    if not user: return redirect('/')
    streak_from_activities(user.strava_id)
    return redirect('/')

@app.route('/invalid_permissions')
def invalid_permissions():
    return render_template('invalid_permissions.html', authLink=get_oauth_url())

@app.route('/exchange_token')
def exchange_token():
    if request.args.get('scope') != 'read,activity:read,activity:read_all':
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
        pfp = user_data['athlete']['profile']
        if pfp[-9:] == 'large.jpg': pfp = pfp[:-9] + 'original.jpg'
        new_user = User(firstname=user_data['athlete']['firstname'],
                lastname=user_data['athlete']['lastname'],
                profile_pic=pfp,
                strava_id=user_data['athlete']['id'],
                refresh_token=user_data['refresh_token'],
                access_token=user_data['access_token'],
                access_token_exp_date=datetime.datetime.fromtimestamp(user_data['expires_at'])
            )
        db.session.add(new_user)
        db.session.commit()
        streak_from_activities(new_user.strava_id)
        # Initiate webhook
        ws_init = requests.post('https://www.strava.com/api/v3/push_subscriptions', params={
                'client_id': cfg['CLIENT_ID'],
                'client_secret': cfg['CLIENT_SECRET'],
                'callback_url': f"https://{cfg['DOMAIN']}/receive_webhook",
                'verify_token': cfg['VERIFY_TOKEN']
            })
    response = make_response(redirect('/'))
    response.set_cookie('strava_id', str(user_data['athlete']['id']).encode())
    return response

@app.route('/receive_webhook', methods=['GET', 'POST'])
def receive_webhook():
    if request.method == 'GET':
        # Validate subscription
        return jsonify({'hub.challenge': request.args.get('hub.challenge')})
    elif request.method == 'POST':
        print(request.json)
        if request.json['aspect_type'] == 'create' and request.json['object_type'] == 'activity':
            # Check if newly uploaded activity extends streak
            user = User.query.filter_by(strava_id=request.json['owner_id']).first()
            # Check if user exists here? # Delete webhook if user not existing in db
            # Get activity
            activity_r = requests.get(f"https://www.strava.com/api/v3/activities/{request.json['object_id']}", headers={
                    'Authorization': f'Bearer {user.access_token}'
                })
            if activity_r.status_code == 200:
                activity_time = datetime.datetime.fromisoformat(json.loads(activity_r.content)['start_date_local'][:-1])
                if (activity_time - datetime.timedelta(hours=24)).date() == user.last_activity_date.date():
                    # Extending streak
                    user.cur_streak = user.cur_streak + 1
                    user.last_activity_date = activity_time
                    db.session.commit()
                elif activity_time.date() != user.last_activity_date.date():
                    # New streak started
                    user.cur_streak = 1
                    user.last_activity_date = activity_time
                    user.streak_start_date = activity_time
                    db.session.commit()
                # else: other activity logged today (ignore)
        return jsonify({})

if __name__ == '__main__':
    app.run(port=5000, debug=True)
