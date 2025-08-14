import pytest
from eth_account.signers.local import LocalAccount

from python_sdk.common.constants import NATIVE_TOKEN
from python_sdk.common.types.order_types import OrderApiStatus, OrderStatusResponse
from python_sdk.common.types.types import Chain
from python_sdk.pmm.client import PMMClient
from python_sdk.pmm.types.quote_types import QuoteRequest


async def send_order(pmm: PMMClient, quote_request: QuoteRequest) -> None:
    if quote_request.gasless:
        result = await pmm.send_gasless_order(quote_request)
        assert isinstance(result, OrderStatusResponse)
        assert result.status in {OrderApiStatus.Settled, OrderApiStatus.Confirmed}
    else:
        _, _, success = await pmm.send_taker_order(quote_request)
        assert success is True


# ----------------------------------- Tests ---------------------------------- #
@pytest.mark.asyncio(loop_scope="class")
class Testmaker:
    async def test_121(self, chain: Chain, pmm: PMMClient, account: LocalAccount, maker: str, gasless: bool) -> None:
        quote_request = QuoteRequest(
            sell_tokens=[chain.tokens["USDT"]],
            buy_tokens=[chain.tokens["WETH"]],
            sell_amounts=[int(2 * 10**6)],
            taker_address=account.address,
            include_makers=maker,
            gasless=gasless,
        )
        await send_order(pmm, quote_request)

    async def test_121_sell_native(
        self, chain: Chain, pmm: PMMClient, account: LocalAccount, maker: str, gasless: bool
    ) -> None:
        if gasless:
            pytest.skip("Gasless order not supported for native token")
        quote_request = QuoteRequest(
            sell_tokens=[NATIVE_TOKEN],
            buy_tokens=[chain.tokens["USDT"]],
            sell_amounts=[int(0.0007 * 10**18)],
            taker_address=account.address,
            include_makers=maker,
            gasless=gasless,
        )
        await send_order(pmm, quote_request)

    async def test_121_buy_native(
        self, chain: Chain, pmm: PMMClient, account: LocalAccount, maker: str, gasless: bool
    ) -> None:
        quote_request = QuoteRequest(
            sell_tokens=[chain.tokens["USDT"]],
            buy_tokens=[NATIVE_TOKEN],
            sell_amounts=[int(2 * 10**6)],
            taker_address=account.address,
            include_makers=maker,
            gasless=gasless,
        )
        await send_order(pmm, quote_request)

    async def test_simple_12M(
        self, chain: Chain, pmm: PMMClient, account: LocalAccount, maker: str, gasless: bool
    ) -> None:
        quote_request = QuoteRequest(
            sell_tokens=[chain.tokens["USDT"]],
            buy_tokens=[chain.tokens["WETH"], chain.tokens["WBTC"], chain.tokens["USDC"]],
            sell_amounts=[int(0.3 * 10**6)],
            taker_address=account.address,
            include_makers=maker,
            gasless=gasless,
            buy_tokens_ratios=[0.33, 0.33, 0.33],
        )
        await send_order(pmm, quote_request)

    async def test_simple_M21(
        self, chain: Chain, pmm: PMMClient, account: LocalAccount, maker: str, gasless: bool
    ) -> None:
        quote_request = QuoteRequest(
            sell_tokens=[chain.tokens["USDT"], chain.tokens["USDC"]],
            buy_tokens=[chain.tokens["WETH"]],
            sell_amounts=[int(2 * 10**6), int(2 * 10**6)],
            taker_address=account.address,
            include_makers=maker,
            gasless=gasless,
        )
        await send_order(pmm, quote_request)
