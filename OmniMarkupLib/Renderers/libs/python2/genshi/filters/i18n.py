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

"""Directives and utilities for internationalization and localization of
templates.

:since: version 0.4
:note: Directives support added since version 0.6
"""

try:
    any
except NameError:
    from genshi.util import any
from gettext import NullTranslations
import os
import re
from types import FunctionType

from genshi.core import Attrs, Namespace, QName, START, END, TEXT, \
                        XML_NAMESPACE, _ensure, StreamEventKind
from genshi.template.eval import _ast
from genshi.template.base import DirectiveFactory, EXPR, SUB, _apply_directives
from genshi.template.directives import Directive, StripDirective
from genshi.template.markup import MarkupTemplate, EXEC
from genshi.compat import IS_PYTHON2

__all__ = ['Translator', 'extract']
__docformat__ = 'restructuredtext en'


I18N_NAMESPACE = Namespace('http://genshi.edgewall.org/i18n')

MSGBUF = StreamEventKind('MSGBUF')
SUB_START = StreamEventKind('SUB_START')
SUB_END = StreamEventKind('SUB_END')

GETTEXT_FUNCTIONS = ('_', 'gettext', 'ngettext', 'dgettext', 'dngettext',
                     'ugettext', 'ungettext')


class I18NDirective(Directive):
    """Simple interface for i18n directives to support messages extraction."""

    def __call__(self, stream, directives, ctxt, **vars):
        return _apply_directives(stream, directives, ctxt, vars)


class ExtractableI18NDirective(I18NDirective):
    """Simple interface for directives to support messages extraction."""

    def extract(self, translator, stream, gettext_functions=GETTEXT_FUNCTIONS,
                search_text=True, comment_stack=None):
        raise NotImplementedError


class CommentDirective(I18NDirective):
    """Implementation of the ``i18n:comment`` template directive which adds
    translation comments.
    
    >>> tmpl = MarkupTemplate('''<html xmlns:i18n="http://genshi.edgewall.org/i18n">
    ...   <p i18n:comment="As in Foo Bar">Foo</p>
    ... </html>''')
    >>> translator = Translator()
    >>> translator.setup(tmpl)
    >>> list(translator.extract(tmpl.stream))
    [(2, None, u'Foo', [u'As in Foo Bar'])]
    """
    __slots__ = ['comment']

    def __init__(self, value, template=None, namespaces=None, lineno=-1,
                 offset=-1):
        Directive.__init__(self, None, template, namespaces, lineno, offset)
        self.comment = value


class MsgDirective(ExtractableI18NDirective):
    r"""Implementation of the ``i18n:msg`` directive which marks inner content
    as translatable. Consider the following examples:
    
    >>> tmpl = MarkupTemplate('''<html xmlns:i18n="http://genshi.edgewall.org/i18n">
    ...   <div i18n:msg="">
    ...     <p>Foo</p>
    ...     <p>Bar</p>
    ...   </div>
    ...   <p i18n:msg="">Foo <em>bar</em>!</p>
    ... </html>''')
    
    >>> translator = Translator()
    >>> translator.setup(tmpl)
    >>> list(translator.extract(tmpl.stream))
    [(2, None, u'[1:Foo]\n    [2:Bar]', []), (6, None, u'Foo [1:bar]!', [])]
    >>> print(tmpl.generate().render())
    <html>
      <div><p>Foo</p>
        <p>Bar</p></div>
      <p>Foo <em>bar</em>!</p>
    </html>

    >>> tmpl = MarkupTemplate('''<html xmlns:i18n="http://genshi.edgewall.org/i18n">
    ...   <div i18n:msg="fname, lname">
    ...     <p>First Name: ${fname}</p>
    ...     <p>Last Name: ${lname}</p>
    ...   </div>
    ...   <p i18n:msg="">Foo <em>bar</em>!</p>
    ... </html>''')
    >>> translator.setup(tmpl)
    >>> list(translator.extract(tmpl.stream)) #doctest: +NORMALIZE_WHITESPACE
    [(2, None, u'[1:First Name: %(fname)s]\n    [2:Last Name: %(lname)s]', []),
    (6, None, u'Foo [1:bar]!', [])]

    >>> tmpl = MarkupTemplate('''<html xmlns:i18n="http://genshi.edgewall.org/i18n">
    ...   <div i18n:msg="fname, lname">
    ...     <p>First Name: ${fname}</p>
    ...     <p>Last Name: ${lname}</p>
    ...   </div>
    ...   <p i18n:msg="">Foo <em>bar</em>!</p>
    ... </html>''')
    >>> translator.setup(tmpl)
    >>> print(tmpl.generate(fname='John', lname='Doe').render())
    <html>
      <div><p>First Name: John</p>
        <p>Last Name: Doe</p></div>
      <p>Foo <em>bar</em>!</p>
    </html>

    Starting and ending white-space is stripped of to make it simpler for
    translators. Stripping it is not that important since it's on the html
    source, the rendered output will remain the same.
    """
    __slots__ = ['params', 'lineno']

    def __init__(self, value, template=None, namespaces=None, lineno=-1,
                 offset=-1):
        Directive.__init__(self, None, template, namespaces, lineno, offset)
        self.params = [param.strip() for param in value.split(',') if param]
        self.lineno = lineno

    @classmethod
    def attach(cls, template, stream, value, namespaces, pos):
        if type(value) is dict:
            value = value.get('params', '').strip()
        return super(MsgDirective, cls).attach(template, stream, value.strip(),
                                               namespaces, pos)

    def __call__(self, stream, directives, ctxt, **vars):
        gettext = ctxt.get('_i18n.gettext')
        if ctxt.get('_i18n.domain'):
            dgettext = ctxt.get('_i18n.dgettext')
            assert hasattr(dgettext, '__call__'), \
                'No domain gettext function passed'
            gettext = lambda msg: dgettext(ctxt.get('_i18n.domain'), msg)

        def _generate():
            msgbuf = MessageBuffer(self)
            previous = stream.next()
            if previous[0] is START:
                yield previous
            else:
                msgbuf.append(*previous)
            previous = stream.next()
            for kind, data, pos in stream:
                msgbuf.append(*previous)
                previous = kind, data, pos
            if previous[0] is not END:
                msgbuf.append(*previous)
                previous = None
            for event in msgbuf.translate(gettext(msgbuf.format())):
                yield event
            if previous:
                yield previous

        return _apply_directives(_generate(), directives, ctxt, vars)

    def extract(self, translator, stream, gettext_functions=GETTEXT_FUNCTIONS,
                search_text=True, comment_stack=None):
        msgbuf = MessageBuffer(self)
        strip = False

        stream = iter(stream)
        previous = stream.next()
        if previous[0] is START:
            for message in translator._extract_attrs(previous,
                                                     gettext_functions,
                                                     search_text=search_text):
                yield message
            previous = stream.next()
            strip = True
        for event in stream:
            if event[0] is START:
                for message in translator._extract_attrs(event,
                                                         gettext_functions,
                                                         search_text=search_text):
                    yield message
            msgbuf.append(*previous)
            previous = event
        if not strip:
            msgbuf.append(*previous)

        yield self.lineno, None, msgbuf.format(), comment_stack[-1:]


