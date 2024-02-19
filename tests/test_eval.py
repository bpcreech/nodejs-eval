from asyncio import gather
from time import time

import pytest

from nodejs_eval.eval import JavaScriptError, evaluator


@pytest.mark.asyncio
async def test_basic_sync():
    async with evaluator() as e:
        result = await e.run("return 6*7;")
        assert result == 42


@pytest.mark.asyncio
async def test_exception_sync():
    async with evaluator() as e:
        with pytest.raises(JavaScriptError) as exc_info:
            await e.run("return foo;")

        assert "ReferenceError: foo is not defined" in exc_info.value.args[0]


@pytest.mark.asyncio
async def test_state_sync():
    async with evaluator() as e:
        await e.run("this.x = 6*7;")
        result = await e.run("return this.x;")
        assert result == 42


@pytest.mark.asyncio
async def test_basic_async():
    async with evaluator() as e:
        result = await e.run_async("return 6*7;")
        assert result == 42


@pytest.mark.asyncio
async def test_exception_async():
    async with evaluator() as e:
        with pytest.raises(JavaScriptError) as exc_info:
            await e.run_async("return foo;")

        assert "ReferenceError: foo is not defined" in exc_info.value.args[0]


@pytest.mark.asyncio
async def test_state_async():
    async with evaluator() as e:
        await e.run_async("this.x = 6*7;")
        result = await e.run_async("return this.x;")
        assert result == 42


@pytest.mark.asyncio
async def test_import_async():
    async with evaluator() as e:
        result = await e.run_async(
            'let os = await import("os"); return os.cpus();'
        )
        assert len(result) > 0


@pytest.mark.asyncio
async def test_concurrency_async():
    async with evaluator() as e:
        start = time()
        futures = [
            e.run_async(
                """
await new Promise(r => setTimeout(r, 2000));
return 6*7;
"""
            )
            for _ in range(10)
        ]
        results = await gather(*futures)
        assert all(r == 42 for r in results)
        # We just ran 10 evaluations of something that sleeps 2 seconds, for
        # a total of 20 seconds spent sleeping.
        # However, because we ran concurrently, it should have taken just a
        # little over 2 seconds (and not, e.g., locked up the server on each
        # request):
        assert time() - start < 3
