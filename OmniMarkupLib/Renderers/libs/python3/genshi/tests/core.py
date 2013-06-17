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
import pickle
import unittest

from genshi import core
from genshi.core import Markup, Attrs, Namespace, QName, escape, unescape
from genshi.input import XML, ParseError
from genshi.compat import StringIO, BytesIO


class StreamTestCase(unittest.TestCase):

    def test_render_utf8(self):
        xml = XML('<li>Über uns</li>')
        self.assertEqual('<li>Über uns</li>'.encode('utf-8'), xml.render(encoding='utf-8'))

    def test_render_unicode(self):
        xml = XML('<li>Über uns</li>')
        self.assertEqual('<li>Über uns</li>', xml.render())
        self.assertEqual('<li>Über uns</li>', xml.render(encoding=None))

    def test_render_ascii(self):
        xml = XML('<li>Über uns</li>')
        self.assertEqual('<li>&#220;ber uns</li>'.encode('ascii'), xml.render(encoding='ascii'))

    def test_render_output_stream_utf8(self):
        xml = XML('<li>Über uns</li>')
        strio = BytesIO()
        self.assertEqual(None, xml.render(encoding='utf-8', out=strio))
        self.assertEqual('<li>Über uns</li>'.encode('utf-8'), strio.getvalue())

    def test_render_output_stream_unicode(self):
        xml = XML('<li>Über uns</li>')
        strio = StringIO()
        self.assertEqual(None, xml.render(encoding=None, out=strio))
        self.assertEqual('<li>Über uns</li>', strio.getvalue())

    def test_pickle(self):
        xml = XML('<li>Foo</li>')
        buf = BytesIO()
        pickle.dump(xml, buf, 2)
        buf.seek(0)
        xml = pickle.load(buf)
        self.assertEquals('<li>Foo</li>', xml.render(encoding=None))


class MarkupTestCase(unittest.TestCase):

    def test_new_with_encoding(self):
        markup = Markup('Döner'.encode('utf-8'), encoding='utf-8')
        # mimic Markup.__repr__ when constructing output for Python 2/3 compatibility
        self.assertEquals("<Markup %r>" % 'D\u00f6ner', repr(markup))

    def test_repr(self):
        markup = Markup('foo')
        self.assertEquals("<Markup 'foo'>", repr(markup))

    def test_escape(self):
        markup = escape('<b>"&"</b>')
        assert type(markup) is Markup
        self.assertEquals('&lt;b&gt;&#34;&amp;&#34;&lt;/b&gt;', markup)

    def test_escape_noquotes(self):
        markup = escape('<b>"&"</b>', quotes=False)
        assert type(markup) is Markup
        self.assertEquals('&lt;b&gt;"&amp;"&lt;/b&gt;', markup)

    def test_unescape_markup(self):
        string = '<b>"&"</b>'
        markup = Markup.escape(string)
        assert type(markup) is Markup
        self.assertEquals(string, unescape(markup))

    def test_Markup_escape_None_noquotes(self):
        markup = Markup.escape(None, False)
        assert type(markup) is Markup
        self.assertEquals('', markup)

    def test_add_str(self):
        markup = Markup('<b>foo</b>') + '<br/>'
        assert type(markup) is Markup
        self.assertEquals('<b>foo</b>&lt;br/&gt;', markup)

    def test_add_markup(self):
        markup = Markup('<b>foo</b>') + Markup('<br/>')
        assert type(markup) is Markup
        self.assertEquals('<b>foo</b><br/>', markup)

    def test_add_reverse(self):
        markup = '<br/>' + Markup('<b>bar</b>')
        assert type(markup) is Markup
        self.assertEquals('&lt;br/&gt;<b>bar</b>', markup)

    def test_mod(self):
        markup = Markup('<b>%s</b>') % '&'
        assert type(markup) is Markup
        self.assertEquals('<b>&amp;</b>', markup)

    def test_mod_multi(self):
        markup = Markup('<b>%s</b> %s') % ('&', 'boo')
        assert type(markup) is Markup
        self.assertEquals('<b>&amp;</b> boo', markup)

    def test_mod_mapping(self):
        markup = Markup('<b>%(foo)s</b>') % {'foo': '&'}
        assert type(markup) is Markup
        self.assertEquals('<b>&amp;</b>', markup)

    def test_mod_noescape(self):
        markup = Markup('<b>%(amp)s</b>') % {'amp': Markup('&amp;')}
        assert type(markup) is Markup
        self.assertEquals('<b>&amp;</b>', markup)

    def test_mul(self):
        markup = Markup('<b>foo</b>') * 2
        assert type(markup) is Markup
        self.assertEquals('<b>foo</b><b>foo</b>', markup)

    def test_mul_reverse(self):
        markup = 2 * Markup('<b>foo</b>')
        assert type(markup) is Markup
        self.assertEquals('<b>foo</b><b>foo</b>', markup)

    def test_join(self):
        markup = Markup('<br />').join(['foo', '<bar />', Markup('<baz />')])
        assert type(markup) is Markup
        self.assertEquals('foo<br />&lt;bar /&gt;<br /><baz />', markup)

    def test_stripentities_all(self):
        markup = Markup('&amp; &#106;').stripentities()
        assert type(markup) is Markup
        self.assertEquals('& j', markup)

    def test_stripentities_keepxml(self):
        markup = Markup('&amp; &#106;').stripentities(keepxmlentities=True)
        assert type(markup) is Markup
        self.assertEquals('&amp; j', markup)

    def test_striptags_empty(self):
        markup = Markup('<br />').striptags()
        assert type(markup) is Markup
        self.assertEquals('', markup)

    def test_striptags_mid(self):
        markup = Markup('<a href="#">fo<br />o</a>').striptags()
        assert type(markup) is Markup
        self.assertEquals('foo', markup)

    def test_pickle(self):
        markup = Markup('foo')
        buf = BytesIO()
        pickle.dump(markup, buf, 2)
        buf.seek(0)
        self.assertEquals("<Markup 'foo'>", repr(pickle.load(buf)))


