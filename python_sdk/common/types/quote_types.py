from __future__ import annotations

from decimal import Decimal
from typing import Any

from eth_account.datastructures import SignedTransaction
from eth_account.signers.local import LocalAccount
from eth_typing import HexAddress, HexStr
from hexbytes import HexBytes
from pydantic import BaseModel, Field, model_validator
from typing_extensions import TypedDict
from web3 import AsyncWeb3
from web3.types import Nonce

from python_sdk.common.types.types import ApprovalType


# ---------------------------------------------------------------------------- #
#                                 Request Types                                #
# ---------------------------------------------------------------------------- #
class QuoteRequest(BaseModel):
    sell_tokens: list[str]
    buy_tokens: list[str]
    sell_amounts: list[int] = []
    buy_amounts: list[int] = []
    taker_address: str | None = None  # for quote requests only
    receiver_address: str | None = None
    source: str | None = "sdk"
    approval_type: ApprovalType = ApprovalType.Standard
    buy_tokens_ratios: list[float] | None = None
    sell_tokens_ratios: list[float] | None = None
    skip_validation: bool = False
    gasless: bool = True

    source_auth: str | None = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def assign_receiver_address(self) -> QuoteRequest:
        if self.receiver_address is None:
            self.receiver_address = self.taker_address
        return self

    @model_validator(mode="after")
    def check_input(self) -> QuoteRequest:
        if len(self.buy_tokens) > 1 and self.buy_tokens_ratios is None:
            raise ValueError("buy_tokens_ratios is required when buy_tokens has multiple tokens")
        if self.sell_amounts and self.buy_amounts:
            raise ValueError("sell_amounts and buy_amounts cannot be both set")
        if not self.sell_amounts and not self.buy_amounts:
            raise ValueError("Either sell_amounts or buy_amounts must be set")
        return self

    def to_params(self) -> dict[str, Any]:
        if not self.taker_address:
            self.taker_address = "0x0000000000000000000000000000000000000001"
        params = self.model_dump(exclude_none=True, exclude_unset=True, mode="json")
        params["sell_tokens"] = ",".join(self.sell_tokens)
        params["buy_tokens"] = ",".join(self.buy_tokens)
        if self.sell_amounts:
            params["sell_amounts"] = ",".join(str(amt) for amt in self.sell_amounts)
        if self.buy_amounts:
            params["buy_amounts"] = ",".join(str(amt) for amt in self.buy_amounts)
        if self.buy_tokens_ratios:
            params["buy_tokens_ratios"] = ",".join(str(ratio) for ratio in self.buy_tokens_ratios)
        if self.sell_tokens_ratios:
            params["sell_tokens_ratios"] = ",".join(str(ratio) for ratio in self.sell_tokens_ratios)
        params["gasless"] = str(self.gasless).lower()
        params["skip_validation"] = str(self.skip_validation).lower()
        return params


# ---------------------------------------------------------------------------- #
#                                Response Types                                #
# ---------------------------------------------------------------------------- #
class ResponseToken(BaseModel):
    amount: str
    decimals: int
    symbol: str
    priceUsd: float | None = None

    @property
    def amount_decimal(self) -> Decimal:
        return Decimal(int(self.amount)) / Decimal(10**self.decimals)


class ResponseSellToken(ResponseToken):
    price: float | None = None
    priceBeforeFee: float | None = None


class ResponseBuyToken(ResponseToken):
    price: float | None = None
    priceBeforeFee: float | None = None
    amountBeforeFee: str | None = None

    @property
    def amount_before_fee_decimal(self) -> Decimal:
        return Decimal(int(self.amountBeforeFee)) / Decimal(10**self.decimals) if self.amountBeforeFee else Decimal(0)


ResponseSellTokens = dict[str, ResponseSellToken]
ResponseBuyTokens = dict[str, ResponseBuyToken]


class GasFeeResponse(BaseModel):
    native: str
    usd: float | None = None


TxData = TypedDict(
    "TxData",
    {
        "from": str | None,
        "to": str,
        "value": str,
        "data": HexStr,
        "gas": int | None,
        "gasPrice": int | None,
        "nonce": Nonce | None,
    },
    total=False,
)


class QuoteResponse(BaseModel):
    type: str
    status: str
    quoteId: str
    chainId: int
    approvalType: ApprovalType
    nativeToken: str
    taker: str
    receiver: str
    expiry: int
    gasFee: GasFeeResponse
    buyTokens: ResponseBuyTokens
    sellTokens: ResponseSellTokens
    settlementAddress: str
    approvalTarget: str
    requiredSignatures: list[str]
    partnerFee: dict[HexAddress, str] | None = None
    protocolFee: dict[HexAddress, str] | None = None
    tx: TxData | None = None

    @property
    def sell_usd_amount(self) -> float:
        return sum(
            sell_token.priceUsd * float(sell_token.amount_decimal)
            for sell_token in self.sellTokens.values()
            if sell_token.priceUsd
        )

    @property
    def buy_usd_amount(self) -> float:
        return sum(
            buy_token.priceUsd * float(buy_token.amount_decimal)
            for buy_token in self.buyTokens.values()
            if buy_token.priceUsd
        )

    async def sign_transaction(self, web3: AsyncWeb3, account: LocalAccount) -> HexBytes:
        """Sign transaction for self execution"""
        if not self.tx:
            raise ValueError("No tx data found, ensure `gasless`=`False` when requesting quote.")
        self.tx["nonce"] = await web3.eth.get_transaction_count(account.address)
        self.tx["gasPrice"] = int((await web3.eth.gas_price) * 1.5)
        assert self.tx["gas"]
        self.tx["gas"] = int(self.tx["gas"] * 4)
        signed_tx: SignedTransaction = account.sign_transaction(self.tx)
        return signed_tx.raw_transaction
