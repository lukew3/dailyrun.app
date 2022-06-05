# Fitness Streak Tracker

Track your current and longest fitness streaks

## Setup
1. **Create config.json** - Copy the `config_example.json` file to `config.json`. You will fill out the fields in the next step.
2. **Setup Domain** - Install [ngrok](https://ngrok.com/) and run it with `ngrok http 5000`. Copy the domain you are given and put it into the `DOMAIN` field of `config.json`.
3. **Setup Strava API** - [Create a Strava account](https://www.strava.com/register) if you don't already have one. Then, create an app at [https://www.strava.com/settings/api](https://www.strava.com/settings/api). Copy the ngrok domain from step 2 into the domain field of the Strava app form. Then, fill the fields of `config.json` with Client ID, Client Secret, Your Access Token, and Your Refresh Token. 
4. **Install Python requirements**
```bash
pip install -r requirements.txt
```
5. **Run**
```bash
python main.py
```
Go to the domain given by ngrok in step 2 to test the site.