class ChooseBranchDirective(I18NDirective):
    __slots__ = ['params']

    def __call__(self, stream, directives, ctxt, **vars):
        self.params = ctxt.get('_i18n.choose.params', [])[:]
        msgbuf = MessageBuffer(self)
        stream = _apply_directives(stream, directives, ctxt, vars)

        previous = stream.next()
        if previous[0] is START:
            yield previous
        else:
            msgbuf.append(*previous)

        try:
            previous = stream.next()
        except StopIteration:
            # For example <i18n:singular> or <i18n:plural> directives
            yield MSGBUF, (), -1 # the place holder for msgbuf output
            ctxt['_i18n.choose.%s' % self.tagname] = msgbuf
            return

        for event in stream:
            msgbuf.append(*previous)
            previous = event
        yield MSGBUF, (), -1 # the place holder for msgbuf output

        if previous[0] is END:
            yield previous # the outer end tag
        else:
            msgbuf.append(*previous)
        ctxt['_i18n.choose.%s' % self.tagname] = msgbuf

    def extract(self, translator, stream, gettext_functions=GETTEXT_FUNCTIONS,
                search_text=True, comment_stack=None, msgbuf=None):
        stream = iter(stream)
        previous = stream.next()

        if previous[0] is START:
            # skip the enclosing element
            for message in translator._extract_attrs(previous,
                                                     gettext_functions,
                                                     search_text=search_text):
                yield message
            previous = stream.next()

        for event in stream:
            if previous[0] is START:
                for message in translator._extract_attrs(previous,
                                                         gettext_functions,
                                                         search_text=search_text):
                    yield message
            msgbuf.append(*previous)
            previous = event

        if previous[0] is not END:
            msgbuf.append(*previous)


class SingularDirective(ChooseBranchDirective):
    """Implementation of the ``i18n:singular`` directive to be used with the
    ``i18n:choose`` directive."""


class PluralDirective(ChooseBranchDirective):
    """Implementation of the ``i18n:plural`` directive to be used with the
    ``i18n:choose`` directive."""


