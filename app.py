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
    return df

def load_assignments():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_assignments(assignments):
    with open(DATA_FILE, "w") as f:
        json.dump(assignments, f)

# ---------------------------
# FIND SLOT
# ---------------------------

def find_slot(assignments):
    grid = {i: [] for i in range(1, 26)}

    for data in assignments.values():
        grid[int(data["charger"])].append(int(data["slot"]))

    for c in grid:
        if len(grid[c]) == 0:
            return c, 1

    for c in grid:
        if len(grid[c]) == 1:
            return c, 2

    return None, None

# ---------------------------
# ROUTE
# ---------------------------

@app.route("/", methods=["GET", "POST"])
def index():

    assignments = load_assignments()
    df = load_bus_data()

    page = request.form.get("page", "welcome")
    result = None
    error = None

    if request.method == "POST":

        action = request.form.get("action")

        if action == "reset":
            save_assignments({})
            return redirect("/")

        if action == "go_status":
            page = "status"

        if action == "go_input":
            page = "input"

        if action == "checkin":
            bus_input = request.form.get("bus_id")

            if not bus_input.isdigit():
                error = "Ugyldigt nummer"
                page = "input"
            else:
                bus_id = int(bus_input)

                row = df[df["bus_id"] == bus_id]

                if row.empty:
                    error = "Bus findes ikke"
                    page = "input"
                else:
                    row = row.iloc[0]

                    if str(bus_id) in assignments:
                        data = assignments[str(bus_id)]
                    else:
                        charger, slot = find_slot(assignments)

                        if charger is None:
                            error = "Ingen plads"
                            page = "input"
                        else:
                            # 🔋 Batteri (simuleret)
                            battery = int(100 - (row["energy_needed"] / 300 * 100))

                            # ⏱️ tid
                            time_left = int(row["available_time"])

                            # ⚠️ risiko
                            if time_left < 60:
                                risk = "🔴 Kritisk"
                            elif time_left < 120:
                                risk = "🟠 Risiko"
                            else:
                                risk = "🟢 OK"

                            assignments[str(bus_id)] = {
                                "bus_id": bus_id,
                                "charger": charger,
                                "slot": slot,
                                "battery": battery,
                                "time": time_left,
                                "risk": risk
                            }

                            save_assignments(assignments)
                            data = assignments[str(bus_id)]

                    result = data
                    page = "result"

        if action == "to_status":
            page = "status"

    # ---------------------------
    # GRID
    # ---------------------------

    grid = {i: {1: None, 2: None} for i in range(1, 26)}

    for data in assignments.values():
        grid[int(data["charger"])][int(data["slot"])] = data

    return render_template(
        "index.html",
        page=page,
        result=result,
        error=error,
        grid=grid
    )

if __name__ == "__main__":
    app.run(debug=True)