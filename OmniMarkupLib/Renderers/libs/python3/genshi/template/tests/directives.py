# -*- coding: utf-8 -*-
#
# Copyright (C) 2006-2010 Edgewall Software
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
import re
import sys
import unittest

from genshi.template import directives, MarkupTemplate, TextTemplate, \
                            TemplateRuntimeError, TemplateSyntaxError


class AttrsDirectiveTestCase(unittest.TestCase):
    """Tests for the `py:attrs` template directive."""

    def test_combined_with_loop(self):
        """
        Verify that the directive has access to the loop variables.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <elem py:for="item in items" py:attrs="item"/>
        </doc>""")
        items = [{'id': 1}, {'id': 2}]
        self.assertEqual("""<doc>
          <elem id="1"/><elem id="2"/>
        </doc>""", tmpl.generate(items=items).render(encoding=None))

    def test_update_existing_attr(self):
        """
        Verify that an attribute value that evaluates to `None` removes an
        existing attribute of that name.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <elem class="foo" py:attrs="{'class': 'bar'}"/>
        </doc>""")
        self.assertEqual("""<doc>
          <elem class="bar"/>
        </doc>""", tmpl.generate().render(encoding=None))

    def test_remove_existing_attr(self):
        """
        Verify that an attribute value that evaluates to `None` removes an
        existing attribute of that name.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <elem class="foo" py:attrs="{'class': None}"/>
        </doc>""")
        self.assertEqual("""<doc>
          <elem/>
        </doc>""", tmpl.generate().render(encoding=None))


class ChooseDirectiveTestCase(unittest.TestCase):
    """Tests for the `py:choose` template directive and the complementary
    directives `py:when` and `py:otherwise`."""

    def test_multiple_true_whens(self):
        """
        Verify that, if multiple `py:when` bodies match, only the first is
        output.
        """
        tmpl = MarkupTemplate("""<div xmlns:py="http://genshi.edgewall.org/" py:choose="">
          <span py:when="1 == 1">1</span>
          <span py:when="2 == 2">2</span>
          <span py:when="3 == 3">3</span>
        </div>""")
        self.assertEqual("""<div>
          <span>1</span>
        </div>""", tmpl.generate().render(encoding=None))

    def test_otherwise(self):
        tmpl = MarkupTemplate("""<div xmlns:py="http://genshi.edgewall.org/" py:choose="">
          <span py:when="False">hidden</span>
          <span py:otherwise="">hello</span>
        </div>""")
        self.assertEqual("""<div>
          <span>hello</span>
        </div>""", tmpl.generate().render(encoding=None))

    def test_nesting(self):
        """
        Verify that `py:choose` blocks can be nested:
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <div py:choose="1">
            <div py:when="1" py:choose="3">
              <span py:when="2">2</span>
              <span py:when="3">3</span>
            </div>
          </div>
        </doc>""")
        self.assertEqual("""<doc>
          <div>
            <div>
              <span>3</span>
            </div>
          </div>
        </doc>""", tmpl.generate().render(encoding=None))

    def test_complex_nesting(self):
        """
        Verify more complex nesting.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <div py:choose="1">
            <div py:when="1" py:choose="">
              <span py:when="2">OK</span>
              <span py:when="1">FAIL</span>
            </div>
          </div>
        </doc>""")
        self.assertEqual("""<doc>
          <div>
            <div>
              <span>OK</span>
            </div>
          </div>
        </doc>""", tmpl.generate().render(encoding=None))

    def test_complex_nesting_otherwise(self):
        """
        Verify more complex nesting using otherwise.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <div py:choose="1">
            <div py:when="1" py:choose="2">
              <span py:when="1">FAIL</span>
              <span py:otherwise="">OK</span>
            </div>
          </div>
        </doc>""")
        self.assertEqual("""<doc>
          <div>
            <div>
              <span>OK</span>
            </div>
          </div>
        </doc>""", tmpl.generate().render(encoding=None))

    def test_when_with_strip(self):
        """
        Verify that a when directive with a strip directive actually strips of
        the outer element.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <div py:choose="" py:strip="">
            <span py:otherwise="">foo</span>
          </div>
        </doc>""")
        self.assertEqual("""<doc>
            <span>foo</span>
        </doc>""", tmpl.generate().render(encoding=None))

    def test_when_outside_choose(self):
        """
        Verify that a `when` directive outside of a `choose` directive is
        reported as an error.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <div py:when="xy" />
        </doc>""")
        self.assertRaises(TemplateRuntimeError, str, tmpl.generate())

    def test_otherwise_outside_choose(self):
        """
        Verify that an `otherwise` directive outside of a `choose` directive is
        reported as an error.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <div py:otherwise="" />
        </doc>""")
        self.assertRaises(TemplateRuntimeError, str, tmpl.generate())

    def test_when_without_test(self):
        """
        Verify that an `when` directive that doesn't have a `test` attribute
        is reported as an error.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <div py:choose="" py:strip="">
            <py:when>foo</py:when>
          </div>
        </doc>""")
        self.assertRaises(TemplateRuntimeError, str, tmpl.generate())

    def test_when_without_test_but_with_choose_value(self):
        """
        Verify that an `when` directive that doesn't have a `test` attribute
        works as expected as long as the parent `choose` directive has a test
        expression.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <div py:choose="foo" py:strip="">
            <py:when>foo</py:when>
          </div>
        </doc>""")
        self.assertEqual("""<doc>
            foo
        </doc>""", tmpl.generate(foo='Yeah').render(encoding=None))

    def test_otherwise_without_test(self):
        """
        Verify that an `otherwise` directive can be used without a `test`
        attribute.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <div py:choose="" py:strip="">
            <py:otherwise>foo</py:otherwise>
          </div>
        </doc>""")
        self.assertEqual("""<doc>
            foo
        </doc>""", tmpl.generate().render(encoding=None))

    def test_as_element(self):
        """
        Verify that the directive can also be used as an element.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <py:choose>
            <py:when test="1 == 1">1</py:when>
            <py:when test="2 == 2">2</py:when>
            <py:when test="3 == 3">3</py:when>
          </py:choose>
        </doc>""")
        self.assertEqual("""<doc>
            1
        </doc>""", tmpl.generate().render(encoding=None))

    def test_in_text_template(self):
        """
        Verify that the directive works as expected in a text template.
        """
        tmpl = TextTemplate("""#choose
          #when 1 == 1
            1
          #end
          #when 2 == 2
            2
          #end
          #when 3 == 3
            3
          #end
        #end""")
        self.assertEqual("""            1\n""",
                         tmpl.generate().render(encoding=None))


