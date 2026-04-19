# test_bridge.py en la raíz del proyecto local
import asyncio
import os
from custom.mcp_bridge.bridge_client import start

async def main():
    task = start(
        user_id="jose",
        api_key="aa08432e468879fb7d8f2af3afeba3775f945a01364121180e38d192cb05897a"
    )
    await task  # corre indefinidamente

asyncio.run(main())