class ChooseDirective(ExtractableI18NDirective):
    """Implementation of the ``i18n:choose`` directive which provides plural
    internationalisation of strings.
    
    This directive requires at least one parameter, the one which evaluates to
    an integer which will allow to choose the plural/singular form. If you also
    have expressions inside the singular and plural version of the string you
    also need to pass a name for those parameters. Consider the following
    examples:
    
    >>> tmpl = MarkupTemplate('''<html xmlns:i18n="http://genshi.edgewall.org/i18n">
    ...   <div i18n:choose="num; num">
    ...     <p i18n:singular="">There is $num coin</p>
    ...     <p i18n:plural="">There are $num coins</p>
    ...   </div>
    ... </html>''')
    >>> translator = Translator()
    >>> translator.setup(tmpl)
    >>> list(translator.extract(tmpl.stream)) #doctest: +NORMALIZE_WHITESPACE
    [(2, 'ngettext', (u'There is %(num)s coin',
                      u'There are %(num)s coins'), [])]

    >>> tmpl = MarkupTemplate('''<html xmlns:i18n="http://genshi.edgewall.org/i18n">
    ...   <div i18n:choose="num; num">
    ...     <p i18n:singular="">There is $num coin</p>
    ...     <p i18n:plural="">There are $num coins</p>
    ...   </div>
    ... </html>''')
    >>> translator.setup(tmpl)
    >>> print(tmpl.generate(num=1).render())
    <html>
      <div>
        <p>There is 1 coin</p>
      </div>
    </html>
    >>> print(tmpl.generate(num=2).render())
    <html>
      <div>
        <p>There are 2 coins</p>
      </div>
    </html>

    When used as a element and not as an attribute:

    >>> tmpl = MarkupTemplate('''<html xmlns:i18n="http://genshi.edgewall.org/i18n">
    ...   <i18n:choose numeral="num" params="num">
    ...     <p i18n:singular="">There is $num coin</p>
    ...     <p i18n:plural="">There are $num coins</p>
    ...   </i18n:choose>
    ... </html>''')
    >>> translator.setup(tmpl)
    >>> list(translator.extract(tmpl.stream)) #doctest: +NORMALIZE_WHITESPACE
    [(2, 'ngettext', (u'There is %(num)s coin',
                      u'There are %(num)s coins'), [])]
    """
    __slots__ = ['numeral', 'params', 'lineno']

    def __init__(self, value, template=None, namespaces=None, lineno=-1,
                 offset=-1):
        Directive.__init__(self, None, template, namespaces, lineno, offset)
        params = [v.strip() for v in value.split(';')]
        self.numeral = self._parse_expr(params.pop(0), template, lineno, offset)
        self.params = params and [name.strip() for name in
                                  params[0].split(',') if name] or []
        self.lineno = lineno

    @classmethod
    def attach(cls, template, stream, value, namespaces, pos):
        if type(value) is dict:
            numeral = value.get('numeral', '').strip()
            assert numeral is not '', "at least pass the numeral param"
            params = [v.strip() for v in value.get('params', '').split(',')]
            value = '%s; ' % numeral + ', '.join(params)
        return super(ChooseDirective, cls).attach(template, stream, value,
                                                  namespaces, pos)

    def __call__(self, stream, directives, ctxt, **vars):
        ctxt.push({'_i18n.choose.params': self.params,
                   '_i18n.choose.singular': None,
                   '_i18n.choose.plural': None})

        ngettext = ctxt.get('_i18n.ngettext')
        assert hasattr(ngettext, '__call__'), 'No ngettext function available'
        dngettext = ctxt.get('_i18n.dngettext')
        if not dngettext:
            dngettext = lambda d, s, p, n: ngettext(s, p, n)

        new_stream = []
        singular_stream = None
        singular_msgbuf = None
        plural_stream = None
        plural_msgbuf = None

        numeral = self.numeral.evaluate(ctxt)
        is_plural = self._is_plural(numeral, ngettext)

        for event in stream:
            if event[0] is SUB and any(isinstance(d, ChooseBranchDirective)
                                       for d in event[1][0]):
                subdirectives, substream = event[1]

                if isinstance(subdirectives[0], SingularDirective):
                    singular_stream = list(_apply_directives(substream,
                                                             subdirectives,
                                                             ctxt, vars))
                    new_stream.append((MSGBUF, None, (None, -1, -1)))

                elif isinstance(subdirectives[0], PluralDirective):
                    if is_plural:
                        plural_stream = list(_apply_directives(substream,
                                                               subdirectives,
                                                               ctxt, vars))

            else:
                new_stream.append(event)

        if ctxt.get('_i18n.domain'):
            ngettext = lambda s, p, n: dngettext(ctxt.get('_i18n.domain'),
                                                 s, p, n)

        singular_msgbuf = ctxt.get('_i18n.choose.singular')
        if is_plural:
            plural_msgbuf = ctxt.get('_i18n.choose.plural')
            msgbuf, choice = plural_msgbuf, plural_stream
        else:
            msgbuf, choice = singular_msgbuf, singular_stream
            plural_msgbuf = MessageBuffer(self)

        for kind, data, pos in new_stream:
            if kind is MSGBUF:
                for event in choice:
                    if event[0] is MSGBUF:
                        translation = ngettext(singular_msgbuf.format(),
                                               plural_msgbuf.format(),
                                               numeral)
                        for subevent in msgbuf.translate(translation):
                            yield subevent
                    else:
                        yield event
            else:
                yield kind, data, pos

        ctxt.pop()

    def extract(self, translator, stream, gettext_functions=GETTEXT_FUNCTIONS,
                search_text=True, comment_stack=None):
        strip = False
        stream = iter(stream)
        previous = stream.next()

        if previous[0] is START:
            # skip the enclosing element
            for message in translator._extract_attrs(previous,
                                                     gettext_functions,
                                                     search_text=search_text):
                yield message
            previous = stream.next()
            strip = True

        singular_msgbuf = MessageBuffer(self)
        plural_msgbuf = MessageBuffer(self)

        for event in stream:
            if previous[0] is SUB:
                directives, substream = previous[1]
                for directive in directives:
                    if isinstance(directive, SingularDirective):
                        for message in directive.extract(translator,
                                substream, gettext_functions, search_text,
                                comment_stack, msgbuf=singular_msgbuf):
                            yield message
                    elif isinstance(directive, PluralDirective):
                        for message in directive.extract(translator,
                                substream, gettext_functions, search_text,
                                comment_stack, msgbuf=plural_msgbuf):
                            yield message
                    elif not isinstance(directive, StripDirective):
                        singular_msgbuf.append(*previous)
                        plural_msgbuf.append(*previous)
            else:
                if previous[0] is START:
                    for message in translator._extract_attrs(previous,
                                                             gettext_functions,
                                                             search_text):
                        yield message
                singular_msgbuf.append(*previous)
                plural_msgbuf.append(*previous)
            previous = event

        if not strip:
            singular_msgbuf.append(*previous)
            plural_msgbuf.append(*previous)

        yield self.lineno, 'ngettext', \
            (singular_msgbuf.format(), plural_msgbuf.format()), \
            comment_stack[-1:]

    def _is_plural(self, numeral, ngettext):
        # XXX: should we test which form was chosen like this!?!?!?
        # There should be no match in any catalogue for these singular and
        # plural test strings
        singular = u'O\x85\xbe\xa9\xa8az\xc3?\xe6\xa1\x02n\x84\x93'
        plural = u'\xcc\xfb+\xd3Pn\x9d\tT\xec\x1d\xda\x1a\x88\x00'
        return ngettext(singular, plural, numeral) == plural


