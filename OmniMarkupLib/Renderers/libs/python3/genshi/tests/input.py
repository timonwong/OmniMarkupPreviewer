# -*- coding: utf-8 -*-
#
# Copyright (C) 2006-2009 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://genshi.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://genshi.edgewall.org/log/.

import doctest
import sys
import unittest

from genshi.core import Attrs, Stream
from genshi.input import XMLParser, HTMLParser, ParseError
from genshi.compat import StringIO, BytesIO


class XMLParserTestCase(unittest.TestCase):

    def test_text_node_pos_single_line(self):
        text = '<elem>foo bar</elem>'
        events = list(XMLParser(StringIO(text)))
        kind, data, pos = events[1]
        self.assertEqual(Stream.TEXT, kind)
        self.assertEqual('foo bar', data)
        self.assertEqual((None, 1, 6), pos)

    def test_text_node_pos_multi_line(self):
        text = '''<elem>foo
bar</elem>'''
        events = list(XMLParser(StringIO(text)))
        kind, data, pos = events[1]
        self.assertEqual(Stream.TEXT, kind)
        self.assertEqual('foo\nbar', data)
        self.assertEqual((None, 1, -1), pos)

    def test_element_attribute_order(self):
        text = '<elem title="baz" id="foo" class="bar" />'
        events = list(XMLParser(StringIO(text)))
        kind, data, pos = events[0]
        self.assertEqual(Stream.START, kind)
        tag, attrib = data
        self.assertEqual('elem', tag)
        self.assertEqual(('title', 'baz'), attrib[0])
        self.assertEqual(('id', 'foo'), attrib[1])
        self.assertEqual(('class', 'bar'), attrib[2])

    def test_unicode_input(self):
        text = '<div>\u2013</div>'
        events = list(XMLParser(StringIO(text)))
        kind, data, pos = events[1]
        self.assertEqual(Stream.TEXT, kind)
        self.assertEqual('\u2013', data)

    def test_latin1_encoded(self):
        text = '<div>\xf6</div>'.encode('iso-8859-1')
        events = list(XMLParser(BytesIO(text), encoding='iso-8859-1'))
        kind, data, pos = events[1]
        self.assertEqual(Stream.TEXT, kind)
        self.assertEqual('\xf6', data)

    def test_latin1_encoded_xmldecl(self):
        text = """<?xml version="1.0" encoding="iso-8859-1" ?>
        <div>\xf6</div>
        """.encode('iso-8859-1')
        events = list(XMLParser(BytesIO(text)))
        kind, data, pos = events[2]
        self.assertEqual(Stream.TEXT, kind)
        self.assertEqual('\xf6', data)

    def test_html_entity_with_dtd(self):
        text = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html>&nbsp;</html>
        """
        events = list(XMLParser(StringIO(text)))
        kind, data, pos = events[2]
        self.assertEqual(Stream.TEXT, kind)
        self.assertEqual('\xa0', data)

    def test_html_entity_without_dtd(self):
        text = '<html>&nbsp;</html>'
        events = list(XMLParser(StringIO(text)))
        kind, data, pos = events[1]
        self.assertEqual(Stream.TEXT, kind)
        self.assertEqual('\xa0', data)

    def test_html_entity_in_attribute(self):
        text = '<p title="&nbsp;"/>'
        events = list(XMLParser(StringIO(text)))
        kind, data, pos = events[0]
        self.assertEqual(Stream.START, kind)
        self.assertEqual('\xa0', data[1].get('title'))
        kind, data, pos = events[1]
        self.assertEqual(Stream.END, kind)

    def test_undefined_entity_with_dtd(self):
        text = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html>&junk;</html>
        """
        events = XMLParser(StringIO(text))
        self.assertRaises(ParseError, list, events)

    def test_undefined_entity_without_dtd(self):
        text = '<html>&junk;</html>'
        events = XMLParser(StringIO(text))
        self.assertRaises(ParseError, list, events)


