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
import os
import shutil
import tempfile
import unittest

from genshi.template.base import TemplateSyntaxError
from genshi.template.loader import TemplateLoader
from genshi.template.text import OldTextTemplate, NewTextTemplate


class OldTextTemplateTestCase(unittest.TestCase):
    """Tests for text template processing."""

    def setUp(self):
        self.dirname = tempfile.mkdtemp(suffix='markup_test')

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_escaping(self):
        tmpl = OldTextTemplate('\\#escaped')
        self.assertEqual('#escaped', tmpl.generate().render(encoding=None))

    def test_comment(self):
        tmpl = OldTextTemplate('## a comment')
        self.assertEqual('', tmpl.generate().render(encoding=None))

    def test_comment_escaping(self):
        tmpl = OldTextTemplate('\\## escaped comment')
        self.assertEqual('## escaped comment',
                         tmpl.generate().render(encoding=None))

    def test_end_with_args(self):
        tmpl = OldTextTemplate("""
        #if foo
          bar
        #end 'if foo'""")
        self.assertEqual('\n', tmpl.generate(foo=False).render(encoding=None))

    def test_latin1_encoded(self):
        text = '$foo\xf6$bar'.encode('iso-8859-1')
        tmpl = OldTextTemplate(text, encoding='iso-8859-1')
        self.assertEqual('x\xf6y',
                         tmpl.generate(foo='x', bar='y').render(encoding=None))

    def test_unicode_input(self):
        text = '$foo\xf6$bar'
        tmpl = OldTextTemplate(text)
        self.assertEqual('x\xf6y',
                         tmpl.generate(foo='x', bar='y').render(encoding=None))

    def test_empty_lines1(self):
        tmpl = OldTextTemplate("""Your items:

        #for item in items
          * ${item}
        #end""")
        self.assertEqual("""Your items:

          * 0
          * 1
          * 2
""", tmpl.generate(items=list(range(3))).render(encoding=None))

    def test_empty_lines2(self):
        tmpl = OldTextTemplate("""Your items:

        #for item in items
          * ${item}

        #end""")
        self.assertEqual("""Your items:

          * 0

          * 1

          * 2

""", tmpl.generate(items=list(range(3))).render(encoding=None))

    def test_include(self):
        file1 = open(os.path.join(self.dirname, 'tmpl1.txt'), 'wb')
        try:
            file1.write("Included\n".encode("utf-8"))
        finally:
            file1.close()

        file2 = open(os.path.join(self.dirname, 'tmpl2.txt'), 'wb')
        try:
            file2.write("""----- Included data below this line -----
            #include tmpl1.txt
            ----- Included data above this line -----""".encode("utf-8"))
        finally:
            file2.close()

        loader = TemplateLoader([self.dirname])
        tmpl = loader.load('tmpl2.txt', cls=OldTextTemplate)
        self.assertEqual("""----- Included data below this line -----
Included
            ----- Included data above this line -----""",
                         tmpl.generate().render(encoding=None))


class NewTextTemplateTestCase(unittest.TestCase):
    """Tests for text template processing."""

    def setUp(self):
        self.dirname = tempfile.mkdtemp(suffix='markup_test')

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_escaping(self):
        tmpl = NewTextTemplate('\\{% escaped %}')
        self.assertEqual('{% escaped %}',
                         tmpl.generate().render(encoding=None))

    def test_comment(self):
        tmpl = NewTextTemplate('{# a comment #}')
        self.assertEqual('', tmpl.generate().render(encoding=None))

    def test_comment_escaping(self):
        tmpl = NewTextTemplate('\\{# escaped comment #}')
        self.assertEqual('{# escaped comment #}',
                         tmpl.generate().render(encoding=None))

    def test_end_with_args(self):
        tmpl = NewTextTemplate("""
{% if foo %}
  bar
{% end 'if foo' %}""")
        self.assertEqual('\n', tmpl.generate(foo=False).render(encoding=None))

    def test_latin1_encoded(self):
        text = '$foo\xf6$bar'.encode('iso-8859-1')
        tmpl = NewTextTemplate(text, encoding='iso-8859-1')
        self.assertEqual('x\xf6y',
                         tmpl.generate(foo='x', bar='y').render(encoding=None))

    def test_unicode_input(self):
        text = '$foo\xf6$bar'
        tmpl = NewTextTemplate(text)
        self.assertEqual('x\xf6y',
                         tmpl.generate(foo='x', bar='y').render(encoding=None))

    def test_empty_lines1(self):
        tmpl = NewTextTemplate("""Your items:

{% for item in items %}\
  * ${item}
{% end %}""")
        self.assertEqual("""Your items:

  * 0
  * 1
  * 2
""", tmpl.generate(items=list(range(3))).render(encoding=None))

    def test_empty_lines2(self):
        tmpl = NewTextTemplate("""Your items:

{% for item in items %}\
  * ${item}

{% end %}""")
        self.assertEqual("""Your items:

  * 0

  * 1

  * 2

""", tmpl.generate(items=list(range(3))).render(encoding=None))

    def test_exec_with_trailing_space(self):
        """
        Verify that a code block with trailing space does not cause a syntax
        error (see ticket #127).
        """
        NewTextTemplate("""
          {% python
            bar = 42
          $}
        """)

    def test_exec_import(self):
        tmpl = NewTextTemplate("""{% python from datetime import timedelta %}
        ${timedelta(days=2)}
        """)
        self.assertEqual("""
        2 days, 0:00:00
        """, tmpl.generate().render(encoding=None))

    def test_exec_def(self):
        tmpl = NewTextTemplate("""{% python
        def foo():
            return 42
        %}
        ${foo()}
        """)
        self.assertEqual("""
        42
        """, tmpl.generate().render(encoding=None))

    def test_include(self):
        file1 = open(os.path.join(self.dirname, 'tmpl1.txt'), 'wb')
        try:
            file1.write("Included".encode("utf-8"))
        finally:
            file1.close()

        file2 = open(os.path.join(self.dirname, 'tmpl2.txt'), 'wb')
        try:
            file2.write("""----- Included data below this line -----
{% include tmpl1.txt %}
----- Included data above this line -----""".encode("utf-8"))
        finally:
            file2.close()

        loader = TemplateLoader([self.dirname])
        tmpl = loader.load('tmpl2.txt', cls=NewTextTemplate)
        self.assertEqual("""----- Included data below this line -----
Included
----- Included data above this line -----""",
                         tmpl.generate().render(encoding=None))

    def test_include_expr(self):
         file1 = open(os.path.join(self.dirname, 'tmpl1.txt'), 'wb')
         try:
             file1.write("Included".encode("utf-8"))
         finally:
             file1.close()
 
         file2 = open(os.path.join(self.dirname, 'tmpl2.txt'), 'wb')
         try:
             file2.write("""----- Included data below this line -----
    {% include ${'%s.txt' % ('tmpl1',)} %}
    ----- Included data above this line -----""".encode("utf-8"))
         finally:
             file2.close()

         loader = TemplateLoader([self.dirname])
         tmpl = loader.load('tmpl2.txt', cls=NewTextTemplate)
         self.assertEqual("""----- Included data below this line -----
    Included
    ----- Included data above this line -----""",
                          tmpl.generate().render(encoding=None))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(NewTextTemplate.__module__))
    suite.addTest(unittest.makeSuite(OldTextTemplateTestCase, 'test'))
    suite.addTest(unittest.makeSuite(NewTextTemplateTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