class DomainDirective(I18NDirective):
    """Implementation of the ``i18n:domain`` directive which allows choosing
    another i18n domain(catalog) to translate from.
    
    >>> from genshi.filters.tests.i18n import DummyTranslations
    >>> tmpl = MarkupTemplate('''<html xmlns:i18n="http://genshi.edgewall.org/i18n">
    ...   <p i18n:msg="">Bar</p>
    ...   <div i18n:domain="foo">
    ...     <p i18n:msg="">FooBar</p>
    ...     <p>Bar</p>
    ...     <p i18n:domain="bar" i18n:msg="">Bar</p>
    ...     <p i18n:domain="">Bar</p>
    ...   </div>
    ...   <p>Bar</p>
    ... </html>''')

    >>> translations = DummyTranslations({'Bar': 'Voh'})
    >>> translations.add_domain('foo', {'FooBar': 'BarFoo', 'Bar': 'foo_Bar'})
    >>> translations.add_domain('bar', {'Bar': 'bar_Bar'})
    >>> translator = Translator(translations)
    >>> translator.setup(tmpl)

    >>> print(tmpl.generate().render())
    <html>
      <p>Voh</p>
      <div>
        <p>BarFoo</p>
        <p>foo_Bar</p>
        <p>bar_Bar</p>
        <p>Voh</p>
      </div>
      <p>Voh</p>
    </html>
    """
    __slots__ = ['domain']

    def __init__(self, value, template=None, namespaces=None, lineno=-1,
                 offset=-1):
        Directive.__init__(self, None, template, namespaces, lineno, offset)
        self.domain = value and value.strip() or '__DEFAULT__'

    @classmethod
    def attach(cls, template, stream, value, namespaces, pos):
        if type(value) is dict:
            value = value.get('name')
        return super(DomainDirective, cls).attach(template, stream, value,
                                                  namespaces, pos)

    def __call__(self, stream, directives, ctxt, **vars):
        ctxt.push({'_i18n.domain': self.domain})
        for event in _apply_directives(stream, directives, ctxt, vars):
            yield event
        ctxt.pop()


