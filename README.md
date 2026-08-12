# AI Travel Planner

A professional AI + ML travel planning web application.

- **Frontend:** HTML5, CSS3, Vanilla JavaScript (no frameworks, no build step)
- **Backend:** Python + Flask
- **ML:** pandas, NumPy, scikit-learn, joblib (supplied trained artefacts)
- **AI:** Google Gemini API 
- **Database:** SQLite

## Quick start

```bash
cd AI-Travel-Planner
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then fill in your keys
python app.py
```

Open http://localhost:5000 — you'll land on the login page. Create an account
with the **Register** button, then you're taken to the Home page.

## Environment variables (`.env`)

| Variable | Purpose | Required |
| --- | --- | --- |
| `SECRET_KEY` | Flask session signing | yes |
| `GEMINI_API_KEY` | AI briefings and itineraries | yes for AI pages |
| `GEMINI_MODEL` | Defaults to `gemini-2.5-flash` | no |
| `UNSPLASH_ACCESS_KEY` | Destination photography | no (falls back gracefully) |
| `OPENWEATHER_API_KEY` | Current weather in the planner | no |

Keys are read only in Python. They are never rendered into HTML, CSS or JS.

## ML pipeline

The supplied artefacts are used exactly as trained — nothing is retrained or
re-ordered:

| Artefact | Type |
| --- | --- |
| `recommendation_model.pkl` | `NearestNeighbors(metric='cosine')`, 11 features, 560 fitted rows |
| `feature_scaler.pkl` | `StandardScaler` over the 11 feature columns |
| `budget_encoder.pkl` | `LabelEncoder` — Budget / Luxury / Mid-range |
| `duration_encoder.pkl` | `LabelEncoder` — Long trip / One week / Short trip / Weekend |

Feature order comes straight from `feature_scaler.feature_names_in_`:

```
ideal_durations, budget_level, culture, adventure, nature,
beaches, nightlife, cuisine, wellness, urban, seclusion
```

Request → feature vector:

- **Total INR budget ÷ days** → per-day spend → dataset `budget_level``
- **Days** → `Weekend` (≤2), `Short trip` (≤4), `One week` (≤8), `Long trip` → `duration_encoder`
- **Interests** map directly onto the trained rating columns
  (Adventure→adventure, Beach→beaches, Food→cuisine, Nature→nature,
  History→culture, Wildlife→nature, Nightlife→nightlife, Urban→urban,
  Wellness→wellness, Seclusion→seclusion). The model was trained on 1–5
  ratings, so a chosen interest is expressed at the training maximum (5) and an
  unchosen one at that column's dataset mean (neutral).
- The vector is scaled with the supplied `StandardScaler` and passed to
  `kneighbors`; cosine distance is reported as `match = (1 - distance) × 100`.

**Best month** is computed from the real `avg_temp_monthly` data in the CSV,
restricted to the chosen season, picking the month closest to 23 °C.

**Budget is always the TOTAL trip budget in INR**, never per-day, on every page
and in every AI prompt.

## Project structure

```
AI-Travel-Planner/
├── app.py               Flask routes + JSON API
├── config.py            env-based configuration
├── data/WWT_clean.csv   destination dataset (560 rows)
├── models/*.pkl         supplied trained artefacts
├── services/            recommender, gemini, image, weather
├── database/database.py SQLite users / trips / messages
├── templates/           Jinja pages
└── static/css, static/js
```

## API

| Method | Route | Purpose |
| --- | --- | --- |
| POST | `/api/predict` | ML destination recommendations |
| POST | `/api/insight` | AI destination briefing |
| POST | `/api/ai-plan` | AI day-by-day itinerary |
| POST | `/api/save-trip` | Save a generated trip |
| GET | `/api/my-trips` | List saved trips |
| DELETE | `/api/my-trips/<id>` | Delete a saved trip |
| POST | `/api/contact` | Store a contact message |

All API routes require a signed-in session and return friendly JSON errors —
stack traces are never sent to the browser.
