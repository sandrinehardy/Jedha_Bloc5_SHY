import os
from pathlib import Path
from typing import List, Union

import mlflow
import mlflow.sklearn
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# --- Connexion a MLflow et chargement modele ---
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])

model = mlflow.sklearn.load_model("models:/getaround_rental_price@production")

# --- Application et forme de l'entree ---
description = """
Vous mettez en location votre voiture ? Cette Api vous permet d'estimer le prix de location journalier.

Ce que fait cette api :
* `/predict` : predit le prix de location par jour pour une ou plusieurs voitures
"""

app = FastAPI(
    title="API Getaround - prix de location",
    description=description,
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home():
    return """
    <h1>API Getaround</h1>
    <p>Vous mettez en location votre voiture ? Cette Api vous permet d'estimer le prix de location journalier.</p>
    <p><a href="/docs">Voir la documentation</a></p>
    """


class PredictionFeatures(BaseModel):
    input: List[List[Union[str, float, bool, None]]]


# --- Prediction ---
FEATURES = ["model_key", "mileage", "engine_power", "fuel", "paint_color", "car_type",
            "private_parking_available", "has_gps", "has_air_conditioning",
            "automatic_car", "has_getaround_connect", "has_speed_regulator", "winter_tires"]
BOOL_COLS = FEATURES[6:]


@app.post("/predict", tags=["Prediction"])
async def predict(predictionFeatures: PredictionFeatures):
    """
    Estime un prix de location par jour pour une ou plusieurs voitures.

    **Entree** : un dictionnaire avec la cle `input`, qui contient une liste de voitures.
    Chaque voiture est une liste de 13 valeurs, dans cet ordre :

    `model_key, mileage, engine_power, fuel, paint_color, car_type,
    private_parking_available, has_gps, has_air_conditioning, automatic_car,
    has_getaround_connect, has_speed_regulator, winter_tires`

    Seules les valeurs `mileage` et `engine_power` sont indispensables.

    **Sortie** : un dictionnaire avec la cle `prediction`, qui contient une liste de prix,
    dans le meme ordre que les voitures envoyees.

    **Exemple** :

    Entree :
    ```
    {"input": [["Citroën", 140411, 100, "diesel", null, "convertible", true, true, false, false, true, true, true]]}
    ```

    Sortie :
    ```
    {"prediction": [107.13943084829988]}
    ```
    """
    data = pd.DataFrame(predictionFeatures.input, columns=FEATURES)
    data[BOOL_COLS] = data[BOOL_COLS].astype(float)
    prediction = model.predict(data)
    return {"prediction": prediction.tolist()}
