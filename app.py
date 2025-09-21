# app.py
import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import lsq_linear
import io

# ---------- Config ----------
EXCEL_PATH = "concise-14-edition.xlsx"  # make sure this file is in the repo root

# ---------- Helpers ----------

@st.cache_data
def load_foods(path=EXCEL_PATH):
    df = pd.read_excel(path, sheet_name=0)
    df.columns = [c.strip() for c in df.columns]
    lc = {c.lower(): c for c in df.columns}

    mapping = {}
    if "name" in lc:
        mapping[lc["name"]] = "name"
    elif "foodname" in lc:
        mapping[lc["foodname"]] = "name"
    else:
        mapping[df.columns[0]] = "name"

    if "calories" in lc:
        mapping[lc["calories"]] = "calories"
    elif "kcal" in lc:
        mapping[lc["kcal"]] = "calories"

    for k in ["protein", "protein_g", "protein (g)"]:
        if k in lc:
            mapping[lc[k]] = "protein_g"
            break
    for k in ["carbs", "carbohydrate", "carbs_g", "carbs (g)", "carbohydrate_g"]:
        if k in lc:
            mapping[lc[k]] = "carbs_g"
            break
    for k in ["fat", "fat_g", "fat (g)"]:
        if k in lc:
            mapping[lc[k]] = "fat_g"
            break
    for k in ["serving_grams", "servinggrams", "serving_g", "serving (g)", "grams"]:
        if k in lc:
            mapping[lc[k]] = "serving_grams"
            break

    df = df.rename(columns=mapping)

    for col in ["calories", "protein_g", "carbs_g", "fat_g", "serving_grams"]:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    if "name" not in df.columns:
        df["name"] = df.iloc[:, 0].astype(str)

    def per_gram(row, val_col):
        s = row["serving_grams"]
        if s > 0:
            return row[val_col] / s
        else:
            return row[val_col] / 100.0

    df["kcal_per_g"] = df.apply(lambda r: per_gram(r, "calories"), axis=1)
    df["prot_per_g"] = df.apply(lambda r: per_gram(r, "protein_g"), axis=1)
    df["carb_per_g"] = df.apply(lambda r: per_gram(r, "carbs_g"), axis=1)
    df["fat_per_g"] = df.apply(lambda r: per_gram(r, "fat_g"), axis=1)

    return df.reset_index(drop=True)


def solve_quantities(selected_df, target_prot, target_carb, target_fat):
    A = np.vstack(
        [
            selected_df["prot_per_g"].to_numpy(),
            selected_df["carb_per_g"].to_numpy(),
            selected_df["fat_per_g"].to_numpy(),
        ]
    ).T
    b = np.array([target_prot, target_carb, target_fat])
    res = lsq_linear(A, b, bounds=(0, np.inf))
    return np.maximum(res.x, 0.0)


def compute_meal_totals(selected_df, grams):
    kcal = (selected_df["kcal_per_g"].to_numpy() * grams).sum()
    prot = (selected_df["prot_per_g"].to_numpy() * grams).sum()
    carb = (selected_df["carb_per_g"].to_numpy() * grams).sum()
    fat = (selected_df["fat_per_g"].to_numpy() * grams).sum()
    return {"kcal": kcal, "protein_g": prot, "carbs_g": carb, "fat_g": fat}


# ---------- Streamlit UI ----------

st.set_page_config(page_title="TGK Meal Builder", layout="wide")
st.title("TGK Meal Builder — Streamlit prototype")

# Load foods
with st.spinner("Loading food database..."):
    foods = load_foods()

st.sidebar.header("Client & Meal settings")
client_name = st.sidebar.text_input("Client name", value="Test Client")

st.sidebar.subheader("Preset meal templates")
preset = st.sidebar.selectbox(
    "Choose template",
    [
        "Manual",
        "Breakfast (~395 kcal, 30C/23P/13F)",
        "Lunch (~435 kcal, 35C/26P/9F)",
        "Dinner (~435 kcal, 30C/20P/9F)",
        "Snack (~200 kcal, 20C/20P/4F)",
    ],
)

