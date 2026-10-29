
from datetime import timedelta

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from models import HospitalDailyStats


def _build_features(data):
    """Create date and recent-history features for patient demand."""
    result = data.copy()

    result["day_number"] = (
        result["date"] - result["date"].min()
    ).dt.days
    result["day_of_week"] = result["date"].dt.dayofweek

    # Recent patient counts help the model learn repeating patterns.
    result["lag_1"] = result["patients"].shift(1)
    result["lag_7"] = result["patients"].shift(7)
    result["rolling_mean_7"] = (
        result["patients"].shift(1).rolling(7).mean()
    )

    return result


def _error_metrics(actual, predicted):
    """Return MAE and RMSE for predictions."""
    return {
        "mae": round(float(mean_absolute_error(actual, predicted)), 2),
        "rmse": round(float(mean_squared_error(actual, predicted) ** 0.5), 2),
    }


def predict_patient_demand(days_ahead=7):
    """
    Forecast patient demand with Random Forest and compare it with
    a seasonal-naive baseline. This is an experimental demo model.
    """

    records = (
        HospitalDailyStats.query
        .order_by(HospitalDailyStats.record_date.asc())
        .all()
    )

    if len(records) < 14:
        return {
            "success": False,
            "message": (
                "At least 14 daily records are recommended for the "
                "weekly-pattern model. Add more daily records first."
            ),
        }

    data = pd.DataFrame([
        {
            "date": record.record_date,
            "patients": record.patients,
        }
        for record in records
    ])

    data["date"] = pd.to_datetime(data["date"])
    data = data.sort_values("date").reset_index(drop=True)

    # Require one record per day for meaningful weekly lag features.
    date_gaps = data["date"].diff().dropna()
    if not date_gaps.eq(pd.Timedelta(days=1)).all():
        return {
            "success": False,
            "message": (
                "The model requires consecutive daily records without "
                "missing dates. Add or correct missing daily records."
            ),
        }

    featured = _build_features(data)
    features = [
        "day_number",
        "day_of_week",
        "lag_1",
        "lag_7",
        "rolling_mean_7",
    ]

    # First seven rows do not have a full lag-7 history.
    usable = featured.dropna(subset=features).reset_index(drop=True)

    if len(usable) < 7:
        return {
            "success": False,
            "message": "More daily records are needed to evaluate the model.",
        }

    # Keep the test period at the end of the timeline.
    split_index = max(1, int(len(usable) * 0.8))
    split_index = min(split_index, len(usable) - 1)

    train = usable.iloc[:split_index].copy()
    test = usable.iloc[split_index:].copy()

    X_train = train[features]
    y_train = train["patients"]
    X_test = test[features]
    y_test = test["patients"]

    evaluation_model = RandomForestRegressor(
        n_estimators=200,
        random_state=42,
    )
    evaluation_model.fit(X_train, y_train)
    test_predictions = evaluation_model.predict(X_test)

    # Seasonal-naive prediction: use the value from seven days earlier.
    # The original data is indexed by consecutive calendar days.
    original_by_date = data.set_index("date")["patients"]
    baseline_predictions = test["date"].apply(
        lambda d: float(original_by_date.loc[d - pd.Timedelta(days=7)])
    ).to_numpy()

    rf_metrics = _error_metrics(y_test, test_predictions)
    baseline_metrics = _error_metrics(y_test, baseline_predictions)

    r2 = (
        round(float(r2_score(y_test, test_predictions)), 3)
        if len(y_test) >= 2
        else None
    )

    # Retrain on all usable records for the future forecast.
    final_model = RandomForestRegressor(
        n_estimators=200,
        random_state=42,
    )
    final_model.fit(usable[features], usable["patients"])

    # Predict future dates recursively, updating the recent history.
    history = data[["date", "patients"]].copy()
    forecast_dates = []
    forecast_patients = []

    for offset in range(1, days_ahead + 1):
        future_date = data["date"].max() + timedelta(days=offset)
        last_date = history["date"].max()

        day_number = int((future_date - data["date"].min()).days)
        lag_1 = float(history.iloc[-1]["patients"])

        if len(history) >= 7:
            lag_7 = float(history.iloc[-7]["patients"])
            rolling_mean_7 = float(history["patients"].tail(7).mean())
        else:
            lag_7 = lag_1
            rolling_mean_7 = float(history["patients"].mean())

        future_features = pd.DataFrame([{
            "day_number": day_number,
            "day_of_week": future_date.dayofweek,
            "lag_1": lag_1,
            "lag_7": lag_7,
            "rolling_mean_7": rolling_mean_7,
        }])

        predicted = max(
            0,
            round(float(final_model.predict(future_features)[0])),
        )

        forecast_dates.append(future_date.isoformat())
        forecast_patients.append(predicted)

        history = pd.concat([
            history,
            pd.DataFrame([{
                "date": future_date,
                "patients": predicted,
            }]),
        ], ignore_index=True)

    return {
        "success": True,
        "historical_dates": [
            record.record_date.isoformat() for record in records
        ],
        "historical_patients": [
            record.patients for record in records
        ],
        "forecast_dates": forecast_dates,
        "forecast_patients": forecast_patients,
        "model": "Random Forest Regression with weekly lag features",
        "is_experimental": True,
        "metrics": {
            "mae": rf_metrics["mae"],
            "rmse": rf_metrics["rmse"],
            "r2": r2,
            "baseline_mae": baseline_metrics["mae"],
            "baseline_rmse": baseline_metrics["rmse"],
            "test_records": len(y_test),
            "baseline_name": "Previous-week seasonal baseline",
        },
    }


