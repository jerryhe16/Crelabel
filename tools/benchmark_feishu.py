from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from feishu_client import load_feishu_data


URL = "https://ncn5zs910x3g.feishu.cn/wiki/CCOzwaWc0iNBjNkUpdLcKeOInie?table=tblm4wsfEdEUU6t6&view=vewcqkgMpi"


for run in (1, 2):
    started = time.perf_counter()
    data = load_feishu_data(
        URL,
        progress=lambda message, number=run: print(f"RUN{number} {message}", flush=True),
        force_refresh=True,
    )
    elapsed = time.perf_counter() - started
    records = data["records"]
    link_count = sum(bool(item.get("record_share_link")) for item in records)
    print(f"RUN{run}_SECONDS={elapsed:.3f} RECORDS={len(records)} LINKS={link_count}", flush=True)
