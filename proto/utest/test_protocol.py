import socket
import unittest
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), '..','src'))
from Message import Field
from Protocol import Protocol, Length, UInt, PDU, MessageTemplate, MessageStream, Char, Struct, List
from binary_conversions import to_bin_of_length, to_bin, to_hex


def _get_pair():
    struct = Struct('Pair', 'pair')
    struct.add(UInt(2, 'first', 1))
    struct.add(UInt(2, 'second', 2))
    return struct

def _get_recursive_struct():
    str_str = Struct('StructStruct', 'str_str')
    inner = _get_pair()
    str_str.add(inner)
    return str_str


class TestProtocol(unittest.TestCase):

    def setUp(self):
        self._protocol = Protocol('Test')

    def test_header_length(self):
        self._protocol.add(UInt(1, 'name1', None))
        self.assertEquals(self._protocol.header_length(), 1)

    def test_header_length_with_pdu(self):
        self._protocol.add(UInt(1, 'name1', None))
        self._protocol.add(UInt(2, 'name2', 5))
        self._protocol.add(UInt(2, 'length', None))
        self._protocol.add(PDU('length'))
        self._protocol.add(UInt(1, 'checksum', None))
        self.assertEquals(self._protocol.header_length(), 5)

    def test_verify_undefined_length(self):
        self._protocol.add(UInt(1, 'name1', None))
        self._protocol.add(UInt(2, 'name2', 5))
        self.assertRaises(Exception, self._protocol.add, PDU('length'))

    def test_verify_calculated_length(self):
        self._protocol.add(UInt(1, 'name1', 1))
        self._protocol.add(UInt(2, 'length', None))
        self._protocol.add(PDU('length-8'))
        self.assertEquals(self._protocol.header_length(), 3)


class _MockStream(object):

    def __init__(self, data):
        self.data = data

    def read(self, length, timeout=None):
        if length > len(self.data):
            if timeout:
                raise socket.timeout('timeout')
            else:
                raise AssertionError('No timeout, but out of data.')
        result = self.data[:length]
        self.data = self.data[length:]
        return result


class TestProtocolMessageReceiving(unittest.TestCase):

    def setUp(self):
        self._protocol = Protocol('Test')
        self._protocol.add(UInt(1, 'id', 1))
        self._protocol.add(UInt(2, 'length', None))
        self._protocol.add(PDU('length-2'))

    def test_read_header_and_pdu(self):
        stream = _MockStream(to_bin('0xff0004cafe'))
        header, data = self._protocol.read(stream)
        self.assertEquals(header.id.hex, '0xff')
        self.assertEquals(data, '\xca\xfe')


class TestMessageStream(unittest.TestCase):

    def setUp(self):
        self._protocol = Protocol('Test')
        self._protocol.add(UInt(1, 'id', 1))
        self._protocol.add(UInt(2, 'length', None))
        self._protocol.add(PDU('length-2'))
        self._msg = MessageTemplate('FooRequest', self._protocol, {'id':'0xaa'})
        self._msg.add(UInt(1, 'field_1', None))
        self._msg.add(UInt(1, 'field_2', None))

    def test_get_message(self):
        byte_stream = _MockStream(to_bin('0xff0004cafe aa0004dead'))
        msg_stream = MessageStream(byte_stream, self._protocol)
        msg = msg_stream.get(self._msg)
        self.assertEquals(msg.field_1.hex, '0xde')

    def test_get_message_from_buffer(self):
        byte_stream = _MockStream(to_bin('0xff0004cafe aa0004dead'))
        msg_stream = MessageStream(byte_stream, self._protocol)
        _ = msg_stream.get(self._msg)
        self._msg.header_parameters = {}
        msg = msg_stream.get(self._msg)
        self.assertEquals(msg.field_1.hex, '0xca')

    def test_timeout_goes_to_stream(self):
        byte_stream = _MockStream(to_bin('0xff0004cafe aa0004dead'))
        msg_stream = MessageStream(byte_stream, self._protocol)
        self._msg.header_parameters = {'id':'0x00'}
        self.assertRaises(socket.timeout, msg_stream.get, self._msg, timeout=1)


