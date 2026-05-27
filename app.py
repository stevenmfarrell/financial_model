import pandas as pd
from flask import Flask, render_template, jsonify

app = Flask(__name__)


@app.route("/")
def dashboard():
    """Serves the main HTML interface."""
    return render_template("dashboard.html")


@app.route("/api/data")
def get_data():
    """API endpoint providing the simulation data as JSON."""
    try:
        df = pd.read_csv("simulation_results.csv")

        data_packet = {
            "years": df["year"].tolist(),
            "ages": df["age"].tolist(),
            "assets": {
                "brokerage_basis": df["state_brokerage_basis_balance"].tolist(),
                "brokerage_growth": df["state_brokerage_growth_balance"].tolist(),
                "traditional": df["state_traditional_retirement_balance"].tolist(),
                "roth_basis": df["state_roth_basis_balance"].tolist(),
                "roth_conversion": df["state_roth_conversion_recent_balance"].tolist(),
                "roth_growth": df["state_roth_growth_balance"].tolist(),
                "hsa": df["state_hsa_balance"].tolist(),
                "cash": df["state_cash_balance"].tolist(),
                "total": df["state_liquid_assets"].tolist(),
            },
            "withdrawals": {
                "trad": df["decisions_from_traditional_retirement"].tolist(),
                "roth_basis": df["decisions_from_roth_retirement_basis"].tolist(),
                "roth_growth": df["decisions_from_roth_retirement_earnings"].tolist(),
                "brokerage_basis": df[
                    "decisions_from_taxable_brokerage_basis"
                ].tolist(),
                "brokerage_growth": df[
                    "decisions_from_taxable_brokerage_growth"
                ].tolist(),
                "hsa": df["decisions_from_hsa_nonmedical"].tolist(),
                "cash": df["decisions_from_cash_reserve"].tolist(),
                "total": df["decisions_total_inflows"].tolist(),
            },
            "outflows": {
                "taxes": df["decisions_to_taxes"].tolist(),
                "mortgage": df["decisions_to_mortgage"].tolist(),
                "spending": df["decisions_to_lifestyle_spending"].tolist(),
                "healthcare": df["decisions_to_healthcare_spending"].tolist(),
                "total": df["decisions_total_outflows"].tolist(),
            },
            "savings": {
                "to_hsa": df["decisions_payroll_to_hsa"].tolist(),
                "to_roth": df["decisions_to_roth"].tolist(),
                "to_trad": df["decisions_payroll_to_trad_401k"].tolist(),
                "to_cash": df["decisions_to_cash_reserve"].tolist(),
                "to_brokerage": df["decisions_to_brokerage"].tolist(),
            },
            "income": {
                "earned": df["decisions_gross_earned_income"].tolist(),
                "ss": df["decisions_social_security_received"].tolist(),
                "dividends": df["decisions_dividends_received"].tolist(),
            },
            "market": {
                "inflation": df["mkt_annual_inflation_rate"].tolist(),
                "stocks": df["mkt_annual_total_stock_return"].tolist(),
                "bonds": df["mkt_annual_total_bond_return"].tolist(),
            },
        }

        return jsonify(data_packet)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=8000)
