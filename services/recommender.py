"""ML recommendation service.


Loads the supplied trained artefacts with joblib and reproduces the exact
preprocessing used at training time:

    features (in this order, taken from feature_scaler.feature_names_in_):
        ideal_durations  -> duration_encoder.transform (LabelEncoder)
        budget_level     -> budget_encoder.transform   (LabelEncoder)
        culture, adventure, nature, beaches, nightlife,
        cuisine, wellness, urban, seclusion  -> raw 1..5 ratings
    then StandardScaler, then NearestNeighbors(metric='cosine').

The user's request is turned into a vector in the *same* representation:
the trained model is rating based (1..5 per interest column), so a selected
interest is expressed as the maximum training value (5) and an unselected one
as the dataset mean for that column (a neutral, non-preferential value).
No feature is invented and no column is re-ordered.
"""
import json
import math

import joblib
import numpy as np
import pandas as pd

from config import config

# Interest label shown in the UI -> dataset feature column
INTEREST_MAP = {
    "Adventure": "adventure",
    "Beach": "beaches",
    "Culture": "culture",
    "Food": "cuisine",
    "Nature": "nature",
    "History": "culture",
    "Wildlife": "nature",
    "Nightlife": "nightlife",
    "Urban": "urban",
    "Wellness": "wellness",
    "Seclusion": "seclusion",
    "Luxury": None,  # handled through the budget level, not an interest column
}

RATING_COLUMNS = [
    "culture",
    "adventure",
    "nature",
    "beaches",
    "nightlife",
    "cuisine",
    "wellness",
    "urban",
    "seclusion",
]

# Indicative all-in daily spend per person, in INR, for each dataset budget
# level. Used only to translate a TOTAL trip budget into the categorical
# budget_level the model was trained on, and to estimate a trip total.
DAILY_COST_INR = {"Budget": 90000, "Mid-range": 120000, "Luxury": 200000}

SEASON_MONTHS = {
    "Summer": [4, 5, 6],
    "Monsoon": [7, 8, 9],
    "Autumn": [10, 11],
    "Winter": [12, 1, 2, 3],
}
MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class RecommenderError(Exception):
    """Raised for user-correctable recommendation problems."""


