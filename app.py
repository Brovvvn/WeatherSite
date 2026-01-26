from flask import Flask, render_template, jsonify, request, session, make_response, redirect, url_for
import requests
import json

app = Flask(__name__)
app.secret_key = "f8a4d7c2b9e1a6d3c5f7e9b2a4d6c8e1"

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/", methods=["GET", "POST"])
def home():
    weather_data = None
    search_history = json.loads(request.cookies.get('search_history', '[]'))
    
    if request.method == "POST":
        city = request.form.get("city")
        america = request.form.get("america") == "on"
        session["america"] = america
        weather_data = get_weather(city)
        
        if weather_data and not str(weather_data.get("temp_c", "")).startswith(("400", "401", "403", "404", "500", "502", "503", "504", "ERROR")):

            history_entry = {
                "city": city,
                "temp_c": weather_data["temp_c"],
                "temp_f": weather_data["temp_f"],
                "description": weather_data["description"],
                "emoji": weather_data["emoji"]
            }
            
            search_history = [h for h in search_history if h["city"].lower() != city.lower()]
            
            search_history.insert(0, history_entry)
            search_history = search_history[:5]
        
        session["weather_data"] = weather_data
        resp = make_response(redirect(url_for('home')))
        resp.set_cookie('search_history', json.dumps(search_history), max_age=60*60*24*365)
        return resp
    
    if "weather_data" in session:
        weather_data = session["weather_data"]
    
    use_fahrenheit = session.get("america", False)
    resp = make_response(render_template("site.html", weather_data=weather_data, use_fahrenheit=use_fahrenheit, search_history=search_history))
    resp.set_cookie('search_history', json.dumps(search_history), max_age=60*60*24*365)  # 1 year
    return resp

def get_weather(city):
    api_key = "30c684ca65b3de8de22e0a7f0f3a5742"
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if data["cod"] == 200:
            temp_k = data["main"]["temp"]
            temp_c = int(temp_k - 273.15)
            temp_f = int((temp_k * 9/5) - 459.67)
            emoji = get_emoji(data["weather"][0]["id"])
            return {
                "city": city,
                "temp_c": temp_c,
                "temp_f": temp_f,
                "description": data["weather"][0]["description"],
                "emoji": emoji
            }
    
    except requests.exceptions.HTTPError as http_error:
        match response.status_code:
            case 400:
                return {"temp_c": "400", "temp_f": "400", "description": "Bad request:\nPlease check your input", "emoji": "❌"}
            case 401:
                return {"temp_c": "401", "temp_f": "401", "description": "Unauthorized:\nInvalid API key", "emoji": "❌"}
            case 403: 
                return {"temp_c": "403", "temp_f": "403", "description": "Forbidden:\nAccess is denied", "emoji": "❌"}
            case 404:
                return {"temp_c": "404", "temp_f": "404", "description": "Not found:\nCity not found", "emoji": "❌"}
            case 500:
                return {"temp_c": "500", "temp_f": "500", "description": "Internal Server Error:\nPlease try again later", "emoji": "❌"}
            case 502:
                return {"temp_c": "502", "temp_f": "502", "description": "Bad Gateway:\nInvalid response from the server", "emoji": "❌"}
            case 503:
                return {"temp_c": "503", "temp_f": "503", "description": "Service Unavalible:\nServer is down", "emoji": "❌"}
            case 504:
                return {"temp_c": "504", "temp_f": "504", "description": "Gateway Timeout:\nNo response from the server", "emoji": "❌"}
            case _:
                return {"temp_c": f"{http_error}", "temp_f": f"{http_error}", "description": f"HTTP error occured:\n{http_error}", "emoji": "❌"}
            
    except requests.exceptions.ConnectionError:
        return {"temp_c": "ERROR!", "temp_f": "ERROR!", "description": "Connection Error:\nCheck your internet connection", "emoji": "❌"}
    except requests.exceptions.Timeout:
        return {"temp_c": "ERROR!", "temp_f": "ERROR!", "description": "Timeout Error:\nThe request timed out", "emoji": "❌"}
    except requests.exceptions.TooManyRedirects:
        return {"temp_c": "ERROR!", "temp_f": "ERROR!", "description": "Too many Redirects:\nCheck the URL", "emoji": "❌"}
    except requests.exceptions.RequestException as req_error:
        return {"temp_c": "ERROR!", "temp_f": "ERROR!", "description": f"Request Error:\n{req_error}", "emoji": "❌"}

@app.route("/delete_history/<int:index>")
def delete_history(index):
    search_history = json.loads(request.cookies.get('search_history', '[]'))
    
    if 0 <= index < len(search_history):
        search_history.pop(index)
    
    resp = make_response(jsonify({"success": True}))
    resp.set_cookie('search_history', json.dumps(search_history), max_age=60*60*24*365)
    return resp

@app.route("/autocomplete")
def autocomplete():
    query = request.args.get("q", "")
    if len(query) < 2:
        return jsonify([])
    
    api_key = "30c684ca65b3de8de22e0a7f0f3a5742"
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={query}&limit=5&appid={api_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        suggestions = []
        for city in data:
            name = city["name"]
            country = city.get("country", "")
            state = city.get("state", "")
            if state:
                suggestions.append(f"{name}, {state}, {country}")
            else:
                suggestions.append(f"{name}, {country}")
        
        return jsonify(suggestions)
    except:
        return jsonify([])

def get_emoji(id):
    match id:
        case _ if 200 <= id <= 232:
            return "⛈️"
        case _ if 300 <= id <= 321:
            return "🌦️"
        case _ if 500 <= id <= 531:
            return "🌧️"
        case _ if 600 <= id <= 622:
            return "❄️"
        case _ if 701 <= id <= 741:
            return "🌫️"
        case 762:
            return "🌋"
        case 771:
            return "💨"
        case 781:
            return "🌪️"
        case 800:
            return "☀️"
        case _ if 801 <= id <= 804:
            return "☁️"
        case _:
            return ""