def generate_resource_recommendations():
    """Generate preliminary checks using the latest saved hospital record."""

    latest = (
        HospitalDailyStats.query
        .order_by(HospitalDailyStats.record_date.desc())
        .first()
    )

    if latest is None:
        return {
            "success": False,
            "message": "Please add hospital records first.",
            "recommendations": [],
        }

    forecast = predict_patient_demand(days_ahead=7)

    if not forecast["success"]:
        return {
            "success": False,
            "message": forecast["message"],
            "recommendations": [],
        }

    total_beds = latest.total_beds
    occupied_beds = latest.occupied_beds
    available_beds = max(total_beds - occupied_beds, 0)
    available_doctors = latest.available_doctors
    peak_patients = max(forecast["forecast_patients"])

    recommendations = []

    if total_beds <= 0:
        recommendations.append({
            "level": "warning",
            "title": "Bed Capacity Not Recorded",
            "message": "Enter a valid total bed capacity.",
        })
    elif peak_patients > total_beds:
        recommendations.append({
            "level": "warning",
            "title": "Potential Capacity Pressure",
            "message": (
                f"The forecast peak is {peak_patients} patients, "
                f"compared with {total_beds} total beds. "
                "Review capacity and contingency plans."
            ),
        })
    else:
        recommendations.append({
            "level": "success",
            "title": "Forecast Within Recorded Bed Capacity",
            "message": (
                f"The forecast peak is {peak_patients} patients "
                f"against {total_beds} total beds. "
                "Review daily occupancy before making decisions."
            ),
        })

    recommendations.append({
        "level": "info",
        "title": "Current Bed Availability",
        "message": (
            f"{available_beds} beds available, {occupied_beds} occupied, "
            f"{total_beds} total beds."
        ),
    })

    if available_doctors <= 0:
        recommendations.append({
            "level": "warning",
            "title": "Verify Doctor Availability",
            "message": "No available doctors are recorded. Verify staffing.",
        })
    else:
        recommendations.append({
            "level": "info",
            "title": "Staffing Review",
            "message": (
                f"{available_doctors} doctors are recorded as available. "
                "Review staffing against expected demand."
            ),
        })

    return {
        "success": True,
        "peak_patients": peak_patients,
        "total_beds": total_beds,
        "occupied_beds": occupied_beds,
        "available_beds": available_beds,
        "available_doctors": available_doctors,
        "recommendations": recommendations,
    }
