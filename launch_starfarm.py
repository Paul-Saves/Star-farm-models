import asyncio
import os
import csv
from gama_client.sync_client import GamaSyncClient
import random

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "STAR FARM", "models", "Experiments", "Calibration-Paul.gaml")
CSV_PATH = os.path.join(BASE_DIR, "STAR FARM", "models", "Experiments", "Calibration", "calibration_result.csv")
EXPERIMENT_NAME = "single_evaluation"
PORT = 6868
NUM_CLIENTS = 2

# --- INPUT: parameter definitions (name, default, min, max, step) ---
# Aligned with Calibration and Validation.gaml calibration_ experiment
PARAM_DEFS = [
    # name,                        default,  min,    max,   step
    ("rue_efficiency_factor",        0.71,    0.5,   0.85,  0.01),
    ("pest_infection_prob",          0.6,     0.4,   1.0,   0.1),
    ("pest_daily_increment",         0.04,    0.01,  0.1,   0.01),
    ("toxicity_per_straw_unit",      0.024,   0.0,   0.02,  0.001),
    ("solar_rad_threshold",          15.0,    10.0,  20.0,  0.1),
    ("max_diffuse_bonus",            0.9,     0.0,   0.35,  0.01),
    ("max_light_limit",              23.7,    18.0,  26.0,  0.1),
    ("steepness_factor",             4.8,     2.0,   10.0,  0.1),
    ("max_water_capacity",           74.0,    70.0,  120.0, 1.0),
    ("lateral_leakage_coefficient",  0.005,   0.001, 0.1,   0.001),
    ("water_excess_coefficient",     0.4,     0.1,   0.6,   0.01),
]

PARAM_NAMES = [p[0] for p in PARAM_DEFS]
PARAM_BOUNDS = [(p[2], p[3]) for p in PARAM_DEFS]

# --- OUTPUT: column names in the CSV ---
OUTPUT_COLUMNS = [
    "id", "seed",
    *PARAM_NAMES,
    "error_yield", "error_pesticide", "error_fertilizer", "error_water",
    "fitness",
]


def x_to_params(x):
    """Convert a flat parameter vector x into a list of gama-client parameter dicts."""
    assert len(x) == len(PARAM_NAMES), f"Expected {len(PARAM_NAMES)} params, got {len(x)}"
    return [
        {"name": name, "type": "float", "value": str(val)}
        for name, val in zip(PARAM_NAMES, x)
    ]


def parse_csv_results(csv_path):
    """Read the CSV output and return a list of dicts (one per seed)."""
    results = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed = {}
            for key, val in row.items():
                try:
                    parsed[key] = float(val)
                except (ValueError, TypeError):
                    parsed[key] = val
            results.append(parsed)
    return results


async def run_calibration(x):
    print(f"Input x = {x}")
    print(f"Starting {NUM_CLIENTS} parallel GAMA simulations...")

    async def async_command_answer_handler(message): pass
    
    async def gama_server_message_handler(message): 
        if "type" in message and message["type"] == "SimulationStatus":
            pass # ignore spammy status
        else:
            print(f"Server message: {message}")


    clients = [
        GamaSyncClient("localhost", PORT, async_command_answer_handler, gama_server_message_handler)
        for _ in range(NUM_CLIENTS)
    ]

    try:
        # Clear or initialize the CSV file with headers before running the batch
        header = "id,seed,rue_efficiency_factor,pest_infection_prob,pest_daily_increment,toxicity_per_straw_unit,solar_rad_threshold,max_diffuse_bonus,max_light_limit,steepness_factor,max_water_capacity,lateral_leakage_coefficient,water_excess_coefficient,error_yield,error_pesticide,error_fertilizer,error_water,fitness\n"
        write_header = not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH) == 0
        with open(CSV_PATH, "a") as f:
            if write_header:
                f.write(header)
        
        # Count existing lines to know when new simulations are done
        existing_lines = 0
        if os.path.exists(CSV_PATH):
            with open(CSV_PATH, "r", encoding="utf-8") as f:
                existing_lines = len(f.readlines())

        # 2. Connect all clients, load & play experiments
        params = x_to_params(x)
        for i, client in enumerate(clients):
            print(f"  Client {i+1}: connecting...")
            await client.connect(False)

            safe_csv_path = CSV_PATH.replace("\\", "/")
            client_params = list(params) + [
                {"name": "seed", "type": "int", "value": str(random.randint(1, 2147483647))},
                {"name": "absolute_csv_path", "type": "string", "value": safe_csv_path}
            ]

            print(f"  Client {i+1}: loading experiment...")
            response = client.sync_load(os.path.abspath(MODEL_PATH), EXPERIMENT_NAME, parameters=client_params)

            if "content" in response and isinstance(response["content"], str):
                exp_id = response["content"]
                print(f"  Client {i+1}: experiment loaded (ID: {exp_id}), playing...")
                client.sync_play(exp_id)
            else:
                print(f"  Client {i+1}: FAILED to load. Response: {response}")

        # 3. Wait for all results
        print(f"\nAll simulations running. Waiting for {NUM_CLIENTS} results in CSV (This can take 10-30 minutes)...\n")
        
        # 3. Wait for all CSV lines to be written
        expected_lines = existing_lines + NUM_CLIENTS
        timeout = 3600
        elapsed = 0
        while elapsed < timeout:
            if os.path.exists(CSV_PATH):
                with open(CSV_PATH, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if len(lines) >= expected_lines:
                        break
            await asyncio.sleep(2)
            elapsed += 2

        if elapsed >= timeout:
            print("TIMEOUT: Simulations took too long.")
            return []

        # 4. Parse and display results
        results = parse_csv_results(CSV_PATH)
        print(f"\n{'='*80}")
        print(f"SUCCESS! {len(results)} evaluations completed.")
        print(f"{'='*80}")
        print(f"\n{'--- INPUT (x) ---':^80}")
        for name, val in zip(PARAM_NAMES, x):
            print(f"  {name:35s} = {val}")
        print(f"\n{'--- OUTPUT (per seed) ---':^80}")
        for r in results:
            seed_str = f"{r.get('seed', '?')}"
            print(f"  seed={seed_str:>22s}  |  "
                  f"err_yield={r.get('error_yield', 0):.6f}  "
                  f"err_pest={r.get('error_pesticide', 0):.6f}  "
                  f"err_fert={r.get('error_fertilizer', 0):.6f}  "
                  f"err_water={r.get('error_water', 0):.6f}  "
                  f"fitness={r.get('fitness', 0):.6f}")
        
        fitnesses = [r.get("fitness", 0) for r in results]
        print(f"\n  Mean fitness = {sum(fitnesses)/len(fitnesses):.6f}")
        print(f"{'='*80}")

        return results

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        for client in clients:
            try:
                await client.close_connection()
            except (AttributeError, Exception):
                pass
        print("Disconnected all clients.")


# --- MAIN ---
if __name__ == "__main__":
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model file not found at {MODEL_PATH}")
    else:
        # Example x vector (from calibration_result_gen2.csv best row)
        x = [0.71, 0.6, 0.04, 0.092, 12.0, 1.2, 24.1, 10.8, 78.0, 0.089, 0.4]
        asyncio.run(run_calibration(x))
