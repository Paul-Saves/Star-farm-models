import asyncio
import os
import csv
import pandas as pd
from gama_client.sync_client import GamaSyncClient
import random
import uuid
import glob
import builtins
import uuid
import glob

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- AUTO-LOGGING ---
log_file_path = os.path.join(BASE_DIR, "run_doe_log.txt")
log_file = open(log_file_path, "w", encoding="utf-8")
def custom_print(*args, **kwargs):
    builtins.print(*args, **kwargs)
    builtins.print(*args, **kwargs, file=log_file)
    log_file.flush()
print = custom_print

MODEL_PATH = os.path.join(BASE_DIR, "STAR FARM", "models", "Experiments", "Calibration-Paul.gaml")
CSV_PATH = os.path.join(BASE_DIR, "STAR FARM", "models", "Experiments", "Calibration", "calibration_result.csv")
DOE_PATH = os.path.join(BASE_DIR, "doe_11_params.csv")
EXPERIMENT_NAME = "single_evaluation"
PORT = 6868

# Number of different x evaluated at the same time
CHUNK_SIZE = 5 
# Number of repetitions per x
REPLICAS = 2

PARAM_NAMES = [
    "rue_efficiency_factor", "pest_infection_prob", "pest_daily_increment",
    "toxicity_per_straw_unit", "solar_rad_threshold", "max_diffuse_bonus",
    "max_light_limit", "steepness_factor", "max_water_capacity",
    "lateral_leakage_coefficient", "water_excess_coefficient"
]

def x_to_params(x):
    return [{"name": name, "type": "float", "value": str(val)} for name, val in zip(PARAM_NAMES, x)]

async def run_doe_batch():
    if not os.path.exists(DOE_PATH):
        print(f"Error: {DOE_PATH} not found.")
        return

    df = pd.read_csv(DOE_PATH)
    population = df.values.tolist()
    total_x = len(population)
    
    total_clients = CHUNK_SIZE * REPLICAS
    print(f"--- DOE EVALUATION ---")
    print(f"Total individuals: {total_x}")
    print(f"Replicas per individual: {REPLICAS}")
    print(f"Batch size: {CHUNK_SIZE} individuals at a time")
    print(f"=> Total concurrent GAMA clients: {total_clients}\n")

    async def async_command_answer_handler(message): pass
    async def gama_server_message_handler(message): 
        if "type" in message and message["type"] == "SimulationStatus": pass
        else: print(f"Server message: {message}")

    # Initialize CSV header
    header = "id,seed,rue_efficiency_factor,pest_infection_prob,pest_daily_increment,toxicity_per_straw_unit,solar_rad_threshold,max_diffuse_bonus,max_light_limit,steepness_factor,max_water_capacity,lateral_leakage_coefficient,water_excess_coefficient,error_yield,error_pesticide,error_fertilizer,error_water,fitness\n"
    write_header = not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH) == 0
    with open(CSV_PATH, "a") as f:
        if write_header:
            f.write(header)

    clients = [
        GamaSyncClient("localhost", PORT, async_command_answer_handler, gama_server_message_handler)
        for _ in range(total_clients)
    ]

    try:
        # --- RESUME CAPABILITY ---
        start_individual = 0
        if os.path.exists(CSV_PATH):
            with open(CSV_PATH, "r") as f:
                lines = f.readlines()
                # Subtract header and any potential stray manual runs
                # Count only lines that look like valid DOE outputs (having 18 columns)
                valid_evals = sum(1 for line in lines if len(line.split(",")) == 18)
                # Since we do 2 replicas per individual, the number of finished individuals is:
                start_individual = valid_evals // REPLICAS
                
        if start_individual > 0:
            print(f"Resuming from individual {start_individual} (Found {valid_evals} valid replicas in CSV)")

        for chunk_idx in range(start_individual, total_x, CHUNK_SIZE):
            chunk = population[chunk_idx:chunk_idx + CHUNK_SIZE]
            print(f"\n{'='*60}")
            print(f"Processing Batch {chunk_idx // CHUNK_SIZE + 1} (Individuals {chunk_idx} to {chunk_idx + len(chunk) - 1})")
            print(f"{'='*60}")

            existing_lines = 0
            if os.path.exists(CSV_PATH):
                with open(CSV_PATH, "r", encoding="utf-8") as f:
                    existing_lines = len(f.readlines())

            active_clients = len(chunk) * REPLICAS
            expected_lines = existing_lines + active_clients

            # Connect and launch
            client_idx = 0
            temp_csv_files = []
            
            for i, x in enumerate(chunk):
                params = x_to_params(x)
                for r in range(REPLICAS):
                    client = clients[client_idx]
                    print(f"  Connecting Client {client_idx+1} (Individual {chunk_idx + i}, Replica {r+1})...")
                    await client.connect(False)

                    # Unique CSV file for this specific client to avoid Windows File Lock
                    unique_id = str(uuid.uuid4())
                    temp_csv = os.path.join(BASE_DIR, "STAR FARM", "models", "Experiments", "Calibration", f"temp_result_{unique_id}.csv")
                    safe_csv_path = temp_csv.replace("\\", "/")
                    temp_csv_files.append(temp_csv)

                    client_params = list(params) + [
                        {"name": "seed", "type": "int", "value": str(random.randint(1, 2147483647))},
                        {"name": "absolute_csv_path", "type": "string", "value": safe_csv_path}
                    ]

                    response = client.sync_load(os.path.abspath(MODEL_PATH), EXPERIMENT_NAME, parameters=client_params)
                    if "content" in response and isinstance(response["content"], str):
                        exp_id = response["content"]
                        client.sync_play(exp_id)
                    else:
                        print(f"  Client {client_idx+1}: FAILED to load. Response: {response}")
                    
                    client_idx += 1

            # Wait for ALL temp CSV files to be created
            print(f"\nBatch running... Waiting for {active_clients} clients to finish and write their temp CSV files...")
            timeout = 1500
            elapsed = 0
            while elapsed < timeout:
                finished_count = sum(1 for f in temp_csv_files if os.path.exists(f))
                if finished_count == active_clients:
                    break
                await asyncio.sleep(2)
                elapsed += 2

            if elapsed >= timeout:
                print("TIMEOUT: Batch took too long.")
                break

            # Merge all temp CSVs into the main CSV and delete the temp files
            print(f"Batch {chunk_idx // CHUNK_SIZE + 1} finished! Merging results...")
            with open(CSV_PATH, "a") as main_f:
                for temp_csv in temp_csv_files:
                    if os.path.exists(temp_csv):
                        with open(temp_csv, "r") as tf:
                            content = tf.read().strip()
                            if content:
                                main_f.write(content + "\n")
                        os.remove(temp_csv)

            # Disconnect all active clients for the next batch to ensure clean state
            for c in clients[:active_clients]:
                await c.close_connection()

            print(f"Batch {chunk_idx // CHUNK_SIZE + 1} completed successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        for client in clients:
            try:
                await client.close_connection()
            except:
                pass
        print("Disconnected all clients.")

if __name__ == "__main__":
    asyncio.run(run_doe_batch())
