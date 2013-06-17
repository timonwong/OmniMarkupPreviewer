# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2010 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://genshi.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://genshi.edgewall.org/log/.

from datetime import datetime
import doctest
from gettext import NullTranslations
import unittest

from genshi.core import Attrs
from genshi.template import MarkupTemplate, Context
from genshi.filters.i18n import Translator, extract
from genshi.input import HTML
from genshi.compat import IS_PYTHON2, StringIO


class DummyTranslations(NullTranslations):
    _domains = {}

    def __init__(self, catalog=()):
        NullTranslations.__init__(self)
        self._catalog = catalog or {}
        self.plural = lambda n: n != 1

    def add_domain(self, domain, catalog):
        translation = DummyTranslations(catalog)
        translation.add_fallback(self)
        self._domains[domain] = translation

    def _domain_call(self, func, domain, *args, **kwargs):
        return getattr(self._domains.get(domain, self), func)(*args, **kwargs)

    if IS_PYTHON2:
        def ugettext(self, message):
            missing = object()
            tmsg = self._catalog.get(message, missing)
            if tmsg is missing:
                if self._fallback:
                    return self._fallback.ugettext(message)
                return str(message)
            return tmsg
    else:
        def gettext(self, message):
            missing = object()
            tmsg = self._catalog.get(message, missing)
            if tmsg is missing:
                if self._fallback:
                    return self._fallback.gettext(message)
                return str(message)
            return tmsg

    if IS_PYTHON2:
        def dugettext(self, domain, message):
            return self._domain_call('ugettext', domain, message)
    else:
        def dgettext(self, domain, message):
            return self._domain_call('gettext', domain, message)

    def ungettext(self, msgid1, msgid2, n):
        try:
            return self._catalog[(msgid1, self.plural(n))]
        except KeyError:
            if self._fallback:
                return self._fallback.ngettext(msgid1, msgid2, n)
            if n == 1:
                return msgid1
            else:
                return msgid2

    if not IS_PYTHON2:
        ngettext = ungettext
        del ungettext

    if IS_PYTHON2:
        def dungettext(self, domain, singular, plural, numeral):
            return self._domain_call('ungettext', domain, singular, plural, numeral)
    else:
        def dngettext(self, domain, singular, plural, numeral):
            return self._domain_call('ngettext', domain, singular, plural, numeral)


