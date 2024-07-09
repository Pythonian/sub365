import hashlib
import hmac

import requests

API_SECRET = "C2De72a0d17b15e1dBF7008d94D8aFe9f7A0e5267ec768DAE1a5d3c7D91B88De"
API_PUBLIC_KEY = "6eac3ad4d8ca101e98284bc1188eec7f3cae2ded6a433ca3038a058a21ac01b0"


def create_hmac_signature(data, api_secret_key):
    """Create an HMAC signature for the provided data.

    Args:
        data (str): The data for which the HMAC signature is to be created.
        api_secret_key (str): The API secret key used for creating the HMAC signature.

    Returns:
        str: The hexadecimal representation of the HMAC signature.
    """
    key_bytes = bytes(api_secret_key, "latin-1")
    data_bytes = bytes(data, "latin-1")
    return hmac.new(key_bytes, data_bytes, hashlib.sha512).hexdigest()


endpoint = "https://www.coinpayments.net/api.php"
data = f"version=1&cmd=get_basic_info&key={API_PUBLIC_KEY}&format=json"
header = {
    "Content-Type": "application/x-www-form-urlencoded",
    "HMAC": create_hmac_signature(data, API_SECRET),
}
response = requests.post(endpoint, data=data, headers=header)
response.raise_for_status()
result = response.json()["result"]
print(result)
