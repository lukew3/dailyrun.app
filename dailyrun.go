package main

import (
	"database/sql"
	"fmt"
	"log"
	"net/http"
	"os"
	"html/template"

	_ "github.com/mattn/go-sqlite3"
	"github.com/joho/godotenv"
)

func checkErr(err error) {
	if err != nil {
		panic(err)
	}
}

func createDB(filename string) {
	file, err := os.Create(filename)
	if err != nil {
		log.Fatal(err)
	}
	file.Close()
	db, err := sql.Open("sqlite3", filename)
	checkErr(err)
	users_table := `CREATE TABLE users (
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
		"access_token_exp_date" INT);`
	query, err := db.Prepare(users_table)
	if err != nil {
		log.Fatal(err)
	}
	query.Exec()
	fmt.Println("Table created successfully!")
}

type HomePage struct {
	pfp_url string
	fullname string
	streak string
	start_date string
}

func indexHandler(w http.ResponseWriter, r *http.Request) {
	// Get cookie
	c, _ := r.Cookie("strava_id")
	if c != nil {
		fmt.Println(c)
		p := HomePage{pfp_url: "https://lh3.googleusercontent.com/ogw/ADea4I4h8YTg0BoMqjIUw1EKVi_BVNjhR_3YZea2S_cy=s32-c-mo", fullname: "Luke Weiler", streak: "40", start_date: "May 26, 2022"}
		t, _ := template.ParseFiles("go_templates/home.html")
		t.Execute(w, p)
	} else {
		fmt.Println("No cookie")
		cookie := &http.Cookie{
			Name:  "strava_id",
			Value: "lukew3",
			MaxAge: 300,
		}
		http.SetCookie(w, cookie)
		t, _ := template.ParseFiles("go_templates/landing.html")
		t.Execute(w, getOauthUrl())
	}
	// t, _ := template.ParseFiles("go_templates/hello.html")
	// t.Execute(w, "Luke")
}

func getOauthUrl() string {
	return "http://www.strava.com/oauth/authorize?client_id=" + os.Getenv("CLIENT_ID") + "&response_type=code&redirect_uri=https://" + os.Getenv("DOMAIN") + "/exchange_token&approval_prompt=force&scope=activity:read,activity:read_all"
}

func main() {
	err := godotenv.Load("local.env")
	checkErr(err)

	// var templates *template.Template
	// templates = template.Must(templates.ParseGlob("go_templates/*.html"))
	createDB("./foo.db")

	db, err := sql.Open("sqlite3", "./foo.db")
	checkErr(err)

	stmt, err := db.Prepare("INSERT INTO users(firstname, lastname, profile_pic, cur_streak, streak_start_date, last_activity_date, timezone, strava_id, refresh_token, access_token, access_token_exp_date) values(?,?,?,?,?,?,?,?,?,?,?)")
	checkErr(err)

	stmt.Exec("luke", "weiler", "google.com", 38, 400, 400, "America/New_York", 1, "asdfasdf", "asdfasdfasdf", 4000)

	// API routes
	http.HandleFunc("/", indexHandler)
	http.HandleFunc("/hi", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, "Hi")
	})

	port := ":5000"
	fmt.Println("Server is running on port" + port)

	// Start server on port specified above
	log.Fatal(http.ListenAndServe(port, nil))
}