class Translator(DirectiveFactory):
    """Can extract and translate localizable strings from markup streams and
    templates.
    
    For example, assume the following template:
    
    >>> tmpl = MarkupTemplate('''<html xmlns:py="http://genshi.edgewall.org/">
    ...   <head>
    ...     <title>Example</title>
    ...   </head>
    ...   <body>
    ...     <h1>Example</h1>
    ...     <p>${_("Hello, %(name)s") % dict(name=username)}</p>
    ...   </body>
    ... </html>''', filename='example.html')
    
    For demonstration, we define a dummy ``gettext``-style function with a
    hard-coded translation table, and pass that to the `Translator` initializer:
    
    >>> def pseudo_gettext(string):
    ...     return {
    ...         'Example': 'Beispiel',
    ...         'Hello, %(name)s': 'Hallo, %(name)s'
    ...     }[string]
    >>> translator = Translator(pseudo_gettext)
    
    Next, the translator needs to be prepended to any already defined filters
    on the template:
    
    >>> tmpl.filters.insert(0, translator)
    
    When generating the template output, our hard-coded translations should be
    applied as expected:
    
    >>> print(tmpl.generate(username='Hans', _=pseudo_gettext))
    <html>
      <head>
        <title>Beispiel</title>
      </head>
      <body>
        <h1>Beispiel</h1>
        <p>Hallo, Hans</p>
      </body>
    </html>
    
    Note that elements defining ``xml:lang`` attributes that do not contain
    variable expressions are ignored by this filter. That can be used to
    exclude specific parts of a template from being extracted and translated.
    """

    directives = [
        ('domain', DomainDirective),
        ('comment', CommentDirective),
        ('msg', MsgDirective),
        ('choose', ChooseDirective),
        ('singular', SingularDirective),
        ('plural', PluralDirective)
    ]

    IGNORE_TAGS = frozenset([
        QName('script'), QName('http://www.w3.org/1999/xhtml}script'),
        QName('style'), QName('http://www.w3.org/1999/xhtml}style')
    ])
    INCLUDE_ATTRS = frozenset([
        'abbr', 'alt', 'label', 'prompt', 'standby', 'summary', 'title'
    ])
    NAMESPACE = I18N_NAMESPACE

    def __init__(self, translate=NullTranslations(), ignore_tags=IGNORE_TAGS,
                 include_attrs=INCLUDE_ATTRS, extract_text=True):
        """Initialize the translator.
        
        :param translate: the translation function, for example ``gettext`` or
                          ``ugettext``.
        :param ignore_tags: a set of tag names that should not be localized
        :param include_attrs: a set of attribute names should be localized
        :param extract_text: whether the content of text nodes should be
                             extracted, or only text in explicit ``gettext``
                             function calls
        
        :note: Changed in 0.6: the `translate` parameter can now be either
               a ``gettext``-style function, or an object compatible with the
               ``NullTransalations`` or ``GNUTranslations`` interface
        """
        self.translate = translate
        self.ignore_tags = ignore_tags
        self.include_attrs = include_attrs
        self.extract_text = extract_text

    def __call__(self, stream, ctxt=None, translate_text=True,
                 translate_attrs=True):
        """Translate any localizable strings in the given stream.
        
        This function shouldn't be called directly. Instead, an instance of
        the `Translator` class should be registered as a filter with the
        `Template` or the `TemplateLoader`, or applied as a regular stream
        filter. If used as a template filter, it should be inserted in front of
        all the default filters.
        
        :param stream: the markup event stream
        :param ctxt: the template context (not used)
        :param translate_text: whether text nodes should be translated (used
                               internally)
        :param translate_attrs: whether attribute values should be translated
                                (used internally)
        :return: the localized stream
        """
        ignore_tags = self.ignore_tags
        include_attrs = self.include_attrs
        skip = 0
        xml_lang = XML_NAMESPACE['lang']
        if not self.extract_text:
            translate_text = False
            translate_attrs = False

        if type(self.translate) is FunctionType:
            gettext = self.translate
            if ctxt:
                ctxt['_i18n.gettext'] = gettext
        else:
            if IS_PYTHON2:
                gettext = self.translate.ugettext
                ngettext = self.translate.ungettext
            else:
                gettext = self.translate.gettext
                ngettext = self.translate.ngettext
            try:
                if IS_PYTHON2:
                    dgettext = self.translate.dugettext
                    dngettext = self.translate.dungettext
                else:
                    dgettext = self.translate.dgettext
                    dngettext = self.translate.dngettext
            except AttributeError:
                dgettext = lambda _, y: gettext(y)
                dngettext = lambda _, s, p, n: ngettext(s, p, n)
            if ctxt:
                ctxt['_i18n.gettext'] = gettext
                ctxt['_i18n.ngettext'] = ngettext
                ctxt['_i18n.dgettext'] = dgettext
                ctxt['_i18n.dngettext'] = dngettext

        if ctxt and ctxt.get('_i18n.domain'):
            # TODO: This can cause infinite recursion if dgettext is defined
            #       via the AttributeError case above!
            gettext = lambda msg: dgettext(ctxt.get('_i18n.domain'), msg)

        for kind, data, pos in stream:

            # skip chunks that should not be localized
            if skip:
                if kind is START:
                    skip += 1
                elif kind is END:
                    skip -= 1
                yield kind, data, pos
                continue

            # handle different events that can be localized
            if kind is START:
                tag, attrs = data
                if tag in self.ignore_tags or \
                        isinstance(attrs.get(xml_lang), basestring):
                    skip += 1
                    yield kind, data, pos
                    continue

                new_attrs = []
                changed = False

                for name, value in attrs:
                    newval = value
                    if isinstance(value, basestring):
                        if translate_attrs and name in include_attrs:
                            newval = gettext(value)
                    else:
                        newval = list(
                            self(_ensure(value), ctxt, translate_text=False)
                        )
                    if newval != value:
                        value = newval
                        changed = True
                    new_attrs.append((name, value))
                if changed:
                    attrs = Attrs(new_attrs)

                yield kind, (tag, attrs), pos

            elif translate_text and kind is TEXT:
                text = data.strip()
                if text:
                    data = data.replace(text, unicode(gettext(text)))
                yield kind, data, pos

            elif kind is SUB:
                directives, substream = data
                current_domain = None
                for idx, directive in enumerate(directives):
                    # Organize directives to make everything work
                    # FIXME: There's got to be a better way to do this!
                    if isinstance(directive, DomainDirective):
                        # Grab current domain and update context
                        current_domain = directive.domain
                        ctxt.push({'_i18n.domain': current_domain})
                        # Put domain directive as the first one in order to
                        # update context before any other directives evaluation
                        directives.insert(0, directives.pop(idx))

                # If this is an i18n directive, no need to translate text
                # nodes here
                is_i18n_directive = any([
                    isinstance(d, ExtractableI18NDirective)
                    for d in directives
                ])
                substream = list(self(substream, ctxt,
                                      translate_text=not is_i18n_directive,
                                      translate_attrs=translate_attrs))
                yield kind, (directives, substream), pos

                if current_domain:
                    ctxt.pop()
            else:
                yield kind, data, pos

    def extract(self, stream, gettext_functions=GETTEXT_FUNCTIONS,
                search_text=True, comment_stack=None):
        """Extract localizable strings from the given template stream.
        
        For every string found, this function yields a ``(lineno, function,
        message, comments)`` tuple, where:
        
        * ``lineno`` is the number of the line on which the string was found,
        * ``function`` is the name of the ``gettext`` function used (if the
          string was extracted from embedded Python code), and
        *  ``message`` is the string itself (a ``unicode`` object, or a tuple
           of ``unicode`` objects for functions with multiple string
           arguments).
        *  ``comments`` is a list of comments related to the message, extracted
           from ``i18n:comment`` attributes found in the markup
        
        >>> tmpl = MarkupTemplate('''<html xmlns:py="http://genshi.edgewall.org/">
        ...   <head>
        ...     <title>Example</title>
        ...   </head>
        ...   <body>
        ...     <h1>Example</h1>
        ...     <p>${_("Hello, %(name)s") % dict(name=username)}</p>
        ...     <p>${ngettext("You have %d item", "You have %d items", num)}</p>
        ...   </body>
        ... </html>''', filename='example.html')
        >>> for line, func, msg, comments in Translator().extract(tmpl.stream):
        ...    print('%d, %r, %r' % (line, func, msg))
        3, None, u'Example'
        6, None, u'Example'
        7, '_', u'Hello, %(name)s'
        8, 'ngettext', (u'You have %d item', u'You have %d items', None)
        
        :param stream: the event stream to extract strings from; can be a
                       regular stream or a template stream
        :param gettext_functions: a sequence of function names that should be
                                  treated as gettext-style localization
                                  functions
        :param search_text: whether the content of text nodes should be
                            extracted (used internally)
        
        :note: Changed in 0.4.1: For a function with multiple string arguments
               (such as ``ngettext``), a single item with a tuple of strings is
               yielded, instead an item for each string argument.
        :note: Changed in 0.6: The returned tuples now include a fourth
               element, which is a list of comments for the translator.
        """
        if not self.extract_text:
            search_text = False
        if comment_stack is None:
            comment_stack = []
        skip = 0

        xml_lang = XML_NAMESPACE['lang']

        for kind, data, pos in stream:
            if skip:
                if kind is START:
                    skip += 1
                if kind is END:
                    skip -= 1

            if kind is START and not skip:
                tag, attrs = data
                if tag in self.ignore_tags or \
                        isinstance(attrs.get(xml_lang), basestring):
                    skip += 1
                    continue

                for message in self._extract_attrs((kind, data, pos),
                                                   gettext_functions,
                                                   search_text=search_text):
                    yield message

            elif not skip and search_text and kind is TEXT:
                text = data.strip()
                if text and [ch for ch in text if ch.isalpha()]:
                    yield pos[1], None, text, comment_stack[-1:]

            elif kind is EXPR or kind is EXEC:
                for funcname, strings in extract_from_code(data,
                                                           gettext_functions):
                    # XXX: Do we need to grab i18n:comment from comment_stack ???
                    yield pos[1], funcname, strings, []

            elif kind is SUB:
                directives, substream = data
                in_comment = False

                for idx, directive in enumerate(directives):
                    # Do a first loop to see if there's a comment directive
                    # If there is update context and pop it from directives
                    if isinstance(directive, CommentDirective):
                        in_comment = True
                        comment_stack.append(directive.comment)
                        if len(directives) == 1:
                            # in case we're in the presence of something like:
                            # <p i18n:comment="foo">Foo</p>
                            for message in self.extract(
                                    substream, gettext_functions,
                                    search_text=search_text and not skip,
                                    comment_stack=comment_stack):
                                yield message
                        directives.pop(idx)
                    elif not isinstance(directive, I18NDirective):
                        # Remove all other non i18n directives from the process
                        directives.pop(idx)

                if not directives and not in_comment:
                    # Extract content if there's no directives because
                    # strip was pop'ed and not because comment was pop'ed.
                    # Extraction in this case has been taken care of.
                    for message in self.extract(
                            substream, gettext_functions,
                            search_text=search_text and not skip):
                        yield message

                for directive in directives:
                    if isinstance(directive, ExtractableI18NDirective):
                        for message in directive.extract(self,
                                substream, gettext_functions,
                                search_text=search_text and not skip,
                                comment_stack=comment_stack):
                            yield message
                    else:
                        for message in self.extract(
                                substream, gettext_functions,
                                search_text=search_text and not skip,
                                comment_stack=comment_stack):
                            yield message

                if in_comment:
                    comment_stack.pop()

    def get_directive_index(self, dir_cls):
        total = len(self._dir_order)
        if dir_cls in self._dir_order:
            return self._dir_order.index(dir_cls) - total
        return total

    def setup(self, template):
        """Convenience function to register the `Translator` filter and the
        related directives with the given template.
        
        :param template: a `Template` instance
        """
        template.filters.insert(0, self)
        if hasattr(template, 'add_directives'):
            template.add_directives(Translator.NAMESPACE, self)

    def _extract_attrs(self, event, gettext_functions, search_text):
        for name, value in event[1][1]:
            if search_text and isinstance(value, basestring):
                if name in self.include_attrs:
                    text = value.strip()
                    if text:
                        yield event[2][1], None, text, []
            else:
                for message in self.extract(_ensure(value), gettext_functions,
                                            search_text=False):
                    yield message