class DefDirectiveTestCase(unittest.TestCase):
    """Tests for the `py:def` template directive."""

    def test_function_with_strip(self):
        """
        Verify that a named template function with a strip directive actually
        strips of the outer element.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <div py:def="echo(what)" py:strip="">
            <b>${what}</b>
          </div>
          ${echo('foo')}
        </doc>""")
        self.assertEqual("""<doc>
            <b>foo</b>
        </doc>""", tmpl.generate().render(encoding=None))

    def test_exec_in_replace(self):
        tmpl = MarkupTemplate("""<div xmlns:py="http://genshi.edgewall.org/">
          <p py:def="echo(greeting, name='world')" class="message">
            ${greeting}, ${name}!
          </p>
          <div py:replace="echo('hello')"></div>
        </div>""")
        self.assertEqual("""<div>
          <p class="message">
            hello, world!
          </p>
        </div>""", tmpl.generate().render(encoding=None))

    def test_as_element(self):
        """
        Verify that the directive can also be used as an element.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <py:def function="echo(what)">
            <b>${what}</b>
          </py:def>
          ${echo('foo')}
        </doc>""")
        self.assertEqual("""<doc>
            <b>foo</b>
        </doc>""", tmpl.generate().render(encoding=None))

    def test_nested_defs(self):
        """
        Verify that a template function defined inside a conditional block can
        be called from outside that block.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <py:if test="semantic">
            <strong py:def="echo(what)">${what}</strong>
          </py:if>
          <py:if test="not semantic">
            <b py:def="echo(what)">${what}</b>
          </py:if>
          ${echo('foo')}
        </doc>""")
        self.assertEqual("""<doc>
          <strong>foo</strong>
        </doc>""", tmpl.generate(semantic=True).render(encoding=None))

    def test_function_with_default_arg(self):
        """
        Verify that keyword arguments work with `py:def` directives.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <b py:def="echo(what, bold=False)" py:strip="not bold">${what}</b>
          ${echo('foo')}
        </doc>""")
        self.assertEqual("""<doc>
          foo
        </doc>""", tmpl.generate().render(encoding=None))

    def test_invocation_in_attribute(self):
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <py:def function="echo(what)">${what or 'something'}</py:def>
          <p class="${echo('foo')}">bar</p>
        </doc>""")
        self.assertEqual("""<doc>
          <p class="foo">bar</p>
        </doc>""", tmpl.generate().render(encoding=None))

    def test_invocation_in_attribute_none(self):
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <py:def function="echo()">${None}</py:def>
          <p class="${echo()}">bar</p>
        </doc>""")
        self.assertEqual("""<doc>
          <p>bar</p>
        </doc>""", tmpl.generate().render(encoding=None))

    def test_function_raising_typeerror(self):
        def badfunc():
            raise TypeError
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          <div py:def="dobadfunc()">
            ${badfunc()}
          </div>
          <div py:content="dobadfunc()"/>
        </html>""")
        self.assertRaises(TypeError, list, tmpl.generate(badfunc=badfunc))

    def test_def_in_matched(self):
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <head py:match="head">${select('*')}</head>
          <head>
            <py:def function="maketitle(test)"><b py:replace="test" /></py:def>
            <title>${maketitle(True)}</title>
          </head>
        </doc>""")
        self.assertEqual("""<doc>
          <head><title>True</title></head>
        </doc>""", tmpl.generate().render(encoding=None))

    def test_in_text_template(self):
        """
        Verify that the directive works as expected in a text template.
        """
        tmpl = TextTemplate("""
          #def echo(greeting, name='world')
            ${greeting}, ${name}!
          #end
          ${echo('Hi', name='you')}
        """)
        self.assertEqual("""
                      Hi, you!

        """, tmpl.generate().render(encoding=None))

    def test_function_with_star_args(self):
        """
        Verify that a named template function using "star arguments" works as
        expected.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <div py:def="f(*args, **kwargs)">
            ${repr(args)}
            ${repr(sorted(kwargs.items()))}
          </div>
          ${f(1, 2, a=3, b=4)}
        </doc>""")
        self.assertEqual("""<doc>
          <div>
            [1, 2]
            [('a', 3), ('b', 4)]
          </div>
        </doc>""", tmpl.generate().render(encoding=None))


