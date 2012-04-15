from unittest import TestCase, main
from binary_tools import to_bin, to_bin_of_length, to_hex, to_0xhex, to_binary_string_of_length, to_tbcd_value, to_bin_str_from_int_string, to_tbcd_binary


class TestBinaryConversions(TestCase):

    def test_integer_to_bin(self):
        self.assertEquals(to_bin(0), '\x00')
        self.assertEquals(to_bin(5), '\x05')
        self.assertEquals(to_bin(255), '\xff')
        self.assertEquals(to_bin(256), '\x01\x00')
        self.assertEquals(to_bin(18446744073709551615L), '\xff\xff\xff\xff\xff\xff\xff\xff')

    def test_string_integer_to_bin(self):
        self.assertEquals(to_bin('0'), '\x00')
        self.assertEquals(to_bin('5'), '\x05')
        self.assertEquals(to_bin('255'), '\xff')
        self.assertEquals(to_bin('256'), '\x01\x00')
        self.assertEquals(to_bin('18446744073709551615'), '\xff\xff\xff\xff\xff\xff\xff\xff')

    def test_binary_to_bin(self):
        self.assertEquals(to_bin('0b0'), '\x00')
        self.assertEquals(to_bin('0b1'), '\x01')
        self.assertEquals(to_bin('0b1111 1111'), '\xff')
        self.assertEquals(to_bin('0b1 0000 0000'), '\x01\x00')
        self.assertEquals(to_bin('0b01 0b01 0b01'), '\x15')
        self.assertEquals(to_bin('0b11'*32), '\xff\xff\xff\xff\xff\xff\xff\xff')
        self.assertEquals(to_bin('0b11'*1024), '\xff\xff\xff\xff\xff\xff\xff\xff'*32)

    def test_hex_to_bin(self):
        self.assertEquals(to_bin('0x0'), '\x00')
        self.assertEquals(to_bin('0x5'), '\x05')
        self.assertEquals(to_bin('0xff'), '\xff')
        self.assertEquals(to_bin('0x100'), '\x01\x00')
        self.assertEquals(to_bin('0x01 0x02 0x03'), '\x01\x02\x03')

    def test_integer_larger_than_8_bytes_works(self):
        self.assertEquals(to_bin('18446744073709551616'), '\x01\x00\x00\x00\x00\x00\x00\x00\x00')

    def test_hex_larger_than_8_bytes_works(self):
        self.assertEquals(to_bin('0xcafebabe f00dd00d deadbeef'), '\xca\xfe\xba\xbe\xf0\x0d\xd0\x0d\xde\xad\xbe\xef')

    def test_to_bin_of_length(self):
        self.assertEquals(to_bin_of_length(1, 0), '\x00')
        self.assertEquals(to_bin_of_length(2, 0), '\x00\x00')
        self.assertEquals(to_bin_of_length(3, 256), '\x00\x01\x00')
        self.assertRaises(AssertionError, to_bin_of_length, 1, 256)

    def test_to_hex(self):
        self.assertEquals(to_hex('\x00'), '00')
        self.assertEquals(to_hex('\x00\x00'), '0000')
        self.assertEquals(to_hex('\x00\xff\x00'), '00ff00')
        self.assertEquals(to_hex('\xca\xfe\xba\xbe\xf0\x0d\xd0\x0d\xde\xad\xbe\xef'), 'cafebabef00dd00ddeadbeef')

    def test_to_0xhex(self):
        self.assertEquals(to_0xhex('\x00'), '0x00')
        self.assertEquals(to_0xhex('\xca\xfe\xba\xbe\xf0\x0d\xd0\x0d\xde\xad\xbe\xef'), '0xcafebabef00dd00ddeadbeef')

    def test_to_0bbinary(self):
        self.assertEquals(to_binary_string_of_length(1,'\x00'), '0b0')
        self.assertEquals(to_binary_string_of_length(3,'\x00'), '0b000')
        self.assertEquals(to_binary_string_of_length(9,'\x01\xff'), '0b111111111')
        self.assertEquals(to_binary_string_of_length(12,'\x01\xff'), '0b000111111111')
        self.assertEquals(to_binary_string_of_length(68,'\x01\x00\x00\x00\x00\x00\x00\x00\x00'), '0b0001'+('0000'*16))
        self.assertEquals(to_binary_string_of_length(2048,'\xff\xff\xff\xff\xff\xff\xff\xff'*32), '0b'+('11'*1024))

    def test_to_tbcd_value(self):
        self.assertEquals('1', to_tbcd_value(to_bin('0b00011111')))
        self.assertEquals('11', to_tbcd_value(to_bin('0b00010001')))
        self.assertEquals('2', to_tbcd_value(to_bin('0b00101111')))
        self.assertEquals('23', to_tbcd_value(to_bin('0b00110010')))
        self.assertEquals('123', to_tbcd_value(to_bin('0b0010000100111111')))

    def test_to_tbcd_binary(self):
        self.assertEquals(to_bin('0b00011111'), to_tbcd_binary('1'))
        self.assertEquals(to_bin('0b00010001'), to_tbcd_binary('11'))
        self.assertEquals(to_bin('0b00101111'), to_tbcd_binary('2'))
        self.assertEquals(to_bin('0b00110010'), to_tbcd_binary('23'))
        self.assertEquals(to_bin('0b0010000100111111'), to_tbcd_binary('123'))

    def test_to_bin_str_from_int_string(self):
        self.assertEquals('00000001', to_bin_str_from_int_string(8, '1'))
        self.assertEquals('00000010', to_bin_str_from_int_string(8, '2'))
        self.assertEquals('0001', to_bin_str_from_int_string(4, '1'))
        self.assertEquals('0010', to_bin_str_from_int_string(4, '2'))
        self.assertEquals('1111', to_bin_str_from_int_string(4, '15'))

if __name__ == "__main__":
    main()