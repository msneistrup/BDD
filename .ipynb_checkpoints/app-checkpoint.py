from flask import Flask, render_template, request, redirect
import pandas as pd
import json
import os
import time
from datetime import datetime

app = Flask(__name__)

DATA_FILE = "assignments.json"

log = []

VOLTAGE = 400
MAX_CHARGERS = 10

def load_assignments():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_assignments(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def load_bus_data():
    return pd.read_csv("bus_data.csv")

@app.route("/", methods=["GET", "POST"])
def index():

    assignments = load_assignments()
    df = load_bus_data()

    page = "welcome"
    search_result = None
    highlight_bus = None
    access = False
    error_message = None
    result_message = None

    if request.method == "POST":
        action = request.form.get("action")

        if action == "go_input":
            page = "input"

        elif action == "go_status":
            page = "status"

        elif action == "go_admin":
            page = "login"

        elif action == "login":
            if request.form.get("code") == "2026":
                page = "admin"
                access = True
            else:
                page = "login"

        elif action == "reset":
            save_assignments({})
            log.clear()
            return redirect("/")

        elif action == "search_bus":
            page = "status"
            sid = request.form.get("search_id")

            if not sid or not sid.isdigit():
                error_message = "Bus findes ikke"

            elif int(sid) not in df["bus_id"].values:
                error_message = "Bus findes ikke"

            elif sid not in assignments:
                error_message = "Bus er ude at køre"

            else:
                search_result = assignments[sid]
                highlight_bus = sid

        elif action == "checkin":
            bus_id = request.form.get("bus_id")

            if not bus_id or not bus_id.isdigit():
                error_message = "Bus findes ikke"
                page = "input"

            elif int(bus_id) not in df["bus_id"].values:
                error_message = "Bus findes ikke"
                page = "input"

            elif bus_id in assignments:
                error_message = "Bus er allerede tilsluttet"
                page = "input"

            else:
                row = df[df["bus_id"] == int(bus_id)]

                new_bus = {
                    "bus_id": int(bus_id),
                    "time": int(row.iloc[0]["available_time"]),
                    "timestamp": time.time()
                }

                assignments[bus_id] = new_bus
                save_assignments(assignments)

                log.append({
                    "bus_id": bus_id,
                    "time": datetime.now().strftime("%H:%M")
                })

                # 🔥 FIND PLADS (101/201 system)
                taken_slots = []

                for i, data in enumerate(assignments.values()):
                    charger = (i % 5) + 1
                    pos = 1 if i < 5 else 2

                    if pos == 1:
                        taken_slots.append(100 + charger)
                    else:
                        taken_slots.append(200 + charger)

                assigned_slot = None

                for charger in range(1, 6):
                    for prefix in [100, 200]:
                        slot_number = prefix + charger
                        if slot_number not in taken_slots:
                            assigned_slot = slot_number
                            break
                    if assigned_slot:
                        break

                result_message = f"Kør til plads {assigned_slot}"

                new_bus["slot"] = assigned_slot

                page = "result"

    # GRID
    grid = {i: {1: None, 2: None} for i in range(1, 6)}

    total_power = 0
    total_energy = 0

    for i, data in enumerate(assignments.values()):
        charger = (i % 5) + 1
        pos = 1 if i < 5 else 2

        slot_number = 100 + charger if pos == 1 else 200 + charger
        data["slot"] = slot_number

        elapsed = time.time() - data["timestamp"]
        total = data["time"]

        progress = elapsed / max(1, total)
        battery = min(90, 20 + progress * 70)

        power = 100
        total_power += power

        total_energy += (elapsed / 3600) * power

        remaining = max(0, total - elapsed)

        data["battery_now"] = int(battery)
        data["remaining_text"] = f"{int(remaining//3600)}t {int((remaining%3600)//60)}m"

        grid[charger][pos] = data

    ampere = int(total_power * 1000 / VOLTAGE)

    return render_template(
        "index.html",
        page=page,
        grid=grid,
        search_result=search_result,
        highlight_bus=highlight_bus,
        total_power=int(total_power),
        total_energy=int(total_energy),
        ampere=ampere,
        active=len(assignments),
        max_chargers=MAX_CHARGERS,
        access=access,
        log=log,
        error_message=error_message,
        result_message=result_message
    )

if __name__ == "__main__":
    print("🚀 Starter server på http://127.0.0.1:5100")
if __name__ == "__main__":
    app.run()