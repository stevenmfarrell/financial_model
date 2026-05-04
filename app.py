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
                "brokerage": df["state_taxable_brokerage_balance_real"].tolist(),
                "traditional": df["state_traditional_retirement_balance_real"].tolist(),
                "roth": df["state_roth_retirement_balance_real"].tolist(),
                "hsa": df["state_hsa_balance_real"].tolist(),
                "total": df["state_liquid_assets_real"].tolist(),
            },
            "withdrawals": {
                "trad": df["decisions_from_traditional_retirement_real"].tolist(),
                "roth_basis": df["decisions_from_roth_retirement_basis_real"].tolist(),
                "roth_growth": df[
                    "decisions_from_roth_retirement_earnings_real"
                ].tolist(),
                "brokerage_basis": df[
                    "decisions_from_taxable_brokerage_basis_real"
                ].tolist(),
                "brokerage_growth": df[
                    "decisions_from_taxable_brokerage_growth_real"
                ].tolist(),
                "hsa": df["decisions_from_hsa_nonmedical_real"].tolist(),
                "cash": df["decisions_from_cash_reserve_real"].tolist(),
            },
            "outflows": {
                "taxes": df["decisions_to_taxes_real"].tolist(),
                "mortgage": df["decisions_to_mortgage_real"].tolist(),
                "spending": df["decisions_to_lifestyle_spending_real"].tolist(),
            },
            "savings": {
                "to_hsa": df["decisions_payroll_to_hsa_real"].tolist(),
                "to_roth": df["decisions_to_roth_real"].tolist(),
                "to_trad": df["decisions_payroll_to_trad_401k_real"].tolist(),
                "to_cash": df["decisions_to_cash_reserve_real"].tolist(),
                "to_brokerage": df["decisions_to_brokerage_real"].tolist(),
            },
            "income": {
                "earned": df["decisions_gross_earned_income_real"].tolist(),
                "ss": df["decisions_social_security_received_real"].tolist(),
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
