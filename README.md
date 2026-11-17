# Bloc 5 - Projet Getaround 🚘

Projet de deploiement autour de Getaround, en deux parties :
- **prediction du prix de location** d'une voiture, avec un modele de machine learning expose par une API ;
- **analyse des retards** au retour des voitures, pour aider le product manager a choisir un delai minimum entre deux locations.

## En ligne

- Dashboard (prediction de prix et delais entre deux locations) : https://sandrine-dsfs36-getaround-dashboard.hf.space
- API de prediction de prix : https://sandrine-dsfs36-getaround-api.hf.space (documentation : `/docs`)
- Serveur MLflow (suivi des modeles) : https://sandrine-dsfs36-getaround-mlflow.hf.space

## Structure du depot

```
repo_bloc5/
├── 01_rental_price_prediction/   prediction du prix de location
│   ├── data/                     donnees sur les prix
│   ├── sandbox.ipynb             EDA et premiers essais de modeles
│   ├── train.py                  entrainement des modeles et enregistrement dans MLflow
│   └── api/                      API FastAPI, deployee sur Hugging Face
│       ├── app.py                code de l'API (endpoint /predict)
│       ├── Dockerfile            image Docker de l'API
│       └── test.json             exemple de donnees pour tester l'API
├── 02_delays_analysis/           analyse des retards
│   ├── data/                     donnees des retards
│   ├── eda_and_tests.ipynb       EDA des retards et choix du delai minimum
│   └── dashboard/                dashboard Streamlit
│       ├── app.py                pages du dashboard (prediction de prix et delais)
│       ├── analysis.py           calculs utilises par le dashboard
│       └── Dockerfile            image Docker du dashboard
└── mlflow_space/                 serveur MLflow deploye sur Hugging Face
    └── Dockerfile                image Docker du serveur MLflow
```

## Données

Les 2 fichier de données ne sont pas inclus dans ce repo.
Pour les récupérer, télécharger les deux fichiers suivants et les placer chacun dans le dossier `data/` indiqué :

- Prix de location : https://full-stack-assets.s3.eu-west-3.amazonaws.com/Deployment/get_around_pricing_project.csv
  -> `01_rental_price_prediction/data/`
- Analyse des retards : https://full-stack-assets.s3.eu-west-3.amazonaws.com/Deployment/get_around_delay_analysis.xlsx
  -> `02_delays_analysis/data/`
