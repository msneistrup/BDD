from flask import Flask, render_template, request, redirect
import pandas as pd
import json
import os

app = Flask(__name__)

DATA_FILE = "assignments.json"

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


@app.route("/", methods=["GET", "POST"])
def index():

    assignments = load_assignments()

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
            bus_id = request.form.get("bus_id")

            if not bus_id.isdigit():
                error = "Ugyldigt nummer"
                page = "input"
            else:
                bus_id = int(bus_id)

                if str(bus_id) in assignments:
                    data = assignments[str(bus_id)]
                else:
                    charger, slot = find_slot(assignments)

                    if charger is None:
                        error = "Ingen plads"
                        page = "input"
                    else:
                        assignments[str(bus_id)] = {
                            "charger": charger,
                            "slot": slot
                        }
                        save_assignments(assignments)
                        data = assignments[str(bus_id)]

                result = {
                    "bus_id": bus_id,
                    "charger": data["charger"],
                    "slot": data["slot"]
                }

                page = "result"

        if action == "to_status":
            page = "status"

    # GRID
    grid = {i: {1: None, 2: None} for i in range(1, 26)}

    for bus_id, data in assignments.items():
        grid[int(data["charger"])][int(data["slot"])] = bus_id

    return render_template(
        "index.html",
        page=page,
        result=result,
        error=error,
        grid=grid
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)