import pytest
from eth_account.signers.local import LocalAccount

from python_sdk.common.constants import NATIVE_TOKEN
from python_sdk.common.types.order_types import OrderApiStatus, OrderStatusResponse
from python_sdk.common.types.types import Chain
from python_sdk.jam.client import JamClient
from python_sdk.jam.types.quote_types import QuoteRequest


async def send_order(jam: JamClient, quote_request: QuoteRequest) -> None:
    if quote_request.gasless:
        result = await jam.send_gasless_order(quote_request)
        assert isinstance(result, OrderStatusResponse)
        assert result.status in {OrderApiStatus.Settled, OrderApiStatus.Confirmed}
    else:
        _, _, success = await jam.send_taker_order(quote_request)
        assert success is True


# ----------------------------------- Tests ---------------------------------- #
@pytest.mark.asyncio(loop_scope="class")
class TestSolver:
    async def test_121_basic(
        self, chain: Chain, jam: JamClient, account: LocalAccount, solver: str, gasless: bool
    ) -> None:
        quote_request = QuoteRequest(
            sell_tokens=[chain.tokens["USDT"]],
            buy_tokens=[chain.tokens["WETH"]],
            sell_amounts=[(10 * 10**6)],
            taker_address=account.address,
            include_solvers=solver,
            gasless=gasless,
        )
        await send_order(jam, quote_request)

    async def test_121_sell_native(
        self, chain: Chain, jam: JamClient, account: LocalAccount, solver: str, gasless: bool
    ) -> None:
        if gasless:
            pytest.skip("Gasless order not supported for native token")
        quote_request = QuoteRequest(
            sell_tokens=[NATIVE_TOKEN],
            buy_tokens=[chain.tokens["USDT"]],
            sell_amounts=[int(0.0007 * 10**18)],
            taker_address=account.address,
            include_solvers=solver,
            gasless=gasless,
        )
        await send_order(jam, quote_request)

    async def test_121_buy_native(
        self, chain: Chain, jam: JamClient, account: LocalAccount, solver: str, gasless: bool
    ) -> None:
        quote_request = QuoteRequest(
            sell_tokens=[chain.tokens["USDT"]],
            buy_tokens=[NATIVE_TOKEN],
            sell_amounts=[int(2 * 10**18)],
            taker_address=account.address,
            include_solvers=solver,
            gasless=gasless,
        )
        await send_order(jam, quote_request)

    async def test_simple_12M(
        self, chain: Chain, jam: JamClient, account: LocalAccount, solver: str, gasless: bool
    ) -> None:
        quote_request = QuoteRequest(
            sell_tokens=[chain.tokens["USDT"]],
            buy_tokens=[chain.tokens["WETH"], chain.tokens["WBTC"], chain.tokens["USDC"]],
            sell_amounts=[int(2 * 10**6)],
            taker_address=account.address,
            include_solvers=solver,
            gasless=gasless,
            buy_tokens_ratios=[0.33, 0.33, 0.33],
        )
        await send_order(jam, quote_request)

    async def test_simple_M21(
        self, chain: Chain, jam: JamClient, account: LocalAccount, solver: str, gasless: bool
    ) -> None:
        quote_request = QuoteRequest(
            sell_tokens=[chain.tokens["USDT"], chain.tokens["USDC"]],
            buy_tokens=[chain.tokens["WETH"]],
            sell_amounts=[int(2 * 10**6), int(2 * 10**6)],
            taker_address=account.address,
            include_solvers=solver,
            gasless=gasless,
        )
        await send_order(jam, quote_request)
