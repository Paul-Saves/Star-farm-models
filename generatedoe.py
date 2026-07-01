import pandas as pd
import numpy as np
from smt.sampling_methods import LHS
import os

# --- INPUT: parameter definitions (name, min, max) ---
# Aligned with Calibration and Validation.gaml calibration_ experiment
PARAM_DEFS = [
    # name,                          min,    max
    ("rue_efficiency_factor",        0.5,   0.85),
    ("pest_infection_prob",          0.4,   1.0),
    ("pest_daily_increment",         0.01,  0.1),
    ("toxicity_per_straw_unit",      0.0,   0.02),
    ("solar_rad_threshold",          10.0,  20.0),
    ("max_diffuse_bonus",            0.0,   0.35),
    ("max_light_limit",              18.0,  26.0),
    ("steepness_factor",             2.0,   10.0),
    ("max_water_capacity",           70.0,  120.0),
    ("lateral_leakage_coefficient",  0.001, 0.1),
    ("water_excess_coefficient",     0.1,   0.6),
]

PARAM_NAMES = [p[0] for p in PARAM_DEFS]

def generate_doe(num_samples=110, output_file="doe_11_params.csv"):
    """
    Generates a Design of Experiments (LHS) for the 11 StarFarm parameters.
    """
    # Create the limits array for SMT
    xlimits = np.array([[p[1], p[2]] for p in PARAM_DEFS])
    
    # Initialize Latin Hypercube Sampling
    sampling = LHS(xlimits=xlimits, criterion="ese", seed=41)
    
    # Generate points
    print(f"Generating {num_samples} samples for {len(PARAM_NAMES)} parameters...")
    x = sampling(num_samples)
    
    # Create DataFrame
    df = pd.DataFrame(x, columns=PARAM_NAMES)
    
    # Save to CSV
    df.to_csv(output_file, index=False)
    print(f"DOE successfully saved to {output_file}")
    
    return df

if __name__ == "__main__":
    # Generate 110 samples by default
    generate_doe(110, "doe_11_params.csv")