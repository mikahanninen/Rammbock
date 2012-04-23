#  Copyright 2012 Nokia Siemens Networks Oyj
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from math import ceil
from binary_tools import to_0xhex, to_binary_string_of_length, to_bin_of_length, to_tbcd_value, to_tbcd_binary, to_bin_str_from_int_string, to_hex
from ordered_dict import OrderedDict


class _StructuredElement(object):

    _type = None

    def __init__(self, name):
        self._name = name
        self._fields = OrderedDict()
        self._parent = None

    def __setitem__(self, name, child):
        self._fields[name] = child
        child._parent = self

    def __getitem__(self, name):
        return self._fields[str(name)]

    def __getattr__(self, name):
        return self[name]

    def __str__(self):
        return self._get_name()

    def __repr__(self):
        result = '%s\n' % str(self._get_name())
        for field in self._fields.values():
            result += self._format_indented('%s' % repr(field))
        return result

    def __contains__(self, key):
        return key in self._fields

    def _format_indented(self, text):
        return ''.join(['  %s\n' % line for line in text.splitlines()])

    @property
    def _raw(self):
        return self._get_raw_bytes()

    def _get_name(self):
        return '%s %s' % (self._type, self._name)

    def _get_raw_bytes(self):
        return ''.join((field._raw for field in self._fields.values()))

    def __len__(self):
        return sum(len(field) for field in self._fields.values())

    def _get_recursive_name(self, parent):
        return self._parent._get_recursive_name(parent) + self._name \
                        if self._parent != None else self._name

class List(_StructuredElement):

    _type = 'List'

    def __init__(self, name, type_name):
        self._name, self._type = name, type_name
        self._fields = OrderedDict()

    def _get_name(self):
        return '%s %s[]' % (self._type, self._name)


class Struct(_StructuredElement):

    _type = 'Struct'

    def __init__(self, name, type_name):
        self._name = name
        self._type = type_name
        self._fields = OrderedDict()


class Union(_StructuredElement):

    _type = 'Union'

    def __init__(self, name, length):
        self._length = length
        _StructuredElement.__init__(self, name)

    def _get_raw_bytes(self):
        max_raw = ''
        for field in self._fields.values():
            if len(field._raw) > len(max_raw):
                max_raw = field._raw
        return max_raw.ljust(self._length, '\x00')


class BinaryContainer(_StructuredElement):

    _type = 'BinaryContainer'

    def __init__(self, name, little_endian=False):
        self._little_endian = little_endian
        _StructuredElement.__init__(self, name)

    def _binlength(self):
        return sum(field.binlength for field in self._fields.values())

    def __len__(self):
        return self._binlength()/8

    def _get_raw_bytes(self):
        # TODO: faster implementation...
        result = to_bin_of_length(len(self), ' '.join((field.bin for field in self._fields.values())))
        if self._little_endian:
            return result[::-1]
        return result


class TBCDContainer(BinaryContainer):

    _type = 'TBCDContainer'

    def _get_raw_bytes(self):
        return to_tbcd_binary("".join(field.tbcd for field in self._fields.values()))

    def __len__(self):
        return int(ceil(sum(len(field.tbcd) for field in self._fields.values())/2.0))


class Message(_StructuredElement):

    _type = 'Message'

    def _add_header(self, header):
        new = OrderedDict({'_header':header})
        new.update(self._fields)
        self._fields = new


class Header(_StructuredElement):

    _type = 'Header'


class Field(object):

    def __init__(self, type, name, value, aligned_len=None, little_endian=False):
        self._type = type
        self._name = name
        self._original_value = value
        self._length = aligned_len or len(value)
        self._little_endian = little_endian
        self._parent = None

    @property
    def _value(self):
        return self._original_value[::-1] if self._little_endian else self._original_value
    # TODO: If needed, original value and raw value can be precalculated
    # in __init__

    @property
    def name(self):
        return self._name

    @property
    def int(self):
        return int(self)

    def __int__(self):
        return int(to_0xhex(self._value), 16)

    @property
    def hex(self):
        return hex(self)

    @property
    def tbcd(self):
        return to_tbcd_value(self._original_value)

    def __hex__(self):
        return to_0xhex(self._value)

    @property
    def bytes(self):
        return self._value

    @property
    def chars(self):
        return str(self._value)

    @property
    def bin(self):
        return self._bin()

    def _bin(self):
        return to_binary_string_of_length(self._length * 8, self._value)

    @property
    def ascii(self):
        return ''.join(i for i in self._value if 128 > ord(i) >= 32)

    @property
    def _raw(self):
        return self._original_value.ljust(self._length, '\x00')

    def __str__(self):
        return self.hex

    def __repr__(self):
        return '%s = %s' % (self.name, str(self))

    def __len__(self):
        return self._length


class BinaryField(Field):

    _type = 'binary'

    def __init__(self, length, name, value, aligned_len=None, little_endian=False):
        self._name = name
        self._original_value = value
        self._binlength = int(length)
        self._length = int(ceil(self._binlength / 8.0))
        self._parent = None
        self._little_endian = False
        if little_endian:
            raise AssertionError('Internal error. Binary fields should always be big endian, the containers only are little endian')

    def _bin(self):
        return to_binary_string_of_length(self._binlength, self._value)

    @property
    def binlength(self):
        return self._binlength