class TranslatorTestCase(unittest.TestCase):

    def test_translate_included_attribute_text(self):
        """
        Verify that translated attributes end up in a proper `Attrs` instance.
        """
        html = HTML("""<html>
          <span title="Foo"></span>
        </html>""")
        translator = Translator(lambda s: "Voh")
        stream = list(html.filter(translator))
        kind, data, pos = stream[2]
        assert isinstance(data[1], Attrs)

    def test_extract_without_text(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          <p title="Bar">Foo</p>
          ${ngettext("Singular", "Plural", num)}
        </html>""")
        translator = Translator(extract_text=False)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual((3, 'ngettext', ('Singular', 'Plural', None), []),
                         messages[0])

    def test_extract_plural_form(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          ${ngettext("Singular", "Plural", num)}
        </html>""")
        translator = Translator()
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual((2, 'ngettext', ('Singular', 'Plural', None), []),
                         messages[0])

    def test_extract_funky_plural_form(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          ${ngettext(len(items), *widget.display_names)}
        </html>""")
        translator = Translator()
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual((2, 'ngettext', (None, None), []), messages[0])

    def test_extract_gettext_with_unicode_string(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          ${gettext("Grüße")}
        </html>""")
        translator = Translator()
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual((2, 'gettext', 'Gr\xfc\xdfe', []), messages[0])

    def test_extract_included_attribute_text(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          <span title="Foo"></span>
        </html>""")
        translator = Translator()
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual((2, None, 'Foo', []), messages[0])

    def test_extract_attribute_expr(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          <input type="submit" value="${_('Save')}" />
        </html>""")
        translator = Translator()
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual((2, '_', 'Save', []), messages[0])

    def test_extract_non_included_attribute_interpolated(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          <a href="#anchor_${num}">Foo</a>
        </html>""")
        translator = Translator()
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual((2, None, 'Foo', []), messages[0])

    def test_extract_text_from_sub(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          <py:if test="foo">Foo</py:if>
        </html>""")
        translator = Translator()
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual((2, None, 'Foo', []), messages[0])

    def test_ignore_tag_with_fixed_xml_lang(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          <p xml:lang="en">(c) 2007 Edgewall Software</p>
        </html>""")
        translator = Translator()
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(0, len(messages))

    def test_extract_tag_with_variable_xml_lang(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          <p xml:lang="${lang}">(c) 2007 Edgewall Software</p>
        </html>""")
        translator = Translator()
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual((2, None, '(c) 2007 Edgewall Software', []),
                         messages[0])

    def test_ignore_attribute_with_expression(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          <input type="submit" value="Reply" title="Reply to comment $num" />
        </html>""")
        translator = Translator()
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(0, len(messages))

    def test_translate_with_translations_object(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="" i18n:comment="As in foo bar">Foo</p>
        </html>""")
        translator = Translator(DummyTranslations({'Foo': 'Voh'}))
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>Voh</p>
        </html>""", tmpl.generate().render())


class MsgDirectiveTestCase(unittest.TestCase):

    def test_extract_i18n_msg(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="">
            Please see <a href="help.html">Help</a> for details.
          </p>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual('Please see [1:Help] for details.', messages[0][2])

    def test_translate_i18n_msg(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="">
            Please see <a href="help.html">Help</a> for details.
          </p>
        </html>""")
        gettext = lambda s: "Für Details siehe bitte [1:Hilfe]."
        translator = Translator(gettext)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>Für Details siehe bitte <a href="help.html">Hilfe</a>.</p>
        </html>""".encode('utf-8'), tmpl.generate().render(encoding='utf-8'))

    def test_extract_i18n_msg_nonewline(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="">Please see <a href="help.html">Help</a></p>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual('Please see [1:Help]', messages[0][2])

    def test_translate_i18n_msg_nonewline(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="">Please see <a href="help.html">Help</a></p>
        </html>""")
        gettext = lambda s: "Für Details siehe bitte [1:Hilfe]"
        translator = Translator(gettext)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>Für Details siehe bitte <a href="help.html">Hilfe</a></p>
        </html>""", tmpl.generate().render())

    def test_extract_i18n_msg_elt_nonewline(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <i18n:msg>Please see <a href="help.html">Help</a></i18n:msg>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual('Please see [1:Help]', messages[0][2])

    def test_translate_i18n_msg_elt_nonewline(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <i18n:msg>Please see <a href="help.html">Help</a></i18n:msg>
        </html>""")
        gettext = lambda s: "Für Details siehe bitte [1:Hilfe]"
        translator = Translator(gettext)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          Für Details siehe bitte <a href="help.html">Hilfe</a>
        </html>""".encode('utf-8'), tmpl.generate().render(encoding='utf-8'))

    def test_extract_i18n_msg_with_attributes(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="" title="A helpful paragraph">
            Please see <a href="help.html" title="Click for help">Help</a>
          </p>
        </html>""")
        translator = Translator()
        translator.setup(tmpl)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(3, len(messages))
        self.assertEqual('A helpful paragraph', messages[0][2])
        self.assertEqual(3, messages[0][0])
        self.assertEqual('Click for help', messages[1][2])
        self.assertEqual(4, messages[1][0])
        self.assertEqual('Please see [1:Help]', messages[2][2])
        self.assertEqual(3, messages[2][0])

    def test_translate_i18n_msg_with_attributes(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="" title="A helpful paragraph">
            Please see <a href="help.html" title="Click for help">Help</a>
          </p>
        </html>""")
        translator = Translator(lambda msgid: {
            'A helpful paragraph': 'Ein hilfreicher Absatz',
            'Click for help': 'Klicken für Hilfe',
            'Please see [1:Help]': 'Siehe bitte [1:Hilfe]'
        }[msgid])
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p title="Ein hilfreicher Absatz">Siehe bitte <a href="help.html" title="Klicken für Hilfe">Hilfe</a></p>
        </html>""", tmpl.generate().render(encoding=None))

    def test_extract_i18n_msg_with_dynamic_attributes(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="" title="${_('A helpful paragraph')}">
            Please see <a href="help.html" title="${_('Click for help')}">Help</a>
          </p>
        </html>""")
        translator = Translator()
        translator.setup(tmpl)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(3, len(messages))
        self.assertEqual('A helpful paragraph', messages[0][2])
        self.assertEqual(3, messages[0][0])
        self.assertEqual('Click for help', messages[1][2])
        self.assertEqual(4, messages[1][0])
        self.assertEqual('Please see [1:Help]', messages[2][2])
        self.assertEqual(3, messages[2][0])

    def test_translate_i18n_msg_with_dynamic_attributes(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="" title="${_('A helpful paragraph')}">
            Please see <a href="help.html" title="${_('Click for help')}">Help</a>
          </p>
        </html>""")
        translator = Translator(lambda msgid: {
            'A helpful paragraph': 'Ein hilfreicher Absatz',
            'Click for help': 'Klicken für Hilfe',
            'Please see [1:Help]': 'Siehe bitte [1:Hilfe]'
        }[msgid])
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p title="Ein hilfreicher Absatz">Siehe bitte <a href="help.html" title="Klicken für Hilfe">Hilfe</a></p>
        </html>""", tmpl.generate(_=translator.translate).render(encoding=None))

    def test_extract_i18n_msg_as_element_with_attributes(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <i18n:msg params="">
            Please see <a href="help.html" title="Click for help">Help</a>
          </i18n:msg>
        </html>""")
        translator = Translator()
        translator.setup(tmpl)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(2, len(messages))
        self.assertEqual('Click for help', messages[0][2])
        self.assertEqual(4, messages[0][0])
        self.assertEqual('Please see [1:Help]', messages[1][2])
        self.assertEqual(3, messages[1][0])

    def test_translate_i18n_msg_as_element_with_attributes(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <i18n:msg params="">
            Please see <a href="help.html" title="Click for help">Help</a>
          </i18n:msg>
        </html>""")
        translator = Translator(lambda msgid: {
            'Click for help': 'Klicken für Hilfe',
            'Please see [1:Help]': 'Siehe bitte [1:Hilfe]'
        }[msgid])
        translator.setup(tmpl)
        self.assertEqual("""<html>
          Siehe bitte <a href="help.html" title="Klicken für Hilfe">Hilfe</a>
        </html>""", tmpl.generate().render(encoding=None))

    def test_extract_i18n_msg_nested(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="">
            Please see <a href="help.html"><em>Help</em> page</a> for details.
          </p>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual('Please see [1:[2:Help] page] for details.',
                         messages[0][2])

    def test_translate_i18n_msg_nested(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="">
            Please see <a href="help.html"><em>Help</em> page</a> for details.
          </p>
        </html>""")
        gettext = lambda s: "Für Details siehe bitte [1:[2:Hilfeseite]]."
        translator = Translator(gettext)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>Für Details siehe bitte <a href="help.html"><em>Hilfeseite</em></a>.</p>
        </html>""", tmpl.generate().render())

    def test_extract_i18n_msg_label_with_nested_input(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <div i18n:msg="">
            <label><input type="text" size="3" name="daysback" value="30" /> days back</label>
          </div>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual('[1:[2:] days back]',
                         messages[0][2])

    def test_translate_i18n_msg_label_with_nested_input(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <div i18n:msg="">
            <label><input type="text" size="3" name="daysback" value="30" /> foo bar</label>
          </div>
        </html>""")
        gettext = lambda s: "[1:[2:] foo bar]"
        translator = Translator(gettext)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <div><label><input type="text" size="3" name="daysback" value="30"/> foo bar</label></div>
        </html>""", tmpl.generate().render())

    def test_extract_i18n_msg_empty(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="">
            Show me <input type="text" name="num" /> entries per page.
          </p>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual('Show me [1:] entries per page.', messages[0][2])

    def test_translate_i18n_msg_empty(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="">
            Show me <input type="text" name="num" /> entries per page.
          </p>
        </html>""")
        gettext = lambda s: "[1:] Einträge pro Seite anzeigen."
        translator = Translator(gettext)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p><input type="text" name="num"/> Einträge pro Seite anzeigen.</p>
        </html>""", tmpl.generate().render())

    def test_extract_i18n_msg_multiple(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="">
            Please see <a href="help.html">Help</a> for <em>details</em>.
          </p>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual('Please see [1:Help] for [2:details].', messages[0][2])

    def test_translate_i18n_msg_multiple(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="">
            Please see <a href="help.html">Help</a> for <em>details</em>.
          </p>
        </html>""")
        gettext = lambda s: "Für [2:Details] siehe bitte [1:Hilfe]."
        translator = Translator(gettext)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>Für <em>Details</em> siehe bitte <a href="help.html">Hilfe</a>.</p>
        </html>""", tmpl.generate().render())

    def test_extract_i18n_msg_multiple_empty(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="">
            Show me <input type="text" name="num" /> entries per page, starting at page <input type="text" name="num" />.
          </p>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual('Show me [1:] entries per page, starting at page [2:].',
                         messages[0][2])

    def test_translate_i18n_msg_multiple_empty(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="">
            Show me <input type="text" name="num" /> entries per page, starting at page <input type="text" name="num" />.
          </p>
        </html>""", encoding='utf-8')
        gettext = lambda s: "[1:] Einträge pro Seite, beginnend auf Seite [2:]."
        translator = Translator(gettext)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p><input type="text" name="num"/> Eintr\u00E4ge pro Seite, beginnend auf Seite <input type="text" name="num"/>.</p>
        </html>""".encode('utf-8'), tmpl.generate().render(encoding='utf-8'))

    def test_extract_i18n_msg_with_param(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="name">
            Hello, ${user.name}!
          </p>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual('Hello, %(name)s!', messages[0][2])

    def test_translate_i18n_msg_with_param(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="name">
            Hello, ${user.name}!
          </p>
        </html>""")
        gettext = lambda s: "Hallo, %(name)s!"
        translator = Translator(gettext)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>Hallo, Jim!</p>
        </html>""", tmpl.generate(user=dict(name='Jim')).render())

    def test_translate_i18n_msg_with_param_reordered(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="name">
            Hello, ${user.name}!
          </p>
        </html>""")
        gettext = lambda s: "%(name)s, sei gegrüßt!"
        translator = Translator(gettext)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>Jim, sei gegrüßt!</p>
        </html>""", tmpl.generate(user=dict(name='Jim')).render())

    def test_translate_i18n_msg_with_attribute_param(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="">
            Hello, <a href="#${anchor}">dude</a>!
          </p>
        </html>""")
        gettext = lambda s: "Sei gegrüßt, [1:Alter]!"
        translator = Translator(gettext)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>Sei gegrüßt, <a href="#42">Alter</a>!</p>
        </html>""", tmpl.generate(anchor='42').render())

    def test_extract_i18n_msg_with_two_params(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="name, time">
            Posted by ${post.author} at ${entry.time.strftime('%H:%m')}
          </p>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual('Posted by %(name)s at %(time)s', messages[0][2])

    def test_translate_i18n_msg_with_two_params(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="name, time">
            Written by ${entry.author} at ${entry.time.strftime('%H:%M')}
          </p>
        </html>""")
        gettext = lambda s: "%(name)s schrieb dies um %(time)s"
        translator = Translator(gettext)
        translator.setup(tmpl)
        entry = {
            'author': 'Jim',
            'time': datetime(2008, 4, 1, 14, 30)
        }
        self.assertEqual("""<html>
          <p>Jim schrieb dies um 14:30</p>
        </html>""", tmpl.generate(entry=entry).render())

    def test_extract_i18n_msg_with_directive(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="">
            Show me <input type="text" name="num" py:attrs="{'value': x}" /> entries per page.
          </p>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual('Show me [1:] entries per page.', messages[0][2])

    def test_translate_i18n_msg_with_directive(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="">
            Show me <input type="text" name="num" py:attrs="{'value': 'x'}" /> entries per page.
          </p>
        </html>""")
        gettext = lambda s: "[1:] Einträge pro Seite anzeigen."
        translator = Translator(gettext)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p><input type="text" name="num" value="x"/> Einträge pro Seite anzeigen.</p>
        </html>""", tmpl.generate().render())

    def test_extract_i18n_msg_with_comment(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:comment="As in foo bar" i18n:msg="">Foo</p>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual((3, None, 'Foo', ['As in foo bar']), messages[0])
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="" i18n:comment="As in foo bar">Foo</p>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual((3, None, 'Foo', ['As in foo bar']), messages[0])

    def test_translate_i18n_msg_with_comment(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="" i18n:comment="As in foo bar">Foo</p>
        </html>""")
        gettext = lambda s: "Voh"
        translator = Translator(gettext)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>Voh</p>
        </html>""", tmpl.generate().render())

    def test_extract_i18n_msg_with_attr(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="" title="Foo bar">Foo</p>
        </html>""")
        translator = Translator()
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(2, len(messages))
        self.assertEqual((3, None, 'Foo bar', []), messages[0])
        self.assertEqual((3, None, 'Foo', []), messages[1])

    def test_translate_i18n_msg_with_attr(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="" title="Foo bar">Foo</p>
        </html>""")
        gettext = lambda s: "Voh"
        translator = Translator(DummyTranslations({
            'Foo': 'Voh',
            'Foo bar': 'Voh bär'
        }))
        tmpl.filters.insert(0, translator)
        tmpl.add_directives(Translator.NAMESPACE, translator)
        self.assertEqual("""<html>
          <p title="Voh bär">Voh</p>
        </html>""", tmpl.generate().render())

    def test_translate_i18n_msg_and_py_strip_directives(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="" py:strip="">Foo</p>
          <p py:strip="" i18n:msg="">Foo</p>
        </html>""")
        translator = Translator(DummyTranslations({'Foo': 'Voh'}))
        translator.setup(tmpl)
        self.assertEqual("""<html>
          Voh
          Voh
        </html>""", tmpl.generate().render())

    def test_i18n_msg_ticket_300_extract(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <i18n:msg params="date, author">
            Changed ${ '10/12/2008' } ago by ${ 'me, the author' }
          </i18n:msg>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual(
            (3, None, 'Changed %(date)s ago by %(author)s', []), messages[0]
        )

    def test_i18n_msg_ticket_300_translate(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <i18n:msg params="date, author">
            Changed ${ date } ago by ${ author }
          </i18n:msg>
        </html>""")
        translations = DummyTranslations({
            'Changed %(date)s ago by %(author)s': 'Modificado à %(date)s por %(author)s'
        })
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          Modificado à um dia por Pedro
        </html>""".encode('utf-8'), tmpl.generate(date='um dia', author="Pedro").render(encoding='utf-8'))


    def test_i18n_msg_ticket_251_extract(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg=""><tt><b>Translation[&nbsp;0&nbsp;]</b>: <em>One coin</em></tt></p>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual(
            (3, None, '[1:[2:Translation\\[\xa00\xa0\\]]: [3:One coin]]', []), messages[0]
        )

    def test_i18n_msg_ticket_251_translate(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg=""><tt><b>Translation[&nbsp;0&nbsp;]</b>: <em>One coin</em></tt></p>
        </html>""")
        translations = DummyTranslations({
            '[1:[2:Translation\\[\xa00\xa0\\]]: [3:One coin]]':
                '[1:[2:Trandução\\[\xa00\xa0\\]]: [3:Uma moeda]]'
        })
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p><tt><b>Trandução[ 0 ]</b>: <em>Uma moeda</em></tt></p>
        </html>""".encode('utf-8'), tmpl.generate().render(encoding='utf-8'))

    def test_extract_i18n_msg_with_other_directives_nested(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="" py:with="q = quote_plus(message[:80])">Before you do that, though, please first try
            <strong><a href="${trac.homepage}search?ticket=yes&amp;noquickjump=1&amp;q=$q">searching</a>
            for similar issues</strong>, as it is quite likely that this problem
            has been reported before. For questions about installation
            and configuration of Trac, please try the
            <a href="${trac.homepage}wiki/MailingList">mailing list</a>
            instead of filing a ticket.
          </p>
        </html>""")
        translator = Translator()
        translator.setup(tmpl)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual(
            'Before you do that, though, please first try\n            '
            '[1:[2:searching]\n            for similar issues], as it is '
            'quite likely that this problem\n            has been reported '
            'before. For questions about installation\n            and '
            'configuration of Trac, please try the\n            '
            '[3:mailing list]\n            instead of filing a ticket.',
            messages[0][2]
        )

    def test_translate_i18n_msg_with_other_directives_nested(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="">Before you do that, though, please first try
            <strong><a href="${trac.homepage}search?ticket=yes&amp;noquickjump=1&amp;q=q">searching</a>
            for similar issues</strong>, as it is quite likely that this problem
            has been reported before. For questions about installation
            and configuration of Trac, please try the
            <a href="${trac.homepage}wiki/MailingList">mailing list</a>
            instead of filing a ticket.
          </p>
        </html>""")
        translations = DummyTranslations({
            'Before you do that, though, please first try\n            '
            '[1:[2:searching]\n            for similar issues], as it is '
            'quite likely that this problem\n            has been reported '
            'before. For questions about installation\n            and '
            'configuration of Trac, please try the\n            '
            '[3:mailing list]\n            instead of filing a ticket.':
                'Antes de o fazer, porém,\n            '
                '[1:por favor tente [2:procurar]\n            por problemas semelhantes], uma vez que '
                'é muito provável que este problema\n            já tenha sido reportado '
                'anteriormente. Para questões relativas à instalação\n            e '
                'configuração do Trac, por favor tente a\n            '
                '[3:mailing list]\n            em vez de criar um assunto.'
        })
        translator = Translator(translations)
        translator.setup(tmpl)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        ctx = Context()
        ctx.push({'trac': {'homepage': 'http://trac.edgewall.org/'}})
        self.assertEqual("""<html>
          <p>Antes de o fazer, porém,
            <strong>por favor tente <a href="http://trac.edgewall.org/search?ticket=yes&amp;noquickjump=1&amp;q=q">procurar</a>
            por problemas semelhantes</strong>, uma vez que é muito provável que este problema
            já tenha sido reportado anteriormente. Para questões relativas à instalação
            e configuração do Trac, por favor tente a
            <a href="http://trac.edgewall.org/wiki/MailingList">mailing list</a>
            em vez de criar um assunto.</p>
        </html>""", tmpl.generate(ctx).render())

    def test_i18n_msg_with_other_nested_directives_with_reordered_content(self):
        # See: http://genshi.edgewall.org/ticket/300#comment:10
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p py:if="not editable" class="hint" i18n:msg="">
            <strong>Note:</strong> This repository is defined in
            <code><a href="${ 'href.wiki(TracIni)' }">trac.ini</a></code>
            and cannot be edited on this page.
          </p>
        </html>""")
        translations = DummyTranslations({
            '[1:Note:] This repository is defined in\n            '
            '[2:[3:trac.ini]]\n            and cannot be edited on this page.':
                '[1:Nota:] Este repositório está definido em \n           '
                '[2:[3:trac.ini]]\n            e não pode ser editado nesta página.',
        })
        translator = Translator(translations)
        translator.setup(tmpl)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual(
            '[1:Note:] This repository is defined in\n            '
            '[2:[3:trac.ini]]\n            and cannot be edited on this page.',
            messages[0][2]
        )
        self.assertEqual("""<html>
          <p class="hint"><strong>Nota:</strong> Este repositório está definido em
           <code><a href="href.wiki(TracIni)">trac.ini</a></code>
            e não pode ser editado nesta página.</p>
        </html>""".encode('utf-8'), tmpl.generate(editable=False).render(encoding='utf-8'))

    def test_extract_i18n_msg_with_py_strip(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="" py:strip="">
            Please see <a href="help.html">Help</a> for details.
          </p>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual((3, None, 'Please see [1:Help] for details.', []),
                         messages[0])

    def test_extract_i18n_msg_with_py_strip_and_comment(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="" py:strip="" i18n:comment="Foo">
            Please see <a href="help.html">Help</a> for details.
          </p>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual((3, None, 'Please see [1:Help] for details.',
                          ['Foo']), messages[0])

    def test_translate_i18n_msg_and_comment_with_py_strip_directives(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="" i18n:comment="As in foo bar" py:strip="">Foo</p>
          <p py:strip="" i18n:msg="" i18n:comment="As in foo bar">Foo</p>
        </html>""")
        translator = Translator(DummyTranslations({'Foo': 'Voh'}))
        translator.setup(tmpl)
        self.assertEqual("""<html>
          Voh
          Voh
        </html>""", tmpl.generate().render())

    def test_translate_i18n_msg_ticket_404(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="first,second">
            $first <span>$second</span> KEPT <span>Inside a tag</span> tail
          </p></html>""")
        translator = Translator(DummyTranslations())
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>FIRST <span>SECOND</span> KEPT <span>Inside a tag</span> tail"""
          """</p></html>""",
          tmpl.generate(first="FIRST", second="SECOND").render())


class ChooseDirectiveTestCase(unittest.TestCase):

    def test_translate_i18n_choose_as_attribute(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <div i18n:choose="one">
            <p i18n:singular="">FooBar</p>
            <p i18n:plural="">FooBars</p>
          </div>
          <div i18n:choose="two">
            <p i18n:singular="">FooBar</p>
            <p i18n:plural="">FooBars</p>
          </div>
        </html>""")
        translations = DummyTranslations()
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <div>
            <p>FooBar</p>
          </div>
          <div>
            <p>FooBars</p>
          </div>
        </html>""", tmpl.generate(one=1, two=2).render())

    def test_translate_i18n_choose_as_directive(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
        <i18n:choose numeral="two">
          <p i18n:singular="">FooBar</p>
          <p i18n:plural="">FooBars</p>
        </i18n:choose>
        <i18n:choose numeral="one">
          <p i18n:singular="">FooBar</p>
          <p i18n:plural="">FooBars</p>
        </i18n:choose>
        </html>""")
        translations = DummyTranslations()
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>FooBars</p>
          <p>FooBar</p>
        </html>""", tmpl.generate(one=1, two=2).render())

    def test_translate_i18n_choose_as_directive_singular_and_plural_with_strip(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
        <i18n:choose numeral="two">
          <p i18n:singular="" py:strip="">FooBar Singular with Strip</p>
          <p i18n:plural="">FooBars Plural without Strip</p>
        </i18n:choose>
        <i18n:choose numeral="two">
          <p i18n:singular="">FooBar singular without strip</p>
          <p i18n:plural="" py:strip="">FooBars plural with strip</p>
        </i18n:choose>
        <i18n:choose numeral="one">
          <p i18n:singular="">FooBar singular without strip</p>
          <p i18n:plural="" py:strip="">FooBars plural with strip</p>
        </i18n:choose>
        <i18n:choose numeral="one">
          <p i18n:singular="" py:strip="">FooBar singular with strip</p>
          <p i18n:plural="">FooBars plural without strip</p>
        </i18n:choose>
        </html>""")
        translations = DummyTranslations()
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>FooBars Plural without Strip</p>
          FooBars plural with strip
          <p>FooBar singular without strip</p>
          FooBar singular with strip
        </html>""", tmpl.generate(one=1, two=2).render())

    def test_translate_i18n_choose_plural_singular_as_directive(self):
        # Ticket 371
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
        <i18n:choose numeral="two">
          <i18n:singular>FooBar</i18n:singular>
          <i18n:plural>FooBars</i18n:plural>
        </i18n:choose>
        <i18n:choose numeral="one">
          <i18n:singular>FooBar</i18n:singular>
          <i18n:plural>FooBars</i18n:plural>
        </i18n:choose>
        </html>""")
        translations = DummyTranslations({
            ('FooBar', 0): 'FuBar',
            ('FooBars', 1): 'FuBars',
            'FooBar': 'FuBar',
            'FooBars': 'FuBars',
        })
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          FuBars
          FuBar
        </html>""", tmpl.generate(one=1, two=2).render())

    def test_translate_i18n_choose_as_attribute_with_params(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <div i18n:choose="two; fname, lname">
            <p i18n:singular="">Foo $fname $lname</p>
            <p i18n:plural="">Foos $fname $lname</p>
          </div>
        </html>""")
        translations = DummyTranslations({
            ('Foo %(fname)s %(lname)s', 0): 'Voh %(fname)s %(lname)s',
            ('Foo %(fname)s %(lname)s', 1): 'Vohs %(fname)s %(lname)s',
                 'Foo %(fname)s %(lname)s': 'Voh %(fname)s %(lname)s',
                'Foos %(fname)s %(lname)s': 'Vohs %(fname)s %(lname)s',
        })
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <div>
            <p>Vohs John Doe</p>
          </div>
        </html>""", tmpl.generate(two=2, fname='John', lname='Doe').render())

    def test_translate_i18n_choose_as_attribute_with_params_and_domain_as_param(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n"
            i18n:domain="foo">
          <div i18n:choose="two; fname, lname">
            <p i18n:singular="">Foo $fname $lname</p>
            <p i18n:plural="">Foos $fname $lname</p>
          </div>
        </html>""")
        translations = DummyTranslations()
        translations.add_domain('foo', {
            ('Foo %(fname)s %(lname)s', 0): 'Voh %(fname)s %(lname)s',
            ('Foo %(fname)s %(lname)s', 1): 'Vohs %(fname)s %(lname)s',
                 'Foo %(fname)s %(lname)s': 'Voh %(fname)s %(lname)s',
                'Foos %(fname)s %(lname)s': 'Vohs %(fname)s %(lname)s',
        })
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <div>
            <p>Vohs John Doe</p>
          </div>
        </html>""", tmpl.generate(two=2, fname='John', lname='Doe').render())

    def test_translate_i18n_choose_as_directive_with_params(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
        <i18n:choose numeral="two" params="fname, lname">
          <p i18n:singular="">Foo ${fname} ${lname}</p>
          <p i18n:plural="">Foos ${fname} ${lname}</p>
        </i18n:choose>
        <i18n:choose numeral="one" params="fname, lname">
          <p i18n:singular="">Foo ${fname} ${lname}</p>
          <p i18n:plural="">Foos ${fname} ${lname}</p>
        </i18n:choose>
        </html>""")
        translations = DummyTranslations({
            ('Foo %(fname)s %(lname)s', 0): 'Voh %(fname)s %(lname)s',
            ('Foo %(fname)s %(lname)s', 1): 'Vohs %(fname)s %(lname)s',
                 'Foo %(fname)s %(lname)s': 'Voh %(fname)s %(lname)s',
                'Foos %(fname)s %(lname)s': 'Vohs %(fname)s %(lname)s',
        })
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>Vohs John Doe</p>
          <p>Voh John Doe</p>
        </html>""", tmpl.generate(one=1, two=2,
                                  fname='John', lname='Doe').render())

    def test_translate_i18n_choose_as_directive_with_params_and_domain_as_directive(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
        <i18n:domain name="foo">
        <i18n:choose numeral="two" params="fname, lname">
          <p i18n:singular="">Foo ${fname} ${lname}</p>
          <p i18n:plural="">Foos ${fname} ${lname}</p>
        </i18n:choose>
        </i18n:domain>
        <i18n:choose numeral="one" params="fname, lname">
          <p i18n:singular="">Foo ${fname} ${lname}</p>
          <p i18n:plural="">Foos ${fname} ${lname}</p>
        </i18n:choose>
        </html>""")
        translations = DummyTranslations()
        translations.add_domain('foo', {
            ('Foo %(fname)s %(lname)s', 0): 'Voh %(fname)s %(lname)s',
            ('Foo %(fname)s %(lname)s', 1): 'Vohs %(fname)s %(lname)s',
                 'Foo %(fname)s %(lname)s': 'Voh %(fname)s %(lname)s',
                'Foos %(fname)s %(lname)s': 'Vohs %(fname)s %(lname)s',
        })
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>Vohs John Doe</p>
          <p>Foo John Doe</p>
        </html>""", tmpl.generate(one=1, two=2,
                                  fname='John', lname='Doe').render())

    def test_extract_i18n_choose_as_attribute(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <div i18n:choose="one">
            <p i18n:singular="">FooBar</p>
            <p i18n:plural="">FooBars</p>
          </div>
          <div i18n:choose="two">
            <p i18n:singular="">FooBar</p>
            <p i18n:plural="">FooBars</p>
          </div>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(2, len(messages))
        self.assertEqual((3, 'ngettext', ('FooBar', 'FooBars'), []), messages[0])
        self.assertEqual((7, 'ngettext', ('FooBar', 'FooBars'), []), messages[1])

    def test_extract_i18n_choose_as_directive(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
        <i18n:choose numeral="two">
          <p i18n:singular="">FooBar</p>
          <p i18n:plural="">FooBars</p>
        </i18n:choose>
        <i18n:choose numeral="one">
          <p i18n:singular="">FooBar</p>
          <p i18n:plural="">FooBars</p>
        </i18n:choose>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(2, len(messages))
        self.assertEqual((3, 'ngettext', ('FooBar', 'FooBars'), []), messages[0])
        self.assertEqual((7, 'ngettext', ('FooBar', 'FooBars'), []), messages[1])

    def test_extract_i18n_choose_as_attribute_with_params(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <div i18n:choose="two; fname, lname">
            <p i18n:singular="">Foo $fname $lname</p>
            <p i18n:plural="">Foos $fname $lname</p>
          </div>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual((3, 'ngettext', ('Foo %(fname)s %(lname)s',
                                          'Foos %(fname)s %(lname)s'), []),
                         messages[0])

    def test_extract_i18n_choose_as_attribute_with_params_and_domain_as_param(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n"
            i18n:domain="foo">
          <div i18n:choose="two; fname, lname">
            <p i18n:singular="">Foo $fname $lname</p>
            <p i18n:plural="">Foos $fname $lname</p>
          </div>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual((4, 'ngettext', ('Foo %(fname)s %(lname)s',
                                          'Foos %(fname)s %(lname)s'), []),
                         messages[0])

    def test_extract_i18n_choose_as_directive_with_params(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
        <i18n:choose numeral="two" params="fname, lname">
          <p i18n:singular="">Foo ${fname} ${lname}</p>
          <p i18n:plural="">Foos ${fname} ${lname}</p>
        </i18n:choose>
        <i18n:choose numeral="one" params="fname, lname">
          <p i18n:singular="">Foo ${fname} ${lname}</p>
          <p i18n:plural="">Foos ${fname} ${lname}</p>
        </i18n:choose>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(2, len(messages))
        self.assertEqual((3, 'ngettext', ('Foo %(fname)s %(lname)s',
                                          'Foos %(fname)s %(lname)s'), []),
                         messages[0])
        self.assertEqual((7, 'ngettext', ('Foo %(fname)s %(lname)s',
                                          'Foos %(fname)s %(lname)s'), []),
                         messages[1])

    def test_extract_i18n_choose_as_directive_with_params_and_domain_as_directive(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
        <i18n:domain name="foo">
        <i18n:choose numeral="two" params="fname, lname">
          <p i18n:singular="">Foo ${fname} ${lname}</p>
          <p i18n:plural="">Foos ${fname} ${lname}</p>
        </i18n:choose>
        </i18n:domain>
        <i18n:choose numeral="one" params="fname, lname">
          <p i18n:singular="">Foo ${fname} ${lname}</p>
          <p i18n:plural="">Foos ${fname} ${lname}</p>
        </i18n:choose>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(2, len(messages))
        self.assertEqual((4, 'ngettext', ('Foo %(fname)s %(lname)s',
                                          'Foos %(fname)s %(lname)s'), []),
                         messages[0])
        self.assertEqual((9, 'ngettext', ('Foo %(fname)s %(lname)s',
                                          'Foos %(fname)s %(lname)s'), []),
                         messages[1])

    def test_extract_i18n_choose_as_attribute_with_params_and_comment(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <div i18n:choose="two; fname, lname" i18n:comment="As in Foo Bar">
            <p i18n:singular="">Foo $fname $lname</p>
            <p i18n:plural="">Foos $fname $lname</p>
          </div>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual((3, 'ngettext', ('Foo %(fname)s %(lname)s',
                                          'Foos %(fname)s %(lname)s'),
                          ['As in Foo Bar']),
                         messages[0])

    def test_extract_i18n_choose_as_directive_with_params_and_comment(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
        <i18n:choose numeral="two" params="fname, lname" i18n:comment="As in Foo Bar">
          <p i18n:singular="">Foo ${fname} ${lname}</p>
          <p i18n:plural="">Foos ${fname} ${lname}</p>
        </i18n:choose>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual((3, 'ngettext', ('Foo %(fname)s %(lname)s',
                                          'Foos %(fname)s %(lname)s'),
                          ['As in Foo Bar']),
                         messages[0])

    def test_extract_i18n_choose_with_attributes(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:choose="num; num" title="Things">
            <i18n:singular>
              There is <a href="$link" title="View thing">${num} thing</a>.
            </i18n:singular>
            <i18n:plural>
              There are <a href="$link" title="View things">${num} things</a>.
            </i18n:plural>
          </p>
        </html>""")
        translator = Translator()
        translator.setup(tmpl)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(4, len(messages))
        self.assertEqual((3, None, 'Things', []), messages[0])
        self.assertEqual((5, None, 'View thing', []), messages[1])
        self.assertEqual((8, None, 'View things', []), messages[2])
        self.assertEqual(
            (3, 'ngettext', ('There is [1:%(num)s thing].',
                             'There are [1:%(num)s things].'), []),
            messages[3])

    def test_translate_i18n_choose_with_attributes(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:choose="num; num" title="Things">
            <i18n:singular>
              There is <a href="$link" title="View thing">${num} thing</a>.
            </i18n:singular>
            <i18n:plural>
              There are <a href="$link" title="View things">${num} things</a>.
            </i18n:plural>
          </p>
        </html>""")
        translations = DummyTranslations({
            'Things': 'Sachen',
            'View thing': 'Sache betrachten',
            'View things': 'Sachen betrachten',
            ('There is [1:%(num)s thing].', 0): 'Da ist [1:%(num)s Sache].',
            ('There is [1:%(num)s thing].', 1): 'Da sind [1:%(num)s Sachen].'
        })
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p title="Sachen">
            Da ist <a href="/things" title="Sache betrachten">1 Sache</a>.
          </p>
        </html>""", tmpl.generate(link="/things", num=1).render(encoding=None))
        self.assertEqual("""<html>
          <p title="Sachen">
            Da sind <a href="/things" title="Sachen betrachten">3 Sachen</a>.
          </p>
        </html>""", tmpl.generate(link="/things", num=3).render(encoding=None))

    def test_extract_i18n_choose_as_element_with_attributes(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <i18n:choose numeral="num" params="num">
            <p i18n:singular="" title="Things">
              There is <a href="$link" title="View thing">${num} thing</a>.
            </p>
            <p i18n:plural="" title="Things">
              There are <a href="$link" title="View things">${num} things</a>.
            </p>
          </i18n:choose>
        </html>""")
        translator = Translator()
        translator.setup(tmpl)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(5, len(messages))
        self.assertEqual((4, None, 'Things', []), messages[0])
        self.assertEqual((5, None, 'View thing', []), messages[1])
        self.assertEqual((7, None, 'Things', []), messages[2])
        self.assertEqual((8, None, 'View things', []), messages[3])
        self.assertEqual(
            (3, 'ngettext', ('There is [1:%(num)s thing].',
                             'There are [1:%(num)s things].'), []),
            messages[4])

    def test_translate_i18n_choose_as_element_with_attributes(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <i18n:choose numeral="num" params="num">
            <p i18n:singular="" title="Things">
              There is <a href="$link" title="View thing">${num} thing</a>.
            </p>
            <p i18n:plural="" title="Things">
              There are <a href="$link" title="View things">${num} things</a>.
            </p>
          </i18n:choose>
        </html>""")
        translations = DummyTranslations({
            'Things': 'Sachen',
            'View thing': 'Sache betrachten',
            'View things': 'Sachen betrachten',
            ('There is [1:%(num)s thing].', 0): 'Da ist [1:%(num)s Sache].',
            ('There is [1:%(num)s thing].', 1): 'Da sind [1:%(num)s Sachen].'
        })
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
            <p title="Sachen">Da ist <a href="/things" title="Sache betrachten">1 Sache</a>.</p>
        </html>""", tmpl.generate(link="/things", num=1).render(encoding=None))
        self.assertEqual("""<html>
            <p title="Sachen">Da sind <a href="/things" title="Sachen betrachten">3 Sachen</a>.</p>
        </html>""", tmpl.generate(link="/things", num=3).render(encoding=None))

    def test_translate_i18n_choose_and_py_strip(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <div i18n:choose="two; fname, lname">
            <p i18n:singular="">Foo $fname $lname</p>
            <p i18n:plural="">Foos $fname $lname</p>
          </div>
        </html>""")
        translations = DummyTranslations({
            ('Foo %(fname)s %(lname)s', 0): 'Voh %(fname)s %(lname)s',
            ('Foo %(fname)s %(lname)s', 1): 'Vohs %(fname)s %(lname)s',
                 'Foo %(fname)s %(lname)s': 'Voh %(fname)s %(lname)s',
                'Foos %(fname)s %(lname)s': 'Vohs %(fname)s %(lname)s',
        })
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <div>
            <p>Vohs John Doe</p>
          </div>
        </html>""", tmpl.generate(two=2, fname='John', lname='Doe').render())

    def test_translate_i18n_choose_and_domain_and_py_strip(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n"
            i18n:domain="foo">
          <div i18n:choose="two; fname, lname">
            <p i18n:singular="">Foo $fname $lname</p>
            <p i18n:plural="">Foos $fname $lname</p>
          </div>
        </html>""")
        translations = DummyTranslations()
        translations.add_domain('foo', {
            ('Foo %(fname)s %(lname)s', 0): 'Voh %(fname)s %(lname)s',
            ('Foo %(fname)s %(lname)s', 1): 'Vohs %(fname)s %(lname)s',
                 'Foo %(fname)s %(lname)s': 'Voh %(fname)s %(lname)s',
                'Foos %(fname)s %(lname)s': 'Vohs %(fname)s %(lname)s',
        })
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <div>
            <p>Vohs John Doe</p>
          </div>
        </html>""", tmpl.generate(two=2, fname='John', lname='Doe').render())
        
    def test_translate_i18n_choose_and_singular_with_py_strip(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <div i18n:choose="two; fname, lname">
            <p i18n:singular="" py:strip="">Foo $fname $lname</p>
            <p i18n:plural="">Foos $fname $lname</p>
          </div>
          <div i18n:choose="one; fname, lname">
            <p i18n:singular="" py:strip="">Foo $fname $lname</p>
            <p i18n:plural="">Foos $fname $lname</p>
          </div>
        </html>""")
        translations = DummyTranslations({
            ('Foo %(fname)s %(lname)s', 0): 'Voh %(fname)s %(lname)s',
            ('Foo %(fname)s %(lname)s', 1): 'Vohs %(fname)s %(lname)s',
                 'Foo %(fname)s %(lname)s': 'Voh %(fname)s %(lname)s',
                'Foos %(fname)s %(lname)s': 'Vohs %(fname)s %(lname)s',
        })
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <div>
            <p>Vohs John Doe</p>
          </div>
          <div>
            Voh John Doe
          </div>
        </html>""", tmpl.generate(
            one=1, two=2, fname='John',lname='Doe').render())
        
    def test_translate_i18n_choose_and_plural_with_py_strip(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <div i18n:choose="two; fname, lname">
            <p i18n:singular="" py:strip="">Foo $fname $lname</p>
            <p i18n:plural="">Foos $fname $lname</p>
          </div>
        </html>""")
        translations = DummyTranslations({
            ('Foo %(fname)s %(lname)s', 0): 'Voh %(fname)s %(lname)s',
            ('Foo %(fname)s %(lname)s', 1): 'Vohs %(fname)s %(lname)s',
                 'Foo %(fname)s %(lname)s': 'Voh %(fname)s %(lname)s',
                'Foos %(fname)s %(lname)s': 'Vohs %(fname)s %(lname)s',
        })
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <div>
            Voh John Doe
          </div>
        </html>""", tmpl.generate(two=1, fname='John', lname='Doe').render())

    def test_extract_i18n_choose_as_attribute_and_py_strip(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <div i18n:choose="one" py:strip="">
            <p i18n:singular="" py:strip="">FooBar</p>
            <p i18n:plural="" py:strip="">FooBars</p>
          </div>
        </html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(1, len(messages))
        self.assertEqual((3, 'ngettext', ('FooBar', 'FooBars'), []), messages[0])


class DomainDirectiveTestCase(unittest.TestCase):

    def test_translate_i18n_domain_with_msg_directives(self):
        #"""translate with i18n:domain and nested i18n:msg directives """

        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <div i18n:domain="foo">
            <p i18n:msg="">FooBar</p>
            <p i18n:msg="">Bar</p>
          </div>
        </html>""")
        translations = DummyTranslations({'Bar': 'Voh'})
        translations.add_domain('foo', {'FooBar': 'BarFoo', 'Bar': 'PT_Foo'})
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <div>
            <p>BarFoo</p>
            <p>PT_Foo</p>
          </div>
        </html>""", tmpl.generate().render())

    def test_translate_i18n_domain_with_inline_directives(self):
        #"""translate with inlined i18n:domain and i18n:msg directives"""
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="" i18n:domain="foo">FooBar</p>
        </html>""")
        translations = DummyTranslations({'Bar': 'Voh'})
        translations.add_domain('foo', {'FooBar': 'BarFoo'})
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>BarFoo</p>
        </html>""", tmpl.generate().render())

    def test_translate_i18n_domain_without_msg_directives(self):
        #"""translate domain call without i18n:msg directives still uses current domain"""

        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="">Bar</p>
          <div i18n:domain="foo">
            <p i18n:msg="">FooBar</p>
            <p i18n:msg="">Bar</p>
            <p>Bar</p>
          </div>
          <p>Bar</p>
        </html>""")
        translations = DummyTranslations({'Bar': 'Voh'})
        translations.add_domain('foo', {'FooBar': 'BarFoo', 'Bar': 'PT_Foo'})
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>Voh</p>
          <div>
            <p>BarFoo</p>
            <p>PT_Foo</p>
            <p>PT_Foo</p>
          </div>
          <p>Voh</p>
        </html>""", tmpl.generate().render())

    def test_translate_i18n_domain_as_directive_not_attribute(self):
        #"""translate with domain as directive"""

        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
        <i18n:domain name="foo">
          <p i18n:msg="">FooBar</p>
          <p i18n:msg="">Bar</p>
          <p>Bar</p>
        </i18n:domain>
          <p>Bar</p>
        </html>""")
        translations = DummyTranslations({'Bar': 'Voh'})
        translations.add_domain('foo', {'FooBar': 'BarFoo', 'Bar': 'PT_Foo'})
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>BarFoo</p>
          <p>PT_Foo</p>
          <p>PT_Foo</p>
          <p>Voh</p>
        </html>""", tmpl.generate().render())

    def test_translate_i18n_domain_nested_directives(self):
        #"""translate with nested i18n:domain directives"""

        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="">Bar</p>
          <div i18n:domain="foo">
            <p i18n:msg="">FooBar</p>
            <p i18n:domain="bar" i18n:msg="">Bar</p>
            <p>Bar</p>
          </div>
          <p>Bar</p>
        </html>""")
        translations = DummyTranslations({'Bar': 'Voh'})
        translations.add_domain('foo', {'FooBar': 'BarFoo', 'Bar': 'foo_Bar'})
        translations.add_domain('bar', {'Bar': 'bar_Bar'})
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>Voh</p>
          <div>
            <p>BarFoo</p>
            <p>bar_Bar</p>
            <p>foo_Bar</p>
          </div>
          <p>Voh</p>
        </html>""", tmpl.generate().render())

    def test_translate_i18n_domain_with_empty_nested_domain_directive(self):
        #"""translate with empty nested i18n:domain directive does not use dngettext"""

        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n">
          <p i18n:msg="">Bar</p>
          <div i18n:domain="foo">
            <p i18n:msg="">FooBar</p>
            <p i18n:domain="" i18n:msg="">Bar</p>
            <p>Bar</p>
          </div>
          <p>Bar</p>
        </html>""")
        translations = DummyTranslations({'Bar': 'Voh'})
        translations.add_domain('foo', {'FooBar': 'BarFoo', 'Bar': 'foo_Bar'})
        translations.add_domain('bar', {'Bar': 'bar_Bar'})
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>Voh</p>
          <div>
            <p>BarFoo</p>
            <p>Voh</p>
            <p>foo_Bar</p>
          </div>
          <p>Voh</p>
        </html>""", tmpl.generate().render())

    def test_translate_i18n_domain_with_inline_directive_on_START_NS(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n" i18n:domain="foo">
          <p i18n:msg="">FooBar</p>
        </html>""")
        translations = DummyTranslations({'Bar': 'Voh'})
        translations.add_domain('foo', {'FooBar': 'BarFoo'})
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""<html>
          <p>BarFoo</p>
        </html>""", tmpl.generate().render())

    def test_translate_i18n_domain_with_inline_directive_on_START_NS_with_py_strip(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
            xmlns:i18n="http://genshi.edgewall.org/i18n"
            i18n:domain="foo" py:strip="">
          <p i18n:msg="">FooBar</p>
        </html>""")
        translations = DummyTranslations({'Bar': 'Voh'})
        translations.add_domain('foo', {'FooBar': 'BarFoo'})
        translator = Translator(translations)
        translator.setup(tmpl)
        self.assertEqual("""
          <p>BarFoo</p>
        """, tmpl.generate().render())

    def test_translate_i18n_domain_with_nested_includes(self):
        import os, shutil, tempfile
        from genshi.template.loader import TemplateLoader
        dirname = tempfile.mkdtemp(suffix='genshi_test')
        try:
            for idx in range(7):
                file1 = open(os.path.join(dirname, 'tmpl%d.html' % idx), 'w')
                try:
                    file1.write("""<html xmlns:xi="http://www.w3.org/2001/XInclude"
                                         xmlns:py="http://genshi.edgewall.org/"
                                         xmlns:i18n="http://genshi.edgewall.org/i18n" py:strip="">
                        <div>Included tmpl$idx</div>
                        <p i18n:msg="idx">Bar $idx</p>
                        <p i18n:domain="bar">Bar</p>
                        <p i18n:msg="idx" i18n:domain="">Bar $idx</p>
                        <p i18n:domain="" i18n:msg="idx">Bar $idx</p>
                        <py:if test="idx &lt; 6">
                        <xi:include href="tmpl${idx}.html" py:with="idx = idx+1"/>
                        </py:if>
                    </html>""")
                finally:
                    file1.close()

            file2 = open(os.path.join(dirname, 'tmpl10.html'), 'w')
            try:
                file2.write("""<html xmlns:xi="http://www.w3.org/2001/XInclude"
                                     xmlns:py="http://genshi.edgewall.org/"
                                     xmlns:i18n="http://genshi.edgewall.org/i18n"
                                     i18n:domain="foo">
                  <xi:include href="tmpl${idx}.html" py:with="idx = idx+1"/>
                </html>""")
            finally:
                file2.close()

            def callback(template):
                translations = DummyTranslations({'Bar %(idx)s': 'Voh %(idx)s'})
                translations.add_domain('foo', {'Bar %(idx)s': 'foo_Bar %(idx)s'})
                translations.add_domain('bar', {'Bar': 'bar_Bar'})
                translator = Translator(translations)
                translator.setup(template)
            loader = TemplateLoader([dirname], callback=callback)
            tmpl = loader.load('tmpl10.html')

            self.assertEqual("""<html>
                        <div>Included tmpl0</div>
                        <p>foo_Bar 0</p>
                        <p>bar_Bar</p>
                        <p>Voh 0</p>
                        <p>Voh 0</p>
                        <div>Included tmpl1</div>
                        <p>foo_Bar 1</p>
                        <p>bar_Bar</p>
                        <p>Voh 1</p>
                        <p>Voh 1</p>
                        <div>Included tmpl2</div>
                        <p>foo_Bar 2</p>
                        <p>bar_Bar</p>
                        <p>Voh 2</p>
                        <p>Voh 2</p>
                        <div>Included tmpl3</div>
                        <p>foo_Bar 3</p>
                        <p>bar_Bar</p>
                        <p>Voh 3</p>
                        <p>Voh 3</p>
                        <div>Included tmpl4</div>
                        <p>foo_Bar 4</p>
                        <p>bar_Bar</p>
                        <p>Voh 4</p>
                        <p>Voh 4</p>
                        <div>Included tmpl5</div>
                        <p>foo_Bar 5</p>
                        <p>bar_Bar</p>
                        <p>Voh 5</p>
                        <p>Voh 5</p>
                        <div>Included tmpl6</div>
                        <p>foo_Bar 6</p>
                        <p>bar_Bar</p>
                        <p>Voh 6</p>
                        <p>Voh 6</p>
                </html>""", tmpl.generate(idx=-1).render())
        finally:
            shutil.rmtree(dirname)

    def test_translate_i18n_domain_with_nested_includes_with_translatable_attrs(self):
        import os, shutil, tempfile
        from genshi.template.loader import TemplateLoader
        dirname = tempfile.mkdtemp(suffix='genshi_test')
        try:
            for idx in range(4):
                file1 = open(os.path.join(dirname, 'tmpl%d.html' % idx), 'w')
                try:
                    file1.write("""<html xmlns:xi="http://www.w3.org/2001/XInclude"
                                         xmlns:py="http://genshi.edgewall.org/"
                                         xmlns:i18n="http://genshi.edgewall.org/i18n" py:strip="">
                        <div>Included tmpl$idx</div>
                        <p title="${dg('foo', 'Bar %(idx)s') % dict(idx=idx)}" i18n:msg="idx">Bar $idx</p>
                        <p title="Bar" i18n:domain="bar">Bar</p>
                        <p title="Bar" i18n:msg="idx" i18n:domain="">Bar $idx</p>
                        <p i18n:msg="idx" i18n:domain="" title="Bar">Bar $idx</p>
                        <p i18n:domain="" i18n:msg="idx" title="Bar">Bar $idx</p>
                        <py:if test="idx &lt; 3">
                        <xi:include href="tmpl${idx}.html" py:with="idx = idx+1"/>
                        </py:if>
                    </html>""")
                finally:
                    file1.close()

            file2 = open(os.path.join(dirname, 'tmpl10.html'), 'w')
            try:
                file2.write("""<html xmlns:xi="http://www.w3.org/2001/XInclude"
                                     xmlns:py="http://genshi.edgewall.org/"
                                     xmlns:i18n="http://genshi.edgewall.org/i18n"
                                     i18n:domain="foo">
                  <xi:include href="tmpl${idx}.html" py:with="idx = idx+1"/>
                </html>""")
            finally:
                file2.close()

            translations = DummyTranslations({'Bar %(idx)s': 'Voh %(idx)s',
                                              'Bar': 'Voh'})
            translations.add_domain('foo', {'Bar %(idx)s': 'foo_Bar %(idx)s'})
            translations.add_domain('bar', {'Bar': 'bar_Bar'})
            translator = Translator(translations)

            def callback(template):
                translator.setup(template)
            loader = TemplateLoader([dirname], callback=callback)
            tmpl = loader.load('tmpl10.html')

            if IS_PYTHON2:
                dgettext = translations.dugettext
            else:
                dgettext = translations.dgettext

            self.assertEqual("""<html>
                        <div>Included tmpl0</div>
                        <p title="foo_Bar 0">foo_Bar 0</p>
                        <p title="bar_Bar">bar_Bar</p>
                        <p title="Voh">Voh 0</p>
                        <p title="Voh">Voh 0</p>
                        <p title="Voh">Voh 0</p>
                        <div>Included tmpl1</div>
                        <p title="foo_Bar 1">foo_Bar 1</p>
                        <p title="bar_Bar">bar_Bar</p>
                        <p title="Voh">Voh 1</p>
                        <p title="Voh">Voh 1</p>
                        <p title="Voh">Voh 1</p>
                        <div>Included tmpl2</div>
                        <p title="foo_Bar 2">foo_Bar 2</p>
                        <p title="bar_Bar">bar_Bar</p>
                        <p title="Voh">Voh 2</p>
                        <p title="Voh">Voh 2</p>
                        <p title="Voh">Voh 2</p>
                        <div>Included tmpl3</div>
                        <p title="foo_Bar 3">foo_Bar 3</p>
                        <p title="bar_Bar">bar_Bar</p>
                        <p title="Voh">Voh 3</p>
                        <p title="Voh">Voh 3</p>
                        <p title="Voh">Voh 3</p>
                </html>""", tmpl.generate(idx=-1,
                                          dg=dgettext).render())
        finally:
            shutil.rmtree(dirname)