class TestMessageTemplate(unittest.TestCase):

    def setUp(self):
        self._protocol = Protocol('TestProtocol')
        self._protocol.add(UInt(2, 'msgId', 5))
        self._protocol.add(UInt(2, 'length', None))
        self._protocol.add(PDU('length-4'))
        self.tmp = MessageTemplate('FooRequest', self._protocol, {})
        self.tmp.add(UInt(2, 'field_1', 1))
        self.tmp.add(UInt(2, 'field_2', 2))

    def test_create_template(self):
        self.assertEquals(len(self.tmp._fields), 2)

    def test_encode_template(self):
        msg = self.tmp.encode({})
        self.assertEquals(msg.field_1.int, 1)
        self.assertEquals(msg.field_2.int, 2)

    def test_message_field_type_conversions(self):
        msg = self.tmp.encode({'field_1': 1024})
        self.assertEquals(msg.field_1.int, 1024)
        self.assertEquals(msg.field_1.hex, '0x0400')
        self.assertEquals(msg.field_1.bytes, '\x04\x00')

    def test_encode_template_with_params(self):
        msg = self.tmp.encode({'field_1':111, 'field_2':222})
        self.assertEquals(msg.field_1.int, 111)
        self.assertEquals(msg.field_2.int, 222)

    def test_encode_template_header(self):
        msg = self.tmp.encode({})
        self.assertEquals(msg._header.msgId.int, 5)
        self.assertEquals(msg._header.length.int, 8)

    def test_encode_to_bytes(self):
        msg = self.tmp.encode({})
        self.assertEquals(msg._header.msgId.int, 5)
        self.assertEquals(msg._raw, to_bin_of_length(8, '0x0005 0008 0001 0002'))

    # TODO: make the fields aware of their type?
    # so that uint fields are pretty printed to uints
    # bytes fields to hex bytes
    # and character fields to characters..
    def test_pretty_print(self):
        msg = self.tmp.encode({})
        self.assertEquals(msg._header.msgId.int, 5)
        self.assertEquals(str(msg), 'Message FooRequest')
        self.assertEquals(repr(msg),
'''Message FooRequest
  TestProtocol header
    msgId = 0x0005
    length = 0x0008
  field_1 = 0x0001
  field_2 = 0x0002
''')

    def test_unknown_params_cause_exception(self):
        self.assertRaises(Exception, self.tmp.encode, {'unknown':111})

    def test_decode_message(self):
        msg = self.tmp.decode(to_bin('0xcafebabe'))
        self.assertEquals(msg.field_1.hex, '0xcafe')

class TestStructuredTemplate(unittest.TestCase):

    def test_access_struct(self):
        self._protocol = Protocol('TestProtocol')
        self._protocol.add(UInt(2, 'msgId', 5))
        self._protocol.add(UInt(2, 'length', None))
        self._protocol.add(PDU('length-4'))
        self.tmp = MessageTemplate('StructuredRequest', self._protocol, {})
        struct = _get_pair()
        self.tmp.add(struct)
        msg = self.tmp.encode({})
        self.assertEquals(msg.pair.first.int, 1)

    def test_create_struct(self):
        struct = _get_pair()
        self.assertEquals(struct.name, 'pair')

    def test_add_fields_to_struct(self):
        struct = _get_pair()
        encoded = struct.encode({})
        self.assertEquals(encoded.first.int, 1)

    def test_add_fields_to_struct_and_override_values(self):
        struct = _get_pair()
        encoded = struct.encode({'pair.first':42})
        self.assertEquals(encoded.first.int, 42)

    def test_yo_dawg_i_heard(self):
        str_str = _get_recursive_struct()
        encoded = str_str.encode({})
        self.assertEquals(encoded.pair.first.int, 1)

    def test_get_recursive_names(self):
        pair = _get_pair()
        names = pair._get_params_sub_tree({'pair.foo':0, 'pairnotyourname.ploo':2, 'pair.goo.doo':3})
        self.assertEquals(len(names), 2)
        self.assertEquals(names['foo'], 0)
        self.assertEquals(names['goo.doo'], 3)

    def test_set_recursive(self):
        str_str = _get_recursive_struct()
        encoded = str_str.encode({'str_str.pair.first':42})
        self.assertEquals(encoded.pair.first.int, 42)


