import secrets

SALT_LENGTH_IN_BYTES = 16

def generate_salt() -> str:
    salt_hex = secrets.token_hex(SALT_LENGTH_IN_BYTES)
    return salt_hex

# Generate a 16-byte salt (recommended minimum)