class MessageBuffer(object):
    """Helper class for managing internationalized mixed content.
    
    :since: version 0.5
    """

    def __init__(self, directive=None):
        """Initialize the message buffer.
        
        :param directive: the directive owning the buffer
        :type directive: I18NDirective
        """
        # params list needs to be copied so that directives can be evaluated
        # more than once
        self.orig_params = self.params = directive.params[:]
        self.directive = directive
        self.string = []
        self.events = {}
        self.values = {}
        self.depth = 1
        self.order = 1
        self._prev_order = None
        self.stack = [0]
        self.subdirectives = {}

    def _add_event(self, order, event):
        if order == self._prev_order:
            self.events[order][-1].append(event)
        else:
            self._prev_order = order
            self.events.setdefault(order, [])
            self.events[order].append([event])

    def append(self, kind, data, pos):
        """Append a stream event to the buffer.
        
        :param kind: the stream event kind
        :param data: the event data
        :param pos: the position of the event in the source
        """
        if kind is SUB:
            # The order needs to be +1 because a new START kind event will
            # happen and we we need to wrap those events into our custom kind(s)
            order = self.stack[-1] + 1
            subdirectives, substream = data
            # Store the directives that should be applied after translation
            self.subdirectives.setdefault(order, []).extend(subdirectives)
            self._add_event(order, (SUB_START, None, pos))
            for skind, sdata, spos in substream:
                self.append(skind, sdata, spos)
            self._add_event(order, (SUB_END, None, pos))
        elif kind is TEXT:
            if '[' in data or ']' in data:
                # Quote [ and ] if it ain't us adding it, ie, if the user is
                # using those chars in his templates, escape them
                data = data.replace('[', '\[').replace(']', '\]')
            self.string.append(data)
            self._add_event(self.stack[-1], (kind, data, pos))
        elif kind is EXPR:
            if self.params:
                param = self.params.pop(0)
            else:
                params = ', '.join(['"%s"' % p for p in self.orig_params if p])
                if params:
                    params = "(%s)" % params
                raise IndexError("%d parameters%s given to 'i18n:%s' but "
                                 "%d or more expressions used in '%s', line %s"
                                 % (len(self.orig_params), params, 
                                    self.directive.tagname,
                                    len(self.orig_params) + 1,
                                    os.path.basename(pos[0] or
                                                     'In-memory Template'),
                                    pos[1]))
            self.string.append('%%(%s)s' % param)
            self._add_event(self.stack[-1], (kind, data, pos))
            self.values[param] = (kind, data, pos)
        else:
            if kind is START: 
                self.string.append('[%d:' % self.order)
                self.stack.append(self.order)
                self._add_event(self.stack[-1], (kind, data, pos))
                self.depth += 1
                self.order += 1
            elif kind is END:
                self.depth -= 1
                if self.depth:
                    self._add_event(self.stack[-1], (kind, data, pos))
                    self.string.append(']')
                    self.stack.pop()

    def format(self):
        """Return a message identifier representing the content in the
        buffer.
        """
        return ''.join(self.string).strip()

    def translate(self, string, regex=re.compile(r'%\((\w+)\)s')):
        """Interpolate the given message translation with the events in the
        buffer and return the translated stream.
        
        :param string: the translated message string
        """
        substream = None

        def yield_parts(string):
            for idx, part in enumerate(regex.split(string)):
                if idx % 2:
                    yield self.values[part]
                elif part:
                    yield (TEXT,
                           part.replace('\[', '[').replace('\]', ']'),
                           (None, -1, -1)
                    )

        parts = parse_msg(string)
        parts_counter = {}
        for order, string in parts:
            parts_counter.setdefault(order, []).append(None)

        while parts:
            order, string = parts.pop(0)
            events = self.events[order].pop(0)
            parts_counter[order].pop()

            for event in events:
                if event[0] is SUB_START:
                    substream = []
                elif event[0] is SUB_END:
                    # Yield a substream which might have directives to be
                    # applied to it (after translation events)
                    yield SUB, (self.subdirectives[order], substream), event[2]
                    substream = None
                elif event[0] is TEXT:
                    if string:
                        for part in yield_parts(string):
                            if substream is not None:
                                substream.append(part)
                            else:
                                yield part
                        # String handled, reset it
                        string = None
                elif event[0] is START:
                    if substream is not None:
                        substream.append(event)
                    else:
                        yield event
                    if string:
                        for part in yield_parts(string):
                            if substream is not None:
                                substream.append(part)
                            else:
                                yield part
                        # String handled, reset it
                        string = None
                elif event[0] is END:
                    if string:
                        for part in yield_parts(string):
                            if substream is not None:
                                substream.append(part)
                            else:
                                yield part
                        # String handled, reset it
                        string = None
                    if substream is not None:
                        substream.append(event)
                    else:
                        yield event
                elif event[0] is EXPR:
                    # These are handled on the strings itself
                    continue
                else:
                    if string:
                        for part in yield_parts(string):
                            if substream is not None:
                                substream.append(part)
                            else:
                                yield part
                        # String handled, reset it
                        string = None
                    if substream is not None:
                        substream.append(event)
                    else:
                        yield event


