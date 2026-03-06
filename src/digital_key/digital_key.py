from datetime import datetime
from .binary_handler.binary_handler import BinaryHandler
from .auth.auth import Key, AES_CMAC
from typing import *

class DigitalKey:
    def __init__(self, user_id: int, room_id: int, timestamp: datetime, expiration: datetime, private_key: Key):
        self.user_id = user_id
        self.room_id = room_id
        self.timestamp = timestamp
        self.expiration = expiration
        self.payload = None
        if private_key: self.config_digital_key(private_key)
        pass


    def config_digital_key(self, private_key: Key):
        """Initializes the digital key.

        Args:
            private_key (Key): the private key used in the AES-CMAC authentication
        """
        self.payload = DigitalKey.get_digital_key_payload(
            self.user_id,
            self.room_id,
            self.timestamp,
            self.expiration,
            private_key
        )
        return
    
    
    def check_validity(self, private_key: Key) -> bool:
        """Checks the validity of a digital key payload, by validating its signature with AES-CMAC algorithm and the given private key. 

        Args:
            private_key (Key): The private key used for AES-CMAC authentication

        Returns:
            bool: True if the digital key is valid, False otherwise
        """
        validity = DigitalKey.check_digital_key_validity(self.payload, private_key)
        return validity
    
    
    @staticmethod
    def check_digital_key_validity(payload: bytes, private_key: Key) -> bool:
        """Checks the validity of a digital key payload, by validating its signature with AES-CMAC algorithm and the given private key.

        Args:
            payload (bytes): The digital key payload to validate
            private_key (Key): The private key used for AES-CMAC authentication

        Returns:
            bool: True if the digital key is valid, False otherwise
        
        Example:
            >>> digital_key = BinaryHandler.encode_bytes_from_hex_str('00 00 00 00 00 00 00 0d 00 00 00 00 00 00 00 0c 00 00 00 00 69 aa d7 25 00 00 00 00 69 aa d7 25 84 c6 a5 fd e6 de 3d f5 5a cd f4 dd f4 ee 0a b8')
            >>> print(DigitalKey.check_digital_key_validity(digital_key, private_key=private_key))
            True
        """
        validity = AES_CMAC.validate_signature(payload, private_key)
        return validity
    

    @staticmethod
    def get_digital_key_payload(user_id: int, room_id: int, timestamp: datetime, expiration: datetime, private_key: Key) -> bytes:
        """Generates a digital key bytes payload, with the given data.

        Args:
            user_id (int): the user ID
            room_id (int): the room ID
            timestamp (datetime): the time at which the digital key is generated
            expiration (datetime): the expiration of the digital key
            private_key (Key): the private key used in the AES-CMAC authentication

        Returns:
            bytes: the digital key payload
        
        Example:
            >>> private_key = Key('38 f9 de f2 cf 55 06 1d ad a9 e0 c5 6d de 09 b4 48 50 d4 80 d8 c3 89 3f bd 37 38 e2 e7 98 8c b9')
            >>> digital_key = DigitalKey(
            ...     user_id=13,
            ...     room_id=12,
            ...     timestamp=datetime.now(),
            ...     expiration=datetime.now(),
            ...     private_key=private_key
            ... )
            >>> digital_key.check_digital_key_validity(private_key)
            True
        """
        encoded_user_id = BinaryHandler.encode_int(input_int=user_id, length=8, byte_order='big')
        encoded_room_id = BinaryHandler.encode_int(input_int=room_id, length=8, byte_order='big')
        encoded_timestamp = BinaryHandler.encode_timestamp(time=timestamp, length=8, byte_order='big')
        encoded_expiration = BinaryHandler.encode_timestamp(time=expiration, length=8, byte_order='big')
        payload = encoded_user_id + encoded_room_id + encoded_timestamp + encoded_expiration
        signed_payload = AES_CMAC.sign_message(message=payload, key=private_key)
        return signed_payload
    

    def __str__(self):
        """Returns a string representation of the digital key.

        Returns:
            str: A string containing the digital key's attributes.
        """
        digital_key_str = ''
        digital_key_str += f'user_id: {self.user_id}\n'
        digital_key_str += f'room_id: {self.room_id}\n'
        digital_key_str += f'timestamp: {self.timestamp}\n'
        digital_key_str += f'expiration: {self.expiration}\n'
        digital_key_str += f'payload:\n{BinaryHandler.get_hex_str_from_bytes(self.payload, bytes_per_line = 8)}'
        return digital_key_str


def health_check():
    return 'digital_key module ok'


def main():
    return


if __name__ == '__main__':
    main()