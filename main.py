from monte_carlo_runner import compute_median_balances_by_age
from output import create_history_dataframe
from simulation_setup import run_monte_carlo, run_single


def main():

    result = run_single()

    df = create_history_dataframe(result.history)
    df.to_csv("simulation_results.csv", float_format="%.2f", index=False)
    print("Simulation successful. Results saved to simulation_results.csv")

    results = run_monte_carlo()
    success_rate = len([r for r in results if r.success]) / len(results)
    failures = [r for r in results if not r.success]
    if failures:
        mean_failure_age = sum(
            r.failure_age for r in failures if r.failure_age is not None
        ) / len(failures)
    else:
        mean_failure_age = None

    mc_df = compute_median_balances_by_age(results)
    mc_df.to_csv("monte_carlo_median_results.csv", float_format="%.2f", index=False)

    final_row = mc_df.iloc[-1] if not mc_df.empty else None
    median_final_net_worth = final_row["median_net_worth"] if final_row is not None else 0.0

    print(f"\nMonte Carlo results over {len(results)} trials:")
    print(f"  Success rate: {success_rate:.2%}")
    if mean_failure_age is not None:
        print(f"  Mean failure age (for failures): {mean_failure_age:.1f}")
    else:
        print("  No failures, so mean failure age is N/A")
    print(f"  Median final net worth: ${median_final_net_worth:,.2f}\n")

    print("Monte Carlo Median Balances by Age:")
    print(f"{'Age':<5} {'Median Net Worth':>20} {'Median Liquid Assets':>22} {'P10 Net Worth':>18} {'P90 Net Worth':>18}")
    print("-" * 88)
    for _, row in mc_df.iterrows():
        age = int(row['age'])
        print(
            f"{age:<5} "
            f"${row['median_net_worth']:>19,.2f} "
            f"${row['median_liquid_assets']:>21,.2f} "
            f"${row['p10_net_worth']:>17,.2f} "
            f"${row['p90_net_worth']:>17,.2f}"
        )


if __name__ == "__main__":
    main()