class Recommender:
    def __init__(self):
        self.model = joblib.load(config.MODEL_DIR / "recommendation_model.pkl")
        self.scaler = joblib.load(config.MODEL_DIR / "feature_scaler.pkl")
        self.budget_encoder = joblib.load(config.MODEL_DIR / "budget_encoder.pkl")
        self.duration_encoder = joblib.load(config.MODEL_DIR / "duration_encoder.pkl")

        self.feature_order = [str(c) for c in self.scaler.feature_names_in_]
        self.df = pd.read_csv(config.DATA_FILE)

        missing = [c for c in self.feature_order if c not in self.df.columns]
        if missing:
            raise RecommenderError(f"Dataset is missing model columns: {missing}")
        if self.model.n_features_in_ != len(self.feature_order):
            raise RecommenderError("Model and scaler expect a different number of features.")

        self.column_means = {c: float(self.df[c].mean()) for c in RATING_COLUMNS}
        self.budget_classes = list(self.budget_encoder.classes_)
        self.duration_classes = list(self.duration_encoder.classes_)

    # ------------------------------------------------------------- helpers
    def budget_level_for(self, total_budget_inr: int, days: int) -> str:
        """Map a TOTAL trip budget in INR to a dataset budget level."""
        per_day = total_budget_inr / max(days, 1)
        if per_day < DAILY_COST_INR["Mid-range"] * 0.75:
            level = "Budget"
        elif per_day < DAILY_COST_INR["Luxury"] * 0.75:
            level = "Mid-range"
        else:
            level = "Luxury"
        return level if level in self.budget_classes else self.budget_classes[0]

    def duration_label_for(self, days: int) -> str:
        if days <= 2:
            label = "Weekend"
        elif days <= 4:
            label = "Short trip"
        elif days <= 8:
            label = "One week"
        else:
            label = "Long trip"
        return label if label in self.duration_classes else self.duration_classes[0]

    def _rating_vector(self, interests, travel_type):
        values = dict(self.column_means)
        for label in interests or []:
            col = INTEREST_MAP.get(label)
            if col:
                values[col] = 5.0
        # Travel type only nudges columns that describe the style of the trip.
        tt = (travel_type or "").lower()
        if tt == "solo":
            values["seclusion"] = max(values["seclusion"], 4.0)
        elif tt == "couple":
            values["wellness"] = max(values["wellness"], 4.0)
        elif tt == "family":
            values["nightlife"] = min(values["nightlife"], 2.0)
        elif tt == "group":
            values["nightlife"] = max(values["nightlife"], 4.0)
        return values

    def best_month(self, row, season):
        """Pick the month with the most comfortable average temperature."""
        try:
            monthly = json.loads(row["avg_temp_monthly"])
        except Exception:
            return None, None
        months = SEASON_MONTHS.get(season) or list(range(1, 13))
        candidates = [(int(m), monthly[str(m)]["avg"]) for m in months if str(m) in monthly]
        if not candidates:
            candidates = [(int(m), v["avg"]) for m, v in monthly.items()]
        if not candidates:
            return None, None
        month, temp = min(candidates, key=lambda mt: abs(mt[1] - 23))
        return MONTH_NAMES[month - 1], round(float(temp), 1)

    # ---------------------------------------------------------- prediction
    def recommend(self, *, budget_inr, days, travel_type, season, interests, start_location, top_n=6):
        if budget_inr <= 0:
            raise RecommenderError("Total budget must be greater than zero.")
        if days <= 0 or days > 60:
            raise RecommenderError("Number of days must be between 1 and 60.")

        budget_level = self.budget_level_for(budget_inr, days)
        duration_label = self.duration_label_for(days)
        ratings = self._rating_vector(interests, travel_type)

        query = {
            "ideal_durations": int(self.duration_encoder.transform([duration_label])[0]),
            "budget_level": int(self.budget_encoder.transform([budget_level])[0]),
        }
        query.update(ratings)

        frame = pd.DataFrame([[query[c] for c in self.feature_order]], columns=self.feature_order)
        vector = self.scaler.transform(frame)

        n = min(max(top_n * 4, top_n), int(self.model.n_samples_fit_))
        distances, indices = self.model.kneighbors(vector, n_neighbors=n)

        results = []
        seen = set()
        for dist, idx in zip(distances[0], indices[0]):
            row = self.df.iloc[int(idx)]
            key = (row["city"], row["country"])
            if key in seen:
                continue
            seen.add(key)
            month, temp = self.best_month(row, season)
            level = str(row["budget_level"])
            estimated = int(DAILY_COST_INR.get(level, DAILY_COST_INR["Mid-range"]) * days)
            results.append(
                {
                    "id": str(row["id"]),
                    "city": str(row["city"]),
                    "country": str(row["country"]),
                    "region": str(row["region"]).replace("_", " ").title(),
                    "description": str(row["short_description"]),
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "budget_level": level,
                    "ideal_duration": str(row["ideal_durations"]),
                    "best_month": month,
                    "best_month_temp": temp,
                    "match": round(max(0.0, (1.0 - float(dist))) * 100, 1),
                    "estimated_total_inr": estimated,
                    "within_budget": estimated <= budget_inr,
                    "tags": [c.title() for c in RATING_COLUMNS if int(row[c]) >= 4],
                }
            )
            if len(results) >= top_n:
                break

        if not results:
            raise RecommenderError("No destination matched those preferences.")

        return {
            "budget_level": budget_level,
            "duration_label": duration_label,
            "per_day_inr": int(round(budget_inr / max(days, 1))),
            "start_location": start_location,
            "season": season,
            "results": results,
        }


_recommender = None
_load_error = None


def get_recommender():
    global _recommender, _load_error
    if _recommender is None and _load_error is None:
        try:
            _recommender = Recommender()
        except Exception as exc:  # noqa: BLE001 - surfaced as a friendly message
            _load_error = str(exc)
    if _recommender is None:
        raise RecommenderError(f"Recommendation engine unavailable: {_load_error}")
    return _recommender


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 1)


def np_safe(value):
    return value.item() if isinstance(value, np.generic) else value