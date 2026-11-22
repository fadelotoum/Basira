"""Start the local Basira Camera ↔ Mac live-analysis bridge."""

import uvicorn

from basira.live_bridge import advertise_on_local_network


if __name__ == "__main__":
    with advertise_on_local_network() as address:
        print(f"Basira Mac is discoverable on the local network at {address}:8000")
        uvicorn.run("basira.live_bridge:app", host="0.0.0.0", port=8000, reload=False)
