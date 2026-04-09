from flask import Flask, render_template, request, redirect
import pandas as pd
import json
import os

app = Flask(__name__)

DATA_FILE = "assignments.json"

# ---------------------------
# LOAD DATA
# ---------------------------

def load_bus_data():
    df = pd.read_csv("bus_data.csv")
    df["bus_id"] = df["bus_id"].astype(int)
    df["urgency"] = df["energy_needed"] / df["available_time"]
    return df

# ---------------------------
# LOAD / SAVE
# ---------------------------

def load_assignments():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_assignments(assignments):
    with open(DATA_FILE, "w") as f:
        json.dump(assignments, f)

# ---------------------------
# RISIKO BEREGNING
# ---------------------------

def calculate_risk(energy_needed, available_time, status):
    power = 150 if status == "FULD" else 75

    charging_time = (energy_needed / power) * 60  # minutter

    if charging_time > available_time:
        return "KRITISK"
    elif charging_time > 0.8 * available_time:
        return "RISIKO"
    else:
        return "OK"

# ---------------------------
# SLOT LOGIK
# ---------------------------

def find_best_slot(assignments, urgency):

    charger_usage = {i: [] for i in range(1, 26)}

    for data in assignments.values():
        charger_usage[int(data["charger_id"])].append(int(data["slot"]))

    if urgency > 1.2:
        for c, slots in charger_usage.items():
            if len(slots) == 0:
                return c, 1, "FULD"
        return None, None, "KRITISK"

    for c, slots in charger_usage.items():
        if len(slots) == 0:
            return c, 1, "FULD"

    for c, slots in charger_usage.items():
        if len(slots) == 1:
            return c, 2, "DELT"

    return None, None, "KRITISK"

# ---------------------------
# ROUTE
# ---------------------------

@app.route("/", methods=["GET", "POST"])
def index():

    assignments = load_assignments()
    df = load_bus_data()

    result = None
    error = None

    if request.method == "POST":
        action = request.form.get("action")

        if action == "reset":
            save_assignments({})
            return redirect("/")

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

                    if str(bus_id) in assignments:
                        data = assignments[str(bus_id)]
                    else:
                        charger, slot, status = find_best_slot(assignments, urgency)

                        if charger is None:
                            error = "⚠️ Ingen ledig plads"
                        else:
                            assignments[str(bus_id)] = {
                                "charger_id": charger,
                                "slot": slot,
                                "status": status
                            }
                            save_assignments(assignments)
                            data = assignments[str(bus_id)]

                    # 🔋 batteri %
                    battery = int(100 - (row["energy_needed"] / 300 * 100))

                    # ⚠️ risiko
                    risk = calculate_risk(
                        row["energy_needed"],
                        row["available_time"],
                        data["status"]
                    )

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
    # GRID
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
# RUN
# ---------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)