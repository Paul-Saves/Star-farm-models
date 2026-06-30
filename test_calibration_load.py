import asyncio
import os
from gama_client.sync_client import GamaSyncClient

async def test_load():
    client = GamaSyncClient("localhost", 6868, lambda m: None, lambda m: None)
    await client.connect(False)
    
    model_path = os.path.abspath("STAR FARM/models/Experiments/Calibration-Paul.gaml")
    exp_name = "single_evaluation"
    
    print(f"Loading {model_path}...")
    try:
        response = client.sync_load(model_path, exp_name)
        print(f"Response: {response}")
    except Exception as e:
        print(f"Exception: {e}")
        
    await client.close_connection()

if __name__ == "__main__":
    asyncio.run(test_load())
