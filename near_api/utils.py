import time
from requests import ReadTimeout
from typing import Union
from base64 import b64decode

from .providers import JsonProvider, JsonProviderError
from .signer import KeyPair, Signer
from .account import Account, TransactionError, ViewFunctionError

DEFAULT_BACKOFF_MULTIPLIER = 2
DEFAULT_MAX_RETRIES = 10
DEFAULT_WAIT_TIME_MS = 1000

def exponential_backoff(do_blockchain_thing, wait_time_ms: int = DEFAULT_WAIT_TIME_MS, max_retries: int = DEFAULT_MAX_RETRIES, backoff_multiplier: int = DEFAULT_BACKOFF_MULTIPLIER):
    for n in range(max_retries):
        try:
            return do_blockchain_thing()
        except ReadTimeout as e:
            print(f"TIMEOUT #{n}: RETRYING NEAR CALL ({e})")
        except (TransactionError, ViewFunctionError, JsonProviderError) as e:
            if "NotEnoughBalance" in str(e):
                raise Exception("Calling account does not have required funds for action.")
            elif "Expired" in str(e):
                # handles the following occasional strange error: {'name': 'HANDLER_ERROR', 'cause': {'info': {}, 'name': 'INVALID_TRANSACTION'}, 'code': -32000, 'message': 'Server error', 'data': {'TxExecutionError': {'InvalidTxError': 'Expired'}}}
                print(f"EXPIRED TRANSACTION #{n}: RETRYING NEAR CALL ({e})")
            else:
                error_string = f"ERROR GETTING NEAR RESULT: {e}"
                raise Exception(error_string)
        time.sleep(wait_time_ms / 1000)  # convert to seconds
        wait_time_ms *= backoff_multiplier
        backoff_multiplier += 1
    # no successful result
    raise Exception("MAX RETRIES EXCEEDED")

def decode_near_success_value(near_tx_result) -> Union[str, None]:
    if "status" in near_tx_result:
        return b64decode(near_tx_result["status"]["SuccessValue"]).decode("utf-8")
    return None