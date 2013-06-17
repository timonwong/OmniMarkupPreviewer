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
import unittest

from genshi.input import HTML, ParseError
from genshi.filters.html import HTMLFormFiller, HTMLSanitizer
from genshi.template import MarkupTemplate

class HTMLFormFillerTestCase(unittest.TestCase):

    def test_fill_input_text_no_value(self):
        html = HTML("""<form><p>
          <input type="text" name="foo" />
        </p></form>""") | HTMLFormFiller()
        self.assertEquals("""<form><p>
          <input type="text" name="foo"/>
        </p></form>""", html.render())

    def test_fill_input_text_single_value(self):
        html = HTML("""<form><p>
          <input type="text" name="foo" />
        </p></form>""") | HTMLFormFiller(data={'foo': 'bar'})
        self.assertEquals("""<form><p>
          <input type="text" name="foo" value="bar"/>
        </p></form>""", html.render())

    def test_fill_input_text_multi_value(self):
        html = HTML("""<form><p>
          <input type="text" name="foo" />
        </p></form>""") | HTMLFormFiller(data={'foo': ['bar']})
        self.assertEquals("""<form><p>
          <input type="text" name="foo" value="bar"/>
        </p></form>""", html.render())

    def test_fill_input_hidden_no_value(self):
        html = HTML("""<form><p>
          <input type="hidden" name="foo" />
        </p></form>""") | HTMLFormFiller()
        self.assertEquals("""<form><p>
          <input type="hidden" name="foo"/>
        </p></form>""", html.render())

    def test_fill_input_hidden_single_value(self):
        html = HTML("""<form><p>
          <input type="hidden" name="foo" />
        </p></form>""") | HTMLFormFiller(data={'foo': 'bar'})
        self.assertEquals("""<form><p>
          <input type="hidden" name="foo" value="bar"/>
        </p></form>""", html.render())

    def test_fill_input_hidden_multi_value(self):
        html = HTML("""<form><p>
          <input type="hidden" name="foo" />
        </p></form>""") | HTMLFormFiller(data={'foo': ['bar']})
        self.assertEquals("""<form><p>
          <input type="hidden" name="foo" value="bar"/>
        </p></form>""", html.render())

    def test_fill_textarea_no_value(self):
        html = HTML("""<form><p>
          <textarea name="foo"></textarea>
        </p></form>""") | HTMLFormFiller()
        self.assertEquals("""<form><p>
          <textarea name="foo"/>
        </p></form>""", html.render())

    def test_fill_textarea_single_value(self):
        html = HTML("""<form><p>
          <textarea name="foo"></textarea>
        </p></form>""") | HTMLFormFiller(data={'foo': 'bar'})
        self.assertEquals("""<form><p>
          <textarea name="foo">bar</textarea>
        </p></form>""", html.render())

    def test_fill_textarea_multi_value(self):
        html = HTML("""<form><p>
          <textarea name="foo"></textarea>
        </p></form>""") | HTMLFormFiller(data={'foo': ['bar']})
        self.assertEquals("""<form><p>
          <textarea name="foo">bar</textarea>
        </p></form>""", html.render())

    def test_fill_textarea_multiple(self):
        # Ensure that the subsequent textarea doesn't get the data from the
        # first
        html = HTML("""<form><p>
          <textarea name="foo"></textarea>
          <textarea name="bar"></textarea>
        </p></form>""") | HTMLFormFiller(data={'foo': 'Some text'})
        self.assertEquals("""<form><p>
          <textarea name="foo">Some text</textarea>
          <textarea name="bar"/>
        </p></form>""", html.render())

    def test_fill_textarea_preserve_original(self):
        html = HTML("""<form><p>
          <textarea name="foo"></textarea>
          <textarea name="bar">Original value</textarea>
        </p></form>""") | HTMLFormFiller(data={'foo': 'Some text'})
        self.assertEquals("""<form><p>
          <textarea name="foo">Some text</textarea>
          <textarea name="bar">Original value</textarea>
        </p></form>""", html.render())

    def test_fill_input_checkbox_single_value_auto_no_value(self):
        html = HTML("""<form><p>
          <input type="checkbox" name="foo" />
        </p></form>""") | HTMLFormFiller()
        self.assertEquals("""<form><p>
          <input type="checkbox" name="foo"/>
        </p></form>""", html.render())

    def test_fill_input_checkbox_single_value_auto(self):
        html = HTML("""<form><p>
          <input type="checkbox" name="foo" />
        </p></form>""")
        self.assertEquals("""<form><p>
          <input type="checkbox" name="foo"/>
        </p></form>""", (html | HTMLFormFiller(data={'foo': ''})).render())
        self.assertEquals("""<form><p>
          <input type="checkbox" name="foo" checked="checked"/>
        </p></form>""", (html | HTMLFormFiller(data={'foo': 'on'})).render())

    def test_fill_input_checkbox_single_value_defined(self):
        html = HTML("""<form><p>
          <input type="checkbox" name="foo" value="1" />
        </p></form>""", encoding='ascii')
        self.assertEquals("""<form><p>
          <input type="checkbox" name="foo" value="1" checked="checked"/>
        </p></form>""", (html | HTMLFormFiller(data={'foo': '1'})).render())
        self.assertEquals("""<form><p>
          <input type="checkbox" name="foo" value="1"/>
        </p></form>""", (html | HTMLFormFiller(data={'foo': '2'})).render())

    def test_fill_input_checkbox_multi_value_auto(self):
        html = HTML("""<form><p>
          <input type="checkbox" name="foo" />
        </p></form>""", encoding='ascii')
        self.assertEquals("""<form><p>
          <input type="checkbox" name="foo"/>
        </p></form>""", (html | HTMLFormFiller(data={'foo': []})).render())
        self.assertEquals("""<form><p>
          <input type="checkbox" name="foo" checked="checked"/>
        </p></form>""", (html | HTMLFormFiller(data={'foo': ['on']})).render())

    def test_fill_input_checkbox_multi_value_defined(self):
        html = HTML("""<form><p>
          <input type="checkbox" name="foo" value="1" />
        </p></form>""")
        self.assertEquals("""<form><p>
          <input type="checkbox" name="foo" value="1" checked="checked"/>
        </p></form>""", (html | HTMLFormFiller(data={'foo': ['1']})).render())
        self.assertEquals("""<form><p>
          <input type="checkbox" name="foo" value="1"/>
        </p></form>""", (html | HTMLFormFiller(data={'foo': ['2']})).render())

    def test_fill_input_radio_no_value(self):
        html = HTML("""<form><p>
          <input type="radio" name="foo" />
        </p></form>""") | HTMLFormFiller()
        self.assertEquals("""<form><p>
          <input type="radio" name="foo"/>
        </p></form>""", html.render())

    def test_fill_input_radio_single_value(self):
        html = HTML("""<form><p>
          <input type="radio" name="foo" value="1" />
        </p></form>""")
        self.assertEquals("""<form><p>
          <input type="radio" name="foo" value="1" checked="checked"/>
        </p></form>""", (html | HTMLFormFiller(data={'foo': '1'})).render())
        self.assertEquals("""<form><p>
          <input type="radio" name="foo" value="1"/>
        </p></form>""", (html | HTMLFormFiller(data={'foo': '2'})).render())

    def test_fill_input_radio_multi_value(self):
        html = HTML("""<form><p>
          <input type="radio" name="foo" value="1" />
        </p></form>""")
        self.assertEquals("""<form><p>
          <input type="radio" name="foo" value="1" checked="checked"/>
        </p></form>""", (html | HTMLFormFiller(data={'foo': ['1']})).render())
        self.assertEquals("""<form><p>
          <input type="radio" name="foo" value="1"/>
        </p></form>""", (html | HTMLFormFiller(data={'foo': ['2']})).render())

    def test_fill_input_radio_empty_string(self):
        html = HTML("""<form><p>
          <input type="radio" name="foo" value="" />
        </p></form>""")
        self.assertEquals("""<form><p>
          <input type="radio" name="foo" value="" checked="checked"/>
        </p></form>""", (html | HTMLFormFiller(data={'foo': ''})).render())

    def test_fill_input_radio_multi_empty_string(self):
        html = HTML("""<form><p>
          <input type="radio" name="foo" value="" />
        </p></form>""")
        self.assertEquals("""<form><p>
          <input type="radio" name="foo" value="" checked="checked"/>
        </p></form>""", (html | HTMLFormFiller(data={'foo': ['']})).render())

    def test_fill_select_no_value_auto(self):
        html = HTML("""<form><p>
          <select name="foo">
            <option>1</option>
            <option>2</option>
            <option>3</option>
          </select>
        </p></form>""") | HTMLFormFiller()
        self.assertEquals("""<form><p>
          <select name="foo">
            <option>1</option>
            <option>2</option>
            <option>3</option>
          </select>
        </p></form>""", html.render())

    def test_fill_select_no_value_defined(self):
        html = HTML("""<form><p>
          <select name="foo">
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
          </select>
        </p></form>""") | HTMLFormFiller()
        self.assertEquals("""<form><p>
          <select name="foo">
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
          </select>
        </p></form>""", html.render())

    def test_fill_select_single_value_auto(self):
        html = HTML("""<form><p>
          <select name="foo">
            <option>1</option>
            <option>2</option>
            <option>3</option>
          </select>
        </p></form>""") | HTMLFormFiller(data={'foo': '1'})
        self.assertEquals("""<form><p>
          <select name="foo">
            <option selected="selected">1</option>
            <option>2</option>
            <option>3</option>
          </select>
        </p></form>""", html.render())

    def test_fill_select_single_value_defined(self):
        html = HTML("""<form><p>
          <select name="foo">
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
          </select>
        </p></form>""") | HTMLFormFiller(data={'foo': '1'})
        self.assertEquals("""<form><p>
          <select name="foo">
            <option value="1" selected="selected">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
          </select>
        </p></form>""", html.render())

    def test_fill_select_multi_value_auto(self):
        html = HTML("""<form><p>
          <select name="foo" multiple>
            <option>1</option>
            <option>2</option>
            <option>3</option>
          </select>
        </p></form>""") | HTMLFormFiller(data={'foo': ['1', '3']})
        self.assertEquals("""<form><p>
          <select name="foo" multiple="multiple">
            <option selected="selected">1</option>
            <option>2</option>
            <option selected="selected">3</option>
          </select>
        </p></form>""", html.render())

    def test_fill_select_multi_value_defined(self):
        html = HTML("""<form><p>
          <select name="foo" multiple>
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
          </select>
        </p></form>""") | HTMLFormFiller(data={'foo': ['1', '3']})
        self.assertEquals("""<form><p>
          <select name="foo" multiple="multiple">
            <option value="1" selected="selected">1</option>
            <option value="2">2</option>
            <option value="3" selected="selected">3</option>
          </select>
        </p></form>""", html.render())

    def test_fill_option_segmented_text(self):
        html = MarkupTemplate("""<form>
          <select name="foo">
            <option value="1">foo $x</option>
          </select>
        </form>""").generate(x=1) | HTMLFormFiller(data={'foo': '1'})
        self.assertEquals("""<form>
          <select name="foo">
            <option value="1" selected="selected">foo 1</option>
          </select>
        </form>""", html.render())

    def test_fill_option_segmented_text_no_value(self):
        html = MarkupTemplate("""<form>
          <select name="foo">
            <option>foo $x bar</option>
          </select>
        </form>""").generate(x=1) | HTMLFormFiller(data={'foo': 'foo 1 bar'})
        self.assertEquals("""<form>
          <select name="foo">
            <option selected="selected">foo 1 bar</option>
          </select>
        </form>""", html.render())

    def test_fill_option_unicode_value(self):
        html = HTML("""<form>
          <select name="foo">
            <option value="&ouml;">foo</option>
          </select>
        </form>""") | HTMLFormFiller(data={'foo': 'ö'})
        self.assertEquals("""<form>
          <select name="foo">
            <option value="ö" selected="selected">foo</option>
          </select>
        </form>""", html.render(encoding=None))

    def test_fill_input_password_disabled(self):
        html = HTML("""<form><p>
          <input type="password" name="pass" />
        </p></form>""") | HTMLFormFiller(data={'pass': 'bar'})
        self.assertEquals("""<form><p>
          <input type="password" name="pass"/>
        </p></form>""", html.render())

    def test_fill_input_password_enabled(self):
        html = HTML("""<form><p>
          <input type="password" name="pass" />
        </p></form>""") | HTMLFormFiller(data={'pass': '1234'}, passwords=True)
        self.assertEquals("""<form><p>
          <input type="password" name="pass" value="1234"/>
        </p></form>""", html.render())


