import asyncio
from typing import Any

import aiohttp
from eth_account.signers.local import LocalAccount

from python_sdk.common.funcs import _get_order_status, _post_order, send_request
from python_sdk.common.types.order_types import (
    OrderApiStatus,
    OrderRequest,
    OrderResponse,
    OrderStatusRequest,
    OrderStatusResponse,
)
from python_sdk.common.types.types import Chain, Env
from python_sdk.common.utils.logger import Logger
from python_sdk.jam.constants import ORDER_STATUS_URL, ORDER_URL, QUOTE_URL
from python_sdk.jam.types.quote_types import QuoteRequest, QuoteResponse

LOGGER = Logger(__name__)


async def get_quote(
    env: Env,
    chain: Chain,
    quote_request: QuoteRequest,
    headers: dict[str, Any] | None,
    auth: aiohttp.BasicAuth | None = None,
) -> QuoteResponse:
    source_auth = {"source-auth": quote_request.source_auth} if quote_request.source_auth else {}
    headers = (headers or {}) | source_auth
    result = await send_request(
        env=env,
        method="get",
        headers=headers,
        auth=auth,
        url=QUOTE_URL.format(chain=chain.name),
        params=quote_request.to_params(),
    )
    return QuoteResponse.model_validate(result)


async def post_order(
    env: Env, chain: Chain, order_request: OrderRequest, headers: dict[str, Any] | None, auth: aiohttp.BasicAuth | None
) -> OrderResponse:
    return await _post_order(
        env=env, order_url=ORDER_URL, chain=chain, order_request=order_request, headers=headers, auth=auth
    )


async def get_order_status(
    env: Env,
    chain: Chain,
    order_status_request: OrderStatusRequest,
    headers: dict[str, Any] | None,
    auth: aiohttp.BasicAuth | None,
) -> OrderStatusResponse:
    return await _get_order_status(
        env=env,
        order_status_url=ORDER_STATUS_URL,
        chain=chain,
        order_status_request=order_status_request,
        headers=headers,
        auth=auth,
    )


async def send_gasless_order(
    env: Env,
    chain: Chain,
    account: LocalAccount,
    quote: QuoteResponse,
    headers: dict[str, Any] | None,
    auth: aiohttp.BasicAuth | None,
    sign_scheme: str = "EIP712",
) -> OrderStatusResponse:
    signature: str = quote.sign_order(account=account)
    order_request = OrderRequest(
        quote_id=quote.quoteId,
        signature=signature,
        sign_scheme=sign_scheme,
    )
    result = await post_order(
        env=env, chain=chain, order_request=order_request, headers=headers, auth=auth
    )
    LOGGER.info(f"Order sent. Result: {result}")

    retries: int = 1
    success: bool = False
    while True:
        order_status_response = await get_order_status(
            env=env,
            chain=chain,
            order_status_request=OrderStatusRequest(quote_id=quote.quoteId),
            headers=headers,
            auth=auth,
        )
        status = OrderApiStatus(order_status_response.status)
        retries += 1
        if status in {OrderApiStatus.Settled, OrderApiStatus.Confirmed}:
            success = True
            break
        if retries > 30:
            break
        await asyncio.sleep(1)

    if success:
        LOGGER.info(f"Order completed: {order_status_response}")
        assert order_status_response.txHash
        LOGGER.info(f"Order completed: {chain.tx_link(order_status_response.txHash)}")
    else:
        LOGGER.warning("Could not confirm order status")
    return order_status_response
