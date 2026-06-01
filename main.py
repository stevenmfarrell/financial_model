import numpy as np

from output import create_history_dataframe

from simulation_setup import run_single, run_monte_carlo


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
    median_final_net_worth = np.median(
        [r.final_financial_state.net_worth for r in results]
    )
    print(f"Monte Carlo results over {len(results)} trials:")
    print(f"  Success rate: {success_rate:.2%}")
    if mean_failure_age is not None:
        print(f"  Mean failure age (for failures): {mean_failure_age:.1f}")
    else:
        print("  No failures, so mean failure age is N/A")
    print(f"  Median final net worth: ${median_final_net_worth:,.2f}")


if __name__ == "__main__":
    main()
