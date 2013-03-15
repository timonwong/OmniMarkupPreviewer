# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Edgewall Software
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
from pprint import pprint
import unittest

from genshi import HTML
from genshi.builder import Element
from genshi.core import START, END, TEXT, QName, Attrs
from genshi.filters.transform import Transformer, StreamBuffer, ENTER, EXIT, \
                                     OUTSIDE, INSIDE, ATTR, BREAK
import genshi.filters.transform


FOO = '<root>ROOT<foo name="foo">FOO</foo></root>'
FOOBAR = '<root>ROOT<foo name="foo" size="100">FOO</foo><bar name="bar">BAR</bar></root>'


def _simplify(stream, with_attrs=False):
    """Simplify a marked stream."""
    def _generate():
        for mark, (kind, data, pos) in stream:
            if kind is START:
                if with_attrs:
                    data = (str(data[0]), dict((str(k), v)
                                                   for k, v in data[1]))
                else:
                    data = str(data[0])
            elif kind is END:
                data = str(data)
            elif kind is ATTR:
                kind = ATTR
                data = dict((str(k), v) for k, v in data[1])
            yield mark, kind, data
    return list(_generate())


def _transform(html, transformer, with_attrs=False):
    """Apply transformation returning simplified marked stream."""
    if isinstance(html, str) and not isinstance(html, str):
        html = HTML(html, encoding='utf-8')
    elif isinstance(html, str):
        html = HTML(html, encoding='utf-8')
    stream = transformer(html, keep_marks=True)
    return _simplify(stream, with_attrs)