class ForDirectiveTestCase(unittest.TestCase):
    """Tests for the `py:for` template directive."""

    def test_loop_with_strip(self):
        """
        Verify that the combining the `py:for` directive with `py:strip` works
        correctly.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <div py:for="item in items" py:strip="">
            <b>${item}</b>
          </div>
        </doc>""")
        self.assertEqual("""<doc>
            <b>1</b>
            <b>2</b>
            <b>3</b>
            <b>4</b>
            <b>5</b>
        </doc>""", tmpl.generate(items=list(range(1, 6))).render(encoding=None))

    def test_as_element(self):
        """
        Verify that the directive can also be used as an element.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <py:for each="item in items">
            <b>${item}</b>
          </py:for>
        </doc>""")
        self.assertEqual("""<doc>
            <b>1</b>
            <b>2</b>
            <b>3</b>
            <b>4</b>
            <b>5</b>
        </doc>""", tmpl.generate(items=list(range(1, 6))).render(encoding=None))

    def test_multi_assignment(self):
        """
        Verify that assignment to tuples works correctly.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <py:for each="k, v in items">
            <p>key=$k, value=$v</p>
          </py:for>
        </doc>""")
        self.assertEqual("""<doc>
            <p>key=a, value=1</p>
            <p>key=b, value=2</p>
        </doc>""", tmpl.generate(items=(('a', 1), ('b', 2)))
                       .render(encoding=None))

    def test_nested_assignment(self):
        """
        Verify that assignment to nested tuples works correctly.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <py:for each="idx, (k, v) in items">
            <p>$idx: key=$k, value=$v</p>
          </py:for>
        </doc>""")
        self.assertEqual("""<doc>
            <p>0: key=a, value=1</p>
            <p>1: key=b, value=2</p>
        </doc>""", tmpl.generate(items=enumerate([('a', 1), ('b', 2)]))
                       .render(encoding=None))

    def test_not_iterable(self):
        """
        Verify that assignment to nested tuples works correctly.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <py:for each="item in foo">
            $item
          </py:for>
        </doc>""", filename='test.html')
        try:
            list(tmpl.generate(foo=12))
            self.fail('Expected TemplateRuntimeError')
        except TypeError as e:
            assert (str(e) == "iteration over non-sequence" or
                    str(e) == "'int' object is not iterable")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            frame = exc_traceback.tb_next
            frames = []
            while frame.tb_next:
                frame = frame.tb_next
                frames.append(frame)
            self.assertEqual("<Expression 'iter(foo)'>",
                             frames[-1].tb_frame.f_code.co_name)
            self.assertEqual('test.html',
                             frames[-1].tb_frame.f_code.co_filename)
            self.assertEqual(2, frames[-1].tb_lineno)

    def test_for_with_empty_value(self):
        """
        Verify an empty 'for' value is an error
        """
        try:
            MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
              <py:for each="">
                empty
              </py:for>
            </doc>""", filename='test.html').generate()
            self.fail('ExpectedTemplateSyntaxError')
        except TemplateSyntaxError as e:
            self.assertEqual('test.html', e.filename)
            if sys.version_info[:2] > (2,4):
                self.assertEqual(2, e.lineno)


class IfDirectiveTestCase(unittest.TestCase):
    """Tests for the `py:if` template directive."""

    def test_loop_with_strip(self):
        """
        Verify that the combining the `py:if` directive with `py:strip` works
        correctly.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <b py:if="foo" py:strip="">${bar}</b>
        </doc>""")
        self.assertEqual("""<doc>
          Hello
        </doc>""", tmpl.generate(foo=True, bar='Hello').render(encoding=None))

    def test_as_element(self):
        """
        Verify that the directive can also be used as an element.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <py:if test="foo">${bar}</py:if>
        </doc>""")
        self.assertEqual("""<doc>
          Hello
        </doc>""", tmpl.generate(foo=True, bar='Hello').render(encoding=None))


class MatchDirectiveTestCase(unittest.TestCase):
    """Tests for the `py:match` template directive."""

    def test_with_strip(self):
        """
        Verify that a match template can produce the same kind of element that
        it matched without entering an infinite recursion.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <elem py:match="elem" py:strip="">
            <div class="elem">${select('text()')}</div>
          </elem>
          <elem>Hey Joe</elem>
        </doc>""")
        self.assertEqual("""<doc>
            <div class="elem">Hey Joe</div>
        </doc>""", tmpl.generate().render(encoding=None))

    def test_without_strip(self):
        """
        Verify that a match template can produce the same kind of element that
        it matched without entering an infinite recursion.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <elem py:match="elem">
            <div class="elem">${select('text()')}</div>
          </elem>
          <elem>Hey Joe</elem>
        </doc>""")
        self.assertEqual("""<doc>
          <elem>
            <div class="elem">Hey Joe</div>
          </elem>
        </doc>""", tmpl.generate().render(encoding=None))

    def test_as_element(self):
        """
        Verify that the directive can also be used as an element.
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <py:match path="elem">
            <div class="elem">${select('text()')}</div>
          </py:match>
          <elem>Hey Joe</elem>
        </doc>""")
        self.assertEqual("""<doc>
            <div class="elem">Hey Joe</div>
        </doc>""", tmpl.generate().render(encoding=None))

    def test_recursive_match_1(self):
        """
        Match directives are applied recursively, meaning that they are also
        applied to any content they may have produced themselves:
        """
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <elem py:match="elem">
            <div class="elem">
              ${select('*')}
            </div>
          </elem>
          <elem>
            <subelem>
              <elem/>
            </subelem>
          </elem>
        </doc>""")
        self.assertEqual("""<doc>
          <elem>
            <div class="elem">
              <subelem>
              <elem>
            <div class="elem">
            </div>
          </elem>
            </subelem>
            </div>
          </elem>
        </doc>""", tmpl.generate().render(encoding=None))

    def test_recursive_match_2(self):
        """
        When two or more match templates match the same element and also
        themselves output the element they match, avoiding recursion is even
        more complex, but should work.
        """
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          <body py:match="body">
            <div id="header"/>
            ${select('*')}
          </body>
          <body py:match="body">
            ${select('*')}
            <div id="footer"/>
          </body>
          <body>
            <h1>Foo</h1>
          </body>
        </html>""")
        self.assertEqual("""<html>
          <body>
            <div id="header"/><h1>Foo</h1>
            <div id="footer"/>
          </body>
        </html>""", tmpl.generate().render(encoding=None))

    def test_recursive_match_3(self):
        tmpl = MarkupTemplate("""<test xmlns:py="http://genshi.edgewall.org/">
          <py:match path="b[@type='bullet']">
            <bullet>${select('*|text()')}</bullet>
          </py:match>
          <py:match path="group[@type='bullet']">
            <ul>${select('*')}</ul>
          </py:match>
          <py:match path="b">
            <generic>${select('*|text()')}</generic>
          </py:match>

          <b>
            <group type="bullet">
              <b type="bullet">1</b>
              <b type="bullet">2</b>
            </group>
          </b>
        </test>
        """)
        self.assertEqual("""<test>
            <generic>
            <ul><bullet>1</bullet><bullet>2</bullet></ul>
          </generic>
        </test>""", tmpl.generate().render(encoding=None))

    def test_not_match_self(self):
        """
        See http://genshi.edgewall.org/ticket/77
        """
        tmpl = MarkupTemplate("""<html xmlns="http://www.w3.org/1999/xhtml"
              xmlns:py="http://genshi.edgewall.org/">
          <body py:match="body" py:content="select('*')" />
          <h1 py:match="h1">
            ${select('text()')}
            Goodbye!
          </h1>
          <body>
            <h1>Hello!</h1>
          </body>
        </html>""")
        self.assertEqual("""<html xmlns="http://www.w3.org/1999/xhtml">
          <body><h1>
            Hello!
            Goodbye!
          </h1></body>
        </html>""", tmpl.generate().render(encoding=None))

    def test_select_text_in_element(self):
        """
        See http://genshi.edgewall.org/ticket/77#comment:1
        """
        tmpl = MarkupTemplate("""<html xmlns="http://www.w3.org/1999/xhtml"
              xmlns:py="http://genshi.edgewall.org/">
          <body py:match="body" py:content="select('*')" />
          <h1 py:match="h1">
            <text>
              ${select('text()')}
            </text>
            Goodbye!
          </h1>
          <body>
            <h1>Hello!</h1>
          </body>
        </html>""")
        self.assertEqual("""<html xmlns="http://www.w3.org/1999/xhtml">
          <body><h1>
            <text>
              Hello!
            </text>
            Goodbye!
          </h1></body>
        </html>""", tmpl.generate().render(encoding=None))

    def test_select_all_attrs(self):
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <div py:match="elem" py:attrs="select('@*')">
            ${select('text()')}
          </div>
          <elem id="joe">Hey Joe</elem>
        </doc>""")
        self.assertEqual("""<doc>
          <div id="joe">
            Hey Joe
          </div>
        </doc>""", tmpl.generate().render(encoding=None))

    def test_select_all_attrs_empty(self):
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <div py:match="elem" py:attrs="select('@*')">
            ${select('text()')}
          </div>
          <elem>Hey Joe</elem>
        </doc>""")
        self.assertEqual("""<doc>
          <div>
            Hey Joe
          </div>
        </doc>""", tmpl.generate().render(encoding=None))

    def test_select_all_attrs_in_body(self):
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <div py:match="elem">
            Hey ${select('text()')} ${select('@*')}
          </div>
          <elem title="Cool">Joe</elem>
        </doc>""")
        self.assertEqual("""<doc>
          <div>
            Hey Joe Cool
          </div>
        </doc>""", tmpl.generate().render(encoding=None))

    def test_def_in_match(self):
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <py:def function="maketitle(test)"><b py:replace="test" /></py:def>
          <head py:match="head">${select('*')}</head>
          <head><title>${maketitle(True)}</title></head>
        </doc>""")
        self.assertEqual("""<doc>
          <head><title>True</title></head>
        </doc>""", tmpl.generate().render(encoding=None))

    def test_match_with_xpath_variable(self):
        tmpl = MarkupTemplate("""<div xmlns:py="http://genshi.edgewall.org/">
          <span py:match="*[name()=$tagname]">
            Hello ${select('@name')}
          </span>
          <greeting name="Dude"/>
        </div>""")
        self.assertEqual("""<div>
          <span>
            Hello Dude
          </span>
        </div>""", tmpl.generate(tagname='greeting').render(encoding=None))
        self.assertEqual("""<div>
          <greeting name="Dude"/>
        </div>""", tmpl.generate(tagname='sayhello').render(encoding=None))

    def test_content_directive_in_match(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          <div py:match="foo">I said <q py:content="select('text()')">something</q>.</div>
          <foo>bar</foo>
        </html>""")
        self.assertEqual("""<html>
          <div>I said <q>bar</q>.</div>
        </html>""", tmpl.generate().render(encoding=None))

    def test_cascaded_matches(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          <body py:match="body">${select('*')}</body>
          <head py:match="head">${select('title')}</head>
          <body py:match="body">${select('*')}<hr /></body>
          <head><title>Welcome to Markup</title></head>
          <body><h2>Are you ready to mark up?</h2></body>
        </html>""")
        self.assertEqual("""<html>
          <head><title>Welcome to Markup</title></head>
          <body><h2>Are you ready to mark up?</h2><hr/></body>
        </html>""", tmpl.generate().render(encoding=None))

    def test_multiple_matches(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          <input py:match="form//input" py:attrs="select('@*')"
                 value="${values[str(select('@name'))]}" />
          <form><p py:for="field in fields">
            <label>${field.capitalize()}</label>
            <input type="text" name="${field}" />
          </p></form>
        </html>""")
        fields = ['hello_%s' % i for i in range(5)]
        values = dict([('hello_%s' % i, i) for i in range(5)])
        self.assertEqual("""<html>
          <form><p>
            <label>Hello_0</label>
            <input value="0" type="text" name="hello_0"/>
          </p><p>
            <label>Hello_1</label>
            <input value="1" type="text" name="hello_1"/>
          </p><p>
            <label>Hello_2</label>
            <input value="2" type="text" name="hello_2"/>
          </p><p>
            <label>Hello_3</label>
            <input value="3" type="text" name="hello_3"/>
          </p><p>
            <label>Hello_4</label>
            <input value="4" type="text" name="hello_4"/>
          </p></form>
        </html>""", tmpl.generate(fields=fields, values=values)
                        .render(encoding=None))

    def test_namespace_context(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/"
                                       xmlns:x="http://www.example.org/">
          <div py:match="x:foo">Foo</div>
          <foo xmlns="http://www.example.org/"/>
        </html>""")
        # FIXME: there should be a way to strip out unwanted/unused namespaces,
        #        such as the "x" in this example
        self.assertEqual("""<html xmlns:x="http://www.example.org/">
          <div>Foo</div>
        </html>""", tmpl.generate().render(encoding=None))

    def test_match_with_position_predicate(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          <p py:match="body/p[1]" class="first">${select('*|text()')}</p>
          <body>
            <p>Foo</p>
            <p>Bar</p>
          </body>
        </html>""")
        self.assertEqual("""<html>
          <body>
            <p class="first">Foo</p>
            <p>Bar</p>
          </body>
        </html>""", tmpl.generate().render(encoding=None))

    def test_match_with_closure(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          <p py:match="body//p" class="para">${select('*|text()')}</p>
          <body>
            <p>Foo</p>
            <div><p>Bar</p></div>
          </body>
        </html>""")
        self.assertEqual("""<html>
          <body>
            <p class="para">Foo</p>
            <div><p class="para">Bar</p></div>
          </body>
        </html>""", tmpl.generate().render(encoding=None))

    def test_match_without_closure(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          <p py:match="body/p" class="para">${select('*|text()')}</p>
          <body>
            <p>Foo</p>
            <div><p>Bar</p></div>
          </body>
        </html>""")
        self.assertEqual("""<html>
          <body>
            <p class="para">Foo</p>
            <div><p>Bar</p></div>
          </body>
        </html>""", tmpl.generate().render(encoding=None))

    def test_match_with_once_attribute(self):
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          <py:match path="body" once="true"><body>
            <div id="wrap">
              ${select("*")}
            </div>
          </body></py:match>
          <body>
            <p>Foo</p>
          </body>
          <body>
            <p>Bar</p>
          </body>
        </html>""")
        self.assertEqual("""<html>
          <body>
            <div id="wrap">
              <p>Foo</p>
            </div>
          </body>
          <body>
            <p>Bar</p>
          </body>
        </html>""", tmpl.generate().render(encoding=None))

    def test_match_with_recursive_attribute(self):
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <py:match path="elem" recursive="false"><elem>
            <div class="elem">
              ${select('*')}
            </div>
          </elem></py:match>
          <elem>
            <subelem>
              <elem/>
            </subelem>
          </elem>
        </doc>""")
        self.assertEqual("""<doc>
          <elem>
            <div class="elem">
              <subelem>
              <elem/>
            </subelem>
            </div>
          </elem>
        </doc>""", tmpl.generate().render(encoding=None))

    # See http://genshi.edgewall.org/ticket/254/
    def test_triple_match_produces_no_duplicate_items(self):
        tmpl = MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
          <div py:match="div[@id='content']" py:attrs="select('@*')" once="true">
            <ul id="tabbed_pane" />
            ${select('*')}
          </div>

          <body py:match="body" once="true" buffer="false">
            ${select('*|text()')}
          </body>
          <body py:match="body" once="true" buffer="false">
              ${select('*|text()')}
          </body>

          <body>
            <div id="content">
              <h1>Ticket X</h1>
            </div>
          </body>
        </doc>""")
        output = tmpl.generate().render('xhtml', doctype='xhtml')
        matches = re.findall("tabbed_pane", output)
        self.assertNotEqual(None, matches)
        self.assertEqual(1, len(matches))

    def test_match_multiple_times1(self):
        # See http://genshi.edgewall.org/ticket/370
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          <py:match path="body[@id='content']/h2" />
          <head py:match="head" />
          <head py:match="head" />
          <head />
          <body />
        </html>""")
        self.assertEqual("""<html>
          <head/>
          <body/>
        </html>""", tmpl.generate().render())

    def test_match_multiple_times2(self):
        # See http://genshi.edgewall.org/ticket/370
        tmpl = MarkupTemplate("""<html xmlns:py="http://genshi.edgewall.org/">
          <py:match path="body/div[@id='properties']" />
          <head py:match="head" />
          <head py:match="head" />
          <head/>
          <body>
            <div id="properties">Foo</div>
          </body>
        </html>""")
        self.assertEqual("""<html>
          <head/>
          <body>
          </body>
        </html>""", tmpl.generate().render())

    def test_match_multiple_times3(self):
        # See http://genshi.edgewall.org/ticket/370#comment:12
        tmpl = MarkupTemplate("""<?xml version="1.0"?>
          <root xmlns:py="http://genshi.edgewall.org/">
            <py:match path="foo/bar">
              <zzzzz/>
            </py:match>
            <foo>
              <bar/>
              <bar/>
            </foo>
            <bar/>
          </root>""")
        self.assertEqual("""<?xml version="1.0"?>\n<root>
            <foo>
              <zzzzz/>
              <zzzzz/>
            </foo>
            <bar/>
          </root>""", tmpl.generate().render())

    # FIXME
    #def test_match_after_step(self):
    #    tmpl = MarkupTemplate("""<div xmlns:py="http://genshi.edgewall.org/">
    #      <span py:match="div/greeting">
    #        Hello ${select('@name')}
    #      </span>
    #      <greeting name="Dude" />
    #    </div>""")
    #    self.assertEqual("""<div>
    #      <span>
    #        Hello Dude
    #      </span>
    #    </div>""", tmpl.generate().render(encoding=None))


