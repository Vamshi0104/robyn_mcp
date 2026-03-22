from __future__ import annotations

import time


def main() -> None:
    start = time.perf_counter()
    # placeholder for discovery benchmark integration
    elapsed = time.perf_counter() - start
    print({"benchmark": "discovery", "seconds": round(elapsed, 6)})


if __name__ == "__main__":
    main()
