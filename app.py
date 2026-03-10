import io
import os
import json
import base64
import sqlite3
import requests
import unicodedata
import numpy as np
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image
from functools import wraps
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch

from werkzeug.security import generate_password_hash, check_password_hash
import torchvision.transforms.functional as TF

from utils.db_manager import DatabaseManager
from utils.market_scraper import fetch_live_market_data
from utils.scheme_engine import scheme_engine
from utils.prediction_models import PredictionModels

load_dotenv()
models = PredictionModels()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
DatabaseManager.init_database()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def home_page():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        phone = request.form.get("phone")
        password = request.form.get("password")

        conn = DatabaseManager().get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE phone = ?", (phone,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["first_name"]
            session["phone"] = user["phone"]
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid phone or password", "error")

    return render_template("auth.html")


@app.route("/signup", methods=["POST"])
def signup():
    first_name = request.form.get("firstname")
    last_name = request.form.get("lastname")
    phone = request.form.get("phone")
    password = request.form.get("password")

    if not first_name or not last_name or not phone or not password:
        flash("All fields are required.", "error")
        return redirect(url_for("login_page"))

    hashed_password = generate_password_hash(password)

    conn = DatabaseManager().get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO users (first_name, last_name, phone, password_hash)
            VALUES (?, ?, ?, ?)
        """,
            (first_name, last_name, phone, hashed_password),
        )
        conn.commit()

        user_id = cursor.lastrowid
        session["user_id"] = user_id
        session["user_name"] = first_name

        flash("Account created successfully!", "success")
        return redirect(url_for("dashboard"))

    except sqlite3.IntegrityError:
        flash("That phone is already registered. Please log in.", "error")
        return redirect(url_for("login_page"))
    except Exception as e:
        flash("An error occurred. Please try again.", "error")
        print(f"Error: {e}")
        return redirect(url_for("login_page"))
    finally:
        conn.close()


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = DatabaseManager().get_connection()
    cursor = conn.cursor()

    required_fields = ["land_size", "annual_income", "age", "state", "gender", "caste"]

    select_fields_sql = ", ".join(required_fields)

    cursor.execute(
        f"SELECT {select_fields_sql} FROM users WHERE id = ?", (session["user_id"],)
    )
    user_data_tuple = cursor.fetchone()

    if user_data_tuple:
        user_data = dict(zip(required_fields, user_data_tuple))
    else:
        user_data = {}

    is_profile_complete = all(
        (value := user_data.get(field)) is not None
        and (value.strip() if isinstance(value, str) else value) not in (0, 0.0, "")
        for field in required_fields
    )

    cursor.execute(
        """
        SELECT * FROM diagnosis 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT 1
    """,
        (session["user_id"],),
    )
    last_scan = cursor.fetchone()

    return render_template(
        "dashboard.html",
        user={},
        last_scan=last_scan,
        is_profile_complete=is_profile_complete,
    )


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if "user_id" not in session:
        flash("Please log in to view your profile.", "warning")
        return redirect(url_for("index"))

    user_id = session["user_id"]
    conn = DatabaseManager().get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        try:
            first_name = request.form["first_name"]
            last_name = request.form["last_name"]
            phone = request.form["phone"]
            new_password = request.form.get("password")

            age = int(request.form["age"])
            gender = request.form["gender"]
            caste = request.form["caste"]
            state = request.form["state"]
            annual_income = float(request.form["annual_income"])
            land_size = float(request.form["land_size"])

            is_tenant = 1 if "is_tenant" in request.form else 0
            has_bank_account = 1 if "has_bank_account" in request.form else 0

            crops_str = request.form.get("crops", "")

            update_fields = [
                "first_name = ?",
                "last_name = ?",
                "phone = ?",
                "age = ?",
                "gender = ?",
                "caste = ?",
                "state = ?",
                "annual_income = ?",
                "land_size = ?",
                "is_tenant = ?",
                "has_bank_account = ?",
                "crops = ?",
            ]
            update_values = [
                first_name,
                last_name,
                phone,
                age,
                gender,
                caste,
                state,
                annual_income,
                land_size,
                is_tenant,
                has_bank_account,
                crops_str,
            ]

            if new_password:
                hashed_password = generate_password_hash(new_password)
                update_fields.append("password_hash = ?")
                update_values.append(hashed_password)

            update_query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
            update_values.append(user_id)

            cursor.execute(update_query, tuple(update_values))
            conn.commit()
            flash("Profile updated successfully!", "success")

        except sqlite3.IntegrityError:
            flash("Error: An account with this phone already exists.", "error")
            conn.rollback()
        except ValueError as e:
            flash(f"Invalid input for a number field: {e}", "error")
            conn.rollback()
        except Exception as e:
            flash(
                f"An unexpected error occurred while saving your profile: {e}", "error"
            )
            conn.rollback()

        return redirect(url_for("profile"))

    else:
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()

        if user_data is None:
            flash("Profile data not found for your account.", "error")
            session.pop("user_id", None)
            return redirect(url_for("index"))

        user_dict = dict(user_data)

        user_dict["crops"] = (
            [c.strip() for c in user_dict["crops"].split(",") if c.strip()]
            if user_dict["crops"]
            else []
        )

        user_dict["is_tenant"] = bool(user_dict["is_tenant"])
        user_dict["has_bank_account"] = bool(user_dict["has_bank_account"])

        return render_template("profile.html", user=user_dict)


def safe_text(text):
    if not text:
        return text
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def get_weather_desc(code):
    if code == 0:
        return "Clear Sky", "fas fa-sun text-yellow-500"
    if code in [1, 2, 3]:
        return "Partly Cloudy", "fas fa-cloud-sun text-gray-400"
    if code in [45, 48]:
        return "Foggy", "fas fa-smog text-gray-400"
    if code in [51, 53, 55, 61, 63, 65]:
        return "Rainy", "fas fa-cloud-rain text-blue-500"
    if code in [71, 73, 75]:
        return "Snowy", "fas fa-snowflake text-blue-300"
    if code in [95, 96, 99]:
        return "Thunderstorm", "fas fa-bolt text-purple-500"
    return "Overcast", "fas fa-cloud text-gray-500"


def get_weather_advisory(weather_data):
    advisory = []
    temp = weather_data.get("temperature", 0)
    wind_speed = weather_data.get("windspeed", 0)
    rain = weather_data.get("precipitation", 0)
    humidity = weather_data.get("humidity", 0)

    if temp > 35:
        advisory.append("Extreme heat expected. Ensure crops are well-watered.")
    elif temp < 5:
        advisory.append("Cold weather expected. Protect frost-sensitive crops.")

    if wind_speed > 25:
        advisory.append(
            "High winds expected. Secure loose structures and monitor crops for wind damage."
        )

    if rain > 10:
        advisory.append(
            "Heavy rain expected. Avoid spraying pesticides or fertilizers."
        )

    if humidity > 80:
        advisory.append("High humidity levels. Be aware of fungal diseases.")

    return advisory


@app.route("/api/get-weather", methods=["POST"])
def get_weather():
    try:
        data = request.get_json()
        lat = data.get("lat")
        lon = data.get("lon")

        if lat is None or lon is None:
            return jsonify({"error": "Location missing"}), 400

        weather_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,soil_temperature_0cm,soil_moisture_0_to_1cm",
            "timezone": "auto",
        }
        w_response = requests.get(weather_url, params=params)
        w_data = w_response.json()

        current = w_data.get("current_weather", {})
        hourly = w_data.get("hourly", {})

        temp = current.get("temperature", 0)
        current_time = current.get("time")
        
        humidity = 0
        rainfall = 0
        soil_temp = 25
        soil_moisture = 0.3
        
        if current_time and "time" in hourly:
            try:
                match_time = current_time[:13] + ":00" 
                if match_time in hourly["time"]:
                    idx = hourly["time"].index(match_time)
                else:
                    idx = hourly["time"].index(current_time)
                    
                humidity = hourly.get("relative_humidity_2m", [0] * len(hourly["time"]))[idx]
                rainfall = hourly.get("precipitation", [0] * len(hourly["time"]))[idx]
                soil_temp = hourly.get("soil_temperature_0cm", [25] * len(hourly["time"]))[idx]
                soil_moisture = hourly.get("soil_moisture_0_to_1cm", [0.3] * len(hourly["time"]))[idx]
            except (ValueError, IndexError):
                if len(hourly.get("relative_humidity_2m", [])) > 0:
                    humidity = hourly["relative_humidity_2m"][0]

        yesterday = (datetime.now() - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        one_year_ago = (datetime.now() - pd.Timedelta(days=365)).strftime('%Y-%m-%d')
        archive_url = "https://archive-api.open-meteo.com/v1/archive"
        archive_params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": one_year_ago,
            "end_date": yesterday,
            "daily": "temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum,soil_moisture_0_to_7cm_mean",
            "timezone": "auto"
        }
        arch_response = requests.get(archive_url, params=archive_params)
        arch_data = arch_response.json()
        
        daily_data = arch_data.get("daily", {})
        
        temp_list = daily_data.get("temperature_2m_mean", [])
        hum_list = daily_data.get("relative_humidity_2m_mean", [])
        rain_list = daily_data.get("precipitation_sum", [])
        mois_list = daily_data.get("soil_moisture_0_to_7cm_mean", [])
        
        annual_temp = sum(temp_list) / len(temp_list) if temp_list else temp
        annual_humidity = sum(hum_list) / len(hum_list) if hum_list else humidity
        annual_rainfall = sum(rain_list) if rain_list else 0
        annual_moisture = sum(mois_list) / len(mois_list) if mois_list else soil_moisture

        ph_url = f"https://rest.isric.org/soilgrids/v2.0/properties/query?lon={lon}&lat={lat}&property=phh2o&depth=0-5cm&value=mean"
        ph_val = 6.5
        try:
            ph_response = requests.get(ph_url, timeout=5)
            ph_data = ph_response.json()
            raw_ph = ph_data['properties']['layers'][0]['depths'][0]['values']['mean']
            ph_val = round(raw_ph / 10, 1)
        except Exception as e:
            print(f"Soil pH Error: {e}")

        geo_url = "https://nominatim.openstreetmap.org/reverse"
        geo_params = {"lat": lat, "lon": lon, "format": "json", "zoom": 10, "addressdetails": 1}
        g_response = requests.get(geo_url, params=geo_params, headers={"User-Agent": "WeatherApp/1.0"})
        g_data = g_response.json()

        city = "Unknown Location"
        if "address" in g_data:
            addr = g_data["address"]
            city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("state") or addr.get("country")

        advisory = get_weather_advisory(current)

        return jsonify({
            "temp": round(temp),
            "humidity": round(humidity),
            "annual_temp": round(annual_temp, 1),
            "annual_humidity": round(annual_humidity, 1),
            "annual_rainfall": round(annual_rainfall, 2),
            "annual_moisture": round(annual_moisture, 3),
            "ph": ph_val,
            "city": city,
            "soil_temp": soil_temp,
            "soil_moisture": soil_moisture,
            "rainfall": rainfall,
            "wind_speed": current.get("windspeed", 0),
            "advisory": advisory,
            "icon": get_weather_desc(current.get("weathercode", 0))[1],
        })

    except Exception as e:
        print(f"Weather Error: {e}")
        return jsonify({"error": "Failed to fetch weather"}), 500


@app.route("/api/get-advisory", methods=["POST"])
def get_advisory():
    data = request.get_json()

    if not data or "query" not in data:
        return jsonify({"error": "Invalid input. 'query' is required."}), 400

    query = data["query"]

    try:
        model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2)
        search_tool = TavilySearch(max_results=4)

        search_query = (
            f"agriculture news, warnings, alerts, or advice related to {query}"
        )
        news_results = search_tool.invoke(search_query)

        if not news_results:
            return (
                jsonify({"error": "No relevant news found for the given query."}),
                404,
            )

        news_summary = "\n".join(
            [f"- {article['title']}: {article['url']}" for article in news_results]
        )

        report_prompt = f"""
        You are an agricultural assistant. Based on the following news articles, provide a summary and recommendations for farmers.

        **News Articles:**
        {news_summary}

        **Task:**
        - Provide a summary of the key news articles.
        - Offer actionable advice or warnings based on the news for farmers.
        - If the news mentions weather or pest-related information, highlight these and provide relevant warnings or recommendations for preventive actions.
        """

        final_report_response = model.invoke([HumanMessage(content=report_prompt)])

        return jsonify({"advisory_report": final_report_response.content}), 200

    except Exception as e:
        return (
            jsonify({"error": "An error occurred while processing the advisory."}),
            500,
        )


@app.route("/api/market/trends", methods=["GET"])
def get_recent_trends():
    conn = DatabaseManager().get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        WITH RankedData AS (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY commodity ORDER BY created_at DESC) AS rn
            FROM market_trends
        )
        SELECT id, commodity, state, district, market, latest_price, trend, percentage_change,
               data_points_found, average_price, highest_price, lowest_price, prices_data, created_at
        FROM RankedData
        WHERE rn = 1
        LIMIT 6;
        """
    )
    rows = cursor.fetchall()
    conn.close()

    trends = []
    for row in rows:
        trends.append(
            {
                "commodity": row["commodity"],
                "market": row["market"],
                "state": row["state"],
                "price": row["latest_price"],
                "change": row["percentage_change"],
                "trend": row["trend"],
                "high": row["highest_price"],
                "low": row["lowest_price"],
                "updated": row["created_at"],
            }
        )

    return jsonify(trends)


