import pandas as pd
from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def dashboard():
    try:
        df = pd.read_csv("simulation_results.csv")

        # Define columns to extract
        balance_cols = [
            "state_taxable_brokerage_balance",
            "state_traditional_retirement_balance",
            "state_roth_retirement_balance",
            "state_hsa_balance",
            "state_liquid_assets",
        ]
        market_cols = [
            "mkt_annual_inflation_rate",
            "mkt_annual_stock_return",
            "mkt_annual_bond_return",
        ]
        flow_cols = [
            "decisions_gross_earned_income",
            "decisions_social_security_received",
            "decisions_to_lifestyle_spending",
            "decisions_to_mortgage",
            "decisions_to_taxes",
            "decisions_from_traditional_retirement",
            "decisions_from_roth_retirement",
            "decisions_from_taxable_brokerage_basis",
            "decisions_from_taxable_brokerage_growth",
            "decisions_from_hsa_nonmedical",
            "decisions_from_cash_reserve",
        ]

        # Convert to numeric and fill NaNs
        all_cols = balance_cols + market_cols + flow_cols + ["year"]
        for c in all_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

        # Calculate aggregates for the flows plot
        df["total_income"] = (
            df["decisions_gross_earned_income"]
            + df["decisions_social_security_received"]
        )
        df["total_spending"] = (
            df["decisions_to_lifestyle_spending"]
            + df["decisions_to_mortgage"]
            + df["decisions_to_taxes"]
        )
        df["total_withdrawals"] = (
            df["decisions_from_traditional_retirement"]
            + df["decisions_from_roth_retirement"]
            + df["decisions_from_taxable_brokerage_basis"]
            + df["decisions_from_taxable_brokerage_growth"]
            + df["decisions_from_hsa_nonmedical"]
            + df["decisions_from_cash_reserve"]
        )

        data_packet = {
            "years": df["year"].tolist(),
            "assets": {
                "brokerage": df["state_taxable_brokerage_balance"].tolist(),
                "traditional": df["state_traditional_retirement_balance"].tolist(),
                "roth": df["state_roth_retirement_balance"].tolist(),
                "hsa": df["state_hsa_balance"].tolist(),
                "liquid_assets": df["state_liquid_assets"].tolist(),
            },
            "market": {
                "inflation": df["mkt_annual_inflation_rate"].tolist(),
                "stocks": df["mkt_annual_stock_return"].tolist(),
                "bonds": df["mkt_annual_bond_return"].tolist(),
            },
            "flows": {
                "income": df["total_income"].tolist(),
                "spending": df["total_spending"].tolist(),
                "withdrawals": df["total_withdrawals"].tolist(),
            },
        }

        return render_template("dashboard.html", data=data_packet)
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    app.run(debug=True)
