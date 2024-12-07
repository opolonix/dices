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


"""Старый код на запрос аватарки пользователя"""
    # url = f"https://api.telegram.org/bot{cp['bot']['token']}/getUserProfilePhotos"
    # response = requests.get(url, params={"user_id": client.telegram_id, "limit": 1})

    # if response.status_code == 200:
    #     user_info = response.json()
    #     if user_info['ok']:
    #         file_data = user_info['result']['photos'][0][0] if user_info['result']['total_count'] != 0 else None
    #         if not file_data:
    #             client.avatar = None
    #             session.commit()
    #         elif len(glob.glob(os.path.join("images", file_data['file_unique_id']) + ".*")) == 0:

    #             answer = requests.get(f"https://api.telegram.org/bot{cp['bot']['token']}/getFile?file_id={file_data['file_id']}")
    #             content = requests.get(f"https://api.telegram.org/file/bot{cp['bot']['token']}/{answer.json()['result']['file_path']}")

    #             file_name = answer.json()['result']['file_path'].split(".")[-1]
    #             avatar_url = f"{file_data['file_unique_id']}.{file_name}"

    #             with open(os.path.join("images", avatar_url), "wb+") as f:
    #                 f.write(content.content)

    #             client.avatar = avatar_url
    #             session.commit()