@app.route("/api/market/search", methods=["POST"])
def search_market():
    data = request.json
    commodity = data.get("commodity")
    state = data.get("state")
    district = data.get("district")

    if not commodity or not state:
        return jsonify({"error": "Commodity and State are required"}), 400

    conn = DatabaseManager().get_connection()
    cursor = conn.cursor()

    search_commodity = f"%{commodity}%"
    search_state = f"%{state}%"

    cursor.execute(
        """
        SELECT * FROM market_trends 
        WHERE commodity LIKE ? AND state LIKE ? AND date(created_at) = date('now')
        ORDER BY created_at DESC LIMIT 1
    """,
        (search_commodity, search_state),
    )

    cached_row = cursor.fetchone()
    conn.close()

    if cached_row:
        print(f"Serving cached data for '{commodity}'")

        prices_list = []
        if cached_row["prices_data"]:
            try:
                prices_list = json.loads(cached_row["prices_data"])
            except:
                prices_list = []

        return jsonify(
            {
                "source": "cache",
                "commodity": cached_row["commodity"],
                "state": cached_row["state"],
                "district": cached_row["district"],
                "market": cached_row["market"],
                "latest_price": cached_row["latest_price"],
                "trend": cached_row["trend"],
                "percentage_change": cached_row["percentage_change"],
                "data_points_found": cached_row["data_points_found"],
                "average_price": cached_row["average_price"],
                "highest_price": cached_row["highest_price"],
                "lowest_price": cached_row["lowest_price"],
                "prices": prices_list,
            }
        )

    print(f"Scraping live data for {commodity} in {state}...")
    result = fetch_live_market_data(commodity, state, district)

    if "error" in result:
        return jsonify(result), 404

    try:
        conn = DatabaseManager().get_connection()
        cursor = conn.cursor()

        prices_json = json.dumps(result.get("prices", []))

        cursor.execute(
            """
            INSERT INTO market_trends (
                commodity, state, district, market, latest_price, trend, percentage_change,
                data_points_found, average_price, highest_price, lowest_price,
                prices_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                result.get("commodity"),
                result.get("state"),
                result.get("district"),
                result.get("market"),
                result.get("latest_price"),
                result.get("trend"),
                result.get("percentage_change"),
                result.get("data_points_found", 0),
                result.get("average_price"),
                result.get("highest_price"),
                result.get("lowest_price"),
                prices_json,
            ),
        )

        conn.commit()
        print(f"Successfully cached data for {commodity}")

    except Exception as e:
        print(f"Error caching market data: {e}")
    finally:
        if conn:
            conn.close()

    result["source"] = "live"
    return jsonify(result)


@app.route("/api/schemes/search", methods=["POST"])
@login_required
def search_schemes():
    user_id = session["user_id"]
    conn = DatabaseManager().get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()

    if user_data is None:
        return (
            jsonify(
                {
                    "error": "User profile not found. Please update your profile or log in again."
                }
            ),
            404,
        )

    user_profile = dict(user_data)

    user_profile["crops"] = (
        [c.strip() for c in user_profile["crops"].split(",") if c.strip()]
        if user_profile["crops"]
        else []
    )

    user_profile["is_tenant"] = bool(user_profile["is_tenant"])
    user_profile["has_bank_account"] = bool(user_profile["has_bank_account"])

    data = request.json
    query = data.get("query", "").strip()

    try:
        results = scheme_engine.search_schemes(query, user_profile=user_profile)
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Error in scheme search API: {e}", exc_info=True)
        return (
            jsonify({"error": "An internal error occurred during scheme search."}),
            500,
        )


@app.route("/schemes")
@login_required
def schemes_page():
    return render_template("schemes.html")


@app.route("/market")
@login_required
def market_page():
    conn = DatabaseManager().get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT DISTINCT state_name, district_name 
            FROM api_cached_locations 
            WHERE state_name IS NOT NULL AND district_name IS NOT NULL 
            ORDER BY state_name ASC, district_name ASC
        """
        )
        location_rows = cursor.fetchall()
    except sqlite3.OperationalError:
        location_rows = []
        print("Warning: api_cache_locations table missing.")

    locations = {}
    for row in location_rows:
        state = row["state_name"].strip()
        market = row["district_name"].strip()

        if state not in locations:
            locations[state] = []
        if market not in locations[state]:
            locations[state].append(market)

    try:
        cursor.execute(
            """
            SELECT DISTINCT commodity_name 
            FROM api_cached_commodities 
            WHERE commodity_name IS NOT NULL 
            ORDER BY commodity_name ASC
        """
        )
        commodity_rows = cursor.fetchall()
        commodities = [row["commodity_name"].strip() for row in commodity_rows]
    except sqlite3.OperationalError:
        commodities = []
        print("Warning: api_cache_commodities table missing.")

    conn.close()

    return render_template(
        "market_trends.html", locations=locations, commodities=commodities
    )


