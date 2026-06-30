import asyncio, os
from gama_client.sync_client import GamaSyncClient
async def test():
	async def msg_handler(m):
		pass
	client = GamaSyncClient("localhost", 6868, lambda m: None, msg_handler)
	await client.connect(False)
	csv_path = os.path.abspath("test_out.csv").replace("\\", "/")
	params = [{'name': 'absolute_csv_path', 'type': 'string', 'value': csv_path}]
	r = client.sync_load(os.path.abspath("test_write.gaml"), "test_exp", parameters=params)
	exp_id = r.get("content")
	print("STEP:", client.sync_step(exp_id))
	await asyncio.sleep(1)
	await client.close_connection()
asyncio.run(test())