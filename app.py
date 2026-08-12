"""AI Travel Planner — Flask application entry point."""
import os
import re
import sys
from functools import wraps
from pathlib import Path


from flask import (
    Flask,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import config  # noqa: E402
from database import database as db  # noqa: E402
from services import image_service, weather_service  # noqa: E402
from services.gemini_service import GeminiError, generate_insight, generate_plan  # noqa: E402
from services.recommender import RecommenderError, get_recommender  # noqa: E402

app = Flask(__name__)
app.config.from_object(config)

db.init_db()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")

INTEREST_OPTIONS = [
    "Adventure", "Beach", "Culture", "Food", "Nature", "Luxury",
    "History", "Wildlife", "Nightlife", "Urban", "Wellness", "Seclusion",
]
TRAVEL_TYPES = ["Solo", "Couple", "Family", "Group"]
SEASONS = ["Summer", "Monsoon", "Autumn", "Winter"]


# ----------------------------------------------------------------- helpers
def current_user():
    uid = session.get("user_id")
    if uid and db.user_exists(uid):
        return {"id": uid, "email": session.get("email")}
    return None


@app.before_request
def load_user():
    g.user = current_user()


@app.context_processor
def inject_globals():
    return {
        "user": getattr(g, "user", None),
        "interest_options": INTEREST_OPTIONS,
        "travel_types": TRAVEL_TYPES,
        "seasons": SEASONS,
    }


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not getattr(g, "user", None):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Please sign in to continue."}), 401
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapper


def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("Invalid request body.")
    return data


def parse_int(value, field, lo, hi):
    try:
        number = int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a number.")
    if number < lo or number > hi:
        raise ValueError(f"{field} must be between {lo} and {hi}.")
    return number


def clean_interests(values):
    if not isinstance(values, list):
        return []
    return [v for v in values if v in INTEREST_OPTIONS][:12]


# ------------------------------------------------------------------ pages
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        action = request.form.get("action", "login")
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""

        if not EMAIL_RE.match(email):
            flash("Please enter a valid email address.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        elif action == "register":
            try:
                user = db.create_user(email, password)
                session.clear()
                session["user_id"] = user["id"]
                session["email"] = user["email"]
                session.permanent = bool(request.form.get("remember"))
                return redirect(url_for("home"))
            except ValueError as exc:
                flash(str(exc), "error")
            except Exception:
                flash("We could not create your account right now.", "error")
        else:
            try:
                user = db.verify_user(email, password)
            except Exception:
                user = None
                flash("Sign in is temporarily unavailable.", "error")
            if user:
                session.clear()
                session["user_id"] = user["id"]
                session["email"] = user["email"]
                session.permanent = bool(request.form.get("remember"))
                return redirect(request.args.get("next") or url_for("home"))
            flash("Incorrect email or password.", "error")

    if getattr(g, "user", None):
        return redirect(url_for("home"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def home():
    return render_template("home.html", active="home")


@app.route("/ml-prediction")
@login_required
def ml_prediction():
    return render_template("ml_prediction.html", active="ml")


@app.route("/ai-recommendation")
@login_required
def ai_recommendation():
    return render_template("ai_recommendation.html", active="ai")


@app.route("/planner")
@login_required
def planner():
    return render_template("planner.html", active="planner")


@app.route("/features")
@login_required
def features():
    return render_template("features.html", active="features")


@app.route("/my-trips")
@login_required
def my_trips():
    return render_template("my_trips.html", active="trips")


@app.route("/contact")
@login_required
def contact():
    return render_template("contact.html", active="contact")


# -------------------------------------------------------------------- API
@app.post("/api/predict")
@login_required
def api_predict():
    try:
        data = payload()
        budget = parse_int(data.get("budget_inr"), "Total budget", 1000, 100_000_000)
        days = parse_int(data.get("days"), "Days", 1, 60)
        travel_type = data.get("travel_type") if data.get("travel_type") in TRAVEL_TYPES else None
        season = data.get("season") if data.get("season") in SEASONS else None
        interests = clean_interests(data.get("interests"))
        start_location = (data.get("start_location") or "").strip()[:80]

        result = get_recommender().recommend(
            budget_inr=budget,
            days=days,
            travel_type=travel_type,
            season=season,
            interests=interests,
            start_location=start_location,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RecommenderError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception:
        app.logger.exception("prediction failed")
        return jsonify({"error": "Something went wrong while generating recommendations."}), 500

    for item in result["results"]:
        item["image_url"] = image_service.get_image(f"{item['city']} {item['country']}")
    return jsonify(result)


@app.post("/api/insight")
@login_required
def api_insight():
    try:
        data = payload()
        ctx = {
            "destination": (data.get("destination") or "").strip()[:80],
            "country": (data.get("country") or "").strip()[:60],
            "budget_inr": parse_int(data.get("budget_inr"), "Total budget", 1000, 100_000_000),
            "days": parse_int(data.get("days"), "Days", 1, 60),
            "travel_type": data.get("travel_type"),
            "season": data.get("season"),
            "interests": clean_interests(data.get("interests")),
            "start_location": (data.get("start_location") or "").strip()[:80],
        }
        if not ctx["destination"]:
            raise ValueError("Please choose a destination first.")
        insight = generate_insight(ctx)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except GeminiError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception:
        app.logger.exception("insight failed")
        return jsonify({"error": "Could not generate the AI briefing."}), 500

    insight["hero_image"] = image_service.get_image(f"{ctx['destination']} {ctx['country']}")
    for item in insight.get("highlights") or []:
        if isinstance(item, dict):
            item["image_url"] = image_service.get_image(
                f"{item.get('title', '')} {ctx['destination']}"
            )
    return jsonify({"destination": ctx["destination"], "country": ctx["country"], "insight": insight})


@app.post("/api/ai-plan")
@login_required
def api_ai_plan():
    try:
        data = payload()
        ctx = {
            "destination": (data.get("destination") or "").strip()[:80],
            "country": (data.get("country") or "").strip()[:60],
            "budget_inr": parse_int(data.get("budget_inr"), "Total budget", 1000, 100_000_000),
            "days": parse_int(data.get("days"), "Days", 1, 60),
            "travel_type": data.get("travel_type"),
            "season": data.get("season"),
            "interests": clean_interests(data.get("interests")),
            "start_location": (data.get("start_location") or "").strip()[:80],
        }
        if not ctx["destination"]:
            raise ValueError("Please choose a destination first.")
        plan = generate_plan(ctx)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except GeminiError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception:
        app.logger.exception("plan failed")
        return jsonify({"error": "Could not generate the AI itinerary."}), 500

    place = f"{ctx['destination']} {ctx['country']}".strip()
    plan["hero_image"] = image_service.get_image(place)
    for hotel in (plan.get("hotels") or [])[:6]:
        if isinstance(hotel, dict):
            hotel["image_url"] = image_service.get_image(f"hotel {ctx['destination']}")
    for rest in (plan.get("restaurants") or [])[:6]:
        if isinstance(rest, dict):
            rest["image_url"] = image_service.get_image(
                f"{rest.get('cuisine', '')} food {ctx['destination']}"
            )
    for act in (plan.get("activities") or [])[:6]:
        if isinstance(act, dict):
            act["image_url"] = image_service.get_image(f"{act.get('name', '')} {ctx['destination']}")

    weather = None
    if data.get("latitude") and data.get("longitude"):
        try:
            weather = weather_service.get_weather(
                float(data["latitude"]), float(data["longitude"]), ctx["destination"]
            )
        except (TypeError, ValueError):
            weather = None

    return jsonify({"context": ctx, "plan": plan, "weather": weather})


@app.post("/api/save-trip")
@login_required
def api_save_trip():
    try:
        data = payload()
        trip = {
            "destination": (data.get("destination") or "").strip()[:80],
            "country": (data.get("country") or "").strip()[:60],
            "budget_inr": parse_int(data.get("budget_inr"), "Total budget", 1000, 100_000_000),
            "days": parse_int(data.get("days"), "Days", 1, 60),
            "travel_type": data.get("travel_type"),
            "interests": clean_interests(data.get("interests")),
            "season": data.get("season"),
            "start_location": (data.get("start_location") or "").strip()[:80],
            "image_url": (data.get("image_url") or "")[:500],
            "plan": data.get("plan") if isinstance(data.get("plan"), dict) else {},
        }
        if not trip["destination"] or not trip["plan"]:
            raise ValueError("Generate an itinerary before saving the trip.")
        trip_id = db.save_trip(g.user["id"], trip)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        app.logger.exception("save trip failed")
        return jsonify({"error": "Could not save this trip. Please try again."}), 500
    return jsonify({"id": trip_id, "message": "Trip saved to My Trips."})


@app.get("/api/my-trips")
@login_required
def api_my_trips():
    try:
        return jsonify({"trips": db.list_trips(g.user["id"])})
    except Exception:
        app.logger.exception("list trips failed")
        return jsonify({"error": "Could not load your saved trips."}), 500
    
@app.delete("/api/my-trips/<int:trip_id>")
@login_required
def api_delete_trip(trip_id):
    try:
        if not db.delete_trip(g.user["id"], trip_id):
            return jsonify({"error": "Trip not found."}), 404
    except Exception:
        return jsonify({"error": "Could not delete this trip."}), 500
    return jsonify({"message": "Trip deleted."})


@app.post("/api/contact")
@login_required
def api_contact():
    try:
        data = payload()
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip()
        message = (data.get("message") or "").strip()
        if not (2 <= len(name) <= 100):
            raise ValueError("Please enter your name (2-100 characters).")
        if not EMAIL_RE.match(email) or len(email) > 255:
            raise ValueError("Please enter a valid email address.")
        if not (10 <= len(message) <= 1000):
            raise ValueError("Message must be between 10 and 1000 characters.")
        db.save_message(name, email, message, g.user["id"])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        app.logger.exception("contact failed")
        return jsonify({"error": "Could not send your message right now."}), 500
    return jsonify({"message": "Thanks! Your message has been received."})


# --------------------------------------------------------------- handlers
@app.errorhandler(404)
def not_found(_):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Endpoint not found."}), 404
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(_):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error."}), 500
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)