@app.route("/tools/fertilizer", methods=["GET", "POST"])
@login_required
def fertilizer_recommendation():
    result = None

    if request.method == "POST":
        try:
            temp = request.form.get("temp")
            humi = request.form.get("humid")
            mois = request.form.get("mois")
            soil = request.form.get("soil")
            crop = request.form.get("crop")
            nitro = request.form.get("nitro")
            pota = request.form.get("pota")
            phosp = request.form.get("phos")

            input = [
                int(temp),
                int(humi),
                int(mois),
                int(soil),
                int(crop),
                int(nitro),
                int(pota),
                int(phosp),
            ]
            res = models.ferti_model.classes_[models.classifier_model.predict([input])]

            result = f"Predicted Fertilizer is {res[0]}"

        except Exception as e:
            result = f"Error: {str(e)}"

    return render_template("tools/fertilizer.html", x=result)


@app.route("/tools/crop", methods=["GET", "POST"])
@login_required
def crop_recommendation():
    result = None
    error = None

    if request.method == "POST":
        try:
            if not models.crop_model:
                raise Exception("Model not loaded properly.")

            N = float(request.form.get("nitrogen"))
            P = float(request.form.get("phosphorus"))
            K = float(request.form.get("potassium"))
            temp = float(request.form.get("temperature"))
            humidity = float(request.form.get("humidity"))
            ph = float(request.form.get("ph"))
            rainfall = float(request.form.get("rainfall"))

            input_data = np.array([[N, P, K, temp, humidity, ph, rainfall]])

            prediction = models.crop_model.predict(input_data)

            result = prediction[0]

        except ValueError:
            error = "Invalid input. Please ensure all fields contain valid numbers."
        except Exception as e:
            error = f"Error during prediction: {str(e)}"

    strategy = None
    metrics = None
    if result and not error:
        land_area = request.form.get("land_area")
        fallow_percent = request.form.get("fallow_percent")
        duration = request.form.get("duration")
        
        if fallow_percent and duration:
            try:
                fp = float(fallow_percent)
                dr = float(duration)
                n_boost = (fp / 100) * dr * 2.5
                metrics = {
                    "n_boost": round(n_boost, 1),
                    "recovery_rate": round((fp * dr) / 12, 1)
                }
            except:
                metrics = None

        if land_area or (fallow_percent and int(fallow_percent) > 0) or duration:
            try:
                model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)
                prompt = f"""
                As an agricultural expert, provide an extremely brief, single-paragraph sustainability strategy (strictly max 40 words) for a farmer with:
                - Predicted Crop: {result}
                - Total Land: {land_area} acres
                - Barren/Fallow Land: {fallow_percent}%
                - Farming Duration: {duration} months
                - Soil Conditions: N={request.form.get('nitrogen')}, P={request.form.get('phosphorus')}, K={request.form.get('potassium')}, pH={request.form.get('ph')}

                The strategy must be ONE very short cohesive paragraph. Focus only on the most critical advice. No bullet points, no bold text, no headers.
                """
                strategy_response = model.invoke([HumanMessage(content=prompt)])
                strategy = strategy_response.content
            except Exception as e:
                print(f"Strategy Generation Error: {e}")
                strategy = "Focus on crop rotation and maintaining soil organic matter through balanced fertilization."

    return render_template(
        "tools/crop.html",
        result=result,
        error=error,
        strategy=strategy,
        metrics=metrics,
        user_input={
            "land_area": request.form.get("land_area"),
            "fallow_percent": request.form.get("fallow_percent"),
            "duration": request.form.get("duration"),
        }
        if request.method == "POST"
        else {},
    )


