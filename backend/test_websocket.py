import asyncio
import websockets


async def main():
    uri = "ws://127.0.0.1:8000/ws/tracking/5"

    async with websockets.connect(uri) as websocket:
        print("✅ Connected to WebSocket")

        while True:
            message = await websocket.recv()
            print("Received:", message)


if __name__ == "__main__":
    asyncio.run(main())
