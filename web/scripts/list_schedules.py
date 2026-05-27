import asyncio, os, sys
sys.path.insert(0, "/usr/src/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "reNgine.settings")
import django; django.setup()
from temporalio.client import Client

async def main():
    client = await Client.connect("temporal:7233", namespace="default")
    # list_schedules is async and returns ScheduleAsyncIterator
    iterator = await client.list_schedules()
    count = 0
    async for s in iterator:
        count += 1
        print(f"SCHEDULE: {s.id}")
    print(f"Total schedules: {count}")

asyncio.run(main())