class HTMLParserTestCase(unittest.TestCase):

    def test_text_node_pos_single_line(self):
        text = '<elem>foo bar</elem>'
        events = list(HTMLParser(StringIO(text)))
        kind, data, pos = events[1]
        self.assertEqual(Stream.TEXT, kind)
        self.assertEqual('foo bar', data)
        self.assertEqual((None, 1, 6), pos)

    def test_text_node_pos_multi_line(self):
        text = '''<elem>foo
bar</elem>'''
        events = list(HTMLParser(StringIO(text)))
        kind, data, pos = events[1]
        self.assertEqual(Stream.TEXT, kind)
        self.assertEqual('foo\nbar', data)
        self.assertEqual((None, 1, 6), pos)

    def test_input_encoding_text(self):
        text = '<div>\xf6</div>'.encode('iso-8859-1')
        events = list(HTMLParser(BytesIO(text), encoding='iso-8859-1'))
        kind, data, pos = events[1]
        self.assertEqual(Stream.TEXT, kind)
        self.assertEqual('\xf6', data)

    def test_input_encoding_attribute(self):
        text = '<div title="\xf6"></div>'.encode('iso-8859-1')
        events = list(HTMLParser(BytesIO(text), encoding='iso-8859-1'))
        kind, (tag, attrib), pos = events[0]
        self.assertEqual(Stream.START, kind)
        self.assertEqual('\xf6', attrib.get('title'))

    def test_unicode_input(self):
        text = '<div>\u2013</div>'
        events = list(HTMLParser(StringIO(text)))
        kind, data, pos = events[1]
        self.assertEqual(Stream.TEXT, kind)
        self.assertEqual('\u2013', data)

    def test_html_entity_in_attribute(self):
        text = '<p title="&nbsp;"></p>'
        events = list(HTMLParser(StringIO(text)))
        kind, data, pos = events[0]
        self.assertEqual(Stream.START, kind)
        self.assertEqual('\xa0', data[1].get('title'))
        kind, data, pos = events[1]
        self.assertEqual(Stream.END, kind)

    def test_html_entity_in_text(self):
        text = '<p>&nbsp;</p>'
        events = list(HTMLParser(StringIO(text)))
        kind, data, pos = events[1]
        self.assertEqual(Stream.TEXT, kind)
        self.assertEqual('\xa0', data)

    def test_processing_instruction(self):
        text = '<?php echo "Foobar" ?>'
        events = list(HTMLParser(StringIO(text)))
        kind, (target, data), pos = events[0]
        self.assertEqual(Stream.PI, kind)
        self.assertEqual('php', target)
        self.assertEqual('echo "Foobar"', data)

    def test_processing_instruction_no_data_1(self):
        text = '<?foo ?>'
        events = list(HTMLParser(StringIO(text)))
        kind, (target, data), pos = events[0]
        self.assertEqual(Stream.PI, kind)
        self.assertEqual('foo', target)
        self.assertEqual('', data)

    def test_processing_instruction_no_data_2(self):
        text = '<?experiment>...<?/experiment>'
        events = list(HTMLParser(StringIO(text)))
        kind, (target, data), pos = events[0]
        self.assertEqual(Stream.PI, kind)
        self.assertEqual('experiment', target)
        self.assertEqual('', data)
        kind, (target, data), pos = events[2]
        self.assertEqual('/experiment', target)
        self.assertEqual('', data)

    def test_xmldecl(self):
        text = '<?xml version="1.0" ?><root />'
        events = list(XMLParser(StringIO(text)))
        kind, (version, encoding, standalone), pos = events[0]
        self.assertEqual(Stream.XML_DECL, kind)
        self.assertEqual('1.0', version)
        self.assertEqual(None, encoding)
        self.assertEqual(-1, standalone)

    def test_xmldecl_encoding(self):
        text = '<?xml version="1.0" encoding="utf-8" ?><root />'
        events = list(XMLParser(StringIO(text)))
        kind, (version, encoding, standalone), pos = events[0]
        self.assertEqual(Stream.XML_DECL, kind)
        self.assertEqual('1.0', version)
        self.assertEqual('utf-8', encoding)
        self.assertEqual(-1, standalone)

    def test_xmldecl_standalone(self):
        text = '<?xml version="1.0" standalone="yes" ?><root />'
        events = list(XMLParser(StringIO(text)))
        kind, (version, encoding, standalone), pos = events[0]
        self.assertEqual(Stream.XML_DECL, kind)
        self.assertEqual('1.0', version)
        self.assertEqual(None, encoding)
        self.assertEqual(1, standalone)

    def test_processing_instruction_trailing_qmark(self):
        text = '<?php echo "Foobar" ??>'
        events = list(HTMLParser(StringIO(text)))
        kind, (target, data), pos = events[0]
        self.assertEqual(Stream.PI, kind)
        self.assertEqual('php', target)
        self.assertEqual('echo "Foobar" ?', data)

    def test_out_of_order_tags1(self):
        text = '<span><b>Foobar</span></b>'
        events = list(HTMLParser(StringIO(text)))
        self.assertEqual(5, len(events))
        self.assertEqual((Stream.START, ('span', ())), events[0][:2])
        self.assertEqual((Stream.START, ('b', ())), events[1][:2])
        self.assertEqual((Stream.TEXT, 'Foobar'), events[2][:2])
        self.assertEqual((Stream.END, 'b'), events[3][:2])
        self.assertEqual((Stream.END, 'span'), events[4][:2])

    def test_out_of_order_tags2(self):
        text = '<span class="baz"><b><i>Foobar</span></b></i>'.encode('utf-8')
        events = list(HTMLParser(BytesIO(text), encoding='utf-8'))
        self.assertEqual(7, len(events))
        self.assertEqual((Stream.START, ('span', Attrs([('class', 'baz')]))),
                         events[0][:2])
        self.assertEqual((Stream.START, ('b', ())), events[1][:2])
        self.assertEqual((Stream.START, ('i', ())), events[2][:2])
        self.assertEqual((Stream.TEXT, 'Foobar'), events[3][:2])
        self.assertEqual((Stream.END, 'i'), events[4][:2])
        self.assertEqual((Stream.END, 'b'), events[5][:2])
        self.assertEqual((Stream.END, 'span'), events[6][:2])

    def test_out_of_order_tags3(self):
        text = '<span><b>Foobar</i>'.encode('utf-8')
        events = list(HTMLParser(BytesIO(text), encoding='utf-8'))
        self.assertEqual(5, len(events))
        self.assertEqual((Stream.START, ('span', ())), events[0][:2])
        self.assertEqual((Stream.START, ('b', ())), events[1][:2])
        self.assertEqual((Stream.TEXT, 'Foobar'), events[2][:2])
        self.assertEqual((Stream.END, 'b'), events[3][:2])
        self.assertEqual((Stream.END, 'span'), events[4][:2])

    def test_hex_charref(self):
        text = '<span>&#x27;</span>'
        events = list(HTMLParser(StringIO(text)))
        self.assertEqual(3, len(events))
        self.assertEqual((Stream.START, ('span', ())), events[0][:2])
        self.assertEqual((Stream.TEXT, "'"), events[1][:2])
        self.assertEqual((Stream.END, 'span'), events[2][:2])

    def test_multibyte_character_on_chunk_boundary(self):
        text = 'a' * ((4 * 1024) - 1) + '\xe6'
        events = list(HTMLParser(BytesIO(text.encode('utf-8')),
                                 encoding='utf-8'))
        self.assertEqual(1, len(events))
        self.assertEqual((Stream.TEXT, text), events[0][:2])


def suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(XMLParser.__module__))
    suite.addTest(unittest.makeSuite(XMLParserTestCase, 'test'))
    suite.addTest(unittest.makeSuite(HTMLParserTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
