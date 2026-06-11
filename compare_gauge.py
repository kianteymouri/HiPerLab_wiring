#!/usr/bin/env python3
"""
this script allows u to compare the different types of wire gauges

a wire type should be selected by amalyzing the following categories
1. its ability to sustain continous current for long periods of time
2. its ability to sustain peak current for short preiods of time
3. minimizing its voltage drop
4. minimizing power loss to heat

for each sub section(esc, motors etc) our script calculates:
round trip resistance: R = 2Lr
voltage drop: V_drop = (I_continous)*R and peak
voltage drop percent: V_percent = ( V_drop/(V_Battnominal) ) * 100 ----for both peak and continous
Heat power loss: P = ( (I_continous)^2 ) * R
Estimated conducotr mass for each canidate AWG

users should first edit the BRANCHES list with wiring branches and then edit the CANIDATE_AWGS to compare specific gauges and then run the code

Notes:
    - one_way_length_m is the routed physical distance from source to load.
    - Power circuits need positive and negative conductors, so round-trip length is 2x one-way length.
    - num_parallel_runs should usually be 1. Use 2 only if you intentionally run two wires in parallel because of space/thickness constraints
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass


# Approximate copper/ETFE aircraft wire values from website: https://wovenwire.com/reference/AWG-copper-wire-gauge-chart.htm
#keep in mind that resistance values are approximate at 20 C.
AWG_TABLE = {
    "27": {"resistance_ohm_per_m": 0.16800, "mass_g_per_m": 0.909},
    "26": {"resistance_ohm_per_m": 0.13400, "mass_g_per_m": 1.150},
    "25": {"resistance_ohm_per_m": 0.10600, "mass_g_per_m": 1.440},
    "24": {"resistance_ohm_per_m": 0.08420, "mass_g_per_m": 1.820},
    "22": {"resistance_ohm_per_m": 0.05300, "mass_g_per_m": 2.890},
    "20": {"resistance_ohm_per_m": 0.03330, "mass_g_per_m": 4.610},
    "18": {"resistance_ohm_per_m": 0.02090, "mass_g_per_m": 7.320},
    "16": {"resistance_ohm_per_m": 0.01320, "mass_g_per_m": 11.600},
    "14": {"resistance_ohm_per_m": 0.00828, "mass_g_per_m": 18.500},
    "12": {"resistance_ohm_per_m": 0.00521, "mass_g_per_m": 29.500},
    "10": {"resistance_ohm_per_m": 0.00328, "mass_g_per_m": 46.800},
    "8":  {"resistance_ohm_per_m": 0.00206, "mass_g_per_m": 74.300},
    "6":  {"resistance_ohm_per_m": 0.00130, "mass_g_per_m": 118.000},
    "4":  {"resistance_ohm_per_m": 0.000815, "mass_g_per_m": 188.000},
    "2":  {"resistance_ohm_per_m": 0.000513, "mass_g_per_m": 299.000},
    "1":  {"resistance_ohm_per_m": 0.000407, "mass_g_per_m": 376.000},
}


@dataclass
class Branch:
    name: str
    system_voltage: float
    current_continuous: float
    current_peak: float
    one_way_length_m: float
    candidate_awgs: list[str]

    #included parralel runs for instances of thickness constraints
    num_parallel_runs: int = 1
    allowance_percent: float = 10.0
    notes: str = ""

    @property
    def installed_one_way_length_m(self) -> float:
        return self.one_way_length_m * (1.0 + self.allowance_percent / 100.0)

    @property
    def round_trip_conductor_length_m(self) -> float:
        return 2.0 * self.installed_one_way_length_m


#edit these branches with your measured/routed lengths.
#included a ten percent margin for wiring around spars or other parts of the air craft
#from left to right it reads; section name, branch voltage, continous current(A), peak current(A), one way length, awgs you want to test, percent allowance, and notes
BRANCHES = [
    Branch("ESC branch1(front_left)", 44.4, 45, 70, 1.2, ["10", "8", "6"], allowance_percent=10, notes="12S bus to ESC input(FL)"),
    Branch("ESC branch2(front_right)", 44.4, 45, 70, 1.2, ["10", "8", "6"], allowance_percent=10, notes="12S bus to ESC input(FR)"),
    Branch("ESC branch(rear)", 44.4, 45, 70, 1.7, ["10", "8", "6"], allowance_percent=10, notes="12S bus to rear ESC input"),
    Branch("8.4 V control-servo trunk", 8.4, 15, 30, 0.4, ["16", "14", "12"], allowance_percent=10, notes="Regulator output to control-surface-servo distribution"),
    Branch("Control-surface servo branch", 8.4, 3, 6, 1.5, ["18", "16", "14"], allowance_percent=15, notes="Distribution to ONE 40 kg-cm servo"),
    Branch("16 V tilt-servo trunk", 16.0, 10, 24, 0.4, ["14", "12", "10"], allowance_percent=10, notes="Regulator output to tilt-servo distribution"),
    Branch("Tilt-servo branch", 16.0, 5, 12, 1.2, ["18", "16", "14"], allowance_percent=15, notes="Distribution to ONE 80 kg-cm tilt servo"),
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



        #calculating voltage drops
        vdrop_cont = branch.current_continuous * total_resistance #continuous current voltage drop
        vdrop_peak = branch.current_peak * total_resistance #peak current voltage drop


        #finds percentage in comparison to battery voltage
        pct_cont = 100.0 * vdrop_cont / branch.system_voltage 
        pct_peak = 100.0 * vdrop_peak / branch.system_voltage

        #calculating power loss due to heat
        ploss_cont = (branch.current_continuous ** 2) * total_resistance #with continous current
        ploss_peak = (branch.current_peak ** 2) * total_resistance #with peak current

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
