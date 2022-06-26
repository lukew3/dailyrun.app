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
	if err != nil {
		log.Fatal(err)
	}
	file.Close()
	db, err = sql.Open("sqlite3", filename)
	checkErr(err)
	users_table, _ := ioutil.ReadFile("./init.sql")
	query, err := db.Prepare(string(users_table))
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

	fmt.Println(user_data.AccessToken)
	fmt.Println(user_data.Athlete.FirstName)

	stmt, err := db.Prepare("INSERT INTO users(firstname, lastname, profile_pic, cur_streak, streak_start_date, last_activity_date, timezone, strava_id, refresh_token, access_token, access_token_exp_date) values(?,?,?,?,?,?,?,?,?,?,?)")
        checkErr(err)
        stmt.Exec(user_data.Athlete.FirstName, user_data.Athlete.LastName, user_data.Athlete.ProfilePic, 0, 0, 0, "America/New_York", user_data.Athlete.Id, user_data.RefreshToken, user_data.AccessToken, user_data.ExpiresAt)
	fmt.Println(user_data)
	// fmt.Println(w, "<h1>Success</h1>")
	// t, _ := template.ParseFiles("go_templates/landing.html")
	// t.Execute(w, getOauthUrl())
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
