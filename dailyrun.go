package main

import (
	"bytes"
	"encoding/json"
	"database/sql"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"html/template"

	_ "github.com/mattn/go-sqlite3"
	"github.com/joho/godotenv"
)

var db *sql.DB

func checkErr(err error) {
	if err != nil {
		panic(err)
	}
}

func createDB(filename string) {
	file, err := os.Create(filename)
	checkErr(err)
	file.Close()
	db, err = sql.Open("sqlite3", filename)
	checkErr(err)
	users_table, _ := ioutil.ReadFile("./init.sql")
	query, err := db.Prepare(string(users_table))
	checkErr(err)
	query.Exec()
	fmt.Println("Table created successfully!")
}

type HomePage struct {
	pfp_url string
	fullname string
	streak string
	start_date string
}

func getOauthUrl() string {
	return "http://www.strava.com/oauth/authorize?client_id=" + os.Getenv("CLIENT_ID") + "&response_type=code&redirect_uri=https://" + os.Getenv("DOMAIN") + "/exchange_token&approval_prompt=force&scope=activity:read,activity:read_all"
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
		t, _ := template.ParseFiles("go_templates/landing.html")
		t.Execute(w, getOauthUrl())
	}
	// t, _ := template.ParseFiles("go_templates/hello.html")
	// t.Execute(w, "Luke")
}

func userExists(strava_id uint32) bool {
	// Determine if user exists
	var exists bool = true
	if err := db.QueryRow("SELECT * FROM users WHERE strava_id = ?", strava_id).Scan(&exists); err != nil {
		// UserExists is false if err is sql.ErrNoRows
		exists = err != sql.ErrNoRows
	}
	return exists
}

func streakFromActivities(strava_id uint32) {
	userExists(strava_id)
}

type ExchangeTokenResponse struct {
	AccessToken string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
	ExpiresAt uint32 `json:"expires_at"`
	Athlete struct {
		FirstName string `json:"firstname"`
		LastName string `json:"lastname"`
		Id uint32 `json:"id"`
		ProfilePic string `json:"profile"`
	} `json:"athlete"`
}

func exchangeTokenHandler(w http.ResponseWriter, r *http.Request) {
	query := r.URL.Query()
	if (query.Get("scope") != "read,activity:read,activity:read_all") {
		t, _ := template.ParseFiles("go_templates/invalid_permissions.html")
		t.Execute(w, getOauthUrl())
		return
	}
	reqBody, err := json.Marshal(map[string]string{
		"client_id": os.Getenv("CLIENT_ID"),
		"client_secret": os.Getenv("CLIENT_SECRET"),
		"code": query.Get("code"),
		"grant_type": "authorization_code",
	})
	checkErr(err)
	resp, err := http.Post("https://www.strava.com/oauth/token", "application/json", bytes.NewBuffer(reqBody))
	checkErr(err)
	defer resp.Body.Close()
	body, err := ioutil.ReadAll(resp.Body)
	var user_data ExchangeTokenResponse
	json.Unmarshal(body, &user_data)

	// Create new user if not previously existing
	if (!userExists(user_data.Athlete.Id)) {
		stmt, err := db.Prepare("INSERT INTO users(firstname, lastname, profile_pic, cur_streak, streak_start_date, last_activity_date, timezone, strava_id, refresh_token, access_token, access_token_exp_date) values(?,?,?,?,?,?,?,?,?,?,?)")
		checkErr(err)
		stmt.Exec(user_data.Athlete.FirstName, user_data.Athlete.LastName, user_data.Athlete.ProfilePic, 0, 0, 0, "America/New_York", user_data.Athlete.Id, user_data.RefreshToken, user_data.AccessToken, user_data.ExpiresAt)
		streakFromActivities(user_data.Athlete.Id)
		fmt.Println(user_data)
	}

	// Set cookie
	cookie := &http.Cookie{
		Name:  "strava_id",
		Value: string(user_data.Athlete.Id),
		MaxAge: 300,
	}
	http.SetCookie(w, cookie)
	http.Redirect(w, r, "/", http.StatusSeeOther)
}

func init() {
	err := godotenv.Load("local.env")
	checkErr(err)

	createDB(os.Getenv("DB_FILENAME"))
	// db, err := sql.Open("sqlite3", os.Getenv("DB_FILENAME"))
	db.Query("")
}

func main() {
	// var templates *template.Template
	// templates = template.Must(templates.ParseGlob("go_templates/*.html"))

	// API routes
	http.HandleFunc("/", indexHandler)
	http.HandleFunc("/exchange_token", exchangeTokenHandler)
	http.HandleFunc("/hi", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, "Hi")
	})

	port := ":5000"
	fmt.Println("Server is running on port" + port)

	// Start server on port specified above
	log.Fatal(http.ListenAndServe(port, nil))
}
