import hashlib

def secure_hash(input: str) -> str:
    hash_object = hashlib.sha256(input.encode('utf-8'))
    hex_dig = hash_object.hexdigest()
    return hex_dig