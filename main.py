from flask import Flask, render_template, request, make_response, redirect, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont, ImageOps
from flask_sqlalchemy import SQLAlchemy
from turbo_flask import Turbo
from io import BytesIO
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

def hq_pfp(pfp):
    return pfp[:-9] + 'original.jpg' if pfp[-9:] == 'large.jpg' else pfp

@app.route('/reload_profile')
def reload_profile():
    strava_id = request.cookies.get('strava_id')
    if not strava_id: return redirect('/')
    user = User.query.filter_by(strava_id=int(strava_id)).first()
    if not user: return redirect('/')
    if datetime.datetime.now() > user.access_token_exp_date: refresh_token(user.strava_id)
    r = requests.get('https://www.strava.com/api/v3/athlete', headers={
            'Authorization': f'Bearer {user.access_token}'
        })
    if r.status_code != 200: return redirect('/')
    data = json.loads(r.content)
    user.firstname = data['firstname']
    user.lastname = data['lastname']
    user.profile_pic = hq_pfp(data['profile'])
    db.session.commit()
    return redirect('/')

@app.route('/reload_streak')
def reload_streak():
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
        new_user = User(firstname=user_data['athlete']['firstname'],
                lastname=user_data['athlete']['lastname'],
                profile_pic=hq_pfp(user_data['athlete']['profile']),
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

@app.route('/get_image', methods=['GET'])
def get_image():
    strava_id = request.cookies.get('strava_id')
    user = User.query.filter_by(strava_id=strava_id).first()
    if not user: return redirect('/')
    img = Image.new('RGB', (1000, 1000), (32, 32, 32))
    drw = ImageDraw.Draw(img)
    fnt_sml = ImageFont.truetype('./static/Roboto-Regular.ttf', 34)
    fnt_med = ImageFont.truetype('./static/Roboto-Regular.ttf', 40)
    fnt_lrg = ImageFont.truetype('./static/Roboto-Regular.ttf', 80)
    txt_clr = (255, 255, 255)
    drw.text((40, 40), "dailyrun.app", fill=txt_clr, font=fnt_med)
    # Profile Image
    profile_img = Image.open(BytesIO(requests.get(user.profile_pic).content))
    profile_img.thumbnail((500,500))
    img.paste(profile_img, (250, 125))
    # User name
    fullname = f"{user.firstname} {user.lastname}"
    name_width, _ = drw.textsize(fullname, font=fnt_lrg)
    drw.text(((1000-name_width)/2, 650), fullname, fill=txt_clr, font=fnt_lrg)
    # Streak Label
    streak_lbl_txt = "Has a streak of:"
    streak_lbl_width, _ = drw.textsize(streak_lbl_txt, font=fnt_sml)
    drw.text(((1000-streak_lbl_width)/2, 750), streak_lbl_txt, fill=txt_clr, font=fnt_sml)
    # Streak
    streak_txt = f"{user.cur_streak} days"
    streak_width, _ = drw.textsize(streak_txt, font=fnt_lrg)
    drw.text(((1000-streak_width)/2, 800), streak_txt, fill=txt_clr, font=fnt_lrg)
    # Start_date
    drw.text((40, 920), f"Started {user.streak_start_date.strftime('%b %d, %Y')}", fill=txt_clr, font=fnt_med)
    # Powered_by_image
    powered_by_image = Image.open('static/powered_by_strava_buttons/horiz_gray.png')
    img.paste(powered_by_image, (650, 920), powered_by_image)
    img_io = BytesIO()
    img.save(img_io, 'JPEG', quality=70)
    img_io.seek(0)
    # return send_file(img_io, mimetype='image/jpeg', as_attachment=True, download_name='dailyrun')
    return send_file(img_io, mimetype='image/jpeg', download_name='dailyrun')

if __name__ == '__main__':
    app.run(port=5000, debug=True)