@app.route("/tools/yield", methods=["GET", "POST"])
@login_required
def yield_prediction():
    result = None
    error = None

    if request.method == "POST":
        try:
            current_year = datetime.now().year
            area = "India"

            rainfall = float(request.form["average_rain_fall_mm_per_year"])
            pesticides = float(request.form["pesticides_tonnes"])
            avg_temp = float(request.form["avg_temp"])
            item = request.form["Item"]

            features = np.array(
                [[current_year, rainfall, pesticides, avg_temp, area, item]],
                dtype=object,
            )

            transformed_features = models.yield_preprocessor.transform(features)
            prediction = models.yield_model.predict(transformed_features).reshape(1, -1)

            result = f"{prediction[0][0]:.2f}"

        except Exception as e:
            print(f"Yield Prediction Error: {e}")
            error = f"Error: {str(e)}. Please check your input values."

    return render_template("tools/yield.html", result=result, error=error)


@app.route("/simulation")
def simulation():
    return render_template("simulation.html")


@app.route("/api/simulate", methods=["POST"])
def run_simulation():
    data = request.json
    region = data.get("region")
    crop = data.get("crop")
    scenario = data.get("scenario")
    severity = data.get("severity", 50)
    resilience = data.get("resilience", 50)

    try:
        severity = int(data.get("severity", 50))
        resilience = int(data.get("resilience", 50))
    except (ValueError, TypeError):
        severity = 50
        resilience = 50

    severity_desc = (
        "Mild" if severity < 40 else "Severe" if severity < 80 else "Catastrophic"
    )
    finance_desc = (
        "Low funds/High Debt"
        if resilience < 30
        else "Moderate savings"
        if resilience < 70
        else "Strong financial buffer"
    )
    system_prompt = (
        "You are an expert agricultural advisor focused on creating adaptive and sustainable planting strategies to help farmers thrive despite environmental or economic challenges. "
        "Output ONLY the content body in valid HTML. "
        "Do NOT use Markdown syntax (like **bold** or ## header). Use HTML tags (<strong>, <h3>) instead. "
        "Do NOT wrap the output in ```html code blocks. "
        "Do NOT include <!DOCTYPE html>, <head>, or <body> tags. "
        "Ensure the response is complete and does not cut off mid-sentence."
    )

    user_prompt = f"""
    Create a detailed adaptive planting strategy for:
    - Region: {region}
    - Crop: {crop}
    - Event: {scenario}
    - Severity: {severity}% ({severity_desc})
    - Finances: {resilience}% ({finance_desc})

    Format structure:
    <h3>Executive Summary</h3>
    <p>...summary of the situation and overall strategy for adaptation...</p>

    <h4>1. Immediate Actions (First 48 Hours)</h4>
    <ul>
        <li><strong>[Specific Action Name]:</strong> [Details of adaptive strategies like adjusting planting schedules, irrigation management, or early crop protection measures...]</li>
        <li><strong>[Specific Action Name]:</strong> [Evaluate weather forecasts, assess immediate risks, and implement short-term safeguards...]</li>
    </ul>

    <h4>2. Adaptive Mitigation (Next 7 Days)</h4>
    <ul>
        <li><strong>[Specific Action Name]:</strong> [Adjust crop management techniques, including changes in irrigation, fertilization, and pest control based on new conditions...]</li>
        <li><strong>[Specific Action Name]:</strong> [Explore crop diversification or alternative planting methods to reduce risks in case of further impacts...]</li>
        <li><strong>[Specific Action Name]:</strong> [Collaborate with local farmers or agricultural extension services to share knowledge and resources...]</li>
    </ul>

    <h4>3. Long-term Recovery and Sustainability</h4>
    <ul>
        <li><strong>[Specific Action Name]:</strong> [Incorporate long-term soil health practices, crop rotation, and improved water management to enhance resilience in future growing seasons...]</li>
        <li><strong>[Specific Action Name]:</strong> [Adapt planting schedules or switch to more resilient crop varieties to minimize future risks...]</li>
        <li><strong>[Specific Action Name]:</strong> [Create or strengthen connections with local markets or cooperative groups to ensure better access to resources and sales in the future...]</li>
    </ul>
    """

    try:
        model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)
        
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        response = model.invoke([HumanMessage(content=full_prompt)])
        
        return jsonify({"success": True, "result": response.content})
    except Exception as e:
        print(f"Simulation Error: {e}")
        return jsonify({"success": False, "error": f"AI Simulation failed: {str(e)}"})


