#!/usr/bin/env python3
"""
compare_voltage_drop.py

Purpose:
    Compare candidate wire gauges for each aircraft electrical branch.
    Calculates round-trip resistance, voltage drop, voltage-drop percent,
    wire heating/power loss, and estimated conductor mass for each candidate AWG.

How to use:
    1. Edit the BRANCHES list below with your aircraft wiring branches.
    2. Edit CANDIDATE_AWGS if you want to compare different gauges.
    3. Run:
        python compare_voltage_drop.py

Optional CSV input:
    You can also import branches from a CSV:
        python compare_voltage_drop.py --branches branches.csv

    CSV columns:
        name,system_voltage,current_continuous,current_peak,one_way_length_m,num_parallel_runs,candidate_awgs

    Example candidate_awgs cell:
        "10,8,6"

Notes:
    - one_way_length_m is the routed physical distance from source to load.
    - Power circuits need positive and negative conductors, so round-trip length is 2x one-way length.
    - num_parallel_runs should usually be 1. Use 2 only if you intentionally run two wires in parallel per polarity.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass


# Approximate copper/ETFE aircraft wire values.
# Replace mass_g_per_m with the exact value from your selected wire datasheet.
# Resistance values are approximate at 20 C.
AWG_TABLE = {
    # AWG: resistance ohm/m, mass g/m
    "24": {"resistance_ohm_per_m": 0.0842, "mass_g_per_m": 3.82},
    "22": {"resistance_ohm_per_m": 0.0530, "mass_g_per_m": 5.45},
    "20": {"resistance_ohm_per_m": 0.0333, "mass_g_per_m": 7.50},
    "18": {"resistance_ohm_per_m": 0.0210, "mass_g_per_m": 11.70},
    "16": {"resistance_ohm_per_m": 0.0132, "mass_g_per_m": 14.80},
    "14": {"resistance_ohm_per_m": 0.00829, "mass_g_per_m": 22.20},
    "12": {"resistance_ohm_per_m": 0.00521, "mass_g_per_m": 36.00},
    "10": {"resistance_ohm_per_m": 0.00328, "mass_g_per_m": 55.00},
    "8":  {"resistance_ohm_per_m": 0.00206, "mass_g_per_m": 85.00},
    "6":  {"resistance_ohm_per_m": 0.00130, "mass_g_per_m": 135.00},
    "4":  {"resistance_ohm_per_m": 0.000815, "mass_g_per_m": 218.00},
    "2":  {"resistance_ohm_per_m": 0.000513, "mass_g_per_m": 340.00},
}


@dataclass
class Branch:
    name: str
    system_voltage: float
    current_continuous: float
    current_peak: float
    one_way_length_m: float
    candidate_awgs: list[str]
    num_parallel_runs: int = 1
    allowance_percent: float = 10.0
    notes: str = ""

    @property
    def installed_one_way_length_m(self) -> float:
        return self.one_way_length_m * (1.0 + self.allowance_percent / 100.0)

    @property
    def round_trip_conductor_length_m(self) -> float:
        return 2.0 * self.installed_one_way_length_m


# Edit these branches with your measured/routed lengths.
BRANCHES = [
    Branch("ESC branch - front left", 44.4, 45, 70, 1.2, ["10", "8", "6"], allowance_percent=10, notes="12S bus to ESC input"),
    Branch("ESC branch - front right", 44.4, 45, 70, 1.2, ["10", "8", "6"], allowance_percent=10, notes="12S bus to ESC input"),
    Branch("ESC branch - rear", 44.4, 45, 70, 1.7, ["10", "8", "6"], allowance_percent=10, notes="12S bus to rear ESC input"),
    Branch("8.4 V control-servo trunk", 8.4, 15, 30, 0.4, ["16", "14", "12"], allowance_percent=10, notes="Regulator output to control-servo distribution"),
    Branch("Control-surface servo branch", 8.4, 3, 6, 1.5, ["18", "16", "14"], allowance_percent=15, notes="Distribution to one 40 kg-cm servo"),
    Branch("16 V tilt-servo trunk", 16.0, 10, 24, 0.4, ["14", "12", "10"], allowance_percent=10, notes="Regulator output to tilt-servo distribution"),
    Branch("Tilt-servo branch", 16.0, 5, 12, 1.2, ["18", "16", "14"], allowance_percent=15, notes="Distribution to one 80 kg-cm tilt servo"),
]


def load_branches_from_csv(path: str) -> list[Branch]:
    branches: list[Branch] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        required = {"name", "system_voltage", "current_continuous", "current_peak", "one_way_length_m", "candidate_awgs"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

        for row in reader:
            awgs = [x.strip() for x in row["candidate_awgs"].split(",") if x.strip()]
            branches.append(
                Branch(
                    name=row["name"],
                    system_voltage=float(row["system_voltage"]),
                    current_continuous=float(row["current_continuous"]),
                    current_peak=float(row["current_peak"]),
                    one_way_length_m=float(row["one_way_length_m"]),
                    candidate_awgs=awgs,
                    num_parallel_runs=int(row.get("num_parallel_runs") or 1),
                    allowance_percent=float(row.get("allowance_percent") or 10.0),
                    notes=row.get("notes") or "",
                )
            )
    return branches


def evaluate_branch(branch: Branch) -> list[dict[str, str]]:
    rows = []

    for awg in branch.candidate_awgs:
        if awg not in AWG_TABLE:
            raise ValueError(f"Unknown AWG {awg!r}. Add it to AWG_TABLE.")

        data = AWG_TABLE[awg]
        resistance_per_m = data["resistance_ohm_per_m"]
        mass_per_m = data["mass_g_per_m"]

        round_trip_length = branch.round_trip_conductor_length_m
        total_resistance = (round_trip_length * resistance_per_m) / branch.num_parallel_runs

        vdrop_cont = branch.current_continuous * total_resistance
        vdrop_peak = branch.current_peak * total_resistance

        pct_cont = 100.0 * vdrop_cont / branch.system_voltage
        pct_peak = 100.0 * vdrop_peak / branch.system_voltage

        ploss_cont = (branch.current_continuous ** 2) * total_resistance
        ploss_peak = (branch.current_peak ** 2) * total_resistance

        mass_g = round_trip_length * mass_per_m * branch.num_parallel_runs

        rows.append(
            {
                "Branch": branch.name,
                "AWG": awg,
                "One-way m incl allowance": f"{branch.installed_one_way_length_m:.2f}",
                "Total conductor m": f"{round_trip_length * branch.num_parallel_runs:.2f}",
                "R total ohm": f"{total_resistance:.5f}",
                "Vdrop cont V": f"{vdrop_cont:.3f}",
                "Vdrop cont %": f"{pct_cont:.2f}",
                "Loss cont W": f"{ploss_cont:.1f}",
                "Vdrop peak V": f"{vdrop_peak:.3f}",
                "Vdrop peak %": f"{pct_peak:.2f}",
                "Loss peak W": f"{ploss_peak:.1f}",
                "Est mass g": f"{mass_g:.1f}",
                "Notes": branch.notes,
            }
        )

    return rows


def print_table(rows: list[dict[str, str]]) -> None:
    if not rows:
        return

    headers = list(rows[0].keys())
    widths = {h: len(h) for h in headers}

    for row in rows:
        for h in headers:
            widths[h] = max(widths[h], len(str(row[h])))

    print(" | ".join(h.ljust(widths[h]) for h in headers))
    print("-+-".join("-" * widths[h] for h in headers))

    for row in rows:
        print(" | ".join(str(row[h]).ljust(widths[h]) for h in headers))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--branches", help="Optional CSV file containing branch definitions.")
    args = parser.parse_args()

    branches = load_branches_from_csv(args.branches) if args.branches else BRANCHES

    all_rows: list[dict[str, str]] = []
    for branch in branches:
        all_rows.extend(evaluate_branch(branch))

    print_table(all_rows)


if __name__ == "__main__":
    main()
