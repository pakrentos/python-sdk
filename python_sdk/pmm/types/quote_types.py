from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal

from eth_account.datastructures import SignedMessage
from eth_account.messages import SignableMessage, encode_typed_data
from eth_account.signers.local import LocalAccount

from python_sdk.common.types import quote_types
from python_sdk.pmm.types.eip712_types import (
    ORDER_TYPE_TO_SCHEMA,
    OnchainOrderType,
)
from python_sdk.pmm.types.types import ExpiryType, QuoteToSignApiResponse


class QuoteRequest(quote_types.QuoteRequest):
    include_makers: str | None = None
    expiry_type: ExpiryType = ExpiryType.Standard
    fee: Decimal | None = None


class QuoteResponse(quote_types.QuoteResponse):
    toSign: QuoteToSignApiResponse
    onchainOrderType: OnchainOrderType
    partialFillOffset: int | None = None

    def sign_order(self, account: LocalAccount) -> str:
        """Sign order for gasless execution"""
        structured_msg = ORDER_TYPE_TO_SCHEMA[self.onchainOrderType].structured_message(
            chain_id=self.chainId, message=self.toSign.signable_message
        )
        signable_msg: SignableMessage = encode_typed_data(full_message=asdict(structured_msg))
        signed_msg: SignedMessage = account.sign_message(signable_msg)
        return "0x" + signed_msg.signature.hex()