class TestListTemplate(unittest.TestCase):

    def test_create_list(self):
        list = List(3, 'topthree')
        list.add(UInt(2, None, 1))
        self.assertEquals(list.name, 'topthree')
        self.assertEquals(list.encode({})[0].int, 1)
        self.assertEquals(list.encode({})[2].int, 1)

    def test_create_list_with_setting_value(self):
        list = List('3', 'topthree')
        list.add(UInt(2, None, 1))
        encoded = list.encode({'topthree[0]':42})
        self.assertEquals(encoded[0].int, 42)
        self.assertEquals(encoded[1].int, 1)

    def test_list_with_struct(self):
        list = List(3, 'topthree')
        list.add(_get_pair())
        encoded = list.encode({'topthree[1].first':24})
        self.assertEquals(encoded[0].first.int, 1)
        self.assertEquals(encoded[1].first.int, 24)
        self.assertEquals(encoded[1].second.int, 2)

    def test_list_list(self):
        innerList= List(3, None)
        innerList.add(UInt(2, None, 7))
        outerList = List('4', 'listlist')
        outerList.add(innerList)
        encoded = outerList.encode({'listlist[0][1]':10, 'listlist[3][2]':55})
        self.assertEquals(encoded[0][1].int, 10)
        self.assertEquals(encoded[3][2].int, 55)
        self.assertEquals(encoded[2][2].int, 7)

    def test_decode_message(self):
        list = List('5', 'five')
        list.add(UInt(4, None, 3))
        decoded = list.decode(to_bin('0x'+('00000003'*5)))
        self.assertEquals(len(decoded[4]), 4)
        self.assertEquals(len(decoded), 20)
        self.assertEquals(decoded[0].int, 3)

class TestMessageTemplateValidation(unittest.TestCase):

    def setUp(self):
        self._protocol = Protocol('TestProtocol')
        self._protocol.add(UInt(2, 'msgId', 5))
        self._protocol.add(UInt(2, 'length', None))
        self._protocol.add(PDU('length-4'))
        self.tmp = MessageTemplate('FooRequest', self._protocol, {})
        self.tmp.add(UInt(2, 'field_1', '0xcafe'))
        self.tmp.add(UInt(2, 'field_2', '0xbabe'))

    def test_validate_passing_hex(self):
        msg = self.tmp.decode(to_bin('0xcafebabe'))
        errors = self.tmp.validate(msg, {})
        self.assertEquals(errors, [])

    def test_validate_error_default_value(self):
        msg = self.tmp.decode(to_bin('0xcafedead'))
        errors = self.tmp.validate(msg, {})
        self.assertEquals(errors, ['Value of field field_2 does not match 0xdead!=0xbabe'])

    def test_validate_error_override(self):
        msg = self.tmp.decode(to_bin('0xcafebabe'))
        errors = self.tmp.validate(msg, {'field_2':'0xdead'})
        self.assertEquals(errors, ['Value of field field_2 does not match 0xbabe!=0xdead'])

    def test_validate_two_errors(self):
        msg = self.tmp.decode(to_bin('0xbeefbabe'))
        errors = self.tmp.validate(msg, {'field_2':'0xdead'})
        self.assertEquals(len(errors), 2)

    def test_validate_pattern_pass(self):
        msg = self.tmp.decode(to_bin('0xcafe0002'))
        errors = self.tmp.validate(msg, {'field_2':'(0|2)'})
        self.assertEquals(len(errors), 0)

    def test_validate_pattern_failure(self):
        msg = self.tmp.decode(to_bin('0xcafe0002'))
        errors = self.tmp.validate(msg, {'field_2':'(0|3)'})
        self.assertEquals(len(errors), 1)

    def test_validate_passing_int(self):
        msg = self.tmp.decode(to_bin('0xcafe0200'))
        errors = self.tmp.validate(msg, {'field_2':'512'})
        self.assertEquals(errors, [])

    def test_failing_passing_int(self):
        msg = self.tmp.decode(to_bin('0xcafe0200'))
        errors = self.tmp.validate(msg, {'field_2':'513'})
        self.assertEquals(len(errors), 1)


