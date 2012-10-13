# -*- coding: utf-8 -*-
#
# Copyright (C) 2006 Edgewall Software
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

from genshi.input import XML
from genshi.path import Path, PathParser, PathSyntaxError, GenericStrategy, \
                        SingleStepStrategy, SimplePathStrategy


class FakePath(Path):
    def __init__(self, strategy):
        self.strategy = strategy
    def test(self, ignore_context = False):
        return self.strategy.test(ignore_context)


class PathTestCase(unittest.TestCase):

    strategies = [GenericStrategy, SingleStepStrategy, SimplePathStrategy]

    def test_error_no_absolute_path(self):
        self.assertRaises(PathSyntaxError, Path, '/root')

    def test_error_unsupported_axis(self):
        self.assertRaises(PathSyntaxError, Path, '..')
        self.assertRaises(PathSyntaxError, Path, 'parent::ma')

    def test_1step(self):
        xml = XML('<root><elem/></root>')
        self._test_eval(
            path = 'elem',
            equiv = '<Path "child::elem">',
            input = xml,
            output = '<elem/>'
        )
        self._test_eval(
            path = 'elem',
            equiv = '<Path "child::elem">',
            input = xml,
            output = '<elem/>'
        )
        self._test_eval(
            path = 'child::elem',
            equiv = '<Path "child::elem">',
            input = xml,
            output = '<elem/>'
        )
        self._test_eval(
            path = '//elem',
            equiv = '<Path "descendant-or-self::elem">',
            input = xml,
            output = '<elem/>'
        )
        self._test_eval(
            path = 'descendant::elem',
            equiv = '<Path "descendant::elem">',
            input = xml,
            output = '<elem/>'
        )

    def test_1step_self(self):
        xml = XML('<root><elem/></root>')
        self._test_eval(
            path = '.',
            equiv = '<Path "self::node()">',
            input = xml,
            output = '<root><elem/></root>'
        )
        self._test_eval(
            path = 'self::node()',
            equiv = '<Path "self::node()">',
            input = xml,
            output = '<root><elem/></root>'
        )

    def test_1step_wildcard(self):
        xml = XML('<root><elem/></root>')
        self._test_eval(
            path = '*',
            equiv = '<Path "child::*">',
            input = xml,
            output = '<elem/>'
        )
        self._test_eval(
            path = 'child::*',
            equiv = '<Path "child::*">',
            input = xml,
            output = '<elem/>'
        )
        self._test_eval(
            path = 'child::node()',
            equiv = '<Path "child::node()">',
            input = xml,
            output = '<elem/>'
        )
        self._test_eval(
            path = '//*',
            equiv = '<Path "descendant-or-self::*">',
            input = xml,
            output = '<root><elem/></root>'
        )

    def test_1step_attribute(self):
        self._test_eval(
            path = '@foo',
            equiv = '<Path "attribute::foo">',
            input = XML('<root/>'),
            output = ''
        )
        xml = XML('<root foo="bar"/>')
        self._test_eval(
            path = '@foo',
            equiv = '<Path "attribute::foo">',
            input = xml,
            output = 'bar'
        )
        self._test_eval(
            path = './@foo',
            equiv = '<Path "self::node()/attribute::foo">',
            input = xml,
            output = 'bar'
        )

    def test_1step_text(self):
        xml = XML('<root>Hey</root>')
        self._test_eval(
            path = 'text()',
            equiv = '<Path "child::text()">',
            input = xml,
            output = 'Hey'
        )
        self._test_eval(
            path = './text()',
            equiv = '<Path "self::node()/child::text()">',
            input = xml,
            output = 'Hey'
        )
        self._test_eval(
            path = '//text()',
            equiv = '<Path "descendant-or-self::text()">',
            input = xml,
            output = 'Hey'
        )
        self._test_eval(
            path = './/text()',
            equiv = '<Path "self::node()/descendant-or-self::node()/child::text()">',
            input = xml,
            output = 'Hey'
        )

    def test_2step(self):
        xml = XML('<root><foo/><bar/></root>')
        self._test_eval('*', input=xml, output='<foo/><bar/>')
        self._test_eval('bar', input=xml, output='<bar/>')
        self._test_eval('baz', input=xml, output='')

    def test_2step_attribute(self):
        xml = XML('<elem class="x"><span id="joe">Hey Joe</span></elem>')
        self._test_eval('@*', input=xml, output='x')
        self._test_eval('./@*', input=xml, output='x')
        self._test_eval('.//@*', input=xml, output='xjoe')
        self._test_eval('*/@*', input=xml, output='joe')

        xml = XML('<elem><foo id="1"/><foo id="2"/></elem>')
        self._test_eval('@*', input=xml, output='')
        self._test_eval('foo/@*', input=xml, output='12')

    def test_2step_complex(self):
        xml = XML('<root><foo><bar/></foo></root>')
        self._test_eval(
            path = 'foo/bar',
            equiv = '<Path "child::foo/child::bar">',
            input = xml,
            output = '<bar/>'
        )
        self._test_eval(
            path = './bar',
            equiv = '<Path "self::node()/child::bar">',
            input = xml,
            output = ''
        )
        self._test_eval(
            path = 'foo/*',
            equiv = '<Path "child::foo/child::*">',
            input = xml,
            output = '<bar/>'
        )
        xml = XML('<root><foo><bar id="1"/></foo><bar id="2"/></root>')
        self._test_eval(
            path = './bar',
            equiv = '<Path "self::node()/child::bar">',
            input = xml,
            output = '<bar id="2"/>'
        )
        xml = XML('''<table>
            <tr><td>1</td><td>One</td></tr>
            <tr><td>2</td><td>Two</td></tr>
        </table>''')
        self._test_eval(
            path = 'tr/td[1]',
            input = xml,
            output = '<td>1</td><td>2</td>'
        )
        xml = XML('''<ul>
            <li>item1
                <ul><li>subitem11</li></ul>
            </li>
            <li>item2
                <ul><li>subitem21</li></ul>
            </li>
        </ul>''')
        self._test_eval(
            path = 'li[2]/ul',
            input = xml,
            output = '<ul><li>subitem21</li></ul>'
        )

    def test_2step_text(self):
        xml = XML('<root><item>Foo</item></root>')
        self._test_eval(
            path = 'item/text()',
            equiv = '<Path "child::item/child::text()">',
            input = xml,
            output = 'Foo'
        )
        self._test_eval(
            path = '*/text()',
            equiv = '<Path "child::*/child::text()">',
            input = xml,
            output = 'Foo'
        )
        self._test_eval(
            path = '//text()',
            equiv = '<Path "descendant-or-self::text()">',
            input = xml,
            output = 'Foo'
        )
        self._test_eval(
            path = './text()',
            equiv = '<Path "self::node()/child::text()">',
            input = xml,
            output = ''
        )
        xml = XML('<root><item>Foo</item><item>Bar</item></root>')
        self._test_eval(
            path = 'item/text()',
            equiv = '<Path "child::item/child::text()">',
            input = xml,
            output = 'FooBar'
        )
        xml = XML('<root><item><name>Foo</name><sub><name>Bar</name></sub></item></root>') 
        self._test_eval(
            path = 'item/name/text()',
            equiv = '<Path "child::item/child::name/child::text()">',
            input = xml,
            output = 'Foo'
        )

    def test_3step(self):
        xml = XML('<root><foo><bar/></foo></root>')
        self._test_eval(
            path = 'foo/*',
            equiv = '<Path "child::foo/child::*">',
            input = xml,
            output = '<bar/>'
        )

    def test_3step_complex(self):
        self._test_eval(
            path = '*/bar',
            equiv = '<Path "child::*/child::bar">',
            input = XML('<root><foo><bar/></foo></root>'),
            output = '<bar/>'
        )
        self._test_eval(
            path = '//bar',
            equiv = '<Path "descendant-or-self::bar">',
            input = XML('<root><foo><bar id="1"/></foo><bar id="2"/></root>'),
            output = '<bar id="1"/><bar id="2"/>'
        )

    def test_3step_complex_text(self):
        xml = XML('<root><item><bar>Some text </bar><baz><bar>in here.</bar></baz></item></root>')
        self._test_eval(
            path = 'item/bar/text()',
            equiv = '<Path "child::item/child::bar/child::text()">',
            input = xml,
            output = 'Some text '
        )
        self._test_eval(
            path = 'item//bar/text()',
            equiv = '<Path "child::item/descendant-or-self::node()/child::bar/child::text()">',
            input = xml,
            output = 'Some text in here.'
        )

    def test_node_type_comment(self):
        xml = XML('<root><!-- commented --></root>')
        self._test_eval(
            path = 'comment()',
            equiv = '<Path "child::comment()">',
            input = xml,
            output = '<!-- commented -->'
        )

    def test_node_type_text(self):
        xml = XML('<root>Some text <br/>in here.</root>')
        self._test_eval(
            path = 'text()',
            equiv = '<Path "child::text()">',
            input = xml,
            output = 'Some text in here.'
        )

    def test_node_type_node(self):
        xml = XML('<root>Some text <br/>in here.</root>')
        self._test_eval(
            path = 'node()',
            equiv = '<Path "child::node()">',
            input = xml,
            output = 'Some text <br/>in here.'
        )

    def test_node_type_processing_instruction(self):
        xml = XML('<?python x = 2 * 3 ?><root><?php echo("x") ?></root>')
        self._test_eval(
            path = '//processing-instruction()',
            equiv = '<Path "descendant-or-self::processing-instruction()">',
            input = xml,
            output = '<?python x = 2 * 3 ?><?php echo("x") ?>'
        )
        self._test_eval(
            path = 'processing-instruction()',
            equiv = '<Path "child::processing-instruction()">',
            input = xml,
            output = '<?php echo("x") ?>'
        )
        self._test_eval(
            path = 'processing-instruction("php")',
            equiv = '<Path "child::processing-instruction(\"php\")">',
            input = xml,
            output = '<?php echo("x") ?>'
        )

    def test_simple_union(self):
        xml = XML("""<body>1<br />2<br />3<br /></body>""")
        self._test_eval(
            path = '*|text()',
            equiv = '<Path "child::*|child::text()">',
            input = xml,
            output = '1<br/>2<br/>3<br/>'
        )

    def test_predicate_name(self):
        xml = XML('<root><foo/><bar/></root>')
        self._test_eval('*[name()="foo"]', input=xml, output='<foo/>')

    def test_predicate_localname(self):
        xml = XML('<root><foo xmlns="NS"/><bar/></root>')
        self._test_eval('*[local-name()="foo"]', input=xml,
                              output='<foo xmlns="NS"/>')

    def test_predicate_namespace(self):
        xml = XML('<root><foo xmlns="NS"/><bar/></root>')
        self._test_eval('*[namespace-uri()="NS"]', input=xml,
                                output='<foo xmlns="NS"/>')

    def test_predicate_not_name(self):
        xml = XML('<root><foo/><bar/></root>')
        self._test_eval('*[not(name()="foo")]', input=xml,
                              output='<bar/>')

    def test_predicate_attr(self):
        xml = XML('<root><item/><item important="very"/></root>')
        self._test_eval('item[@important]', input=xml,
                              output='<item important="very"/>')
        self._test_eval('item[@important="very"]', input=xml,
                              output='<item important="very"/>')

    def test_predicate_attr_equality(self):
        xml = XML('<root><item/><item important="notso"/></root>')
        self._test_eval('item[@important="very"]', input=xml, output='')
        self._test_eval('item[@important!="very"]', input=xml,
                              output='<item/><item important="notso"/>')

    def test_predicate_attr_greater_than(self):
        xml = XML('<root><item priority="3"/></root>')
        self._test_eval('item[@priority>3]', input=xml, output='')
        self._test_eval('item[@priority>2]', input=xml,
                              output='<item priority="3"/>')

    def test_predicate_attr_less_than(self):
        xml = XML('<root><item priority="3"/></root>')
        self._test_eval('item[@priority<3]', input=xml, output='')
        self._test_eval('item[@priority<4]', input=xml,
                              output='<item priority="3"/>')

    def test_predicate_attr_and(self):
        xml = XML('<root><item/><item important="very"/></root>')
        self._test_eval('item[@important and @important="very"]',
                                input=xml, output='<item important="very"/>')
        self._test_eval('item[@important and @important="notso"]',
                                input=xml, output='')

    def test_predicate_attr_or(self):
        xml = XML('<root><item/><item important="very"/></root>')
        self._test_eval('item[@urgent or @important]', input=xml,
                              output='<item important="very"/>')
        self._test_eval('item[@urgent or @notso]', input=xml, output='')

    def test_predicate_boolean_function(self):
        xml = XML('<root><foo>bar</foo></root>')
        self._test_eval('*[boolean("")]', input=xml, output='')
        self._test_eval('*[boolean("yo")]', input=xml,
                              output='<foo>bar</foo>')
        self._test_eval('*[boolean(0)]', input=xml, output='')
        self._test_eval('*[boolean(42)]', input=xml,
                              output='<foo>bar</foo>')
        self._test_eval('*[boolean(false())]', input=xml, output='')
        self._test_eval('*[boolean(true())]', input=xml,
                              output='<foo>bar</foo>')

    def test_predicate_ceil_function(self):
        xml = XML('<root><foo>bar</foo></root>')
        self._test_eval('*[ceiling("4.5")=5]', input=xml,
                              output='<foo>bar</foo>')

    def test_predicate_concat_function(self):
        xml = XML('<root><foo>bar</foo></root>')
        self._test_eval('*[name()=concat("f", "oo")]', input=xml,
                              output='<foo>bar</foo>')

    def test_predicate_contains_function(self):
        xml = XML('<root><foo>bar</foo></root>')
        self._test_eval('*[contains(name(), "oo")]', input=xml,
                              output='<foo>bar</foo>')

    def test_predicate_matches_function(self):
        xml = XML('<root><foo>bar</foo><bar>foo</bar></root>')
        self._test_eval('*[matches(name(), "foo|bar")]', input=xml,
                              output='<foo>bar</foo><bar>foo</bar>')

    def test_predicate_false_function(self):
        xml = XML('<root><foo>bar</foo></root>')
        self._test_eval('*[false()]', input=xml, output='')

    def test_predicate_floor_function(self):
        xml = XML('<root><foo>bar</foo></root>')
        self._test_eval('*[floor("4.5")=4]', input=xml,
                              output='<foo>bar</foo>')

    def test_predicate_normalize_space_function(self):
        xml = XML('<root><foo>bar</foo></root>')
        self._test_eval('*[normalize-space(" foo   bar  ")="foo bar"]',
                                input=xml, output='<foo>bar</foo>')

    def test_predicate_number_function(self):
        xml = XML('<root><foo>bar</foo></root>')
        self._test_eval('*[number("3.0")=3]', input=xml,
                              output='<foo>bar</foo>')
        self._test_eval('*[number("3.0")=3.0]', input=xml,
                              output='<foo>bar</foo>')
        self._test_eval('*[number("0.1")=.1]', input=xml,
                              output='<foo>bar</foo>')

    def test_predicate_round_function(self):
        xml = XML('<root><foo>bar</foo></root>')
        self._test_eval('*[round("4.4")=4]', input=xml,
                              output='<foo>bar</foo>')
        self._test_eval('*[round("4.6")=5]', input=xml,
                              output='<foo>bar</foo>')

    def test_predicate_starts_with_function(self):
        xml = XML('<root><foo>bar</foo></root>')
        self._test_eval('*[starts-with(name(), "f")]', input=xml,
                              output='<foo>bar</foo>')
        self._test_eval('*[starts-with(name(), "b")]', input=xml,
                              output='')

    def test_predicate_string_length_function(self):
        xml = XML('<root><foo>bar</foo></root>')
        self._test_eval('*[string-length(name())=3]', input=xml,
                              output='<foo>bar</foo>')

    def test_predicate_substring_function(self):
        xml = XML('<root><foo>bar</foo></root>')
        self._test_eval('*[substring(name(), 1)="oo"]', input=xml,
                              output='<foo>bar</foo>')
        self._test_eval('*[substring(name(), 1, 1)="o"]', input=xml,
                              output='<foo>bar</foo>')

    def test_predicate_substring_after_function(self):
        xml = XML('<root><foo>bar</foo></root>')
        self._test_eval('*[substring-after(name(), "f")="oo"]', input=xml,
                                output='<foo>bar</foo>')

    def test_predicate_substring_before_function(self):
        xml = XML('<root><foo>bar</foo></root>')
        self._test_eval('*[substring-before(name(), "oo")="f"]',
                                input=xml, output='<foo>bar</foo>')

    def test_predicate_translate_function(self):
        xml = XML('<root><foo>bar</foo></root>')
        self._test_eval('*[translate(name(), "fo", "ba")="baa"]',
                                input=xml, output='<foo>bar</foo>')

    def test_predicate_true_function(self):
        xml = XML('<root><foo>bar</foo></root>')
        self._test_eval('*[true()]', input=xml, output='<foo>bar</foo>')

    def test_predicate_variable(self):
        xml = XML('<root><foo>bar</foo></root>')
        self._test_eval(
            path = '*[name()=$bar]',
            input = xml,
            output = '<foo>bar</foo>',
            variables = {'bar': 'foo'}
        )

    def test_predicate_position(self):
        xml = XML('<root><foo id="a1"/><foo id="a2"/><foo id="a3"/></root>')
        self._test_eval('*[2]', input=xml, output='<foo id="a2"/>')

    def test_predicate_attr_and_position(self):
        xml = XML('<root><foo/><foo id="a1"/><foo id="a2"/></root>')
        self._test_eval('*[@id][2]', input=xml, output='<foo id="a2"/>')

    def test_predicate_position_and_attr(self):
        xml = XML('<root><foo/><foo id="a1"/><foo id="a2"/></root>')
        self._test_eval('*[1][@id]', input=xml, output='')
        self._test_eval('*[2][@id]', input=xml, output='<foo id="a1"/>')

    def test_predicate_advanced_position(self):
        xml = XML('<root><a><b><c><d><e/></d></c></b></a></root>')
        self._test_eval(   'descendant-or-self::*/'
                                'descendant-or-self::*/'
                                'descendant-or-self::*[2]/'
                                'self::*/descendant::*[3]', input=xml,
                                output='<d><e/></d>')

    def test_predicate_child_position(self):
        xml = XML('\
<root><a><b>1</b><b>2</b><b>3</b></a><a><b>4</b><b>5</b></a></root>')
        self._test_eval('//a/b[2]', input=xml, output='<b>2</b><b>5</b>')
        self._test_eval('//a/b[3]', input=xml, output='<b>3</b>')

    def test_name_with_namespace(self):
        xml = XML('<root xmlns:f="FOO"><f:foo>bar</f:foo></root>')
        self._test_eval(
            path = 'f:foo',
            equiv = '<Path "child::f:foo">',
            input = xml,
            output = '<foo xmlns="FOO">bar</foo>',
            namespaces = {'f': 'FOO'}
        )

    def test_wildcard_with_namespace(self):
        xml = XML('<root xmlns:f="FOO"><f:foo>bar</f:foo></root>')
        self._test_eval(
            path = 'f:*',
            equiv = '<Path "child::f:*">',
            input = xml,
            output = '<foo xmlns="FOO">bar</foo>',
            namespaces = {'f': 'FOO'}
        )

    def test_predicate_termination(self):
        """
        Verify that a patch matching the self axis with a predicate doesn't
        cause an infinite loop. See <http://genshi.edgewall.org/ticket/82>.
        """
        xml = XML('<ul flag="1"><li>a</li><li>b</li></ul>')
        self._test_eval('.[@flag="1"]/*', input=xml,
                              output='<li>a</li><li>b</li>')

        xml = XML('<ul flag="1"><li>a</li><li>b</li></ul>')
        self._test_eval('.[@flag="0"]/*', input=xml, output='')

    def test_attrname_with_namespace(self):
        xml = XML('<root xmlns:f="FOO"><foo f:bar="baz"/></root>')
        self._test_eval('foo[@f:bar]', input=xml,
                              output='<foo xmlns:ns1="FOO" ns1:bar="baz"/>',
                              namespaces={'f': 'FOO'})

    def test_attrwildcard_with_namespace(self):
        xml = XML('<root xmlns:f="FOO"><foo f:bar="baz"/></root>')
        self._test_eval('foo[@f:*]', input=xml,
                              output='<foo xmlns:ns1="FOO" ns1:bar="baz"/>',
                              namespaces={'f': 'FOO'})

    def test_self_and_descendant(self):
        xml = XML('<root><foo/></root>')
        self._test_eval('self::root', input=xml, output='<root><foo/></root>')
        self._test_eval('self::foo', input=xml, output='')
        self._test_eval('descendant::root', input=xml, output='')
        self._test_eval('descendant::foo', input=xml, output='<foo/>')
        self._test_eval('descendant-or-self::root', input=xml, 
                                output='<root><foo/></root>')
        self._test_eval('descendant-or-self::foo', input=xml, output='<foo/>')

    def test_long_simple_paths(self):
        xml = XML('<root><a><b><a><d><a><b><a><b><a><b><a><c>!'
                    '</c></a></b></a></b></a></b></a></d></a></b></a></root>')
        self._test_eval('//a/b/a/b/a/c', input=xml, output='<c>!</c>')
        self._test_eval('//a/b/a/c', input=xml, output='<c>!</c>')
        self._test_eval('//a/c', input=xml, output='<c>!</c>')
        self._test_eval('//c', input=xml, output='<c>!</c>')
        # Please note that a//b is NOT the same as a/descendant::b 
        # it is a/descendant-or-self::node()/b, which SimplePathStrategy
        # does NOT support
        self._test_eval('a/b/descendant::a/c', input=xml, output='<c>!</c>')
        self._test_eval('a/b/descendant::a/d/descendant::a/c',
                              input=xml, output='<c>!</c>')
        self._test_eval('a/b/descendant::a/d/a/c', input=xml, output='')
        self._test_eval('//d/descendant::b/descendant::b/descendant::b'
                              '/descendant::c', input=xml, output='<c>!</c>')
        self._test_eval('//d/descendant::b/descendant::b/descendant::b'
                              '/descendant::b/descendant::c', input=xml,
                              output='')

    def _test_support(self, strategy_class, text):
        path = PathParser(text, None, -1).parse()[0]
        return strategy_class.supports(path)

    def test_simple_strategy_support(self):
        self.assert_(self._test_support(SimplePathStrategy, 'a/b'))
        self.assert_(self._test_support(SimplePathStrategy, 'self::a/b'))
        self.assert_(self._test_support(SimplePathStrategy, 'descendant::a/b'))
        self.assert_(self._test_support(SimplePathStrategy,
                         'descendant-or-self::a/b'))
        self.assert_(self._test_support(SimplePathStrategy, '//a/b'))
        self.assert_(self._test_support(SimplePathStrategy, 'a/@b'))
        self.assert_(self._test_support(SimplePathStrategy, 'a/text()'))

        # a//b is a/descendant-or-self::node()/b
        self.assert_(not self._test_support(SimplePathStrategy, 'a//b'))
        self.assert_(not self._test_support(SimplePathStrategy, 'node()/@a'))
        self.assert_(not self._test_support(SimplePathStrategy, '@a'))
        self.assert_(not self._test_support(SimplePathStrategy, 'foo:bar'))
        self.assert_(not self._test_support(SimplePathStrategy, 'a/@foo:bar'))

    def _test_strategies(self, input, path, output,
                         namespaces=None, variables=None):
        for strategy in self.strategies:
            if not strategy.supports(path):
                continue
            s = strategy(path)
            rendered = FakePath(s).select(input, namespaces=namespaces,
                                          variables=variables) \
                                  .render(encoding=None)
            msg = 'Bad render using %s strategy' % str(strategy)
            msg += '\nExpected:\t%r' % output
            msg += '\nRendered:\t%r' % rendered
            self.assertEqual(output, rendered, msg)

    def _test_eval(self, path, equiv=None, input=None, output='',
                         namespaces=None, variables=None):
        path = Path(path)
        if equiv is not None:
            self.assertEqual(equiv, repr(path))

        if input is None:
            return

        rendered = path.select(input, namespaces=namespaces,
                               variables=variables).render(encoding=None)
        msg = 'Bad output using whole path'
        msg += '\nExpected:\t%r' % output
        msg += '\nRendered:\t%r' % rendered
        self.assertEqual(output, rendered, msg)

        if len(path.paths) == 1:
            self._test_strategies(input, path.paths[0], output,
                                  namespaces=namespaces, variables=variables)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(Path.__module__))
    suite.addTest(unittest.makeSuite(PathTestCase, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
