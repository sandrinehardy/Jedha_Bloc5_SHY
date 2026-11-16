#Entrainement des modeles de prediction du prix de location (Getaround).

import os
from pathlib import Path

import mlflow
import mlflow.sklearn
import pandas as pd
from dotenv import load_dotenv
from mlflow.tracking import MlflowClient
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# --- Connexion a MLflow (variables lues dans le fichier .env) ---
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
EXPERIMENT = "getaround_rental_price"
MODEL_NAME = "getaround_rental_price"
mlflow.set_experiment(EXPERIMENT)
client = MlflowClient()

# --- Donnees ---
DATA = Path(__file__).resolve().parent.parent / "Data" / "get_around_pricing_project.csv"
df = pd.read_csv(DATA, index_col=0)

target = "rental_price_per_day"
num_cols = ["mileage", "engine_power"]
cat_cols = ["model_key", "fuel", "paint_color", "car_type"]
bool_cols = [
    "private_parking_available",
    "has_gps",
    "has_air_conditioning",
    "automatic_car",
    "has_getaround_connect",
    "has_speed_regulator",
    "winter_tires",
]

# Nettoyage : on retire les lignes aberrantes (kilometrage / puissance)
df_clean = df[
    (df["mileage"] > 0) & (df["engine_power"] > 0) & (df["mileage"] <= 600_000)
].copy()

X = df_clean[num_cols + cat_cols + bool_cols].copy()
X[bool_cols] = X[bool_cols].astype(float) #pour le SimpleImputer
y = df_clean[target]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# --- Preprocessing ---
preprocessor = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), num_cols),
        (
            "cat",
            Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="most_frequent")),
                    ("encoder", OneHotEncoder(handle_unknown="ignore")),
                ]
            ),
            cat_cols,
        ),
        ("bool", SimpleImputer(strategy="most_frequent"), bool_cols),
    ]
)

# --- Modeles et leurs paramètres ---
models = {
    "LinearRegression": (
        LinearRegression(),
        {"regressor__fit_intercept": [True, False]},
    ),
    "Ridge": (
        Ridge(),
        {"regressor__alpha": [0.01, 0.1, 1, 10, 100]},
    ),
    "RandomForest": (
        RandomForestRegressor(random_state=42),
        {
            "regressor__n_estimators": [100, 300],
            "regressor__max_depth": [None, 10, 20],
            "regressor__min_samples_leaf": [1, 3, 5],
        },
    ),
    "GradientBoosting": (
        GradientBoostingRegressor(random_state=42),
        {
            "regressor__n_estimators": [100, 300],
            "regressor__learning_rate": [0.05, 0.1],
            "regressor__max_depth": [3, 5],
        },
    ),
}


best_test_mae = float("inf")
best_name = None
best_params = None
best_regressor = None

# --- Boucle sur les modeles ---
for name, (regressor, param_grid) in models.items():
    pipe = Pipeline([("preprocessor", preprocessor), ("regressor", regressor)])
    grid = GridSearchCV(
        pipe, param_grid=param_grid, cv=5, scoring="neg_mean_absolute_error", n_jobs=-1
    )

    with mlflow.start_run(run_name=name):
        grid.fit(X_train, y_train)
        print(f"entrainement du modele {name} terminé")
        best = grid.best_estimator_

        cv_mae = -grid.best_score_
        cv_std = grid.cv_results_["std_test_score"][grid.best_index_]
        pred = best.predict(X_test)
        test_mae = mean_absolute_error(y_test, pred)
        test_r2 = r2_score(y_test, pred)

        mlflow.log_param("model_type", name)
        mlflow.log_params(grid.best_params_)
        mlflow.log_metric("cv_mae", cv_mae)
        mlflow.log_metric("cv_mae_std", cv_std)
        mlflow.log_metric("test_mae", test_mae)
        mlflow.log_metric("test_r2", test_r2)

        info = mlflow.sklearn.log_model(
            best,
            name="model",
            serialization_format="cloudpickle",
            input_example=X_train.head(3),
            registered_model_name=MODEL_NAME,
        )

        client.update_model_version(
            MODEL_NAME,
            info.registered_model_version,
            description=f"{name} - MAE CV {cv_mae:.2f}, MAE test {test_mae:.2f}",
        )

        print(f"{name}: CV MAE {cv_mae:.2f} (+/- {cv_std:.2f}) | test MAE {test_mae:.2f}")

        # Le meilleur sur le test prend l'alias "challenger"
        if test_mae < best_test_mae:
            best_test_mae = test_mae
            best_name = name
            best_params = grid.best_params_
            best_regressor = regressor
            client.set_registered_model_alias(
                MODEL_NAME, "challenger", info.registered_model_version
            )

print(f"\nGagnant : {best_name} (test MAE {best_test_mae:.2f})")

# --- Reentrainement du meilleur modele sur l'ensemble des donnees ---
final = Pipeline([("preprocessor", preprocessor), ("regressor", best_regressor)])
final.set_params(**best_params)

with mlflow.start_run(run_name=f"final_{best_name}"):
    final.fit(X, y)
    mlflow.log_param("model_type", best_name)
    mlflow.log_param("trained_on", "all_data")
    mlflow.log_params(best_params)
    mlflow.log_metric("test_mae_before_refit", best_test_mae)
    info = mlflow.sklearn.log_model(
        final,
        name="model",
        input_example=X.head(3),
        serialization_format="cloudpickle",
        registered_model_name=MODEL_NAME,
    )
    client.update_model_version(
        MODEL_NAME,
        info.registered_model_version,
        description=f"{best_name} entraine sur toutes les donnees. MAE test avant reentrainement : {best_test_mae:.2f}",
    )
    client.set_registered_model_alias(
        MODEL_NAME, "production", info.registered_model_version
    )

client.update_registered_model(
    MODEL_NAME,
    description="Prediction du prix de location par jour a partir des caracteristiques du vehicule.",
)

print(f"Modele de production : version {info.registered_model_version}")