class SelectTest(unittest.TestCase):
    """Test .select()"""
    def _select(self, select):
        html = HTML(FOOBAR, encoding='utf-8')
        if isinstance(select, str):
            select = [select]
        transformer = Transformer(select[0])
        for sel in select[1:]:
            transformer = transformer.select(sel)
        return _transform(html, transformer)

    def test_select_single_element(self):
        self.assertEqual(
            self._select('foo'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (ENTER, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (EXIT, END, 'foo'),
             (None, START, 'bar'),
             (None, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')],
            )

    def test_select_context(self):
        self.assertEqual(
            self._select('.'),
            [(ENTER, START, 'root'),
             (INSIDE, TEXT, 'ROOT'),
             (INSIDE, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (INSIDE, END, 'foo'),
             (INSIDE, START, 'bar'),
             (INSIDE, TEXT, 'BAR'),
             (INSIDE, END, 'bar'),
             (EXIT, END, 'root')]
            )

    def test_select_inside_select(self):
        self.assertEqual(
            self._select(['.', 'foo']),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (ENTER, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (EXIT, END, 'foo'),
             (None, START, 'bar'),
             (None, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')],
            )

    def test_select_text(self):
        self.assertEqual(
            self._select('*/text()'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (None, START, 'foo'),
             (OUTSIDE, TEXT, 'FOO'),
             (None, END, 'foo'),
             (None, START, 'bar'),
             (OUTSIDE, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')],
            )

    def test_select_attr(self):
        self.assertEqual(
            self._select('foo/@name'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (ATTR, ATTR, {'name': 'foo'}),
             (None, START, 'foo'),
             (None, TEXT, 'FOO'),
             (None, END, 'foo'),
             (None, START, 'bar'),
             (None, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')]
            )

    def test_select_text_context(self):
        self.assertEqual(
            list(Transformer('.')(HTML('foo'), keep_marks=True)),
            [('OUTSIDE', ('TEXT', 'foo', (None, 1, 0)))],
            )


class InvertTest(unittest.TestCase):
    def _invert(self, select):
        return _transform(FOO, Transformer(select).invert())

    def test_invert_element(self):
        self.assertEqual(
            self._invert('foo'),
            [(OUTSIDE, START, 'root'),
             (OUTSIDE, TEXT, 'ROOT'),
             (None, START, 'foo'),
             (None, TEXT, 'FOO'),
             (None, END, 'foo'),
             (OUTSIDE, END, 'root')]
            )

    def test_invert_inverted_element(self):
        self.assertEqual(
            _transform(FOO, Transformer('foo').invert().invert()),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (OUTSIDE, START, 'foo'),
             (OUTSIDE, TEXT, 'FOO'),
             (OUTSIDE, END, 'foo'),
             (None, END, 'root')]
            )

    def test_invert_text(self):
        self.assertEqual(
            self._invert('foo/text()'),
            [(OUTSIDE, START, 'root'),
             (OUTSIDE, TEXT, 'ROOT'),
             (OUTSIDE, START, 'foo'),
             (None, TEXT, 'FOO'),
             (OUTSIDE, END, 'foo'),
             (OUTSIDE, END, 'root')]
            )

    def test_invert_attribute(self):
        self.assertEqual(
            self._invert('foo/@name'),
            [(OUTSIDE, START, 'root'),
             (OUTSIDE, TEXT, 'ROOT'),
             (None, ATTR, {'name': 'foo'}),
             (OUTSIDE, START, 'foo'),
             (OUTSIDE, TEXT, 'FOO'),
             (OUTSIDE, END, 'foo'),
             (OUTSIDE, END, 'root')]
            )

    def test_invert_context(self):
        self.assertEqual(
            self._invert('.'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (None, START, 'foo'),
             (None, TEXT, 'FOO'),
             (None, END, 'foo'),
             (None, END, 'root')]
            )

    def test_invert_text_context(self):
        self.assertEqual(
            _simplify(Transformer('.').invert()(HTML('foo'), keep_marks=True)),
            [(None, 'TEXT', 'foo')],
            )



class EndTest(unittest.TestCase):
    def test_end(self):
        stream = _transform(FOO, Transformer('foo').end())
        self.assertEqual(
            stream,
            [(OUTSIDE, START, 'root'),
             (OUTSIDE, TEXT, 'ROOT'),
             (OUTSIDE, START, 'foo'),
             (OUTSIDE, TEXT, 'FOO'),
             (OUTSIDE, END, 'foo'),
             (OUTSIDE, END, 'root')]
            )


class EmptyTest(unittest.TestCase):
    def _empty(self, select):
        return _transform(FOO, Transformer(select).empty())

    def test_empty_element(self):
        self.assertEqual(
            self._empty('foo'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (ENTER, START, 'foo'),
             (EXIT, END, 'foo'),
             (None, END, 'root')],
            )

    def test_empty_text(self):
        self.assertEqual(
            self._empty('foo/text()'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (None, START, 'foo'),
             (OUTSIDE, TEXT, 'FOO'),
             (None, END, 'foo'),
             (None, END, 'root')]
            )

    def test_empty_attr(self):
        self.assertEqual(
            self._empty('foo/@name'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (ATTR, ATTR, {'name': 'foo'}),
             (None, START, 'foo'),
             (None, TEXT, 'FOO'),
             (None, END, 'foo'),
             (None, END, 'root')]
            )

    def test_empty_context(self):
        self.assertEqual(
            self._empty('.'),
            [(ENTER, START, 'root'),
             (EXIT, END, 'root')]
            )

    def test_empty_text_context(self):
        self.assertEqual(
            _simplify(Transformer('.')(HTML('foo'), keep_marks=True)),
            [(OUTSIDE, TEXT, 'foo')],
            )


class RemoveTest(unittest.TestCase):
    def _remove(self, select):
        return _transform(FOO, Transformer(select).remove())

    def test_remove_element(self):
        self.assertEqual(
            self._remove('foo|bar'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (None, END, 'root')]
            )

    def test_remove_text(self):
        self.assertEqual(
            self._remove('//text()'),
            [(None, START, 'root'),
             (None, START, 'foo'),
             (None, END, 'foo'),
             (None, END, 'root')]
            )

    def test_remove_attr(self):
        self.assertEqual(
            self._remove('foo/@name'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (None, START, 'foo'),
             (None, TEXT, 'FOO'),
             (None, END, 'foo'),
             (None, END, 'root')]
            )

    def test_remove_context(self):
        self.assertEqual(
            self._remove('.'),
            [],
            )

    def test_remove_text_context(self):
        self.assertEqual(
            _transform('foo', Transformer('.').remove()),
            [],
            )


class UnwrapText(unittest.TestCase):
    def _unwrap(self, select):
        return _transform(FOO, Transformer(select).unwrap())

    def test_unwrap_element(self):
        self.assertEqual(
            self._unwrap('foo'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (INSIDE, TEXT, 'FOO'),
             (None, END, 'root')]
            )

    def test_unwrap_text(self):
        self.assertEqual(
            self._unwrap('foo/text()'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (None, START, 'foo'),
             (OUTSIDE, TEXT, 'FOO'),
             (None, END, 'foo'),
             (None, END, 'root')]
            )

    def test_unwrap_attr(self):
        self.assertEqual(
            self._unwrap('foo/@name'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (ATTR, ATTR, {'name': 'foo'}),
             (None, START, 'foo'),
             (None, TEXT, 'FOO'),
             (None, END, 'foo'),
             (None, END, 'root')]
            )

    def test_unwrap_adjacent(self):
        self.assertEqual(
            _transform(FOOBAR, Transformer('foo|bar').unwrap()),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (INSIDE, TEXT, 'FOO'),
             (INSIDE, TEXT, 'BAR'),
             (None, END, 'root')]
            )

    def test_unwrap_root(self):
        self.assertEqual(
            self._unwrap('.'),
            [(INSIDE, TEXT, 'ROOT'),
             (INSIDE, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (INSIDE, END, 'foo')]
            )

    def test_unwrap_text_root(self):
        self.assertEqual(
            _transform('foo', Transformer('.').unwrap()),
            [(OUTSIDE, TEXT, 'foo')],
            )


class WrapTest(unittest.TestCase):
    def _wrap(self, select, wrap='wrap'):
        return _transform(FOO, Transformer(select).wrap(wrap))

    def test_wrap_element(self):
        self.assertEqual(
            self._wrap('foo'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (None, START, 'wrap'),
             (ENTER, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (EXIT, END, 'foo'),
             (None, END, 'wrap'),
             (None, END, 'root')]
            )

    def test_wrap_adjacent_elements(self):
        self.assertEqual(
            _transform(FOOBAR, Transformer('foo|bar').wrap('wrap')),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (None, START, 'wrap'),
             (ENTER, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (EXIT, END, 'foo'),
             (None, END, 'wrap'),
             (None, START, 'wrap'),
             (ENTER, START, 'bar'),
             (INSIDE, TEXT, 'BAR'),
             (EXIT, END, 'bar'),
             (None, END, 'wrap'),
             (None, END, 'root')]
            )

    def test_wrap_text(self):
        self.assertEqual(
            self._wrap('foo/text()'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (None, START, 'foo'),
             (None, START, 'wrap'),
             (OUTSIDE, TEXT, 'FOO'),
             (None, END, 'wrap'),
             (None, END, 'foo'),
             (None, END, 'root')]
            )

    def test_wrap_root(self):
        self.assertEqual(
            self._wrap('.'),
            [(None, START, 'wrap'),
             (ENTER, START, 'root'),
             (INSIDE, TEXT, 'ROOT'),
             (INSIDE, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (INSIDE, END, 'foo'),
             (EXIT, END, 'root'),
             (None, END, 'wrap')]
            )

    def test_wrap_text_root(self):
        self.assertEqual(
            _transform('foo', Transformer('.').wrap('wrap')),
            [(None, START, 'wrap'),
             (OUTSIDE, TEXT, 'foo'),
             (None, END, 'wrap')],
            )

    def test_wrap_with_element(self):
        element = Element('a', href='http://localhost')
        self.assertEqual(
            _transform('foo', Transformer('.').wrap(element), with_attrs=True),
            [(None, START, ('a', {'href': 'http://localhost'})),
             (OUTSIDE, TEXT, 'foo'),
             (None, END, 'a')]
            )


class FilterTest(unittest.TestCase):
    def _filter(self, select, html=FOOBAR):
        """Returns a list of lists of filtered elements."""
        output = []
        def filtered(stream):
            interval = []
            output.append(interval)
            for event in stream:
                interval.append(event)
                yield event
        _transform(html, Transformer(select).filter(filtered))
        simplified = []
        for sub in output:
            simplified.append(_simplify([(None, event) for event in sub]))
        return simplified

    def test_filter_element(self):
        self.assertEqual(
            self._filter('foo'),
            [[(None, START, 'foo'),
              (None, TEXT, 'FOO'),
              (None, END, 'foo')]]
            )

    def test_filter_adjacent_elements(self):
        self.assertEqual(
            self._filter('foo|bar'),
            [[(None, START, 'foo'),
              (None, TEXT, 'FOO'),
              (None, END, 'foo')],
             [(None, START, 'bar'),
              (None, TEXT, 'BAR'),
              (None, END, 'bar')]]
            )

    def test_filter_text(self):
        self.assertEqual(
            self._filter('*/text()'),
            [[(None, TEXT, 'FOO')],
             [(None, TEXT, 'BAR')]]
            )
    def test_filter_root(self):
        self.assertEqual(
            self._filter('.'),
            [[(None, START, 'root'),
              (None, TEXT, 'ROOT'),
              (None, START, 'foo'),
              (None, TEXT, 'FOO'),
              (None, END, 'foo'),
              (None, START, 'bar'),
              (None, TEXT, 'BAR'),
              (None, END, 'bar'),
              (None, END, 'root')]]
            )

    def test_filter_text_root(self):
        self.assertEqual(
            self._filter('.', 'foo'),
            [[(None, TEXT, 'foo')]])

    def test_filter_after_outside(self):
        stream = _transform(
            '<root>x</root>', Transformer('//root/text()').filter(lambda x: x))
        self.assertEqual(
            list(stream),
            [(None, START, 'root'),
             (OUTSIDE, TEXT, 'x'),
             (None, END, 'root')])


class MapTest(unittest.TestCase):
    def _map(self, select, kind=None):
        data = []
        def record(d):
            data.append(d)
            return d
        _transform(FOOBAR, Transformer(select).map(record, kind))
        return data

    def test_map_element(self):
        self.assertEqual(
            self._map('foo'),
            [(QName('foo'), Attrs([(QName('name'), 'foo'),
                                   (QName('size'), '100')])),
             'FOO',
             QName('foo')]
        )

    def test_map_with_text_kind(self):
        self.assertEqual(
            self._map('.', TEXT),
            ['ROOT', 'FOO', 'BAR']
        )

    def test_map_with_root_and_end_kind(self):
        self.assertEqual(
            self._map('.', END),
            [QName('foo'), QName('bar'), QName('root')]
        )

    def test_map_with_attribute(self):
        self.assertEqual(
            self._map('foo/@name'),
            [(QName('foo@*'), Attrs([('name', 'foo')]))]
        )


class SubstituteTest(unittest.TestCase):
    def _substitute(self, select, pattern, replace):
        return _transform(FOOBAR, Transformer(select).substitute(pattern, replace))

    def test_substitute_foo(self):
        self.assertEqual(
            self._substitute('foo', 'FOO|BAR', 'FOOOOO'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (ENTER, START, 'foo'),
             (INSIDE, TEXT, 'FOOOOO'),
             (EXIT, END, 'foo'),
             (None, START, 'bar'),
             (None, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')]
            )

    def test_substitute_foobar_with_group(self):
        self.assertEqual(
            self._substitute('foo|bar', '(FOO|BAR)', r'(\1)'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (ENTER, START, 'foo'),
             (INSIDE, TEXT, '(FOO)'),
             (EXIT, END, 'foo'),
             (ENTER, START, 'bar'),
             (INSIDE, TEXT, '(BAR)'),
             (EXIT, END, 'bar'),
             (None, END, 'root')]
            )


class RenameTest(unittest.TestCase):
    def _rename(self, select):
        return _transform(FOOBAR, Transformer(select).rename('foobar'))

    def test_rename_root(self):
        self.assertEqual(
            self._rename('.'),
            [(ENTER, START, 'foobar'),
             (INSIDE, TEXT, 'ROOT'),
             (INSIDE, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (INSIDE, END, 'foo'),
             (INSIDE, START, 'bar'),
             (INSIDE, TEXT, 'BAR'),
             (INSIDE, END, 'bar'),
             (EXIT, END, 'foobar')]
            )

    def test_rename_element(self):
        self.assertEqual(
            self._rename('foo|bar'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (ENTER, START, 'foobar'),
             (INSIDE, TEXT, 'FOO'),
             (EXIT, END, 'foobar'),
             (ENTER, START, 'foobar'),
             (INSIDE, TEXT, 'BAR'),
             (EXIT, END, 'foobar'),
             (None, END, 'root')]
            )

    def test_rename_text(self):
        self.assertEqual(
            self._rename('foo/text()'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (None, START, 'foo'),
             (OUTSIDE, TEXT, 'FOO'),
             (None, END, 'foo'),
             (None, START, 'bar'),
             (None, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')]
            )


class ContentTestMixin(object):
    def _apply(self, select, content=None, html=FOOBAR):
        class Injector(object):
            count = 0

            def __iter__(self):
                self.count += 1
                return iter(HTML('CONTENT %i' % self.count))

        if isinstance(html, str) and not isinstance(html, str):
            html = HTML(html, encoding='utf-8')
        else:
            html = HTML(html)
        if content is None:
            content = Injector()
        elif isinstance(content, str):
            content = HTML(content)
        return _transform(html, getattr(Transformer(select), self.operation)
                                (content))


class ReplaceTest(unittest.TestCase, ContentTestMixin):
    operation = 'replace'

    def test_replace_element(self):
        self.assertEqual(
            self._apply('foo'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (None, TEXT, 'CONTENT 1'),
             (None, START, 'bar'),
             (None, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')]
            )

    def test_replace_text(self):
        self.assertEqual(
            self._apply('text()'),
            [(None, START, 'root'),
             (None, TEXT, 'CONTENT 1'),
             (None, START, 'foo'),
             (None, TEXT, 'FOO'),
             (None, END, 'foo'),
             (None, START, 'bar'),
             (None, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')]
            )

    def test_replace_context(self):
        self.assertEqual(
            self._apply('.'),
            [(None, TEXT, 'CONTENT 1')],
            )

    def test_replace_text_context(self):
        self.assertEqual(
            self._apply('.', html='foo'),
            [(None, TEXT, 'CONTENT 1')],
            )

    def test_replace_adjacent_elements(self):
        self.assertEqual(
            self._apply('*'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (None, TEXT, 'CONTENT 1'),
             (None, TEXT, 'CONTENT 2'),
             (None, END, 'root')],
            )

    def test_replace_all(self):
        self.assertEqual(
            self._apply('*|text()'),
            [(None, START, 'root'),
             (None, TEXT, 'CONTENT 1'),
             (None, TEXT, 'CONTENT 2'),
             (None, TEXT, 'CONTENT 3'),
             (None, END, 'root')],
            )

    def test_replace_with_callback(self):
        count = [0]
        def content():
            count[0] += 1
            yield '%2i.' % count[0]
        self.assertEqual(
            self._apply('*', content),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (None, TEXT, ' 1.'),
             (None, TEXT, ' 2.'),
             (None, END, 'root')]
            )


class BeforeTest(unittest.TestCase, ContentTestMixin):
    operation = 'before'

    def test_before_element(self):
        self.assertEqual(
            self._apply('foo'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (None, TEXT, 'CONTENT 1'),
             (ENTER, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (EXIT, END, 'foo'),
             (None, START, 'bar'),
             (None, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')]
            )

    def test_before_text(self):
        self.assertEqual(
            self._apply('text()'),
            [(None, START, 'root'),
             (None, TEXT, 'CONTENT 1'),
             (OUTSIDE, TEXT, 'ROOT'),
             (None, START, 'foo'),
             (None, TEXT, 'FOO'),
             (None, END, 'foo'),
             (None, START, 'bar'),
             (None, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')]
            )

    def test_before_context(self):
        self.assertEqual(
            self._apply('.'),
            [(None, TEXT, 'CONTENT 1'),
             (ENTER, START, 'root'),
             (INSIDE, TEXT, 'ROOT'),
             (INSIDE, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (INSIDE, END, 'foo'),
             (INSIDE, START, 'bar'),
             (INSIDE, TEXT, 'BAR'),
             (INSIDE, END, 'bar'),
             (EXIT, END, 'root')]
            )

    def test_before_text_context(self):
        self.assertEqual(
            self._apply('.', html='foo'),
            [(None, TEXT, 'CONTENT 1'),
             (OUTSIDE, TEXT, 'foo')]
            )

    def test_before_adjacent_elements(self):
        self.assertEqual(
            self._apply('*'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (None, TEXT, 'CONTENT 1'),
             (ENTER, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (EXIT, END, 'foo'),
             (None, TEXT, 'CONTENT 2'),
             (ENTER, START, 'bar'),
             (INSIDE, TEXT, 'BAR'),
             (EXIT, END, 'bar'),
             (None, END, 'root')]

            )

    def test_before_all(self):
        self.assertEqual(
            self._apply('*|text()'),
            [(None, START, 'root'),
             (None, TEXT, 'CONTENT 1'),
             (OUTSIDE, TEXT, 'ROOT'),
             (None, TEXT, 'CONTENT 2'),
             (ENTER, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (EXIT, END, 'foo'),
             (None, TEXT, 'CONTENT 3'),
             (ENTER, START, 'bar'),
             (INSIDE, TEXT, 'BAR'),
             (EXIT, END, 'bar'),
             (None, END, 'root')]
            )

    def test_before_with_callback(self):
        count = [0]
        def content():
            count[0] += 1
            yield '%2i.' % count[0]
        self.assertEqual(
            self._apply('foo/text()', content),
            [(None, 'START', 'root'),
             (None, 'TEXT', 'ROOT'),
             (None, 'START', 'foo'),
             (None, 'TEXT', ' 1.'),
             ('OUTSIDE', 'TEXT', 'FOO'),
             (None, 'END', 'foo'),
             (None, 'START', 'bar'),
             (None, 'TEXT', 'BAR'),
             (None, 'END', 'bar'),
             (None, 'END', 'root')]
            )


class AfterTest(unittest.TestCase, ContentTestMixin):
    operation = 'after'

    def test_after_element(self):
        self.assertEqual(
            self._apply('foo'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (ENTER, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (EXIT, END, 'foo'),
             (None, TEXT, 'CONTENT 1'),
             (None, START, 'bar'),
             (None, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')]
            )

    def test_after_text(self):
        self.assertEqual(
            self._apply('text()'),
            [(None, START, 'root'),
             (OUTSIDE, TEXT, 'ROOT'),
             (None, TEXT, 'CONTENT 1'),
             (None, START, 'foo'),
             (None, TEXT, 'FOO'),
             (None, END, 'foo'),
             (None, START, 'bar'),
             (None, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')]
            )

    def test_after_context(self):
        self.assertEqual(
            self._apply('.'),
            [(ENTER, START, 'root'),
             (INSIDE, TEXT, 'ROOT'),
             (INSIDE, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (INSIDE, END, 'foo'),
             (INSIDE, START, 'bar'),
             (INSIDE, TEXT, 'BAR'),
             (INSIDE, END, 'bar'),
             (EXIT, END, 'root'),
             (None, TEXT, 'CONTENT 1')]
            )

    def test_after_text_context(self):
        self.assertEqual(
            self._apply('.', html='foo'),
            [(OUTSIDE, TEXT, 'foo'),
             (None, TEXT, 'CONTENT 1')]
            )

    def test_after_adjacent_elements(self):
        self.assertEqual(
            self._apply('*'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (ENTER, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (EXIT, END, 'foo'),
             (None, TEXT, 'CONTENT 1'),
             (ENTER, START, 'bar'),
             (INSIDE, TEXT, 'BAR'),
             (EXIT, END, 'bar'),
             (None, TEXT, 'CONTENT 2'),
             (None, END, 'root')]

            )

    def test_after_all(self):
        self.assertEqual(
            self._apply('*|text()'),
            [(None, START, 'root'),
             (OUTSIDE, TEXT, 'ROOT'),
             (None, TEXT, 'CONTENT 1'),
             (ENTER, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (EXIT, END, 'foo'),
             (None, TEXT, 'CONTENT 2'),
             (ENTER, START, 'bar'),
             (INSIDE, TEXT, 'BAR'),
             (EXIT, END, 'bar'),
             (None, TEXT, 'CONTENT 3'),
             (None, END, 'root')]
            )

    def test_after_with_callback(self):
        count = [0]
        def content():
            count[0] += 1
            yield '%2i.' % count[0]
        self.assertEqual(
            self._apply('foo/text()', content),
            [(None, 'START', 'root'),
             (None, 'TEXT', 'ROOT'),
             (None, 'START', 'foo'),
             ('OUTSIDE', 'TEXT', 'FOO'),
             (None, 'TEXT', ' 1.'),
             (None, 'END', 'foo'),
             (None, 'START', 'bar'),
             (None, 'TEXT', 'BAR'),
             (None, 'END', 'bar'),
             (None, 'END', 'root')]
            )


class PrependTest(unittest.TestCase, ContentTestMixin):
    operation = 'prepend'

    def test_prepend_element(self):
        self.assertEqual(
            self._apply('foo'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (ENTER, START, 'foo'),
             (None, TEXT, 'CONTENT 1'),
             (INSIDE, TEXT, 'FOO'),
             (EXIT, END, 'foo'),
             (None, START, 'bar'),
             (None, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')]
            )

    def test_prepend_text(self):
        self.assertEqual(
            self._apply('text()'),
            [(None, START, 'root'),
             (OUTSIDE, TEXT, 'ROOT'),
             (None, START, 'foo'),
             (None, TEXT, 'FOO'),
             (None, END, 'foo'),
             (None, START, 'bar'),
             (None, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')]
            )

    def test_prepend_context(self):
        self.assertEqual(
            self._apply('.'),
            [(ENTER, START, 'root'),
             (None, TEXT, 'CONTENT 1'),
             (INSIDE, TEXT, 'ROOT'),
             (INSIDE, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (INSIDE, END, 'foo'),
             (INSIDE, START, 'bar'),
             (INSIDE, TEXT, 'BAR'),
             (INSIDE, END, 'bar'),
             (EXIT, END, 'root')],
            )

    def test_prepend_text_context(self):
        self.assertEqual(
            self._apply('.', html='foo'),
            [(OUTSIDE, TEXT, 'foo')]
            )

    def test_prepend_adjacent_elements(self):
        self.assertEqual(
            self._apply('*'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (ENTER, START, 'foo'),
             (None, TEXT, 'CONTENT 1'),
             (INSIDE, TEXT, 'FOO'),
             (EXIT, END, 'foo'),
             (ENTER, START, 'bar'),
             (None, TEXT, 'CONTENT 2'),
             (INSIDE, TEXT, 'BAR'),
             (EXIT, END, 'bar'),
             (None, END, 'root')]

            )

    def test_prepend_all(self):
        self.assertEqual(
            self._apply('*|text()'),
            [(None, START, 'root'),
             (OUTSIDE, TEXT, 'ROOT'),
             (ENTER, START, 'foo'),
             (None, TEXT, 'CONTENT 1'),
             (INSIDE, TEXT, 'FOO'),
             (EXIT, END, 'foo'),
             (ENTER, START, 'bar'),
             (None, TEXT, 'CONTENT 2'),
             (INSIDE, TEXT, 'BAR'),
             (EXIT, END, 'bar'),
             (None, END, 'root')]
            )

    def test_prepend_with_callback(self):
        count = [0]
        def content():
            count[0] += 1
            yield '%2i.' % count[0]
        self.assertEqual(
            self._apply('foo', content),
            [(None, 'START', 'root'),
             (None, 'TEXT', 'ROOT'),
             (ENTER, 'START', 'foo'),
             (None, 'TEXT', ' 1.'),
             (INSIDE, 'TEXT', 'FOO'),
             (EXIT, 'END', 'foo'),
             (None, 'START', 'bar'),
             (None, 'TEXT', 'BAR'),
             (None, 'END', 'bar'),
             (None, 'END', 'root')]
            )


class AppendTest(unittest.TestCase, ContentTestMixin):
    operation = 'append'

    def test_append_element(self):
        self.assertEqual(
            self._apply('foo'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (ENTER, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (None, TEXT, 'CONTENT 1'),
             (EXIT, END, 'foo'),
             (None, START, 'bar'),
             (None, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')]
            )

    def test_append_text(self):
        self.assertEqual(
            self._apply('text()'),
            [(None, START, 'root'),
             (OUTSIDE, TEXT, 'ROOT'),
             (None, START, 'foo'),
             (None, TEXT, 'FOO'),
             (None, END, 'foo'),
             (None, START, 'bar'),
             (None, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')]
            )

    def test_append_context(self):
        self.assertEqual(
            self._apply('.'),
            [(ENTER, START, 'root'),
             (INSIDE, TEXT, 'ROOT'),
             (INSIDE, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (INSIDE, END, 'foo'),
             (INSIDE, START, 'bar'),
             (INSIDE, TEXT, 'BAR'),
             (INSIDE, END, 'bar'),
             (None, TEXT, 'CONTENT 1'),
             (EXIT, END, 'root')],
            )

    def test_append_text_context(self):
        self.assertEqual(
            self._apply('.', html='foo'),
            [(OUTSIDE, TEXT, 'foo')]
            )

    def test_append_adjacent_elements(self):
        self.assertEqual(
            self._apply('*'),
            [(None, START, 'root'),
             (None, TEXT, 'ROOT'),
             (ENTER, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (None, TEXT, 'CONTENT 1'),
             (EXIT, END, 'foo'),
             (ENTER, START, 'bar'),
             (INSIDE, TEXT, 'BAR'),
             (None, TEXT, 'CONTENT 2'),
             (EXIT, END, 'bar'),
             (None, END, 'root')]

            )

    def test_append_all(self):
        self.assertEqual(
            self._apply('*|text()'),
            [(None, START, 'root'),
             (OUTSIDE, TEXT, 'ROOT'),
             (ENTER, START, 'foo'),
             (INSIDE, TEXT, 'FOO'),
             (None, TEXT, 'CONTENT 1'),
             (EXIT, END, 'foo'),
             (ENTER, START, 'bar'),
             (INSIDE, TEXT, 'BAR'),
             (None, TEXT, 'CONTENT 2'),
             (EXIT, END, 'bar'),
             (None, END, 'root')]
            )

    def test_append_with_callback(self):
        count = [0]
        def content():
            count[0] += 1
            yield '%2i.' % count[0]
        self.assertEqual(
            self._apply('foo', content),
            [(None, 'START', 'root'),
             (None, 'TEXT', 'ROOT'),
             (ENTER, 'START', 'foo'),
             (INSIDE, 'TEXT', 'FOO'),
             (None, 'TEXT', ' 1.'),
             (EXIT, 'END', 'foo'),
             (None, 'START', 'bar'),
             (None, 'TEXT', 'BAR'),
             (None, 'END', 'bar'),
             (None, 'END', 'root')]
            )



class AttrTest(unittest.TestCase):
    def _attr(self, select, name, value):
        return _transform(FOOBAR, Transformer(select).attr(name, value),
                          with_attrs=True)

    def test_set_existing_attr(self):
        self.assertEqual(
            self._attr('foo', 'name', 'FOO'),
            [(None, START, ('root', {})),
             (None, TEXT, 'ROOT'),
             (ENTER, START, ('foo', {'name': 'FOO', 'size': '100'})),
             (INSIDE, TEXT, 'FOO'),
             (EXIT, END, 'foo'),
             (None, START, ('bar', {'name': 'bar'})),
             (None, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')]
            )

    def test_set_new_attr(self):
        self.assertEqual(
            self._attr('foo', 'title', 'FOO'),
            [(None, START, ('root', {})),
             (None, TEXT, 'ROOT'),
             (ENTER, START, ('foo', {'name': 'foo', 'title': 'FOO', 'size': '100'})),
             (INSIDE, TEXT, 'FOO'),
             (EXIT, END, 'foo'),
             (None, START, ('bar', {'name': 'bar'})),
             (None, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')]
            )

    def test_attr_from_function(self):
        def set(name, event):
            self.assertEqual(name, 'name')
            return event[1][1].get('name').upper()

        self.assertEqual(
            self._attr('foo|bar', 'name', set),
            [(None, START, ('root', {})),
             (None, TEXT, 'ROOT'),
             (ENTER, START, ('foo', {'name': 'FOO', 'size': '100'})),
             (INSIDE, TEXT, 'FOO'),
             (EXIT, END, 'foo'),
             (ENTER, START, ('bar', {'name': 'BAR'})),
             (INSIDE, TEXT, 'BAR'),
             (EXIT, END, 'bar'),
             (None, END, 'root')]
            )

    def test_remove_attr(self):
        self.assertEqual(
            self._attr('foo', 'name', None),
            [(None, START, ('root', {})),
             (None, TEXT, 'ROOT'),
             (ENTER, START, ('foo', {'size': '100'})),
             (INSIDE, TEXT, 'FOO'),
             (EXIT, END, 'foo'),
             (None, START, ('bar', {'name': 'bar'})),
             (None, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')]
            )

    def test_remove_attr_with_function(self):
        def set(name, event):
            return None

        self.assertEqual(
            self._attr('foo', 'name', set),
            [(None, START, ('root', {})),
             (None, TEXT, 'ROOT'),
             (ENTER, START, ('foo', {'size': '100'})),
             (INSIDE, TEXT, 'FOO'),
             (EXIT, END, 'foo'),
             (None, START, ('bar', {'name': 'bar'})),
             (None, TEXT, 'BAR'),
             (None, END, 'bar'),
             (None, END, 'root')]
            )


class BufferTestMixin(object):
    def _apply(self, select, with_attrs=False):
        buffer = StreamBuffer()
        events = buffer.events

        class Trace(object):
            last = None
            trace = []

            def __call__(self, stream):
                for event in stream:
                    if events and hash(tuple(events)) != self.last:
                        self.last = hash(tuple(events))
                        self.trace.append(list(events))
                    yield event

        trace = Trace()
        output = _transform(FOOBAR, getattr(Transformer(select), self.operation)
                                    (buffer).apply(trace), with_attrs=with_attrs)
        simplified = []
        for interval in trace.trace:
            simplified.append(_simplify([(None, e) for e in interval],
                                         with_attrs=with_attrs))
        return output, simplified


class CopyTest(unittest.TestCase, BufferTestMixin):
    operation = 'copy'

    def test_copy_element(self):
        self.assertEqual(
            self._apply('foo')[1],
            [[(None, START, 'foo'),
              (None, TEXT, 'FOO'),
              (None, END, 'foo')]]
            )

    def test_copy_adjacent_elements(self):
        self.assertEqual(
            self._apply('foo|bar')[1],
            [[(None, START, 'foo'),
              (None, TEXT, 'FOO'),
              (None, END, 'foo')],
             [(None, START, 'bar'),
              (None, TEXT, 'BAR'),
              (None, END, 'bar')]]
            )

    def test_copy_all(self):
        self.assertEqual(
            self._apply('*|text()')[1],
            [[(None, TEXT, 'ROOT')],
             [(None, START, 'foo'),
              (None, TEXT, 'FOO'),
              (None, END, 'foo')],
             [(None, START, 'bar'),
              (None, TEXT, 'BAR'),
              (None, END, 'bar')]]
            )

    def test_copy_text(self):
        self.assertEqual(
            self._apply('*/text()')[1],
            [[(None, TEXT, 'FOO')],
             [(None, TEXT, 'BAR')]]
            )

    def test_copy_context(self):
        self.assertEqual(
            self._apply('.')[1],
            [[(None, START, 'root'),
              (None, TEXT, 'ROOT'),
              (None, START, 'foo'),
              (None, TEXT, 'FOO'),
              (None, END, 'foo'),
              (None, START, 'bar'),
              (None, TEXT, 'BAR'),
              (None, END, 'bar'),
              (None, END, 'root')]]
            )

    def test_copy_attribute(self):
        self.assertEqual(
            self._apply('foo/@name', with_attrs=True)[1],
            [[(None, ATTR, {'name': 'foo'})]]
            )

    def test_copy_attributes(self):
        self.assertEqual(
            self._apply('foo/@*', with_attrs=True)[1],
            [[(None, ATTR, {'name': 'foo', 'size': '100'})]]
            )


class CutTest(unittest.TestCase, BufferTestMixin):
    operation = 'cut'

    def test_cut_element(self):
        self.assertEqual(
            self._apply('foo'),
            ([(None, START, 'root'),
              (None, TEXT, 'ROOT'),
              (None, START, 'bar'),
              (None, TEXT, 'BAR'),
              (None, END, 'bar'),
              (None, END, 'root')],
             [[(None, START, 'foo'),
               (None, TEXT, 'FOO'),
               (None, END, 'foo')]])
            )

    def test_cut_adjacent_elements(self):
        self.assertEqual(
            self._apply('foo|bar'),
            ([(None, START, 'root'), 
              (None, TEXT, 'ROOT'),
              (BREAK, BREAK, None),
              (None, END, 'root')],
             [[(None, START, 'foo'),
               (None, TEXT, 'FOO'),
               (None, END, 'foo')],
              [(None, START, 'bar'),
               (None, TEXT, 'BAR'),
               (None, END, 'bar')]])
            )

    def test_cut_all(self):
        self.assertEqual(
            self._apply('*|text()'),
            ([(None, 'START', 'root'),
              ('BREAK', 'BREAK', None),
              ('BREAK', 'BREAK', None),
              (None, 'END', 'root')],
             [[(None, 'TEXT', 'ROOT')],
              [(None, 'START', 'foo'),
               (None, 'TEXT', 'FOO'),
               (None, 'END', 'foo')],
              [(None, 'START', 'bar'),
               (None, 'TEXT', 'BAR'),
               (None, 'END', 'bar')]])
            )

    def test_cut_text(self):
        self.assertEqual(
            self._apply('*/text()'),
            ([(None, 'START', 'root'),
              (None, 'TEXT', 'ROOT'),
              (None, 'START', 'foo'),
              (None, 'END', 'foo'),
              (None, 'START', 'bar'),
              (None, 'END', 'bar'),
              (None, 'END', 'root')],
             [[(None, 'TEXT', 'FOO')],
              [(None, 'TEXT', 'BAR')]])
            )

    def test_cut_context(self):
        self.assertEqual(
            self._apply('.')[1],
            [[(None, 'START', 'root'),
              (None, 'TEXT', 'ROOT'),
              (None, 'START', 'foo'),
              (None, 'TEXT', 'FOO'),
              (None, 'END', 'foo'),
              (None, 'START', 'bar'),
              (None, 'TEXT', 'BAR'),
              (None, 'END', 'bar'),
              (None, 'END', 'root')]]
            )

    def test_cut_attribute(self):
        self.assertEqual(
            self._apply('foo/@name', with_attrs=True),
            ([(None, START, ('root', {})),
              (None, TEXT, 'ROOT'),
              (None, START, ('foo', {'size': '100'})),
              (None, TEXT, 'FOO'),
              (None, END, 'foo'),
              (None, START, ('bar', {'name': 'bar'})),
              (None, TEXT, 'BAR'),
              (None, END, 'bar'),
              (None, END, 'root')],
             [[(None, ATTR, {'name': 'foo'})]])
            )

    def test_cut_attributes(self):
        self.assertEqual(
            self._apply('foo/@*', with_attrs=True),
            ([(None, START, ('root', {})),
              (None, TEXT, 'ROOT'),
              (None, START, ('foo', {})),
              (None, TEXT, 'FOO'),
              (None, END, 'foo'),
              (None, START, ('bar', {'name': 'bar'})),
              (None, TEXT, 'BAR'),
              (None, END, 'bar'),
              (None, END, 'root')],
             [[(None, ATTR, {'name': 'foo', 'size': '100'})]])
            )

# XXX Test this when the XPath implementation is fixed (#233).
#    def test_cut_attribute_or_attribute(self):
#        self.assertEqual(
#            self._apply('foo/@name | foo/@size', with_attrs=True),
#            ([(None, START, (u'root', {})),
#              (None, TEXT, u'ROOT'),
#              (None, START, (u'foo', {})),
#              (None, TEXT, u'FOO'),
#              (None, END, u'foo'),
#              (None, START, (u'bar', {u'name': u'bar'})),
#              (None, TEXT, u'BAR'),
#              (None, END, u'bar'),
#              (None, END, u'root')],
#             [[(None, ATTR, {u'name': u'foo', u'size': u'100'})]])
#            )




def suite():
    from genshi.input import HTML
    from genshi.core import Markup
    from genshi.builder import tag
    suite = unittest.TestSuite()
    for test in (SelectTest, InvertTest, EndTest,
                 EmptyTest, RemoveTest, UnwrapText, WrapTest, FilterTest,
                 MapTest, SubstituteTest, RenameTest, ReplaceTest, BeforeTest,
                 AfterTest, PrependTest, AppendTest, AttrTest, CopyTest, CutTest):
        suite.addTest(unittest.makeSuite(test, 'test'))
    suite.addTest(doctest.DocTestSuite(
        genshi.filters.transform, optionflags=doctest.NORMALIZE_WHITESPACE,
        extraglobs={'HTML': HTML, 'tag': tag, 'Markup': Markup}))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
