from hmac import new as hmac_new
from hashlib import sha256
from urllib.parse import unquote


def validate(init_data: str, token: str, c_str="WebAppData") -> None | dict[str, str]:
    """Validates init data from webapp to check if a method was received from Telegram
    Args:
        init_data (str): init_data string received from webapp
        token (str): token of bot that initiated webapp
        c_str (str, optional): Constant string for hash function, you shouldn't change that. Defaults to "WebAppData".
    Returns:
        None | dict[str, str]: object with data deserialized (user is not deserialized, you can do it by own, it's simple json) on successful validation, otherwise None
    """

    hash_string = ""

    init_data_dict = dict()

    for chunk in init_data.split("&"):
        if chunk == "": return None
        [key, value] = chunk.split("=", 1)
        if key == "hash":
            hash_string = value
            continue
        init_data_dict[key] = unquote(value)

    if hash_string == "":
        return None

    init_data = "\n".join(
        [
            f"{key}={init_data_dict[key]}" 
            for key in sorted(init_data_dict.keys())
        ]
    )

    secret_key = hmac_new(c_str.encode(), token.encode(), sha256).digest()
    data_check = hmac_new(secret_key, init_data.encode(), sha256)

    if data_check.hexdigest() != hash_string:
        return None

    return init_data_dict