# TGK Meal Builder (Streamlit)

This is a prototype Streamlit web app for building client meal plans.

## Features
- Loads food database from `concise-14-edition.xlsx`.
- Allows selecting foods and auto-scales their quantities to match target macros.
- Provides preset meal templates (Breakfast, Lunch, Dinner, Snack) based on TGK example plans.
- Exports meal as CSV for sharing.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Cloud
1. Push this repo to GitHub.
2. Go to [Streamlit Cloud](https://share.streamlit.io).
3. Link the repo and branch, then deploy.

## Notes
- Place your Excel file `concise-14-edition.xlsx` in the repo root or update the path in `app.py`.
- This is a prototype. Future improvements include portion constraints, unit rounding, and weekly plan exports.