def parse_msg(string, regex=re.compile(r'(?:\[(\d+)\:)|(?<!\\)\]')):
    """Parse a translated message using Genshi mixed content message
    formatting.
    
    >>> parse_msg("See [1:Help].")
    [(0, 'See '), (1, 'Help'), (0, '.')]
    
    >>> parse_msg("See [1:our [2:Help] page] for details.")
    [(0, 'See '), (1, 'our '), (2, 'Help'), (1, ' page'), (0, ' for details.')]
    
    >>> parse_msg("[2:Details] finden Sie in [1:Hilfe].")
    [(2, 'Details'), (0, ' finden Sie in '), (1, 'Hilfe'), (0, '.')]
    
    >>> parse_msg("[1:] Bilder pro Seite anzeigen.")
    [(1, ''), (0, ' Bilder pro Seite anzeigen.')]
    
    :param string: the translated message string
    :return: a list of ``(order, string)`` tuples
    :rtype: `list`
    """
    parts = []
    stack = [0]
    while True:
        mo = regex.search(string)
        if not mo:
            break

        if mo.start() or stack[-1]:
            parts.append((stack[-1], string[:mo.start()]))
        string = string[mo.end():]

        orderno = mo.group(1)
        if orderno is not None:
            stack.append(int(orderno))
        else:
            stack.pop()
        if not stack:
            break

    if string:
        parts.append((stack[-1], string))

    return parts


