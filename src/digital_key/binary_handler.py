from typing import *
from datetime import datetime

class BinaryHandler:
    def encode_int(input_int: int, length: int = 8, byte_order: Literal['little', 'big'] = 'big') -> bytes:
        """Encodes a given input int in to bytes, as an integer of 64 bits by default.

        Args:
            input_int (int): the input int
            length (int, optional): the length of the bytes array. Defaults to 4.
            byte_order (Literal['little', 'big'], optional): the endianness of the array of bytes. 
            Defaults to 'big'.
            
        Returns:
            bytes: the encoded int
        
        Examples:
            >>> x = BinaryHandler.encode_int(255)
            >>> BinaryHandler.print_bytes(x)
            '00 00 00 00 00 00 00 ff'
        """
        encoded_int = input_int.to_bytes(
            length=length,
            byteorder=byte_order,
            signed=False
        )
        return encoded_int
    

    def encode_timestamp(
        time: datetime,
        length: int = 8,
        byte_order: Literal['little', 'big'] = 'big'
    ) -> bytes:
        """Encodes a given timestamp in to bytes, representing the POSIX timestamp as an 64 bits integer,
        by default.

        Args:
            time (datetime): the input timestamp
            length (int, optional): the length of the bytes array. Defaults to 8.
            byte_order (Literal['little', 'big'], optional): the endianness of the array of bytes. 
            Defaults to 'big'.

        Returns:
            bytes: the encoded timestamp as POSIX
        
        Examples:
            >>> my_datetime = datetime(year=2026, month=3, day=2, hour=21, minute=19, second=30, microsecond=69)
            >>> encoded_datetime = BinaryHandler.encode_time(my_datetime)
            >>> BinaryHandler.print_bytes(encoded_datetime)
            '00 00 00 00 69 a6 29 12' 
        """
        encoded_time = time.timestamp()
        encoded_time = int(encoded_time)
        encoded_time = encoded_time.to_bytes(
            length=length,
            byteorder=byte_order,
            signed=False
        )
        return encoded_time
    
    
    def encode_bytes_from_hex_str(input_hex_str: str, length: int = 32, byte_order: Literal['little', 'big'] = 'big') -> bytes:
        """Encodes the given str, interpreted as a hexadecimal string, as an array of bytes, with
        a fixed length of 20, by default. The not empty space will be filled padding zeros.

        Args:
            input_hex_str (str): the input hex string
            length (int, optional): the array of bytes fixed length. Defaults to 32.
            byte_order (Literal['little', 'big'], optional): the endianness of the array of bytes. Defaults to 'big'.

        Returns:
            bytes: the bytes of your string
        """
        input_hex_str_bytes = bytes.fromhex(input_hex_str)
        padding_size = length - len(input_hex_str_bytes)
        if padding_size > 0:
            padding_bytes = padding_size * b'\x00'
            input_hex_str_bytes = padding_bytes + input_hex_str_bytes
        return input_hex_str_bytes
    

    def get_hex_str_from_bytes(input_bytes: bytes) -> str:
        """From a given array of bytes, generates a hexadecimal str. For example,
        if the input is b'\x9c\xd0\xdf\xbf\xf5Pns\t\xb7%\xe1+8\xe9\x02\x1f\x9b\xc6\x8d', then the
        hex_str will be '9c d0 df bf f5 50 6e 73 09 b7 25 e1 2b 38 e9 02 1f 9b c6 8d'.

        Args:
            key (bytes): the key in bytes.

        Returns:
            str: the hex str.
        
        Examples:
            >>> hex_str = get_hex_str(b'\x9c\xd0\xdf\xbf\xf5Pns\t\xb7%\xe1+8\xe9\x02\x1f\x9b\xc6\x8d')
            >>> print(hex_str)
            '9c d0 df bf f5 50 6e 73 09 b7 25 e1 2b 38 e9 02 1f 9b c6 8d'
        """
        hex_str = ''.join(f'{byte:02x} ' for byte in input_bytes)
        return hex_str
    

    def add_padding(input_bytes: bytes, length: int = 256) -> bytes:
        """Adds padding to the bytes input.

        Args:
            input_bytes (bytes): the input bytes
            length (int, optional): the length of the final binary string. Defaults to 256.

        Returns:
            bytes: the binary data with the added padding
        """
        padding_size = length - len(input_bytes)
        if padding_size > 0:
            padding_bytes = padding_size * b'\x00'
            input_bytes = padding_bytes + input_bytes
        return input_bytes
    

    def print_bytes(input_bytes: bytes):
        """Prints the content of an array of bytes in hex.

        Args:
            input_bytes (bytes): data in bytes.
        
        Examples:
            >>> hex_str = b'\x9c\xd0\xdf\xbf\xf5Pns\t\xb7%\xe1+8\xe9\x02\x1f\x9b\xc6\x8d'
            >>> BinaryHandler.print_bytes(hex_str)
            '9c d0 df bf f5 50 6e 73 09 b7 25 e1 2b 38 e9 02 1f 9b c6 8d'
        """
        print(BinaryHandler.get_hex_str_from_bytes(input_bytes))
        return


def main():
    return


if __name__ == '__main__':
    main()