class ExtractTestCase(unittest.TestCase):

    def test_markup_template_extraction(self):
        buf = StringIO("""<html xmlns:py="http://genshi.edgewall.org/">
          <head>
            <title>Example</title>
          </head>
          <body>
            <h1>Example</h1>
            <p>${_("Hello, %(name)s") % dict(name=username)}</p>
            <p>${ngettext("You have %d item", "You have %d items", num)}</p>
          </body>
        </html>""")
        results = list(extract(buf, ['_', 'ngettext'], [], {}))
        self.assertEqual([
            (3, None, 'Example', []),
            (6, None, 'Example', []),
            (7, '_', 'Hello, %(name)s', []),
            (8, 'ngettext', ('You have %d item', 'You have %d items', None),
                             []),
        ], results)

    def test_extraction_without_text(self):
        buf = StringIO("""<html xmlns:py="http://genshi.edgewall.org/">
          <p title="Bar">Foo</p>
          ${ngettext("Singular", "Plural", num)}
        </html>""")
        results = list(extract(buf, ['_', 'ngettext'], [], {
            'extract_text': 'no'
        }))
        self.assertEqual([
            (3, 'ngettext', ('Singular', 'Plural', None), []),
        ], results)

    def test_text_template_extraction(self):
        buf = StringIO("""${_("Dear %(name)s") % {'name': name}},

        ${ngettext("Your item:", "Your items", len(items))}
        #for item in items
         * $item
        #end

        All the best,
        Foobar""")
        results = list(extract(buf, ['_', 'ngettext'], [], {
            'template_class': 'genshi.template:TextTemplate'
        }))
        self.assertEqual([
            (1, '_', 'Dear %(name)s', []),
            (3, 'ngettext', ('Your item:', 'Your items', None), []),
            (7, None, 'All the best,\n        Foobar', [])
        ], results)

    def test_extraction_with_keyword_arg(self):
        buf = StringIO("""<html xmlns:py="http://genshi.edgewall.org/">
          ${gettext('Foobar', foo='bar')}
        </html>""")
        results = list(extract(buf, ['gettext'], [], {}))
        self.assertEqual([
            (2, 'gettext', ('Foobar'), []),
        ], results)

    def test_extraction_with_nonstring_arg(self):
        buf = StringIO("""<html xmlns:py="http://genshi.edgewall.org/">
          ${dgettext(curdomain, 'Foobar')}
        </html>""")
        results = list(extract(buf, ['dgettext'], [], {}))
        self.assertEqual([
            (2, 'dgettext', (None, 'Foobar'), []),
        ], results)

    def test_extraction_inside_ignored_tags(self):
        buf = StringIO("""<html xmlns:py="http://genshi.edgewall.org/">
          <script type="text/javascript">
            $('#llist').tabs({
              remote: true,
              spinner: "${_('Please wait...')}"
            });
          </script>
        </html>""")
        results = list(extract(buf, ['_'], [], {}))
        self.assertEqual([
            (5, '_', 'Please wait...', []),
        ], results)

    def test_extraction_inside_ignored_tags_with_directives(self):
        buf = StringIO("""<html xmlns:py="http://genshi.edgewall.org/">
          <script type="text/javascript">
            <py:if test="foobar">
              alert("This shouldn't be extracted");
            </py:if>
          </script>
        </html>""")
        self.assertEqual([], list(extract(buf, ['_'], [], {})))

    def test_extract_py_def_directive_with_py_strip(self):
        # Failed extraction from Trac
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/" py:strip="">
    <py:def function="diff_options_fields(diff)">
    <label for="style">View differences</label>
    <select id="style" name="style">
      <option selected="${diff.style == 'inline' or None}"
              value="inline">inline</option>
      <option selected="${diff.style == 'sidebyside' or None}"
              value="sidebyside">side by side</option>
    </select>
    <div class="field">
      Show <input type="text" name="contextlines" id="contextlines" size="2"
                  maxlength="3" value="${diff.options.contextlines &lt; 0 and 'all' or diff.options.contextlines}" />
      <label for="contextlines">lines around each change</label>
    </div>
    <fieldset id="ignore" py:with="options = diff.options">
      <legend>Ignore:</legend>
      <div class="field">
        <input type="checkbox" id="ignoreblanklines" name="ignoreblanklines"
               checked="${options.ignoreblanklines or None}" />
        <label for="ignoreblanklines">Blank lines</label>
      </div>
      <div class="field">
        <input type="checkbox" id="ignorecase" name="ignorecase"
               checked="${options.ignorecase or None}" />
        <label for="ignorecase">Case changes</label>
      </div>
      <div class="field">
        <input type="checkbox" id="ignorewhitespace" name="ignorewhitespace"
               checked="${options.ignorewhitespace or None}" />
        <label for="ignorewhitespace">White space changes</label>
      </div>
    </fieldset>
    <div class="buttons">
      <input type="submit" name="update" value="${_('Update')}" />
    </div>
  </py:def></html>""")
        translator = Translator()
        tmpl.add_directives(Translator.NAMESPACE, translator)
        messages = list(translator.extract(tmpl.stream))
        self.assertEqual(10, len(messages))
        self.assertEqual([
            (3, None, 'View differences', []),
            (6, None, 'inline', []),
            (8, None, 'side by side', []),
            (10, None, 'Show', []),
            (13, None, 'lines around each change', []),
            (16, None, 'Ignore:', []),
            (20, None, 'Blank lines', []),
            (25, None, 'Case changes',[]),
            (30, None, 'White space changes', []),
            (34, '_', 'Update', [])], messages)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(Translator.__module__))
    suite.addTest(unittest.makeSuite(TranslatorTestCase, 'test'))
    suite.addTest(unittest.makeSuite(MsgDirectiveTestCase, 'test'))
    suite.addTest(unittest.makeSuite(ChooseDirectiveTestCase, 'test'))
    suite.addTest(unittest.makeSuite(DomainDirectiveTestCase, 'test'))
    suite.addTest(unittest.makeSuite(ExtractTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