class ContentDirectiveTestCase(unittest.TestCase):
    """Tests for the `py:content` template directive."""

    def test_as_element(self):
        try:
            MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
              <py:content foo="">Foo</py:content>
            </doc>""", filename='test.html').generate()
            self.fail('Expected TemplateSyntaxError')
        except TemplateSyntaxError as e:
            self.assertEqual('test.html', e.filename)
            self.assertEqual(2, e.lineno)


class ReplaceDirectiveTestCase(unittest.TestCase):
    """Tests for the `py:replace` template directive."""

    def test_replace_with_empty_value(self):
        """
        Verify that the directive raises an apprioriate exception when an empty
        expression is supplied.
        """
        try:
            MarkupTemplate("""<doc xmlns:py="http://genshi.edgewall.org/">
              <elem py:replace="">Foo</elem>
            </doc>""", filename='test.html').generate()
            self.fail('Expected TemplateSyntaxError')
        except TemplateSyntaxError as e:
            self.assertEqual('test.html', e.filename)
            self.assertEqual(2, e.lineno)

    def test_as_element(self):
        tmpl = MarkupTemplate("""<div xmlns:py="http://genshi.edgewall.org/">
          <py:replace value="title" />
        </div>""", filename='test.html')
        self.assertEqual("""<div>
          Test
        </div>""", tmpl.generate(title='Test').render(encoding=None))


class StripDirectiveTestCase(unittest.TestCase):
    """Tests for the `py:strip` template directive."""

    def test_strip_false(self):
        tmpl = MarkupTemplate("""<div xmlns:py="http://genshi.edgewall.org/">
          <div py:strip="False"><b>foo</b></div>
        </div>""")
        self.assertEqual("""<div>
          <div><b>foo</b></div>
        </div>""", tmpl.generate().render(encoding=None))

    def test_strip_empty(self):
        tmpl = MarkupTemplate("""<div xmlns:py="http://genshi.edgewall.org/">
          <div py:strip=""><b>foo</b></div>
        </div>""")
        self.assertEqual("""<div>
          <b>foo</b>
        </div>""", tmpl.generate().render(encoding=None))


class WithDirectiveTestCase(unittest.TestCase):
    """Tests for the `py:with` template directive."""

    def test_shadowing(self):
        tmpl = MarkupTemplate("""<div xmlns:py="http://genshi.edgewall.org/">
          ${x}
          <span py:with="x = x * 2" py:replace="x"/>
          ${x}
        </div>""")
        self.assertEqual("""<div>
          42
          84
          42
        </div>""", tmpl.generate(x=42).render(encoding=None))

    def test_as_element(self):
        tmpl = MarkupTemplate("""<div xmlns:py="http://genshi.edgewall.org/">
          <py:with vars="x = x * 2">${x}</py:with>
        </div>""")
        self.assertEqual("""<div>
          84
        </div>""", tmpl.generate(x=42).render(encoding=None))

    def test_multiple_vars_same_name(self):
        tmpl = MarkupTemplate("""<div xmlns:py="http://genshi.edgewall.org/">
          <py:with vars="
            foo = 'bar';
            foo = foo.replace('r', 'z')
          ">
            $foo
          </py:with>
        </div>""")
        self.assertEqual("""<div>
            baz
        </div>""", tmpl.generate(x=42).render(encoding=None))

    def test_multiple_vars_single_assignment(self):
        tmpl = MarkupTemplate("""<div xmlns:py="http://genshi.edgewall.org/">
          <py:with vars="x = y = z = 1">${x} ${y} ${z}</py:with>
        </div>""")
        self.assertEqual("""<div>
          1 1 1
        </div>""", tmpl.generate(x=42).render(encoding=None))

    def test_nested_vars_single_assignment(self):
        tmpl = MarkupTemplate("""<div xmlns:py="http://genshi.edgewall.org/">
          <py:with vars="x, (y, z) = (1, (2, 3))">${x} ${y} ${z}</py:with>
        </div>""")
        self.assertEqual("""<div>
          1 2 3
        </div>""", tmpl.generate(x=42).render(encoding=None))

    def test_multiple_vars_trailing_semicolon(self):
        tmpl = MarkupTemplate("""<div xmlns:py="http://genshi.edgewall.org/">
          <py:with vars="x = x * 2; y = x / 2;">${x} ${y}</py:with>
        </div>""")
        self.assertEqual("""<div>
          84 %s
        </div>""" % (84 / 2), tmpl.generate(x=42).render(encoding=None))

    def test_semicolon_escape(self):
        tmpl = MarkupTemplate("""<div xmlns:py="http://genshi.edgewall.org/">
          <py:with vars="x = 'here is a semicolon: ;'; y = 'here are two semicolons: ;;' ;">
            ${x}
            ${y}
          </py:with>
        </div>""")
        self.assertEqual("""<div>
            here is a semicolon: ;
            here are two semicolons: ;;
        </div>""", tmpl.generate().render(encoding=None))

    def test_ast_transformation(self):
        """
        Verify that the usual template expression AST transformations are
        applied despite the code being compiled to a `Suite` object.
        """
        tmpl = MarkupTemplate("""<div xmlns:py="http://genshi.edgewall.org/">
          <span py:with="bar=foo.bar">
            $bar
          </span>
        </div>""")
        self.assertEqual("""<div>
          <span>
            42
          </span>
        </div>""", tmpl.generate(foo={'bar': 42}).render(encoding=None))

    def test_unicode_expr(self):
        tmpl = MarkupTemplate("""<div xmlns:py="http://genshi.edgewall.org/">
          <span py:with="weeks=('一', '二', '三', '四', '五', '六', '日')">
            $weeks
          </span>
        </div>""")
        self.assertEqual("""<div>
          <span>
            一二三四五六日
          </span>
        </div>""", tmpl.generate().render(encoding=None))
        
    def test_with_empty_value(self):
        """
        Verify that an empty py:with works (useless, but legal)
        """
        tmpl = MarkupTemplate("""<div xmlns:py="http://genshi.edgewall.org/">
          <span py:with="">Text</span></div>""")

        self.assertEqual("""<div>
          <span>Text</span></div>""", tmpl.generate().render(encoding=None))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(directives))
    suite.addTest(unittest.makeSuite(AttrsDirectiveTestCase, 'test'))
    suite.addTest(unittest.makeSuite(ChooseDirectiveTestCase, 'test'))
    suite.addTest(unittest.makeSuite(DefDirectiveTestCase, 'test'))
    suite.addTest(unittest.makeSuite(ForDirectiveTestCase, 'test'))
    suite.addTest(unittest.makeSuite(IfDirectiveTestCase, 'test'))
    suite.addTest(unittest.makeSuite(MatchDirectiveTestCase, 'test'))
    suite.addTest(unittest.makeSuite(ContentDirectiveTestCase, 'test'))
    suite.addTest(unittest.makeSuite(ReplaceDirectiveTestCase, 'test'))
    suite.addTest(unittest.makeSuite(StripDirectiveTestCase, 'test'))
    suite.addTest(unittest.makeSuite(WithDirectiveTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
