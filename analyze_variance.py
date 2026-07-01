import pandas as pd

df = pd.read_csv('STAR FARM/models/Experiments/Calibration/calibration_result_gen2.csv')

# We have 11 parameters.
params = ['rue_efficiency_factor', 'pest_infection_prob', 'pest_daily_increment',
          'toxicity_per_straw_unit', 'solar_rad_threshold', 'max_diffuse_bonus',
          'max_light_limit', 'steepness_factor', 'max_water_capacity',
          'lateral_leakage_coefficient', 'water_excess_coefficient']

# Group by these parameters and calculate the standard deviation of fitness
# and the count of seeds per group.
grouped = df.groupby(params)['fitness'].agg(['count', 'std', 'mean', 'max', 'min']).reset_index()

# Filter for groups that actually have more than 1 evaluation (seed)
replicated = grouped[grouped['count'] > 1].copy()

if len(replicated) > 0:
    replicated['cv'] = (replicated['std'] / replicated['mean']) * 100  # Coefficient of variation in %
    print(f"Total unique parameter sets with multiple seeds: {len(replicated)}")
    print(f"Average standard deviation of fitness: {replicated['std'].mean():.6f}")
    print(f"Average coefficient of variation: {replicated['cv'].mean():.4f}%")
    print(f"Maximum standard deviation of fitness observed: {replicated['std'].max():.6f}")
    print("\nTop 5 sets with highest variance:")
    print(replicated[['mean', 'std', 'cv', 'count']].sort_values(by='std', ascending=False).head())
else:
    print("No parameter sets with multiple seeds found to analyze variance.")
