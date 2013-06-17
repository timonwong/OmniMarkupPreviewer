# -*- coding: utf-8 -*-
#
# Copyright (C) 2006-2007 Edgewall Software
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

from genshi.template.base import Template, Context


class ContextTestCase(unittest.TestCase):
    def test_copy(self):
        # create a non-trivial context with some dummy
        # frames, match templates and py:choice stacks.
        orig_ctxt = Context(a=5, b=6)
        orig_ctxt.push({'c': 7})
        orig_ctxt._match_templates.append(object())
        orig_ctxt._choice_stack.append(object())
        ctxt = orig_ctxt.copy()
        self.assertNotEqual(id(orig_ctxt), id(ctxt))
        self.assertEqual(repr(orig_ctxt), repr(ctxt))
        self.assertEqual(orig_ctxt._match_templates, ctxt._match_templates)
        self.assertEqual(orig_ctxt._choice_stack, ctxt._choice_stack)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(Template.__module__))
    suite.addTest(unittest.makeSuite(ContextTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
