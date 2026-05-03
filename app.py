import pandas as pd
from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def dashboard():
    try:
        df = pd.read_csv("simulation_results.csv")

        # Define specific granular columns to extract
        cols_to_load = [
            "year",
            "decisions_to_taxes",
            "decisions_to_mortgage",
            "decisions_to_lifestyle_spending",
            "decisions_gross_earned_income",
            "decisions_social_security_received",
            "decisions_from_traditional_retirement",
            "decisions_from_roth_retirement",
            "decisions_from_taxable_brokerage_basis",
            "decisions_from_taxable_brokerage_growth",
            "decisions_from_hsa_nonmedical",
            "decisions_from_cash_reserve",
        ]

        # Asset columns for the first chart
        asset_cols = [
            "state_taxable_brokerage_balance",
            "state_traditional_retirement_balance",
            "state_roth_retirement_balance",
            "state_hsa_balance",
            "state_liquid_assets",
        ]

        for c in cols_to_load + asset_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

        data_packet = {
            "years": df["year"].tolist(),
            "ages": df["age"].tolist(),
            "assets": {
                "brokerage": df["state_taxable_brokerage_balance"].tolist(),
                "traditional": df["state_traditional_retirement_balance"].tolist(),
                "roth": df["state_roth_retirement_balance"].tolist(),
                "hsa": df["state_hsa_balance"].tolist(),
                "total": df["state_liquid_assets"].tolist(),
            },
            "withdrawals": {
                "trad": df["decisions_from_traditional_retirement"].tolist(),
                "roth": df["decisions_from_roth_retirement"].tolist(),
                "brokerage_basis": df[
                    "decisions_from_taxable_brokerage_basis"
                ].tolist(),
                "brokerage_growth": df[
                    "decisions_from_taxable_brokerage_growth"
                ].tolist(),
                "hsa": df["decisions_from_hsa_nonmedical"].tolist(),
                "cash": df["decisions_from_cash_reserve"].tolist(),
            },
            "outflows": {
                "taxes": df["decisions_to_taxes"].tolist(),
                "mortgage": df["decisions_to_mortgage"].tolist(),
                "spending": df["decisions_to_lifestyle_spending"].tolist(),
            },
            "income": {
                "earned": df["decisions_gross_earned_income"].tolist(),
                "ss": df["decisions_social_security_received"].tolist(),
            },
            "market": {
                "inflation": df["mkt_annual_inflation_rate"].tolist(),
                "stocks": df["mkt_annual_stock_return"].tolist(),
                "bonds": df["mkt_annual_bond_return"].tolist(),
            },
        }

        return render_template("dashboard.html", data=data_packet)
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    app.run(debug=True)