class TestTemplateFieldValidation(unittest.TestCase):

    def test_validate_uint(self):
        template = UInt(2, 'field', 4)
        field = Field('uint', 'field', to_bin('0x0004'))
        self.assertEquals(template.validate(field, {}), [])

    def test_fail_validating_uint(self):
        template = UInt(2, 'field', 4)
        field = Field('uint', 'field', to_bin('0x0004'))
        self.assertEquals(len(template.validate(field, {'field':'42'})), 1)

    def test_validate_struct_passes(self):
        template = _get_pair()
        field = template.encode({})
        self.assertEquals(template.validate(field, {'pair.first':'1'}), [])

    def test_validate_struct_fails(self):
        template = _get_pair()
        field = template.encode({})
        self.assertEquals(len(template.validate(field, {'pair.first':'42'})), 1)


class TestTemplateFields(unittest.TestCase):

    def test_uint_static_field(self):
        field = UInt(5, "field", 8)
        self.assertTrue(field.length.static)
        self.assertEquals(field.name, "field")
        self.assertEquals(field.default_value, '8')
        self.assertEquals(field.type, 'uint')
        self.assertEquals(field.encode({}).hex, '0x0000000008')

    def test_char_static_field(self):
        field = Char(5, "char_field", 'foo')
        self.assertTrue(field.length.static)
        self.assertEquals(field.name, "char_field")
        self.assertEquals(field.default_value, 'foo')
        self.assertEquals(field.type, 'char')
        self.assertEquals(field.encode({}).bytes, 'foo\x00\x00')

    def test_pdu_field_without_subtractor(self):
        field = PDU('value')
        self.assertEquals(field.length.field, 'value')
        self.assertEquals(field.length.subtractor, 0)
        self.assertEquals(field.type, 'pdu')

    def test_pdu_field_without_subtractor(self):
        field = PDU('value-8')
        self.assertEquals(field.length.field, 'value')
        self.assertEquals(field.length.subtractor, 8)

    def test_decode_uint(self):
        field_template = UInt(2, 'field', 6)
        decoded = field_template.decode(to_bin('0xcafe'))
        self.assertEquals(decoded.hex, '0xcafe')

    def test_decode_chars(self):
        field_template = Char(2, 'field', 6)
        decoded = field_template.decode(to_bin('0xcafe'))
        self.assertEquals(decoded.hex, '0xcafe')

    def test_length_of_struct(self):
        pair = _get_pair()
        encoded = pair.encode({})
        self.assertEquals(len(encoded), 4)

    def test_decode_struct(self):
        pair = _get_pair()
        decoded = pair.decode(to_bin('0xcafebabe'))
        self.assertEquals(decoded.first.hex, '0xcafe')
        self.assertEquals(decoded.second.hex, '0xbabe')

    def test_decode_returns_used_length(self):
        field_template = UInt(2, 'field', 6)
        data = to_bin('0xcafebabeff00ff00')
        decoded = field_template.decode(data)
        self.assertEquals(decoded.hex, '0xcafe')
        self.assertEquals(len(decoded), 2)


class TestLength(unittest.TestCase):

    def test_create_length(self):
        length = Length('5')
        self.assertTrue(length.static)

    def test_create_length(self):
        length = Length('length')
        self.assertFalse(length.static)

    def test_static_length(self):
        length = Length('5')
        self.assertEquals(length.value, 5)

    def test_only_one_variable_in_dynamic_length(self):
        self.assertRaises(Exception,Length,'length-messageId')

    def test_dynamic_length(self):
        length = Length('length-8')
        self.assertEquals(length.solve_value(18), 10)
        self.assertEquals(length.solve_parameter(10), 18)

    def test_dynamic_length(self):
        length = Length('length')
        self.assertEquals(length.solve_value(18), 18)
        self.assertEquals(length.solve_parameter(18), 18)

    def test_get_field_name(self):
        length = Length('length-8')
        self.assertEquals(length.field, 'length')
