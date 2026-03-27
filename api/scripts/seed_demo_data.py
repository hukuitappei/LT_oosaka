from __future__ import annotations

import asyncio
import sys
from pathlib import Path


API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.db.session import AsyncSessionLocal, init_db
from app.services.demo_seed import seed_demo_data


async def main() -> None:
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await seed_demo_data(session)

    print("Seeded demo data")
    print(f"email={result.email}")
    print(f"password={result.password}")
    print(f"workspace_id={result.workspace_id}")
    print(f"repositories={result.repository_count}")
    print(f"pull_requests={result.pull_request_count}")
    print(f"learning_items={result.learning_item_count}")
    print(f"digest_id={result.digest_id}")


if __name__ == "__main__":
    asyncio.run(main())
