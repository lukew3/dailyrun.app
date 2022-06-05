from flask import Flask, render_template, request
import json

with open('config.json', 'r') as config_file:
    cfg = json.load(config_file)

app = Flask(__name__)

def get_oauth_url():
    return f"http://www.strava.com/oauth/authorize?client_id={cfg['CLIENT_ID']}&response_type=code&redirect_uri=https://{cfg['DOMAIN']}/exchange_token&approval_prompt=force&scope=read"

@app.route('/')
def home():
    return render_template('home.html', authLink=get_oauth_url())

@app.route('/exchange_token')
def exchange_token():
    state = request.args.get('state')
    code = request.args.get('code')
    scope = request.args.get('scope')
    return '<p>Account linked</p>'

if __name__ == '__main__':
    app.run(port=5000, debug=True)
