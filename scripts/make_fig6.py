#!/usr/bin/env python3
"""Regenerate Figure 6 (rule coverage vs. number of rules kept) from the data files.

Inputs
  data/rules.csv      one row per surrogate-tree leaf (= rule): leaf id, number of test records
  data/summary.json   surrogate fidelity, coverage and pruning results

Outputs
  figures/fig6_coverage_vs_rules.pdf   (vector, for print)
  figures/fig6_coverage_vs_rules.png   (preview)
  data/derived/fig6_coverage_by_rules.csv   (the exact values plotted)

Usage
  python scripts/make_fig6.py
"""
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch, Rectangle  # noqa: E402
from matplotlib.ticker import FormatStrFormatter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIGURES = ROOT / "figures"
DERIVED = DATA / "derived"

NAVY = "#2E5A88"
TEAL = "#1B7F79"
SHADE = "#E6EDF3"
GREY = "#555555"


def load():
    with open(DATA / "rules.csv", newline="") as fh:
        leaves = [(int(r["leaf"]), int(r["support"])) for r in csv.DictReader(fh)]
    with open(DATA / "summary.json") as fh:
        summary = json.load(fh)
    return leaves, summary


def coverage_curve(leaves):
    """Add rules in descending support order and return cumulative coverage."""
    ordered = sorted(leaves, key=lambda t: (-t[1], t[0]))
    total = sum(s for _, s in ordered)
    rows, cumulative = [], 0
    for k, (leaf, support) in enumerate(ordered, start=1):
        cumulative += support
        rows.append({
            "rules_kept": k,
            "leaf": leaf,
            "support": support,
            "cumulative_support": cumulative,
            "coverage": cumulative / total,
        })
    return rows, total


def write_source_data(rows):
    DERIVED.mkdir(parents=True, exist_ok=True)
    with open(DERIVED / "fig6_coverage_by_rules.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rules_kept", "leaf", "support", "cumulative_support", "coverage"])
        for r in rows:
            w.writerow([r["rules_kept"], r["leaf"], r["support"], r["cumulative_support"], f"{r['coverage']:.6f}"])


def plot(rows, total, summary):
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["DejaVu Serif"],
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,  # embed TrueType fonts (preferred by publishers)
    })
    ks = [r["rules_kept"] for r in rows]
    cov = [r["coverage"] for r in rows]
    fid = summary["logic_fidelity_cov"]
    n_rules = summary["num_rules"]
    n_pruned = summary["pruned_rules"]

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.subplots_adjust(left=0.07, right=0.985, top=0.84, bottom=0.2)

    # Main panel
    ax.fill_between(ks, cov, 1.0, color=SHADE, zorder=0, lw=0)
    ax.axhline(fid, color=TEAL, lw=2, ls="--", zorder=2)
    ax.plot(ks, cov, color=NAVY, lw=3, marker="s", ms=7, mfc=NAVY, mec="white", mew=1.2, zorder=3)
    for r in rows[:4]:
        ax.annotate(f"{r['coverage']:.3f}", (r["rules_kept"], r["coverage"]), textcoords="offset points",
                    xytext=(0, -20), ha="center", fontsize=11, fontweight="bold", color=NAVY)
    ax.set_xlim(0.5, 13.5)
    ax.set_ylim(0, 1.06)
    ax.set_xticks(ks)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    ax.yaxis.grid(True, color="#DDDDDD", lw=0.6)
    ax.set_axisbelow(True)
    ax.set_xlabel("Number of rules kept (added in descending support order)", fontweight="bold", fontsize=13)
    ax.set_ylabel("Fraction of test set", fontweight="bold", fontsize=13)

    # Zoom marker and inset
    ax.add_patch(Rectangle((2.6, 0.968), 10.8, 0.035, fill=False, ls=":", ec="#888888", lw=1, zorder=1))
    ax.annotate("", xy=(6.0, 0.665), xytext=(6.0, 0.962),
                arrowprops=dict(arrowstyle="-|>", color="#888888", lw=1, ls=":"))
    axin = ax.inset_axes([0.37, 0.20, 0.38, 0.41])
    axin.fill_between(ks, cov, 1.0, color=SHADE, zorder=0, lw=0)
    axin.axhline(fid, color=TEAL, lw=1.6, ls="--", zorder=2)
    axin.plot(ks, cov, color=NAVY, lw=2.4, marker="s", ms=5, mfc=NAVY, mec="white", mew=0.8, zorder=3)
    axin.set_xlim(2.6, 13.4)
    axin.set_ylim(0.970, 1.0015)
    axin.set_xticks(range(3, 14))
    axin.set_yticks([0.97, 0.98, 0.99, 1.00])
    axin.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    axin.tick_params(labelsize=9)
    axin.yaxis.grid(True, color="#E3E3E3", lw=0.5)
    for side in ("top", "right", "bottom", "left"):
        axin.spines[side].set_visible(True)
        axin.spines[side].set_color("#999999")
    axin.set_title("Zoom: rules 3–13 (0.970–1.000)", fontsize=10, color="#444444", pad=4)

    # Summary box (values from summary.json)
    note = (f"{n_rules} rules: coverage {summary['rule_coverage']*100:.0f}%, "
            f"fidelity {fid*100:.2f}%\n"
            f"{n_pruned} rules (after pruning): coverage {summary['pruned_coverage']*100:.3f}%, "
            f"fidelity {summary['pruned_fid_cov']*100:.2f}%")
    ax.annotate(note, xy=(13, cov[-1]), xytext=(13.3, 0.865), ha="right", va="center", fontsize=10.5,
                bbox=dict(boxstyle="round,pad=0.45", fc="white", ec="#BBBBBB"),
                arrowprops=dict(arrowstyle="->", color=GREY, lw=1.1, shrinkA=2, shrinkB=6))

    # Titles and legend
    fig.text(0.5, 0.965, "Rule Coverage versus Number of Rules Kept", ha="center", va="center",
             fontsize=17, fontweight="bold", color="#1A1A1A")
    fig.text(0.5, 0.905, f"Surrogate decision tree (max_depth = 4, min_samples_leaf = 40), "
             f"{n_rules} rules, test set (N = {total:,})", ha="center", va="center",
             fontsize=12.5, style="italic", color=GREY)
    handles = [
        Line2D([], [], color=NAVY, lw=3, marker="s", ms=7, mfc=NAVY, mec="white"),
        Line2D([], [], color=TEAL, lw=2, ls="--"),
        Patch(facecolor=SHADE, edgecolor="none"),
    ]
    labels = ["Coverage of the kept rules",
              f"Surrogate fidelity, all {n_rules} rules ({fid*100:.2f}%)",
              "Test records not covered"]
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, fontsize=11.5,
               bbox_to_anchor=(0.5, 0.0))

    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / "fig6_coverage_vs_rules.pdf", bbox_inches="tight", pad_inches=0.08,
                metadata={"CreationDate": None})
    fig.savefig(FIGURES / "fig6_coverage_vs_rules.png", dpi=110, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)


def main():
    leaves, summary = load()
    rows, total = coverage_curve(leaves)
    write_source_data(rows)
    plot(rows, total, summary)
    print("Coverage by number of rules kept:")
    for r in rows:
        print(f"  {r['rules_kept']:>2} rules  leaf {r['leaf']:>2}  support {r['support']:>7,}  coverage {r['coverage']:.5f}")
    print(f"Saved figures/fig6_coverage_vs_rules.pdf and .png, data/derived/fig6_coverage_by_rules.csv")


if __name__ == "__main__":
    main()
