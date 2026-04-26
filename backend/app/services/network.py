import asyncio
import time
from typing import Literal


NetworkMode = Literal["5g"]
ProcessingMode = Literal["edge", "cloud"]

NETWORK_DELAYS_MS: dict[NetworkMode, int] = {
    "5g": 50,
}

PROCESSING_DELAYS_MS: dict[ProcessingMode, int] = {
    "edge": 35,
    "cloud": 140,
}


async def simulate_network(mode: NetworkMode) -> float:
    start = time.perf_counter()
    await asyncio.sleep(NETWORK_DELAYS_MS[mode] / 1000)
    end = time.perf_counter()
    return round((end - start) * 1000, 2)


async def simulate_processing(mode: ProcessingMode) -> float:
    start = time.perf_counter()
    await asyncio.sleep(PROCESSING_DELAYS_MS[mode] / 1000)
    end = time.perf_counter()
    return round((end - start) * 1000, 2)
