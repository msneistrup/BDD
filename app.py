# Importerer de værktøjer vi skal bruge
from flask import Flask, render_template, request, redirect
import pandas as pd
import json
import os

# Opretter Flask app (selve websitet)
app = Flask(__name__)

# Fil hvor vi gemmer hvilke busser der er parkeret
DATA_FILE = "assignments.json"


# ---------------------------
# LOAD DATA (bus-data)
# ---------------------------

def load_bus_data():
    """
    Denne funktion læser vores datasæt med busser.
    Den indeholder:
    - bus_id
    - hvor lang tid bussen har til opladning
    - hvor meget energi den mangler

    Vi beregner også en 'urgency', som bruges til prioritering.
    """
    df = pd.read_csv("bus_data.csv")

    # Sikrer korrekt datatype
    df["bus_id"] = df["bus_id"].astype(int)

    # Urgency = hvor presset bussen er
    df["urgency"] = df["energy_needed"] / df["available_time"]

    return df


# ---------------------------
# LOAD / SAVE (hukommelse)
# ---------------------------

def load_assignments():
    """
    Indlæser hvilke busser der allerede er parkeret.
    Dette gør systemet 'stateful' – det husker tidligere valg.
    """
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_assignments(assignments):
    """
    Gemmer alle busplaceringer i en fil.
    """
    with open(DATA_FILE, "w") as f:
        json.dump(assignments, f)


# ---------------------------
# RISIKO BEREGNING
# ---------------------------

def calculate_risk(energy_needed, available_time, status):
    """
    Beregner om bussen når at lade færdig.

    Vi antager:
    - FULD oplader = 150 kW
    - DELT oplader = 75 kW

    Vi beregner hvor lang tid opladning tager og sammenligner med tiden.
    """

    # Effekt afhænger af om bussen deler oplader
    power = 150 if status == "FULD" else 75

    # Hvor lang tid tager opladning (i minutter)
    charging_time = (energy_needed / power) * 60

    # Klassificering
    if charging_time > available_time:
        return "KRITISK"
    elif charging_time > 0.8 * available_time:
        return "RISIKO"
    else:
        return "OK"


# ---------------------------
# SLOT LOGIK (optimering)
# ---------------------------

def find_best_slot(assignments, urgency):
    """
    Finder den bedste ladestander til en bus.

    Logik:
    1. Kritiske busser må IKKE dele
    2. Ellers gives fuld oplader først
    3. Derefter delt oplader
    """

    # Overblik over hvilke ladere der er brugt
    charger_usage = {i: [] for i in range(1, 26)}

    for data in assignments.values():
        charger_usage[int(data["charger_id"])].append(int(data["slot"]))

    # Kritiske busser (høj urgency)
    if urgency > 1.2:
        for c, slots in charger_usage.items():
            if len(slots) == 0:
                return c, 1, "FULD"
        return None, None, "KRITISK"

    # Først: tom lader (bedst løsning)
    for c, slots in charger_usage.items():
        if len(slots) == 0:
            return c, 1, "FULD"

    # Dernæst: del oplader
    for c, slots in charger_usage.items():
        if len(slots) == 1:
            return c, 2, "DELT"

    # Ingen plads
    return None, None, "KRITISK"


# ---------------------------
# ROUTE (webside)
# ---------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    """
    Dette er hovedsiden.

    Her sker:
    - input fra bruger
    - beregning
    - visning
    """

    assignments = load_assignments()
    df = load_bus_data()

    result = None
    error = None

    if request.method == "POST":
        action = request.form.get("action")

        # RESET system
        if action == "reset":
            save_assignments({})
            return redirect("/")

        # CHECK-IN
        if action == "checkin":
            bus_input = request.form["bus_id"].strip()

            if not bus_input.isdigit():
                error = "Indtast gyldigt nummer"
            else:
                bus_id = int(bus_input)

                bus_row = df[df["bus_id"] == bus_id]

                if bus_row.empty:
                    error = "Bus findes ikke"
                else:
                    row = bus_row.iloc[0]

                    urgency = float(row["urgency"])

                    # Hvis allerede checket ind
                    if str(bus_id) in assignments:
                        data = assignments[str(bus_id)]
                    else:
                        charger, slot, status = find_best_slot(assignments, urgency)

                        if charger is None:
                            error = "⚠️ Ingen plads"
                        else:
                            assignments[str(bus_id)] = {
                                "charger_id": charger,
                                "slot": slot,
                                "status": status
                            }
                            save_assignments(assignments)
                            data = assignments[str(bus_id)]

                    # Batteri (estimat)
                    battery = int(100 - (row["energy_needed"] / 300 * 100))

                    # Risiko
                    risk = calculate_risk(
                        row["energy_needed"],
                        row["available_time"],
                        data["status"]
                    )

                    # Resultat til UI
                    result = {
                        "bus_id": bus_id,
                        "charger_id": data["charger_id"],
                        "slot": data["slot"],
                        "status": data["status"],
                        "battery": battery,
                        "time": int(row["available_time"]),
                        "risk": risk
                    }

    # ---------------------------
    # GRID (visualisering)
    # ---------------------------

    grid = {i: {1: None, 2: None} for i in range(1, 26)}

    for bus_id, data in assignments.items():
        row = df[df["bus_id"] == int(bus_id)].iloc[0]

        battery = int(100 - (row["energy_needed"] / 300 * 100))
        risk = calculate_risk(
            row["energy_needed"],
            row["available_time"],
            data["status"]
        )

        grid[int(data["charger_id"])][int(data["slot"])] = {
            "bus_id": bus_id,
            "status": data["status"],
            "battery": battery,
            "time": int(row["available_time"]),
            "risk": risk
        }

    return render_template("index.html", result=result, error=error, grid=grid)


# ---------------------------
# START SERVER
# ---------------------------

if __name__ == "__main__":
    app.run()