class AttrsTestCase(unittest.TestCase):

    def test_pickle(self):
        attrs = Attrs([("attr1", "foo"), ("attr2", "bar")])
        buf = BytesIO()
        pickle.dump(attrs, buf, 2)
        buf.seek(0)
        unpickled = pickle.load(buf)
        self.assertEquals("Attrs([('attr1', 'foo'), ('attr2', 'bar')])",
                          repr(unpickled))

    def test_non_ascii(self):
        attrs_tuple = Attrs([("attr1", "föö"), ("attr2", "bär")]).totuple()
        self.assertEqual('fööbär', attrs_tuple[1])


class NamespaceTestCase(unittest.TestCase):

    def test_repr(self):
        self.assertEqual("Namespace('http://www.example.org/namespace')",
                         repr(Namespace('http://www.example.org/namespace')))

    def test_repr_eval(self):
        ns = Namespace('http://www.example.org/namespace')
        self.assertEqual(eval(repr(ns)), ns)

    def test_repr_eval_non_ascii(self):
        ns = Namespace('http://www.example.org/nämespäcé')
        self.assertEqual(eval(repr(ns)), ns)

    def test_pickle(self):
        ns = Namespace('http://www.example.org/namespace')
        buf = BytesIO()
        pickle.dump(ns, buf, 2)
        buf.seek(0)
        unpickled = pickle.load(buf)
        self.assertEquals("Namespace('http://www.example.org/namespace')",
                          repr(unpickled))
        self.assertEquals('http://www.example.org/namespace', unpickled.uri)


class QNameTestCase(unittest.TestCase):

    def test_pickle(self):
        qname = QName('http://www.example.org/namespace}elem')
        buf = BytesIO()
        pickle.dump(qname, buf, 2)
        buf.seek(0)
        unpickled = pickle.load(buf)
        self.assertEquals('{http://www.example.org/namespace}elem', unpickled)
        self.assertEquals('http://www.example.org/namespace',
                          unpickled.namespace)
        self.assertEquals('elem', unpickled.localname)

    def test_repr(self):
        self.assertEqual("QName('elem')", repr(QName('elem')))
        self.assertEqual("QName('http://www.example.org/namespace}elem')",
                         repr(QName('http://www.example.org/namespace}elem')))

    def test_repr_eval(self):
        qn = QName('elem')
        self.assertEqual(eval(repr(qn)), qn)

    def test_repr_eval_non_ascii(self):
        qn = QName('élem')
        self.assertEqual(eval(repr(qn)), qn)

    def test_leading_curly_brace(self):
        qname = QName('{http://www.example.org/namespace}elem')
        self.assertEquals('http://www.example.org/namespace', qname.namespace)
        self.assertEquals('elem', qname.localname)

    def test_curly_brace_equality(self):
        qname1 = QName('{http://www.example.org/namespace}elem')
        qname2 = QName('http://www.example.org/namespace}elem')
        self.assertEqual(qname1.namespace, qname2.namespace)
        self.assertEqual(qname1.localname, qname2.localname)
        self.assertEqual(qname1, qname2)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(StreamTestCase, 'test'))
    suite.addTest(unittest.makeSuite(MarkupTestCase, 'test'))
    suite.addTest(unittest.makeSuite(NamespaceTestCase, 'test'))
    suite.addTest(unittest.makeSuite(AttrsTestCase, 'test'))
    suite.addTest(unittest.makeSuite(QNameTestCase, 'test'))
    suite.addTest(doctest.DocTestSuite(core))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
