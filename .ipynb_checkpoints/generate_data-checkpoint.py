import pandas as pd
import numpy as np

np.random.seed(42)

n_buses = 50

arrival_times = np.random.randint(16*60, 23*60, n_buses)
charging_windows = np.random.randint(30, 6*60, n_buses)
departure_times = arrival_times + charging_windows

battery_capacity = 300
target_soc = 0.9

battery_levels = np.random.uniform(0.1, 0.8, n_buses)

energy_needed = (target_soc - battery_levels) * battery_capacity
energy_needed = np.clip(energy_needed, 0, None)

df = pd.DataFrame({
    "bus_id": list(range(1, n_buses + 1)),  # 1,2,3...
    "available_time": departure_times - arrival_times,
    "energy_needed": energy_needed
})

df.to_csv("bus_data.csv", index=False)

print("NY bus_data.csv genereret!")
print(df.head())