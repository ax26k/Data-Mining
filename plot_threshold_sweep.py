import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("outputs/threshold_sweep.csv")

print("CSV columns:")
print(df.columns.tolist())

total_notices = 12000

summary = (
    df.groupby(["threshold", "label"])
    .agg(
        survival_rate=("survives", "mean"),
        mean_candidates=("candidate_count", "mean")
    )
    .reset_index()
)

same = summary[summary["label"] == "same"][
    ["threshold", "survival_rate"]
].rename(columns={"survival_rate": "same_recall"})

different = summary[summary["label"] == "different"][
    ["threshold", "survival_rate"]
].rename(columns={"survival_rate": "different_survival"})

candidates = (
    df.groupby("threshold")["candidate_count"]
    .mean()
    .reset_index()
    .rename(columns={"candidate_count": "mean_candidates"})
)

result = same.merge(different, on="threshold")
result = result.merge(candidates, on="threshold")

result["candidate_reduction"] = (
    1 - result["mean_candidates"] / total_notices
) * 100

result = result.sort_values("threshold")

print("\nCorrect final results:")
print(result.to_string(index=False))

plt.figure(figsize=(8, 5))
plt.plot(
    result["threshold"],
    result["same_recall"] * 100,
    marker="o",
    label="Same-pair recall"
)
plt.plot(
    result["threshold"],
    result["different_survival"] * 100,
    marker="o",
    label="Different-pair survival"
)
plt.xlabel("LSH threshold")
plt.ylabel("Percentage")
plt.title("Recall and Different-Pair Survival by LSH Threshold")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("outputs/threshold_recall_plot.png", dpi=200)
plt.close()

plt.figure(figsize=(8, 5))
plt.plot(
    result["threshold"],
    result["mean_candidates"],
    marker="o"
)
plt.xlabel("LSH threshold")
plt.ylabel("Mean candidate count")
plt.title("Mean Candidate Count by LSH Threshold")
plt.grid(True)
plt.tight_layout()
plt.savefig("outputs/threshold_candidate_plot.png", dpi=200)
plt.close()

result.to_csv(
    "outputs/threshold_sweep_with_reduction.csv",
    index=False
)

print("\nPlots saved successfully.")