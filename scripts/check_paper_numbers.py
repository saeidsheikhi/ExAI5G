#!/usr/bin/env python3
"""Recompute the numbers reported in the paper from the files in data/ and compare them.

Each check lists where the number appears in the paper, the value as printed there,
and the value recomputed from the data, rounded to the precision used in the paper.

Usage
  python scripts/check_paper_numbers.py
Exit code 0 means every check passed.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parents[1] / "data"
results = []


def check(where, what, paper, data, ok):
    results.append((bool(ok), where, what, paper, data))


def same(paper_value, data_value, decimals):
    return round(float(data_value), decimals) == round(float(paper_value), decimals)


def load():
    with open(DATA / "classification_report.csv", newline="") as fh:
        report = {r[""]: r for r in csv.DictReader(fh)}
    with open(DATA / "summary.json") as fh:
        summary = json.load(fh)
    with open(DATA / "baselines.json") as fh:
        baselines = json.load(fh)
    with open(DATA / "ig_mean.csv", newline="") as fh:
        ig = {row[0]: float(row[1]) for row in csv.reader(fh) if row and row[0]}
    with open(DATA / "rules.csv", newline="") as fh:
        support = [int(r["support"]) for r in csv.DictReader(fh)]
    with open(DATA / "latency_ms.csv", newline="") as fh:
        latency = np.array([float(row[0]) for row in list(csv.reader(fh))[1:]])
    return report, summary, baselines, ig, support, latency


def main():
    report, summary, baselines, ig, support, latency = load()

    # Table 1 (test set) and Table 3 / Section 5.1
    table3 = {
        "Brute Force": (0.619, 0.812, 0.703, 32),
        "DDoS": (1.000, 1.000, 1.000, 18341),
        "Device Spoofing": (0.714, 0.625, 0.667, 8),
        "DoS_MQTT": (1.000, 1.000, 1.000, 27835),
        "Eavesdropping": (0.642, 0.944, 0.764, 392),
        "MITM": (0.986, 0.933, 0.959, 75),
        "SQL Injection": (0.978, 0.830, 0.898, 53),
        "Unauthorized Data Access": (0.696, 0.696, 0.696, 23),
        "benign": (1.000, 0.999, 0.999, 148070),
        "macro avg": (0.848, 0.871, 0.854, 194829),
        "weighted avg": (0.999, 0.999, 0.999, 194829),
    }
    for cls, (p, r, f, n) in table3.items():
        got = report[cls]
        data = (float(got["precision"]), float(got["recall"]), float(got["f1-score"]), int(float(got["support"])))
        ok = same(p, data[0], 3) and same(r, data[1], 3) and same(f, data[2], 3) and data[3] == n
        check("Table 3", f"{cls}: precision, recall, F1, support", (p, r, f, n), data, ok)
    classes = [c for c in table3 if "avg" not in c]
    n_test = sum(int(float(report[c]["support"])) for c in classes)
    check("Table 1", "test records (sum of class supports)", 194829, n_test, n_test == 194829)

    acc = summary["overall_accuracy"]
    check("Abstract, 5.1", "accuracy 99.87%", "99.87%", f"{acc*100:.4f}%", same(99.87, acc * 100, 2))
    check("Abstract, 5.1", "macro-F1 0.854", 0.854, f"{summary['macro_F1']:.5f}", same(0.854, summary["macro_F1"], 3))
    low = sum(table3[c][3] for c in ("Brute Force", "Device Spoofing", "Unauthorized Data Access", "Eavesdropping"))
    check("5.1, 7", "four low-support classes: 455 flows, 0.23%", "455, 0.23%", f"{low}, {low/n_test*100:.3f}%",
          low == 455 and same(0.23, low / n_test * 100, 2))
    high = sum(table3[c][3] for c in ("benign", "DDoS", "DoS_MQTT"))
    check("6", "three high-volume classes: 99.7% of test traffic", "99.7%", f"{high/n_test*100:.3f}%",
          same(99.7, high / n_test * 100, 1))

    # Table 4 / Section 5.2
    for label, key, value in (("Decision Tree (depth 4)", "DT_depth4", 0.470), ("MLP", "MLP", 0.885),
                              ("XGBoost", "XGBoost", 0.965), ("Random Forest", "RandomForest", 0.985)):
        check("Table 4", f"{label} macro-F1", value, f"{baselines[key]:.5f}", same(value, baselines[key], 3))
    gap = baselines["RandomForest"] - summary["macro_F1"]
    check("Abstract, 5.2", "Random Forest minus Transformer macro-F1 = 0.131", 0.131, f"{gap:.5f}", same(0.131, gap, 3))
    check("data", "baselines.json equals summary.json['baselines']", "-", "-", baselines == summary["baselines"])

    # Figure 5 / Section 5.3
    fig5 = [("frame.time_relative", .939), ("tcp.time_relative", .350), ("tcp.stream", .293),
            ("tcp.window_size.1", .235), ("tcp.flags", .188), ("tcp.port", .095), ("tcp.srcport", .091),
            ("ip.flags.mf", .089), ("tcp.dstport", .075), ("ip.len", .073), ("tcp.ack_raw", .048),
            ("tcp.len", .039), ("tcp.ack", .036), ("http.request.uri", .035), ("tcp.reassembled.length", .019),
            ("frame.time_delta", .017), ("tcp.segments", .014), ("tcp.time_delta", .012), ("ip.ttl", .005),
            ("tcp.seq", .003), ("tcp.analysis.ack_rtt", .002), ("ip.fragments", .002), ("http.request", .002),
            ("udp.length", .002), ("ip.proto", .001), ("udp.port", .001), ("ip.flags.df", .000),
            ("tcp.urgent_pointer", .000)]
    for feature, value in fig5:
        check("Figure 5", f"mean |IG| {feature}", value, f"{ig[feature]:.5f}", same(value, ig[feature], 3))
    check("Table 2, Figure 5", "28 features", 28, len(ig), len(ig) == 28)
    ranked = [f for f, _ in sorted(ig.items(), key=lambda kv: -kv[1])]
    check("5.3", "ranking: frame.time_relative, tcp.time_relative, tcp.stream", "top 3", ranked[:3],
          ranked[:3] == ["frame.time_relative", "tcp.time_relative", "tcp.stream"])
    top5 = sum(sorted(ig.values(), reverse=True)[:5]) / sum(ig.values())
    check("Figure 5", "top-5 features = 75.2% of total attribution", "75.2%", f"{top5*100:.2f}%", same(75.2, top5 * 100, 1))

    # Section 5.4, Figure 6, Tables 10-11 (depth-4 row), Sections 6-7
    n = sum(support)
    check("5.4", "13 rules", 13, f"{len(support)} leaves; num_rules = {summary['num_rules']}",
          len(support) == 13 == summary["num_rules"])
    check("5.4", "rules partition the test set", 194829, n, n == 194829)
    check("5.4", "fidelity 99.80%", "99.80%", f"{summary['logic_fidelity_cov']*100:.4f}%",
          same(99.80, summary["logic_fidelity_cov"] * 100, 2))
    check("5.4", "coverage 100%", "100%", summary["rule_coverage"], summary["rule_coverage"] == 1.0)
    check("5.4", "12 rules after pruning", 12, summary["pruned_rules"], summary["pruned_rules"] == 12)
    check("5.4", "after pruning: fidelity 99.80%", "99.80%", f"{summary['pruned_fid_cov']*100:.4f}%",
          same(99.80, summary["pruned_fid_cov"] * 100, 2))
    check("5.4", "after pruning: coverage 99.999%", "99.999%", f"{summary['pruned_coverage']*100:.4f}%",
          same(99.999, summary["pruned_coverage"] * 100, 3))
    check("5.4", "pruned rule = least-supported leaf", f"{n - min(support)}/{n}", f"{summary['pruned_coverage']:.10f}",
          abs((n - min(support)) / n - summary["pruned_coverage"]) < 1e-12)
    check("5.4, Table 11", "mean pairwise Jaccard 0.000", 0.000, summary["rule_redundancy"], summary["rule_redundancy"] == 0.0)
    check("Tables 10-11", "depth-4 tree fidelity 0.9980", 0.9980, f"{summary['logic_fidelity_cov']:.5f}",
          same(0.9980, summary["logic_fidelity_cov"], 4))
    disagree = (1 - summary["logic_fidelity_cov"]) * n
    check("6, 7", "about 0.2% (on the order of 400) flows where rule and model differ", "~400, ~0.2%",
          f"{disagree:.0f}, {disagree/n*100:.3f}%", round(disagree) < 450 and same(0.2, disagree / n * 100, 1))
    coverage = np.cumsum(sorted(support, reverse=True)) / n
    for k, value in zip((1, 2, 3, 4), (0.744, 0.887, 0.979, 0.991)):
        check("Figure 6", f"coverage with the {k} largest rules", value, f"{coverage[k-1]:.5f}", same(value, coverage[k - 1], 3))
    check("5.4", "highest-support rules explain over 99% (4 rules)", "> 99%", f"{coverage[3]*100:.3f}%", coverage[3] > 0.99)

    # Figure 7 / Sections 5.8 and 6
    steady = latency[1:]
    check("Figure 7", "N = 200 inference calls", 200, len(latency), len(latency) == 200)
    check("Figure 7", "first call (warm-up) 9.33 ms", 9.33, f"{latency[0]:.5f}", same(9.33, latency[0], 2))
    for label, value, got in (("steady state mean", 2.348, steady.mean()),
                              ("steady state SD", 0.013, steady.std(ddof=1)),
                              ("steady state median (P50)", 2.348, np.median(steady)),
                              ("steady state P95", 2.364, np.percentile(steady, 95)),
                              ("steady state P99", 2.401, np.percentile(steady, 99)),
                              ("steady state minimum", 2.313, steady.min()),
                              ("steady state maximum", 2.434, steady.max()),
                              ("all calls mean", 2.383, latency.mean()),
                              ("all calls SD", 0.494, latency.std(ddof=1)),
                              ("all calls median", 2.348, np.median(latency))):
        check("Figure 7", f"{label} (ms)", value, f"{got:.5f}", same(value, got, 3))
    check("5.8, 6", "median latency 2.35 ms", 2.35, f"{np.median(latency):.5f}",
          same(2.35, np.median(latency), 2) and abs(np.median(latency) - summary["median_latency_ms"]) < 1e-9)

    widths = [max(len(str(r[i])) for r in results) for i in (1, 2, 3)]
    for ok, where, what, paper, data in results:
        print(f"{'PASS' if ok else 'FAIL'}  {where:<{widths[0]}}  {what:<{widths[1]}}  paper: {str(paper):<{widths[2]}}  data: {data}")
    failed = sum(not r[0] for r in results)
    print(f"\n{len(results) - failed} of {len(results)} checks passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
