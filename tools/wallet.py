import requests
from tonsdk.utils import Address

NFT_API = 'https://tonapi.io/v2/accounts/{address}/nfts?offset=0&indirect_ownership=false'

# проверяет нфт из определенной коллекции
# "EQBU7yL9U607XSfL3daXMJwkOdjPZHU0yXTeXGE2jSCJ4sWt"
# NFT_API = 'https://tonapi.io/v2/accounts/{address}/nfts?collection={collection}&limit=1&offset=0&indirect_ownership=false'

def collections(address):
    response = requests.get(NFT_API.format(address=address))
    result = []
    hist = set()

    if response.status_code == 200:
        data = response.json()
        for item in data.get('nft_items'):
            address = item['collection']['address']

            if address in hist: continue

            name = item['collection'].get('name')
            description = item['collection'].get('description')
            address = Address(f"0:{address.split(':')[1]}").to_string(True, True, True)
            result.append({"address": address, "name": name, "description": description})
            hist.add(address)
    return result