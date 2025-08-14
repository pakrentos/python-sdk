import aiohttp
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr
from hexbytes import HexBytes
from web3 import AsyncHTTPProvider, AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware

from python_sdk.common.funcs import send_taker_order
from python_sdk.common.types.order_types import (
    OrderRequest,
    OrderResponse,
    OrderStatusRequest,
    OrderStatusResponse,
)
from python_sdk.common.types.types import Chain, Env
from python_sdk.common.utils.logger import Logger
from python_sdk.common.utils.utils import approve_token, revoke_token
from python_sdk.jam.constants import JAM_BALANCE_MANAGER
from python_sdk.jam.funcs import get_order_status, get_quote, post_order, send_gasless_order
from python_sdk.jam.types.quote_types import QuoteRequest, QuoteResponse

LOGGER = Logger(__name__)


class JamClient:
    def __init__(
        self,
        env: Env,
        chain: Chain,
        private_key: str | None,
        rpc_url: str | None = None,
        source_auth: str | None = None,
        auth: aiohttp.BasicAuth | None = None,
    ):
        self.__chain = chain
        self.__env = env
        self.__headers = {"source-auth": source_auth} if source_auth else None
        self.__auth = auth
        # ----------------------------------- Web3 ----------------------------------- #
        self.web3 = AsyncWeb3(
            AsyncHTTPProvider(rpc_url if rpc_url else chain.public_rpc, request_kwargs={"timeout": 6})
        )
        self.web3.middleware_onion.inject(ExtraDataToPOAMiddleware, "poa", layer=0)
        # ------------------------------- Local Account ------------------------------ #
        self.account: LocalAccount | None = Account.from_key(private_key) if private_key else None

    async def get_quote(self, quote_request: QuoteRequest) -> QuoteResponse:
        if not quote_request.taker_address and self.account:
            quote_request.taker_address = self.account.address
        if not quote_request.receiver_address:
            quote_request.receiver_address = quote_request.taker_address
        return await get_quote(
            env=self.__env, headers=self.__headers, auth=self.__auth, chain=self.__chain, quote_request=quote_request
        )

    async def post_order(self, order_request: OrderRequest) -> OrderResponse:
        return await post_order(
            env=self.__env, headers=self.__headers, auth=self.__auth, chain=self.__chain, order_request=order_request
        )

    async def get_order_status(self, quote_id: str) -> OrderStatusResponse:
        return await get_order_status(
            env=self.__env,
            headers=self.__headers,
            auth=self.__auth,
            chain=self.__chain,
            order_status_request=OrderStatusRequest(quote_id=quote_id),
        )

    async def send_gasless_order(self, request: QuoteRequest) -> tuple[QuoteResponse, OrderStatusResponse]:
        assert self.account, "Account is required for order"
        quote: QuoteResponse = await self.get_quote(request)
        order_status_response: OrderStatusResponse = await send_gasless_order(
            env=self.__env,
            auth=self.__auth,
            headers=self.__headers,
            chain=self.__chain,
            account=self.account,
            quote=quote,
        )
        return quote, order_status_response

    async def send_taker_order(self, request: QuoteRequest) -> tuple[QuoteResponse, HexStr, bool]:
        assert self.account, "Account is required for order"
        quote: QuoteResponse = await self.get_quote(request)
        tx_hash, success = await send_taker_order(chain=self.__chain, web3=self.web3, account=self.account, quote=quote)
        return quote, tx_hash, success

    async def approve_token(self, token_address: str, amount: int) -> HexBytes:
        assert self.account, "Account is required for token approval"
        return await approve_token(
            self.web3, self.account, token_address, amount, spender=JAM_BALANCE_MANAGER[self.__chain.id]
        )

    async def revoke_token(self, token_address: str) -> HexBytes:
        assert self.account, "Account is required for token approval"
        return await revoke_token(self.web3, self.account, token_address, spender=JAM_BALANCE_MANAGER[self.__chain.id])