if preset == "Breakfast (~395 kcal, 30C/23P/13F)":
    target_prot, target_carb, target_fat = 23.0, 30.0, 13.0
elif preset == "Lunch (~435 kcal, 35C/26P/9F)":
    target_prot, target_carb, target_fat = 26.0, 35.0, 9.0
elif preset == "Dinner (~435 kcal, 30C/20P/9F)":
    target_prot, target_carb, target_fat = 20.0, 30.0, 9.0
elif preset == "Snack (~200 kcal, 20C/20P/4F)":
    target_prot, target_carb, target_fat = 20.0, 20.0, 4.0
else:
    target_prot = st.sidebar.number_input("Target protein (g)", value=25.0, step=1.0)
    target_carb = st.sidebar.number_input("Target carbs (g)", value=30.0, step=1.0)
    target_fat = st.sidebar.number_input("Target fat (g)", value=13.0, step=0.5)

st.sidebar.markdown("---")
search = st.sidebar.text_input("Search foods", value="")
min_prot = st.sidebar.slider("Filter: min protein per 100g", 0, 50, 0)

df = foods.copy()
if search.strip():
    df = df[
        df["name"].str.contains(search, case=False, na=False)
        | df.get("brand", "").astype(str).str.contains(search, case=False, na=False)
    ]
if min_prot > 0:
    df = df[df["prot_per_g"] * 100 >= min_prot]

st.header("1) Pick foods for this meal")
selected_indices = st.multiselect(
    "Select up to 6 foods", options=list(df.index.astype(int)), 
    format_func=lambda i: f"{df.loc[i,'name']} — {int(df.loc[i,'calories'])} kcal per serving"
)
selected_df = df.loc[selected_indices].copy()
st.dataframe(selected_df[["name", "calories", "protein_g", "carbs_g", "fat_g", "serving_grams"]])

st.markdown("### 2) Compute quantities")
if len(selected_df) == 0:
    st.info("Pick at least one food.")
else:
    if st.button("Compute optimized quantities"):
        grams = solve_quantities(selected_df, target_prot, target_carb, target_fat)
        grams = np.round(grams, 1)
        selected_df = selected_df.reset_index(drop=True)
        selected_df["grams"] = grams
        totals = compute_meal_totals(selected_df, grams)

        display_df = selected_df[
            ["name", "grams", "kcal_per_g", "prot_per_g", "carb_per_g", "fat_per_g"]
        ].copy()
        display_df["kcal"] = display_df["kcal_per_g"] * display_df["grams"]
        display_df["protein_g"] = display_df["prot_per_g"] * display_df["grams"]
        display_df["carbs_g"] = display_df["carb_per_g"] * display_df["grams"]
        display_df["fat_g"] = display_df["fat_per_g"] * display_df["grams"]
        display_df = display_df[["name", "grams", "kcal", "protein_g", "carbs_g", "fat_g"]]

        st.subheader("Resulting quantities")
        st.dataframe(
            display_df.style.format(
                {"grams": "{:.1f}", "kcal": "{:.0f}", "protein_g": "{:.1f}", "carbs_g": "{:.1f}", "fat_g": "{:.1f}"}
            )
        )

        st.markdown("**Totals:**")
        st.write(
            f"Calories: {totals['kcal']:.0f} kcal | Protein: {totals['protein_g']:.1f} g | Carbs: {totals['carbs_g']:.1f} g | Fat: {totals['fat_g']:.1f} g"
        )

        st.markdown("**Macro differences (target - actual):**")
        st.write(
            {
                "protein_diff_g": target_prot - totals["protein_g"],
                "carbs_diff_g": target_carb - totals["carbs_g"],
                "fat_diff_g": target_fat - totals["fat_g"],
            }
        )

        csv_buf = io.StringIO()
        display_df.to_csv(csv_buf, index=False)
        st.download_button(
            "Download meal CSV",
            csv_buf.getvalue(),
            file_name=f"{client_name}_meal.csv",
            mime="text/csv",
        )
