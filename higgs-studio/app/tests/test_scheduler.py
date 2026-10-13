import asyncio

from studio.scheduler import CUSTOMER, DEV, Scheduler


def test_customer_priority_and_dev_cap():
    async def main():
        s = Scheduler(max_inflight=2, dev_max_inflight=1)
        order = []

        async def job(name, prio, hold):
            async with s.slot(prio):
                order.append(name)
                await asyncio.sleep(hold)
        tasks = [asyncio.create_task(job(f"d{i}", DEV, 0.05)) for i in range(3)]
        await asyncio.sleep(0.01)
        assert s.inflight[DEV] == 1  # the dev cap keeps a slot free for customers
        tasks.append(asyncio.create_task(job("c0", CUSTOMER, 0.01)))
        await asyncio.sleep(0.02)
        assert "c0" in order[:2]
        await asyncio.gather(*tasks)
        assert sorted(order) == ["c0", "d0", "d1", "d2"]
    asyncio.run(main())


def test_exclusive_runs_alone():
    async def main():
        s = Scheduler(max_inflight=4, dev_max_inflight=4)
        seen = []

        async def job(prio, excl, hold):
            async with s.slot(prio, excl):
                seen.append((excl, s.total_inflight))
                await asyncio.sleep(hold)
        t = [asyncio.create_task(job(DEV, False, 0.05)) for _ in range(3)]
        await asyncio.sleep(0.01)
        t.append(asyncio.create_task(job(CUSTOMER, True, 0.02)))
        await asyncio.sleep(0.005)
        t += [asyncio.create_task(job(DEV, False, 0.01)) for _ in range(2)]
        await asyncio.gather(*t)
        assert (True, 1) in seen  # the exclusive request ran with nothing else in flight
    asyncio.run(main())
