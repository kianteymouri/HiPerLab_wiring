#!/usr/bin/env python3
"""
wire_mass_calculator.py

Purpose:
    Calculate wire mass branch-by-branch after you have chosen a wire gauge for each branch.

How to use:
    1. Edit CHOSEN_BRANCHES below with your selected gauges and measured routed lengths.
    2. Run:
        python wire_mass_calculator.py

Optional CSV input:
    python wire_mass_calculator.py --branches chosen_wire_branches.csv

CSV columns:
    name,awg,one_way_length_m,num_conductors,quantity,allowance_percent,notes

Examples:
    Power pair:
        num_conductors = 2
        quantity = 1

    Three motor phase wires:
        num_conductors = 3
        quantity = 1

    Five identical servo branches:
        num_conductors = 2
        quantity = 5
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass


# Approximate mass values for ETFE/Tefzel-style copper aircraft wire.
# Replace with exact manufacturer values when you choose the actual wire.
WIRE_MASS_G_PER_M = {
    "24": 3.82,
    "22": 5.45,
    "20": 7.50,
    "18": 11.70,
    "16": 14.80,
    "14": 22.20,
    "12": 36.00,
    "10": 55.00,
    "8": 85.00,
    "6": 135.00,
    "4": 218.00,
    "2": 340.00,
}


@dataclass
class ChosenBranch:
    name: str
    awg: str
    one_way_length_m: float
    num_conductors: int
    quantity: int = 1
    allowance_percent: float = 10.0
    notes: str = ""

    @property
    def installed_length_per_conductor_m(self) -> float:
        return self.one_way_length_m * (1.0 + self.allowance_percent / 100.0)

    @property
    def total_conductor_length_m(self) -> float:
        return self.installed_length_per_conductor_m * self.num_conductors * self.quantity

    @property
    def mass_g(self) -> float:
        if self.awg not in WIRE_MASS_G_PER_M:
            raise ValueError(f"Unknown AWG {self.awg!r}. Add it to WIRE_MASS_G_PER_M.")
        return self.total_conductor_length_m * WIRE_MASS_G_PER_M[self.awg]


# Edit these after you finalize routing.
CHOSEN_BRANCHES = [
    ChosenBranch("Main battery/fuse/disconnect wiring", "4", 1.20, 1, allowance_percent=10, notes="Combined estimated conductor length entered as one-way equivalent"),
    ChosenBranch("ESC branch - front left power pair", "8", 1.20, 2, allowance_percent=10, notes="12S bus to ESC"),
    ChosenBranch("ESC branch - front right power pair", "8", 1.20, 2, allowance_percent=10, notes="12S bus to ESC"),
    ChosenBranch("ESC branch - rear power pair", "8", 1.70, 2, allowance_percent=10, notes="12S bus to rear ESC"),
    ChosenBranch("ESC-to-motor phase wires", "10", 0.25, 3, quantity=3, allowance_percent=15, notes="Three phase wires per motor, three motors"),
    ChosenBranch("16 V regulator input pair", "14", 0.30, 2, allowance_percent=10, notes="12S protected bus to tilt-servo regulator"),
    ChosenBranch("16 V tilt-servo trunk pair", "12", 0.40, 2, allowance_percent=10, notes="Regulator to tilt-servo distribution"),
    ChosenBranch("Tilt-servo power branches", "22", 1.20, 2, quantity=2, allowance_percent=10, notes="One branch per front motor tilt servo"),
    ChosenBranch("8.4 V regulator input pair", "22", 0.30, 2, allowance_percent=10, notes="12S protected bus to control-servo regulator"),
    ChosenBranch("8.4 V control-servo trunk pair", "22", 0.40, 2, allowance_percent=10, notes="Regulator to control-servo distribution"),
    ChosenBranch("Control-servo branch - left wing", "22", 1.10, 2, allowance_percent=10, notes="8.4 V servo power"),
    ChosenBranch("Control-servo branch - right wing", "22", 1.10, 2, allowance_percent=10, notes="8.4 V servo power"),
    ChosenBranch("Control-servo branch - left tailplane", "22", 1.60, 2, allowance_percent=10, notes="8.4 V servo power"),
    ChosenBranch("Control-servo branch - right tailplane", "22", 1.60, 2, allowance_percent=10, notes="8.4 V servo power"),
    ChosenBranch("Control-servo branch - rudder", "22", 1.70, 2, allowance_percent=10, notes="8.4 V servo power"),
    ChosenBranch("ESC signal and ground pairs", "24", 1.37, 2, quantity=3, allowance_percent=10, notes="Average ESC signal route"),
    ChosenBranch("Servo signal and ground pairs", "24", 1.1, 2, quantity=7, allowance_percent=10, notes="Average servo signal route"),
    ChosenBranch("Contactor/precharge/control wiring", "20", 3.00, 1, allowance_percent=0, notes="Control-circuit total conductor length estimate"),
    ChosenBranch("Internal avionics wiring", "22", 5.00, 1, allowance_percent=0, notes="Avionics total conductor length estimate"),
]


def load_chosen_branches_from_csv(path: str) -> list[ChosenBranch]:
    branches: list[ChosenBranch] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        required = {"name", "awg", "one_way_length_m", "num_conductors"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

        for row in reader:
            branches.append(
                ChosenBranch(
                    name=row["name"],
                    awg=str(row["awg"]).strip(),
                    one_way_length_m=float(row["one_way_length_m"]),
                    num_conductors=int(row["num_conductors"]),
                    quantity=int(row.get("quantity") or 1),
                    allowance_percent=float(row.get("allowance_percent") or 0.0),
                    notes=row.get("notes") or "",
                )
            )
    return branches


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
    parser.add_argument("--branches", help="Optional CSV file containing chosen branch definitions.")
    args = parser.parse_args()

    branches = load_chosen_branches_from_csv(args.branches) if args.branches else CHOSEN_BRANCHES

    rows = []
    total_mass_g = 0.0

    for branch in branches:
        mass = branch.mass_g
        total_mass_g += mass
        rows.append(
            {
                "Branch": branch.name,
                "AWG": branch.awg,
                "Qty": str(branch.quantity),
                "Conductors/run": str(branch.num_conductors),
                "One-way m": f"{branch.one_way_length_m:.2f}",
                "Allowance %": f"{branch.allowance_percent:.1f}",
                "Total conductor m": f"{branch.total_conductor_length_m:.2f}",
                "Mass g": f"{mass:.1f}",
                "Mass kg": f"{mass / 1000:.3f}",
                "Notes": branch.notes,
            }
        )

    print_table(rows)
    print()
    print(f"TOTAL WIRE MASS: {total_mass_g:.1f} g")
    print(f"TOTAL WIRE MASS: {total_mass_g / 1000:.3f} kg")

    low_hardware_allowance_g = 700
    high_hardware_allowance_g = 1300
    print()
    print("Optional installed-system estimate including connectors, fuse holders, contactor,")
    print("distribution blocks, clamps, heat shrink, sleeving, and strain relief:")
    print(f"Low estimate:  {(total_mass_g + low_hardware_allowance_g) / 1000:.3f} kg")
    print(f"High estimate: {(total_mass_g + high_hardware_allowance_g) / 1000:.3f} kg")


if __name__ == "__main__":
    main()
