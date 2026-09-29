import requests
import asyncio
from websockets.asyncio.client import connect

BACKEND_SERVER_URL="http://127.0.0.1:8000"

# Relay stream to backend webhook
async def main():
    async with connect("ws://localhost:8765") as websocket:
        async for message in websocket:
            response = requests.post(
                url=f"{BACKEND_SERVER_URL}/api/webhook",
                headers={
                    # "Authorization": f"Bearer {openrouter_key}"   // ideally, there should be an auth/api key in the header
                    "Content-Type": "application/json",
                },
                data=message
            )

            if response.ok:
                print(f"Relay event successful")
            else:
                print("Relay event failed")


asyncio.run(main())