from collections import defaultdict

from fastapi import WebSocket


# =========================================================
# CONNECTION MANAGER
# =========================================================

class ConnectionManager:

    def __init__(self):

        self.active_connections = defaultdict(list)

    # =====================================================
    # CONNECT
    # =====================================================

    async def connect(
        self,
        user_id: int,
        websocket: WebSocket
    ):

        await websocket.accept()

        self.active_connections[
            user_id
        ].append(
            websocket
        )

        print(
            f"🔌 WebSocket connected: User {user_id}"
        )

    # =====================================================
    # DISCONNECT
    # =====================================================

    def disconnect(
        self,
        user_id: int,
        websocket: WebSocket
    ):

        connections = (
            self.active_connections.get(
                user_id,
                []
            )
        )

        if websocket in connections:

            connections.remove(
                websocket
            )

        if not connections:

            self.active_connections.pop(
                user_id,
                None
            )

        print(
            f"🔌 WebSocket disconnected: User {user_id}"
        )

    # =====================================================
    # SEND TO USER
    # =====================================================

    async def send_to_user(
        self,
        user_id: int,
        message: dict
    ):

        connections = list(
            self.active_connections.get(
                user_id,
                []
            )
        )

        if not connections:

            return

        dead_connections = []

        for websocket in connections:

            try:

                await websocket.send_json(
                    message
                )

            except Exception as error:

                print(
                    f"⚠️ WebSocket send failed: {error}"
                )

                dead_connections.append(
                    websocket
                )

        for websocket in dead_connections:

            self.disconnect(
                user_id,
                websocket
            )

    # =====================================================
    # BROADCAST
    # =====================================================

    async def broadcast(
        self,
        message: dict
    ):

        users = list(
            self.active_connections.keys()
        )

        for user_id in users:

            await self.send_to_user(
                user_id,
                message
            )


# =========================================================
# GLOBAL MANAGER
# =========================================================

manager = ConnectionManager()