def StyleSanitizer():
    safe_attrs = HTMLSanitizer.SAFE_ATTRS | frozenset(['style'])
    return HTMLSanitizer(safe_attrs=safe_attrs)


class HTMLSanitizerTestCase(unittest.TestCase):

    def assert_parse_error_or_equal(self, expected, exploit):
        try:
            html = HTML(exploit)
        except ParseError:
            return
        self.assertEquals(expected, (html | HTMLSanitizer()).render())

    def test_sanitize_unchanged(self):
        html = HTML('<a href="#">fo<br />o</a>')
        self.assertEquals('<a href="#">fo<br/>o</a>',
                          (html | HTMLSanitizer()).render())
        html = HTML('<a href="#with:colon">foo</a>')
        self.assertEquals('<a href="#with:colon">foo</a>',
                          (html | HTMLSanitizer()).render())

    def test_sanitize_escape_text(self):
        html = HTML('<a href="#">fo&amp;</a>')
        self.assertEquals('<a href="#">fo&amp;</a>',
                          (html | HTMLSanitizer()).render())
        html = HTML('<a href="#">&lt;foo&gt;</a>')
        self.assertEquals('<a href="#">&lt;foo&gt;</a>',
                          (html | HTMLSanitizer()).render())

    def test_sanitize_entityref_text(self):
        html = HTML('<a href="#">fo&ouml;</a>')
        self.assertEquals('<a href="#">foö</a>',
                          (html | HTMLSanitizer()).render(encoding=None))

    def test_sanitize_escape_attr(self):
        html = HTML('<div title="&lt;foo&gt;"></div>')
        self.assertEquals('<div title="&lt;foo&gt;"/>',
                          (html | HTMLSanitizer()).render())

    def test_sanitize_close_empty_tag(self):
        html = HTML('<a href="#">fo<br>o</a>')
        self.assertEquals('<a href="#">fo<br/>o</a>',
                          (html | HTMLSanitizer()).render())

    def test_sanitize_invalid_entity(self):
        html = HTML('&junk;')
        self.assertEquals('&amp;junk;', (html | HTMLSanitizer()).render())

    def test_sanitize_remove_script_elem(self):
        html = HTML('<script>alert("Foo")</script>')
        self.assertEquals('', (html | HTMLSanitizer()).render())
        html = HTML('<SCRIPT SRC="http://example.com/"></SCRIPT>')
        self.assertEquals('', (html | HTMLSanitizer()).render())
        src = '<SCR\0IPT>alert("foo")</SCR\0IPT>'
        self.assert_parse_error_or_equal('&lt;SCR\x00IPT&gt;alert("foo")', src)
        src = '<SCRIPT&XYZ SRC="http://example.com/"></SCRIPT>'
        self.assert_parse_error_or_equal('&lt;SCRIPT&amp;XYZ; '
                                         'SRC="http://example.com/"&gt;', src)

    def test_sanitize_remove_onclick_attr(self):
        html = HTML('<div onclick=\'alert("foo")\' />')
        self.assertEquals('<div/>', (html | HTMLSanitizer()).render())

    def test_sanitize_remove_input_password(self):
        html = HTML('<form><input type="password" /></form>')
        self.assertEquals('<form/>', (html | HTMLSanitizer()).render())

    def test_sanitize_remove_comments(self):
        html = HTML('''<div><!-- conditional comment crap --></div>''')
        self.assertEquals('<div/>', (html | HTMLSanitizer()).render())

    def test_sanitize_remove_style_scripts(self):
        sanitizer = StyleSanitizer()
        # Inline style with url() using javascript: scheme
        html = HTML('<DIV STYLE=\'background: url(javascript:alert("foo"))\'>')
        self.assertEquals('<div/>', (html | sanitizer).render())
        # Inline style with url() using javascript: scheme, using control char
        html = HTML('<DIV STYLE=\'background: url(&#1;javascript:alert("foo"))\'>')
        self.assertEquals('<div/>', (html | sanitizer).render())
        # Inline style with url() using javascript: scheme, in quotes
        html = HTML('<DIV STYLE=\'background: url("javascript:alert(foo)")\'>')
        self.assertEquals('<div/>', (html | sanitizer).render())
        # IE expressions in CSS not allowed
        html = HTML('<DIV STYLE=\'width: expression(alert("foo"));\'>')
        self.assertEquals('<div/>', (html | sanitizer).render())
        html = HTML('<DIV STYLE=\'width: e/**/xpression(alert("foo"));\'>')
        self.assertEquals('<div/>', (html | sanitizer).render())
        html = HTML('<DIV STYLE=\'background: url(javascript:alert("foo"));'
                                 'color: #fff\'>')
        self.assertEquals('<div style="color: #fff"/>',
                          (html | sanitizer).render())
        # Inline style with url() using javascript: scheme, using unicode
        # escapes
        html = HTML('<DIV STYLE=\'background: \\75rl(javascript:alert("foo"))\'>')
        self.assertEquals('<div/>', (html | sanitizer).render())
        html = HTML('<DIV STYLE=\'background: \\000075rl(javascript:alert("foo"))\'>')
        self.assertEquals('<div/>', (html | sanitizer).render())
        html = HTML('<DIV STYLE=\'background: \\75 rl(javascript:alert("foo"))\'>')
        self.assertEquals('<div/>', (html | sanitizer).render())
        html = HTML('<DIV STYLE=\'background: \\000075 rl(javascript:alert("foo"))\'>')
        self.assertEquals('<div/>', (html | sanitizer).render())
        html = HTML('<DIV STYLE=\'background: \\000075\r\nrl(javascript:alert("foo"))\'>')
        self.assertEquals('<div/>', (html | sanitizer).render())

    def test_sanitize_remove_style_phishing(self):
        sanitizer = StyleSanitizer()
        # The position property is not allowed
        html = HTML('<div style="position:absolute;top:0"></div>')
        self.assertEquals('<div style="top:0"/>', (html | sanitizer).render())
        # Normal margins get passed through
        html = HTML('<div style="margin:10px 20px"></div>')
        self.assertEquals('<div style="margin:10px 20px"/>',
                          (html | sanitizer).render())
        # But not negative margins
        html = HTML('<div style="margin:-1000px 0 0"></div>')
        self.assertEquals('<div/>', (html | sanitizer).render())
        html = HTML('<div style="margin-left:-2000px 0 0"></div>')
        self.assertEquals('<div/>', (html | sanitizer).render())
        html = HTML('<div style="margin-left:1em 1em 1em -4000px"></div>')
        self.assertEquals('<div/>', (html | sanitizer).render())

    def test_sanitize_remove_src_javascript(self):
        html = HTML('<img src=\'javascript:alert("foo")\'>')
        self.assertEquals('<img/>', (html | HTMLSanitizer()).render())
        # Case-insensitive protocol matching
        html = HTML('<IMG SRC=\'JaVaScRiPt:alert("foo")\'>')
        self.assertEquals('<img/>', (html | HTMLSanitizer()).render())
        # Grave accents (not parsed)
        src = '<IMG SRC=`javascript:alert("RSnake says, \'foo\'")`>'
        self.assert_parse_error_or_equal('<img/>', src)
        # Protocol encoded using UTF-8 numeric entities
        html = HTML('<IMG SRC=\'&#106;&#97;&#118;&#97;&#115;&#99;&#114;&#105;'
                    '&#112;&#116;&#58;alert("foo")\'>')
        self.assertEquals('<img/>', (html | HTMLSanitizer()).render())
        # Protocol encoded using UTF-8 numeric entities without a semicolon
        # (which is allowed because the max number of digits is used)
        html = HTML('<IMG SRC=\'&#0000106&#0000097&#0000118&#0000097'
                    '&#0000115&#0000099&#0000114&#0000105&#0000112&#0000116'
                    '&#0000058alert("foo")\'>')
        self.assertEquals('<img/>', (html | HTMLSanitizer()).render())
        # Protocol encoded using UTF-8 numeric hex entities without a semicolon
        # (which is allowed because the max number of digits is used)
        html = HTML('<IMG SRC=\'&#x6A&#x61&#x76&#x61&#x73&#x63&#x72&#x69'
                    '&#x70&#x74&#x3A;alert("foo")\'>')
        self.assertEquals('<img/>', (html | HTMLSanitizer()).render())
        # Embedded tab character in protocol
        html = HTML('<IMG SRC=\'jav\tascript:alert("foo");\'>')
        self.assertEquals('<img/>', (html | HTMLSanitizer()).render())
        # Embedded tab character in protocol, but encoded this time
        html = HTML('<IMG SRC=\'jav&#x09;ascript:alert("foo");\'>')
        self.assertEquals('<img/>', (html | HTMLSanitizer()).render())

    def test_sanitize_expression(self):
        html = HTML(r'<div style="top:expression(alert())">XSS</div>')
        self.assertEqual('<div>XSS</div>', str(html | StyleSanitizer()))

    def test_capital_expression(self):
        html = HTML(r'<div style="top:EXPRESSION(alert())">XSS</div>')
        self.assertEqual('<div>XSS</div>', str(html | StyleSanitizer()))

    def test_sanitize_url_with_javascript(self):
        html = HTML('<div style="background-image:url(javascript:alert())">'
                    'XSS</div>')
        self.assertEqual('<div>XSS</div>', str(html | StyleSanitizer()))

    def test_sanitize_capital_url_with_javascript(self):
        html = HTML('<div style="background-image:URL(javascript:alert())">'
                    'XSS</div>')
        self.assertEqual('<div>XSS</div>', str(html | StyleSanitizer()))

    def test_sanitize_unicode_escapes(self):
        html = HTML(r'<div style="top:exp\72 ess\000069 on(alert())">'
                    r'XSS</div>')
        self.assertEqual('<div>XSS</div>', str(html | StyleSanitizer()))

    def test_sanitize_backslash_without_hex(self):
        html = HTML(r'<div style="top:e\xp\ression(alert())">XSS</div>')
        self.assertEqual('<div>XSS</div>', str(html | StyleSanitizer()))
        html = HTML(r'<div style="top:e\\xp\\ression(alert())">XSS</div>')
        self.assertEqual(r'<div style="top:e\\xp\\ression(alert())">'
                         'XSS</div>',
                         str(html | StyleSanitizer()))

    def test_sanitize_unsafe_props(self):
        html = HTML('<div style="POSITION:RELATIVE">XSS</div>')
        self.assertEqual('<div>XSS</div>', str(html | StyleSanitizer()))

        html = HTML('<div style="behavior:url(test.htc)">XSS</div>')
        self.assertEqual('<div>XSS</div>', str(html | StyleSanitizer()))

        html = HTML('<div style="-ms-behavior:url(test.htc) url(#obj)">'
                    'XSS</div>')
        self.assertEqual('<div>XSS</div>', str(html | StyleSanitizer()))

        html = HTML("""<div style="-o-link:'javascript:alert(1)';"""
                    """-o-link-source:current">XSS</div>""")
        self.assertEqual('<div>XSS</div>', str(html | StyleSanitizer()))

        html = HTML("""<div style="-moz-binding:url(xss.xbl)">XSS</div>""")
        self.assertEqual('<div>XSS</div>', str(html | StyleSanitizer()))

    def test_sanitize_negative_margin(self):
        html = HTML('<div style="margin-top:-9999px">XSS</div>')
        self.assertEqual('<div>XSS</div>', str(html | StyleSanitizer()))
        html = HTML('<div style="margin:0 -9999px">XSS</div>')
        self.assertEqual('<div>XSS</div>', str(html | StyleSanitizer()))

    def test_sanitize_css_hack(self):
        html = HTML('<div style="*position:static">XSS</div>')
        self.assertEqual('<div>XSS</div>', str(html | StyleSanitizer()))

        html = HTML('<div style="_margin:-10px">XSS</div>')
        self.assertEqual('<div>XSS</div>', str(html | StyleSanitizer()))

    def test_sanitize_property_name(self):
        html = HTML('<div style="display:none;border-left-color:red;'
                    'user_defined:1;-moz-user-selct:-moz-all">prop</div>')
        self.assertEqual('<div style="display:none; border-left-color:red'
                         '">prop</div>',
                         str(html | StyleSanitizer()))

    def test_sanitize_unicode_expression(self):
        # Fullwidth small letters
        html = HTML('<div style="top:ｅｘｐｒｅｓｓｉｏｎ(alert())">'
                    'XSS</div>')
        self.assertEqual('<div>XSS</div>', str(html | StyleSanitizer()))
        # Fullwidth capital letters
        html = HTML('<div style="top:ＥＸＰＲＥＳＳＩＯＮ(alert())">'
                    'XSS</div>')
        self.assertEqual('<div>XSS</div>', str(html | StyleSanitizer()))
        # IPA extensions
        html = HTML('<div style="top:expʀessɪoɴ(alert())">'
                    'XSS</div>')
        self.assertEqual('<div>XSS</div>', str(html | StyleSanitizer()))

    def test_sanitize_unicode_url(self):
        # IPA extensions
        html = HTML('<div style="background-image:uʀʟ(javascript:alert())">'
                    'XSS</div>')
        self.assertEqual('<div>XSS</div>', str(html | StyleSanitizer()))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(HTMLFormFiller.__module__))
    suite.addTest(unittest.makeSuite(HTMLFormFillerTestCase, 'test'))
    suite.addTest(unittest.makeSuite(HTMLSanitizerTestCase, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
