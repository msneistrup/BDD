import pandas as pd
import numpy as np

np.random.seed(42)

n_buses = 50
battery_capacity = 350

battery_levels = np.random.uniform(0.1, 0.5, n_buses)
target_soc = 0.9

energy_needed = (target_soc - battery_levels) * battery_capacity

effective_power = np.random.uniform(50, 90, n_buses)

available_time = (energy_needed / effective_power) * 3600
departure_time = available_time + np.random.randint(3600, 18000, n_buses)

df = pd.DataFrame({
    "bus_id": range(1, n_buses + 1),
    "available_time": available_time.astype(int),
    "departure_time": departure_time.astype(int),
    "battery_start": (battery_levels * 100).astype(int)
})

df.to_csv("bus_data.csv", index=False)

print("Data genereret")