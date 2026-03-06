from cryptography.hazmat.primitives import cmac
from cryptography.hazmat.primitives.ciphers import algorithms
from binary_handler import BinaryHandler
import os
from typing import *


class Key:
    def __init__(self, key_value: Union[str, bytes] = None, key_length: int = 32):
        """Initializes a new cryptography key. If the key_value isn't informed by the args, the key will be initialized
        with n=key_length random bytes.

        Args:
            key_value (Union[str, bytes], optional): the key value. Defaults to None.
            key_length (int, optional): _description_. the size of the key in bytes to 256.
        """
        self.key_value = key_value
        self.key_length = key_length
        self.config_key()
        pass


    def config_key(self):
        """Configures the key in to a standard bytes format.
        """
        if not self.key_value:
            self.key_value = Key.generate_random_key(key_length=self.key_length)
        elif type(self.key_value) == str:
            self.key_value = BinaryHandler.encode_bytes_from_hex_str(self.key_value, length=self.key_length)
            self.key_length = len(self.key_value)
        elif type(self.key_value) == bytes:
            self.key_value = BinaryHandler.add_padding(self.key_value, self.key_length)
        return
    

    @staticmethod
    def generate_random_key(key_length: int = 256) -> bytes:
        """Generates a safe random key with n=key_length random bytes.

        Args:
            key_length (int, optional): length of the key. Defaults to 256.

        Returns:
            bytes: the random key
        """
        return os.urandom(key_length)


    def __str__(self):
        return BinaryHandler.get_hex_str_from_bytes(self.key_value)
    

class AES_CMAC:
    TAG_SIZE = 16

    def __init__(self):
        pass

    def sign_message(message: bytes, key: Key) -> bytes:
        """Signs the given message with AES-CMAC algorithm and the given key.

        Args:
            message (bytes): the input message
            key (Key): the key for authentication

        Returns:
            bytes: the message concatenated with the AES-CMAC tag
        """
        tag = AES_CMAC.compute_tag(message=message, key=key)
        signed_message = message + tag
        return signed_message


    def compute_tag(message: bytes, key: Key) -> bytes:
        """Computes the AES-CMAC tag for the given message, with the informed key.

        Args:
            message (bytes): the input message
            key (Key): the key for authentication

        Returns:
            bytes: the AES-CMAC tag
        """
        tag = cmac.CMAC(algorithms.AES(key.key_value))
        tag.update(message)
        tag = tag.finalize()
        return tag
    

    def validate_signature(signed_message: bytes, private_key: Key) -> bool:
        """Checks if the AES-CMAC signature TAG is valid.

        Args:
            signed_message (bytes): the signed message
            private_key (Key): the private key

        Returns:
            bool: True if the signature is valid; False otherwise
        """
        authentic = False
        message = signed_message[:-AES_CMAC.TAG_SIZE]
        signature = signed_message[-AES_CMAC.TAG_SIZE:]
        check = cmac.CMAC(algorithms.AES(private_key.key_value))
        try:
            check.update(message)
            check.verify(signature)
            authentic = True
        except:
            authentic = False
        
        return authentic


def main():
    return


if __name__ == '__main__':
    main()    