def prediction(image):
    image = image.resize((224, 224))
    input_data = TF.to_tensor(image)
    input_data = input_data.view((-1, 3, 224, 224))
    output = models.plant_diagnoser(input_data)
    output = output.detach().numpy()
    index = np.argmax(output)
    return index


@app.route("/diagnose", methods=["GET", "POST"])
@login_required
def diagnose():
    if request.method == "GET":
        return render_template("diagnose.html", disease_name=None)

    if request.method == "POST":
        try:
            image_b64 = request.form.get("image_b64")
            if not image_b64:
                flash("No image data received.", "error")
                return redirect(url_for("diagnose"))

            try:
                if "," in image_b64:
                    image_data = image_b64.split(",")[1]
                else:
                    image_data = image_b64

                decoded_image = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(decoded_image))
            except Exception as e:
                print(f"Image Processing Error: {e}")
                flash("Could not process the image. Please try again.", "error")
                return redirect(url_for("diagnose"))

            pred = prediction(image)

            healthy_pred_ids = [3, 5, 7, 11, 15, 18, 20, 23, 24, 25, 28, 38]

            full_disease_name = models.disease_info["disease_name"][pred]

            standardized_name = full_disease_name.replace(" : ", "|").replace(
                "___", "|"
            )
            parts = standardized_name.split("|")

            plant_name = parts[0].replace("_", " ").strip()

            is_healthy = pred in healthy_pred_ids

            if is_healthy:
                short_disease_name = "Healthy"
                disease_name = "Healthy"
                display_diagnosis = f"Your {plant_name.lower()} plant looks healthy."
            else:
                if len(parts) > 1:
                    disease_only = parts[1].replace("_", " ").strip()
                else:
                    disease_only = "Condition Detected"

                short_disease_name = disease_only
                disease_name = f"{plant_name} {disease_only}"
                display_diagnosis = (
                    f"Detected {disease_only.lower()} on your {plant_name.lower()}."
                )

            desc = models.disease_info["disease_description"][pred]
            prevent = models.disease_info["recommended_actions"][pred]

            try:
                sname = models.supplement_info["recommended_product"][pred]
                simage = models.supplement_info["product_image_url"][pred]
                purchase_url = models.supplement_info["purchase_url"][pred]
            except:
                sname, simage, purchase_url = None, None, None

            try:
                conn = DatabaseManager.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO diagnosis (user_id, plant_name, disease_name, is_healthy)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        session["user_id"],
                        plant_name,
                        short_disease_name,
                        1 if is_healthy else 0,
                    ),
                )
                conn.commit()
            except Exception as db_e:
                print(f"Database Save Error: {db_e}")

            return render_template(
                "diagnose.html",
                pred=pred,
                healthy_pred_ids=healthy_pred_ids,
                plant_name=plant_name,
                disease_name=disease_name,
                display_diagnosis=display_diagnosis,
                desc=desc,
                prevent=prevent,
                sname=sname,
                simage=simage,
                purchase_url=purchase_url,
                uploaded_image_b64=image_b64,
            )

        except Exception as e:
            import traceback

            traceback.print_exc()
            flash("An internal error occurred. Please try a clearer photo.", "error")
            return redirect(url_for("diagnose"))


@app.route("/supplements")
@login_required
def supplements_page():
    products = []
    for _, row in models.supplement_info.iterrows():
        if pd.notna(row["recommended_product"]) and row["recommended_product"].strip():

            card_type = "healthy" if "healthy" in row["disease_name"] else "diseased"

            product = {
                "name": row["recommended_product"],
                "image": row["product_image_url"],
                "purchase_url": row["purchase_url"],
                "type": card_type,
            }
            products.append(product)

    return render_template("supplements.html", products=products)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