def extract_from_code(code, gettext_functions):
    """Extract strings from Python bytecode.
    
    >>> from genshi.template.eval import Expression
    >>> expr = Expression('_("Hello")')
    >>> list(extract_from_code(expr, GETTEXT_FUNCTIONS))
    [('_', u'Hello')]
    
    >>> expr = Expression('ngettext("You have %(num)s item", '
    ...                            '"You have %(num)s items", num)')
    >>> list(extract_from_code(expr, GETTEXT_FUNCTIONS))
    [('ngettext', (u'You have %(num)s item', u'You have %(num)s items', None))]
    
    :param code: the `Code` object
    :type code: `genshi.template.eval.Code`
    :param gettext_functions: a sequence of function names
    :since: version 0.5
    """
    def _walk(node):
        if isinstance(node, _ast.Call) and isinstance(node.func, _ast.Name) \
                and node.func.id in gettext_functions:
            strings = []
            def _add(arg):
                if isinstance(arg, _ast.Str) and isinstance(arg.s, unicode):
                    strings.append(arg.s)
                elif isinstance(arg, _ast.Str):
                    strings.append(unicode(arg.s, 'utf-8'))
                elif arg:
                    strings.append(None)
            [_add(arg) for arg in node.args]
            _add(node.starargs)
            _add(node.kwargs)
            if len(strings) == 1:
                strings = strings[0]
            else:
                strings = tuple(strings)
            yield node.func.id, strings
        elif node._fields:
            children = []
            for field in node._fields:
                child = getattr(node, field, None)
                if isinstance(child, list):
                    for elem in child:
                        children.append(elem)
                elif isinstance(child, _ast.AST):
                    children.append(child)
            for child in children:
                for funcname, strings in _walk(child):
                    yield funcname, strings
    return _walk(code.ast)


def extract(fileobj, keywords, comment_tags, options):
    """Babel extraction method for Genshi templates.
    
    :param fileobj: the file-like object the messages should be extracted from
    :param keywords: a list of keywords (i.e. function names) that should be
                     recognized as translation functions
    :param comment_tags: a list of translator tags to search for and include
                         in the results
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)`` tuples
    :rtype: ``iterator``
    """
    template_class = options.get('template_class', MarkupTemplate)
    if isinstance(template_class, basestring):
        module, clsname = template_class.split(':', 1)
        template_class = getattr(__import__(module, {}, {}, [clsname]), clsname)
    encoding = options.get('encoding', None)

    extract_text = options.get('extract_text', True)
    if isinstance(extract_text, basestring):
        extract_text = extract_text.lower() in ('1', 'on', 'yes', 'true')

    ignore_tags = options.get('ignore_tags', Translator.IGNORE_TAGS)
    if isinstance(ignore_tags, basestring):
        ignore_tags = ignore_tags.split()
    ignore_tags = [QName(tag) for tag in ignore_tags]

    include_attrs = options.get('include_attrs', Translator.INCLUDE_ATTRS)
    if isinstance(include_attrs, basestring):
        include_attrs = include_attrs.split()
    include_attrs = [QName(attr) for attr in include_attrs]

    tmpl = template_class(fileobj, filename=getattr(fileobj, 'name', None),
                          encoding=encoding)
    tmpl.loader = None

    translator = Translator(None, ignore_tags, include_attrs, extract_text)
    if hasattr(tmpl, 'add_directives'):
        tmpl.add_directives(Translator.NAMESPACE, translator)
    for message in translator.extract(tmpl.stream, gettext_functions=keywords):
        yield message
