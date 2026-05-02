import pandas as pd
from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def dashboard():
    try:
        df = pd.read_csv("simulation_results.csv")

        # Add 'state_liquid_assets' to the target columns
        cols = [
            "state_taxable_brokerage_balance",
            "state_traditional_retirement_balance",
            "state_roth_retirement_balance",
            "state_hsa_balance",
            "state_liquid_assets",
        ]

        for c in cols + ["year"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(subset=["year"] + cols)

        data_packet = {
            "years": df["year"].tolist(),
            "brokerage": df["state_taxable_brokerage_balance"].tolist(),
            "traditional": df["state_traditional_retirement_balance"].tolist(),
            "roth": df["state_roth_retirement_balance"].tolist(),
            "hsa": df["state_hsa_balance"].tolist(),
            "liquid_assets": df["state_liquid_assets"].tolist(),
        }

        return render_template("dashboard.html", data=data_packet)
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    app.run(debug=True)
