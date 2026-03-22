from __future__ import annotations

import time


def main() -> None:
    start = time.perf_counter()
    # placeholder for tool call benchmark integration
    elapsed = time.perf_counter() - start
    print({"benchmark": "tool_call", "seconds": round(elapsed, 6)})


if __name__ == "__main__":
    main()
