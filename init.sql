CREATE TABLE users (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"firstname" TEXT,
	"lastname" TEXT,
	"profile_pic" TEXT,
	"cur_streak" INT DEFAULT 0,
	"streak_start_date" INT,
	"last_activity_date" INT,
	"timezone" TEXT DEFAULT "America/New_York",
	"strava_id" INT,
	"refresh_token" TEXT,
	"access_token" TEXT,
	"access_token_exp_date" INT
);
