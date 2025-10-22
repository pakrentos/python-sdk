from dataclasses import asdict

from eth_account.datastructures import SignedMessage
from eth_account.messages import SignableMessage, encode_typed_data
from eth_account.signers.local import LocalAccount

import python_sdk.common.types.quote_types as common_types
from python_sdk.jam.types.eip712_types import JamOrderSchema
from python_sdk.jam.types.types import JamOrderToSign


class QuoteRequest(common_types.QuoteRequest):
    include_solvers: str | None = None
    fee: int | None = None
    fee_recipient: str | None = None


class QuoteResponse(common_types.QuoteResponse):
    hooksHash: str
    toSign: JamOrderToSign
    solver: str

    def sign_order(self, account: LocalAccount) -> str:
        """Sign order for gasless execution"""
        structured_msg = JamOrderSchema.structured_message(chain_id=self.chainId, message=self.toSign.signable_message)
        signable_msg: SignableMessage = encode_typed_data(full_message=asdict(structured_msg))
        signed_msg: SignedMessage = account.sign_message(signable_msg)
        return signed_msg.signature.to_0x_hex()
