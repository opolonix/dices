from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

from tonsdk.boc import Cell
from tonsdk.utils import Address

import requests
import base64
import binascii
import hashlib
import time
import traceback

from tools.config import config

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


def signature_verify(pubkey: bytes, message: bytes, signature: bytes) -> bool:
    try:
        verify_key = VerifyKey(pubkey)
        verify_key.verify(message, signature)
        return True
    except BadSignatureError:
        traceback.print_exc()
        return False

def convert_ton_proof_message(tp):
    try:
        sig = base64.b64decode(tp["connectItems"]["tonProof"]["proof"]["signature"])

        parsed_message = {
            'address': tp['account']['address'],
            'domain': tp["connectItems"]["tonProof"]["proof"]["domain"],
            'timestamp': tp["connectItems"]["tonProof"]["proof"]["timestamp"],
            'payload': tp["connectItems"]["tonProof"]["proof"]["payload"],
            'signature': sig,
            'state_init': tp['account']['walletStateInit']
        }
        return parsed_message
    except Exception as e:
        return None
    
def create_message(message, payload):
    try:
        wc = int(message['address'].split(":")[0]).to_bytes(4, byteorder='big', signed=True)
        ts = message['timestamp'].to_bytes(8, byteorder='little', signed=True)
        dl = message['domain']['lengthBytes'].to_bytes(4, byteorder='little', signed=True)
        

        m = bytearray("ton-proof-item-v2/".encode())
        m.extend(wc)
        m.extend(bytes.fromhex(message['address'].split(":")[1]))
        m.extend(dl)
        m.extend(message['domain']['value'].encode())
        m.extend(ts)
        m.extend(payload.encode())

        message_hash = hashlib.sha256(m).digest()

        full_mes = bytearray(b'\xff\xff')
        full_mes.extend("ton-connect".encode())
        full_mes.extend(message_hash)

        res = hashlib.sha256(full_mes).digest()

        return res
    
    except Exception as e:
        return None

def check_proof(address, ton_proof_req, payload):
    try:
        state_init = Cell.one_from_boc(base64.b64decode(ton_proof_req['state_init']))
        address_hash_part = base64.b16encode(state_init.bytes_hash()).decode('ascii').lower() 

        if address.endswith(address_hash_part):
            pub_key = state_init.refs[1].bits.array[8:][:32]

        if time.time() > ton_proof_req['timestamp'] + 300000:
            return False

        if ton_proof_req['domain']['value'] != config['server']['domain']:
            return False
        
        mes = create_message(ton_proof_req, payload)
        if not mes:
            return False
        
        return signature_verify(bytes(pub_key), mes, ton_proof_req["signature"])
    except Exception as e:
        return False


def ton_address_to_base64url(address: str) -> str:
    workchain, address_hash = address.split(":")
    
    workchain_byte = int(workchain).to_bytes(1, byteorder='big', signed=True)
    
    address_bytes = binascii.unhexlify(address_hash)
    
    full_address = workchain_byte + address_bytes

    base64url_address = base64.urlsafe_b64encode(full_address).rstrip(b'=').decode('utf-8')
    
    return base64url_address
