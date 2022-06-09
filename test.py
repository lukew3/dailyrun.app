import imgkit
"""
options = {
    'format': 'png',
    'crop-h': '3',
    'crop-w': '3',
    'crop-x': '3',
    'crop-y': '3',
    'encoding': "UTF-8",
    'custom-header' : [
        ('Accept-Encoding', 'gzip')
    ],
    'cookie': [
        ('cookie-name1', 'cookie-value1'),
        ('cookie-name2', 'cookie-value2'),
    ]
}
"""

pfp_url = "https://warehouse-camo.ingress.cmh1.psfhosted.org/ef7983f986337f863e642cb20c5db6379c730360/68747470733a2f2f7365637572652e67726176617461722e636f6d2f6176617461722f65626466353238633336616132393262373765343136616664623462356238653f73697a653d3530"
fullname = "Luke Weiler"
start_date = "July 4, 1776"
streak = "5"
source_html = f"""
<html>
<head>
<style>
* {{
        color: #ECECEC;
        font-family: 'Roboto', sans-serif;
        text-decoration: none;
}}
html {{
        background-color: #2D2D2D;
}}
#streak_card {{
        width: calc(100vw - 60px);
        height: calc(100vw - 60px);
        max-width: 460px;
        max-height: 460px;
        border: solid #ECECEC 1px;
        padding: 20px;
        border-radius: 10px;
        display: grid;
        grid-template-rows: 6% 2% 58% 1% 9% 1.5% 4% 1.5% 9% 3% 5%;
        background-color: #202020;
        justify-content: center;
}}
#streak_card * {{
        margin: 0;
        text-align: center;
}}
#card_brandname {{
        height: 100%;
        justify-self: left;
}}
#card_pfp {{
        justify-self: center;
        align-self: center;
        max-width: 100%;
        max-height: 100%;
        border-radius: 50%;
}}
#card_fullname {{
        height: 100%;
        justify-self: center;
}}
#card_streak_label {{
        height: 100%;
        justify-self: center;
}}
#card_streak {{
        height: 100%;
        justify-self: center;
}}
#card_bottom {{
        display: flex;
        justify-content: space-between;
        width: 100%;
        align-items: end;
}}
#card_start_date {{
        height: 100%;
        justify-self: center;
}}
#card_powered_by {{
        height: 100%;
}}

</style>
</head>
<body>
    <div id="streak_card">
        <svg id="card_brandname" viewbox="0 0 105 18">
                <text fill="white" x="0" y="15">dailyrun.app</text>
        </svg>
        <div></div>
        <img id="card_pfp" src="{pfp_url}" alt="{fullname}">
        <div></div>
        <svg id="card_fullname" viewbox="0 0 85 18">
                <text fill="white" x="0" y="15">{fullname}</text>
        </svg>
        <div></div>
        <svg id="card_streak_label" viewbox="0 0 115 18">
                <text fill="white" x="0" y="15">Has a streak of:</text>
        </svg>
        <div></div>
        <svg id="card_streak" viewbox="0 0 55 18">
                <text fill="white" x="0" y="15">{streak} days</text>
        </svg>
        <div></div>
        <div id="card_bottom">
                <svg id="card_start_date" viewbox="0 0 150 18">
                        <text fill="white" x="0" y="15">Started {start_date}</text>
                </svg>
                <img id="card_powered_by" src="https://lukew3.com/powered_by_strava_horiz_gray.svg">
        </div>
    </div>
    <div id="home_reload">
            <p><a href="/reload_profile">Reload Profile</a></p>
            <p id="refresh_seperator">|</p>
            <p><a href="/reload_streak">Reload Streak</a></p>
    </div>
</body>
</html>
"""

imgkit.from_string(source_html, 'out.png')
