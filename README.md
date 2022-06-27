# DailyRun.app

Track your current and longest fitness streaks

## Setup
1. **Create local.env** - Copy the file `example-local.env` to `local.env`. You will fill out the fields in the next step.
2. **Setup Domain** - Install [ngrok](https://ngrok.com/) and run it with `ngrok http 5000`. Copy the domain you are given and put it into the `DOMAIN` field of `local.env`.
3. **Setup Strava API** - [Create a Strava account](https://www.strava.com/register) if you don't already have one. Then, create an app at [https://www.strava.com/settings/api](https://www.strava.com/settings/api). Copy the ngrok domain from step 2 into the domain field of the Strava app form. Then, fill the fields of `local.env` with the Client ID and Client Secret.
4. **Install Go requirements**
From inside the `dailyrun.app` directory, run
```bash
go install
```
5. **Run**
```bash
go run .
```
Go to the domain given by ngrok in step 2 to test the site.
