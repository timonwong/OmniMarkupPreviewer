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

"""Basic support for evaluating XPath expressions against streams.

>>> from genshi.input import XML
>>> doc = XML('''<doc>
...  <items count="4">
...       <item status="new">
...         <summary>Foo</summary>
...       </item>
...       <item status="closed">
...         <summary>Bar</summary>
...       </item>
...       <item status="closed" resolution="invalid">
...         <summary>Baz</summary>
...       </item>
...       <item status="closed" resolution="fixed">
...         <summary>Waz</summary>
...       </item>
...   </items>
... </doc>''')
>>> print(doc.select('items/item[@status="closed" and '
...     '(@resolution="invalid" or not(@resolution))]/summary/text()'))
BarBaz

Because the XPath engine operates on markup streams (as opposed to tree
structures), it only implements a subset of the full XPath 1.0 language.
"""

from collections import deque
try:
    reduce # builtin in Python < 3
except NameError:
    from functools import reduce
from math import ceil, floor
import operator
import re
from itertools import chain

from genshi.core import Stream, Attrs, Namespace, QName
from genshi.core import START, END, TEXT, START_NS, END_NS, COMMENT, PI, \
                        START_CDATA, END_CDATA

__all__ = ['Path', 'PathSyntaxError']
__docformat__ = 'restructuredtext en'


class Axis(object):
    """Defines constants for the various supported XPath axes."""

    ATTRIBUTE = 'attribute'
    CHILD = 'child'
    DESCENDANT = 'descendant'
    DESCENDANT_OR_SELF = 'descendant-or-self'
    SELF = 'self'

    @classmethod
    def forname(cls, name):
        """Return the axis constant for the given name, or `None` if no such
        axis was defined.
        """
        return getattr(cls, name.upper().replace('-', '_'), None)


ATTRIBUTE = Axis.ATTRIBUTE
CHILD = Axis.CHILD
DESCENDANT = Axis.DESCENDANT
DESCENDANT_OR_SELF = Axis.DESCENDANT_OR_SELF
SELF = Axis.SELF


class GenericStrategy(object):

    @classmethod
    def supports(cls, path):
        return True

    def __init__(self, path):
        self.path = path

    def test(self, ignore_context):
        p = self.path
        if ignore_context:
            if p[0][0] is ATTRIBUTE:
                steps = [_DOTSLASHSLASH] + p
            else:
                steps = [(DESCENDANT_OR_SELF, p[0][1], p[0][2])] + p[1:]
        elif p[0][0] is CHILD or p[0][0] is ATTRIBUTE \
                or p[0][0] is DESCENDANT:
            steps = [_DOTSLASH] + p
        else:
            steps = p

        # for node it contains all positions of xpath expression
        # where its child should start checking for matches
        # with list of corresponding context counters
        # there can be many of them, because position that is from
        # descendant-like axis can be achieved from different nodes
        # for example <a><a><b/></a></a> should match both //a//b[1]
        # and //a//b[2]
        # positions always form increasing sequence (invariant)
        stack = [[(0, [[]])]]

        def _test(event, namespaces, variables, updateonly=False):
            kind, data, pos = event[:3]
            retval = None

            # Manage the stack that tells us "where we are" in the stream
            if kind is END:
                if stack:
                    stack.pop()
                return None
            if kind is START_NS or kind is END_NS \
                    or kind is START_CDATA or kind is END_CDATA:
                # should we make namespaces work?
                return None

            pos_queue = deque([(pos, cou, []) for pos, cou in stack[-1]])
            next_pos = []

            # length of real part of path - we omit attribute axis
            real_len = len(steps) - ((steps[-1][0] == ATTRIBUTE) or 1 and 0)
            last_checked = -1

            # places where we have to check for match, are these
            # provided by parent
            while pos_queue:
                x, pcou, mcou = pos_queue.popleft()
                axis, nodetest, predicates = steps[x]

                # we need to push descendant-like positions from parent
                # further
                if (axis is DESCENDANT or axis is DESCENDANT_OR_SELF) and pcou:
                    if next_pos and next_pos[-1][0] == x:
                        next_pos[-1][1].extend(pcou)
                    else:
                        next_pos.append((x, pcou))

                # nodetest first
                if not nodetest(kind, data, pos, namespaces, variables):
                    continue

                # counters packs that were already bad
                missed = set()
                counters_len = len(pcou) + len(mcou)

                # number of counters - we have to create one
                # for every context position based predicate
                cnum = 0

                # tells if we have match with position x
                matched = True

                if predicates:
                    for predicate in predicates:
                        pretval = predicate(kind, data, pos,
                                            namespaces,
                                            variables)
                        if type(pretval) is float: # FIXME <- need to check
                                                   # this for other types that
                                                   # can be coerced to float

                            # each counter pack needs to be checked
                            for i, cou in enumerate(chain(pcou, mcou)):
                                # it was bad before
                                if i in missed:
                                    continue

                                if len(cou) < cnum + 1:
                                    cou.append(0)
                                cou[cnum] += 1 

                                # it is bad now
                                if cou[cnum] != int(pretval):
                                    missed.add(i)

                            # none of counters pack was good
                            if len(missed) == counters_len:
                                pretval = False
                            cnum += 1

                        if not pretval:
                             matched = False
                             break

                if not matched:
                    continue

                # counter for next position with current node as context node
                child_counter = []

                if x + 1 == real_len:
                    # we reached end of expression, because x + 1
                    # is equal to the length of expression
                    matched = True
                    axis, nodetest, predicates = steps[-1]
                    if axis is ATTRIBUTE:
                        matched = nodetest(kind, data, pos, namespaces,
                                           variables)
                    if matched:
                        retval = matched
                else:
                    next_axis = steps[x + 1][0]

                    # if next axis allows matching self we have
                    # to add next position to our queue
                    if next_axis is DESCENDANT_OR_SELF or next_axis is SELF:
                        if not pos_queue or pos_queue[0][0] > x + 1:
                            pos_queue.appendleft((x + 1, [], [child_counter]))
                        else:
                            pos_queue[0][2].append(child_counter)

                    # if axis is not self we have to add it to child's list
                    if next_axis is not SELF:
                        next_pos.append((x + 1, [child_counter]))

            if kind is START:
                stack.append(next_pos)

            return retval

        return _test


class SimplePathStrategy(object):
    """Strategy for path with only local names, attributes and text nodes."""

    @classmethod
    def supports(cls, path):
        if path[0][0] is ATTRIBUTE:
            return False
        allowed_tests = (LocalNameTest, CommentNodeTest, TextNodeTest)
        for _, nodetest, predicates in path:
            if predicates:
                return False
            if not isinstance(nodetest, allowed_tests):
                return False
        return True

    def __init__(self, path):
        # fragments is list of tuples (fragment, pi, attr, self_beginning)
        # fragment is list of nodetests for fragment of path with only
        # child:: axes between
        # pi is KMP partial match table for this fragment
        # attr is attribute nodetest if fragment ends with @ and None otherwise
        # self_beginning is True if axis for first fragment element
        # was self (first fragment) or descendant-or-self (farther fragment)
        self.fragments = []

        self_beginning = False
        fragment = []

        def nodes_equal(node1, node2):
            """Tests if two node tests are equal"""
            if type(node1) is not type(node2):
                return False
            if type(node1) == LocalNameTest:
                return node1.name == node2.name
            return True

        def calculate_pi(f):
            """KMP prefix calculation for table"""
            # the indexes in prefix table are shifted by one
            # in comparision with common implementations
            # pi[i] = NORMAL_PI[i + 1]
            if len(f) == 0:
                return []
            pi = [0]
            s = 0
            for i in range(1, len(f)):
                while s > 0 and not nodes_equal(f[s], f[i]):
                    s = pi[s-1]
                if nodes_equal(f[s], f[i]):
                    s += 1
                pi.append(s)
            return pi

        for axis in path:
            if axis[0] is SELF:
                if len(fragment) != 0:
                    # if element is not first in fragment it has to be
                    # the same as previous one
                    # for example child::a/self::b is always wrong
                    if axis[1] != fragment[-1][1]:
                        self.fragments = None
                        return
                else:
                    self_beginning = True
                    fragment.append(axis[1])
            elif axis[0] is CHILD:
                fragment.append(axis[1])
            elif axis[0] is ATTRIBUTE:
                pi = calculate_pi(fragment)
                self.fragments.append((fragment, pi, axis[1], self_beginning))
                # attribute has always to be at the end, so we can jump out
                return
            else:
                pi = calculate_pi(fragment)
                self.fragments.append((fragment, pi, None, self_beginning))
                fragment = [axis[1]]
                if axis[0] is DESCENDANT:
                    self_beginning = False
                else: # DESCENDANT_OR_SELF
                    self_beginning = True
        pi = calculate_pi(fragment)
        self.fragments.append((fragment, pi, None, self_beginning))

    def test(self, ignore_context):
        # stack of triples (fid, p, ic)
        # fid is index of current fragment
        # p is position in this fragment
        # ic is if we ignore context in this fragment
        stack = []
        stack_push = stack.append
        stack_pop = stack.pop
        frags = self.fragments
        frags_len = len(frags)

        def _test(event, namespaces, variables, updateonly=False):
            # expression found impossible during init
            if frags is None:
                return None

            kind, data, pos = event[:3]

            # skip events we don't care about
            if kind is END:
                if stack:
                    stack_pop()
                return None
            if kind is START_NS or kind is END_NS \
                    or kind is START_CDATA or kind is END_CDATA:
                return None

            if not stack:
                # root node, nothing on stack, special case
                fid = 0
                # skip empty fragments (there can be actually only one)
                while not frags[fid][0]:
                    fid += 1
                p = 0
                # empty fragment means descendant node at beginning
                ic = ignore_context or (fid > 0)

                # expression can match first node, if first axis is self::,
                # descendant-or-self:: or if ignore_context is True and
                # axis is not descendant::
                if not frags[fid][3] and (not ignore_context or fid > 0):
                    # axis is not self-beggining, we have to skip this node
                    stack_push((fid, p, ic))
                    return None
            else:
                # take position of parent
                fid, p, ic = stack[-1]

            if fid is not None and not ic:
                # fragment not ignoring context - we can't jump back
                frag, pi, attrib, _ = frags[fid]
                frag_len = len(frag)

                if p == frag_len:
                    # that probably means empty first fragment
                    pass
                elif frag[p](kind, data, pos, namespaces, variables):
                    # match, so we can go further
                    p += 1
                else:
                    # not matched, so there will be no match in subtree
                    fid, p = None, None

                if p == frag_len and fid + 1 != frags_len:
                    # we made it to end of fragment, we can go to following
                    fid += 1
                    p = 0
                    ic = True

            if fid is None:
                # there was no match in fragment not ignoring context
                if kind is START:
                    stack_push((fid, p, ic))
                return None

            if ic:
                # we are in fragment ignoring context
                while True:
                    frag, pi, attrib, _ = frags[fid]
                    frag_len = len(frag)

                    # KMP new "character"
                    while p > 0 and (p >= frag_len or not \
                            frag[p](kind, data, pos, namespaces, variables)):
                        p = pi[p-1]
                    if frag[p](kind, data, pos, namespaces, variables):
                        p += 1

                    if p == frag_len:
                        # end of fragment reached
                        if fid + 1 == frags_len:
                            # that was last fragment
                            break
                        else:
                            fid += 1
                            p = 0
                            ic = True
                            if not frags[fid][3]:
                                # next fragment not self-beginning
                                break
                    else:
                        break

            if kind is START:
                # we have to put new position on stack, for children

                if not ic and fid + 1 == frags_len and p == frag_len:
                    # it is end of the only, not context ignoring fragment
                    # so there will be no matches in subtree
                    stack_push((None, None, ic))
                else:
                    stack_push((fid, p, ic))

            # have we reached the end of the last fragment?
            if fid + 1 == frags_len and p == frag_len:
                if attrib: # attribute ended path, return value
                    return attrib(kind, data, pos, namespaces, variables)
                return True

            return None

        return _test


class SingleStepStrategy(object):

    @classmethod
    def supports(cls, path):
        return len(path) == 1

    def __init__(self, path):
        self.path = path

    def test(self, ignore_context):
        steps = self.path
        if steps[0][0] is ATTRIBUTE:
            steps = [_DOTSLASH] + steps
        select_attr = steps[-1][0] is ATTRIBUTE and steps[-1][1] or None

        # for every position in expression stores counters' list
        # it is used for position based predicates
        counters = []
        depth = [0]

        def _test(event, namespaces, variables, updateonly=False):
            kind, data, pos = event[:3]

            # Manage the stack that tells us "where we are" in the stream
            if kind is END:
                if not ignore_context:
                    depth[0] -= 1
                return None
            elif kind is START_NS or kind is END_NS \
                    or kind is START_CDATA or kind is END_CDATA:
                # should we make namespaces work?
                return None

            if not ignore_context:
                outside = (steps[0][0] is SELF and depth[0] != 0) \
                       or (steps[0][0] is CHILD and depth[0] != 1) \
                       or (steps[0][0] is DESCENDANT and depth[0] < 1)
                if kind is START:
                    depth[0] += 1
                if outside:
                    return None

            axis, nodetest, predicates = steps[0]
            if not nodetest(kind, data, pos, namespaces, variables):
                return None

            if predicates:
                cnum = 0
                for predicate in predicates:
                    pretval = predicate(kind, data, pos, namespaces, variables)
                    if type(pretval) is float: # FIXME <- need to check this
                                               # for other types that can be
                                               # coerced to float
                        if len(counters) < cnum + 1:
                            counters.append(0)
                        counters[cnum] += 1 
                        if counters[cnum] != int(pretval):
                            pretval = False
                        cnum += 1
                    if not pretval:
                         return None

            if select_attr:
                return select_attr(kind, data, pos, namespaces, variables)

            return True

        return _test


class Path(object):
    """Implements basic XPath support on streams.
    
    Instances of this class represent a "compiled" XPath expression, and
    provide methods for testing the path against a stream, as well as
    extracting a substream matching that path.
    """

    STRATEGIES = (SingleStepStrategy, SimplePathStrategy, GenericStrategy)

    def __init__(self, text, filename=None, lineno=-1):
        """Create the path object from a string.
        
        :param text: the path expression
        :param filename: the name of the file in which the path expression was
                         found (used in error messages)
        :param lineno: the line on which the expression was found
        """
        self.source = text
        self.paths = PathParser(text, filename, lineno).parse()
        self.strategies = []
        for path in self.paths:
            for strategy_class in self.STRATEGIES:
                if strategy_class.supports(path):
                    self.strategies.append(strategy_class(path))
                    break
            else:
                raise NotImplemented('No strategy found for path')

    def __repr__(self):
        paths = []
        for path in self.paths:
            steps = []
            for axis, nodetest, predicates in path:
                steps.append('%s::%s' % (axis, nodetest))
                for predicate in predicates:
                    steps[-1] += '[%s]' % predicate
            paths.append('/'.join(steps))
        return '<%s "%s">' % (type(self).__name__, '|'.join(paths))

    def select(self, stream, namespaces=None, variables=None):
        """Returns a substream of the given stream that matches the path.
        
        If there are no matches, this method returns an empty stream.
        
        >>> from genshi.input import XML
        >>> xml = XML('<root><elem><child>Text</child></elem></root>')
        
        >>> print(Path('.//child').select(xml))
        <child>Text</child>
        
        >>> print(Path('.//child/text()').select(xml))
        Text
        
        :param stream: the stream to select from
        :param namespaces: (optional) a mapping of namespace prefixes to URIs
        :param variables: (optional) a mapping of variable names to values
        :return: the substream matching the path, or an empty stream
        :rtype: `Stream`
        """
        if namespaces is None:
            namespaces = {}
        if variables is None:
            variables = {}
        stream = iter(stream)
        def _generate(stream=stream, ns=namespaces, vs=variables):
            next = stream.next
            test = self.test()
            for event in stream:
                result = test(event, ns, vs)
                if result is True:
                    yield event
                    if event[0] is START:
                        depth = 1
                        while depth > 0:
                            subevent = next()
                            if subevent[0] is START:
                                depth += 1
                            elif subevent[0] is END:
                                depth -= 1
                            yield subevent
                            test(subevent, ns, vs, updateonly=True)
                elif result:
                    yield result
        return Stream(_generate(),
                      serializer=getattr(stream, 'serializer', None))

    def test(self, ignore_context=False):
        """Returns a function that can be used to track whether the path matches
        a specific stream event.
        
        The function returned expects the positional arguments ``event``,
        ``namespaces`` and ``variables``. The first is a stream event, while the
        latter two are a mapping of namespace prefixes to URIs, and a mapping
        of variable names to values, respectively. In addition, the function
        accepts an ``updateonly`` keyword argument that default to ``False``. If
        it is set to ``True``, the function only updates its internal state,
        but does not perform any tests or return a result.
        
        If the path matches the event, the function returns the match (for
        example, a `START` or `TEXT` event.) Otherwise, it returns ``None``.
        
        >>> from genshi.input import XML
        >>> xml = XML('<root><elem><child id="1"/></elem><child id="2"/></root>')
        >>> test = Path('child').test()
        >>> namespaces, variables = {}, {}
        >>> for event in xml:
        ...     if test(event, namespaces, variables):
        ...         print('%s %r' % (event[0], event[1]))
        START (QName('child'), Attrs([(QName('id'), u'2')]))
        
        :param ignore_context: if `True`, the path is interpreted like a pattern
                               in XSLT, meaning for example that it will match
                               at any depth
        :return: a function that can be used to test individual events in a
                 stream against the path
        :rtype: ``function``
        """
        tests = [s.test(ignore_context) for s in self.strategies]
        if len(tests) == 1:
            return tests[0]

        def _multi(event, namespaces, variables, updateonly=False):
            retval = None
            for test in tests:
                val = test(event, namespaces, variables, updateonly=updateonly)
                if retval is None:
                    retval = val
            return retval
        return _multi


class PathSyntaxError(Exception):
    """Exception raised when an XPath expression is syntactically incorrect."""

    def __init__(self, message, filename=None, lineno=-1, offset=-1):
        if filename:
            message = '%s (%s, line %d)' % (message, filename, lineno)
        Exception.__init__(self, message)
        self.filename = filename
        self.lineno = lineno
        self.offset = offset


class PathParser(object):
    """Tokenizes and parses an XPath expression."""

    _QUOTES = (("'", "'"), ('"', '"'))
    _TOKENS = ('::', ':', '..', '.', '//', '/', '[', ']', '()', '(', ')', '@',
               '=', '!=', '!', '|', ',', '>=', '>', '<=', '<', '$')
    _tokenize = re.compile('("[^"]*")|(\'[^\']*\')|((?:\d+)?\.\d+)|(%s)|([^%s\s]+)|\s+' % (
                           '|'.join([re.escape(t) for t in _TOKENS]),
                           ''.join([re.escape(t[0]) for t in _TOKENS]))).findall

    def __init__(self, text, filename=None, lineno=-1):
        self.filename = filename
        self.lineno = lineno
        self.tokens = [t for t in [dqstr or sqstr or number or token or name
                                   for dqstr, sqstr, number, token, name in
                                   self._tokenize(text)] if t]
        self.pos = 0

    # Tokenizer

    @property
    def at_end(self):
        return self.pos == len(self.tokens) - 1

    @property
    def cur_token(self):
        return self.tokens[self.pos]

    def next_token(self):
        self.pos += 1
        return self.tokens[self.pos]

    def peek_token(self):
        if not self.at_end:
            return self.tokens[self.pos + 1]
        return None

    # Recursive descent parser

    def parse(self):
        """Parses the XPath expression and returns a list of location path
        tests.
        
        For union expressions (such as `*|text()`), this function returns one
        test for each operand in the union. For patch expressions that don't
        use the union operator, the function always returns a list of size 1.
        
        Each path test in turn is a sequence of tests that correspond to the
        location steps, each tuples of the form `(axis, testfunc, predicates)`
        """
        paths = [self._location_path()]
        while self.cur_token == '|':
            self.next_token()
            paths.append(self._location_path())
        if not self.at_end:
            raise PathSyntaxError('Unexpected token %r after end of expression'
                                  % self.cur_token, self.filename, self.lineno)
        return paths

    def _location_path(self):
        steps = []
        while True:
            if self.cur_token.startswith('/'):
                if not steps:
                    if self.cur_token == '//':
                        # hack to make //* match every node - also root
                        self.next_token()
                        axis, nodetest, predicates = self._location_step()
                        steps.append((DESCENDANT_OR_SELF, nodetest, 
                                      predicates))
                        if self.at_end or not self.cur_token.startswith('/'):
                            break
                        continue
                    else:
                        raise PathSyntaxError('Absolute location paths not '
                                              'supported', self.filename,
                                              self.lineno)
                elif self.cur_token == '//':
                    steps.append((DESCENDANT_OR_SELF, NodeTest(), []))
                self.next_token()

            axis, nodetest, predicates = self._location_step()
            if not axis:
                axis = CHILD
            steps.append((axis, nodetest, predicates))
            if self.at_end or not self.cur_token.startswith('/'):
                break

        return steps

    def _location_step(self):
        if self.cur_token == '@':
            axis = ATTRIBUTE
            self.next_token()
        elif self.cur_token == '.':
            axis = SELF
        elif self.cur_token == '..':
            raise PathSyntaxError('Unsupported axis "parent"', self.filename,
                                  self.lineno)
        elif self.peek_token() == '::':
            axis = Axis.forname(self.cur_token)
            if axis is None:
                raise PathSyntaxError('Unsupport axis "%s"' % axis,
                                      self.filename, self.lineno)
            self.next_token()
            self.next_token()
        else:
            axis = None
        nodetest = self._node_test(axis or CHILD)
        predicates = []
        while self.cur_token == '[':
            predicates.append(self._predicate())
        return axis, nodetest, predicates

    def _node_test(self, axis=None):
        test = prefix = None
        next_token = self.peek_token()
        if next_token in ('(', '()'): # Node type test
            test = self._node_type()

        elif next_token == ':': # Namespace prefix
            prefix = self.cur_token
            self.next_token()
            localname = self.next_token()
            if localname == '*':
                test = QualifiedPrincipalTypeTest(axis, prefix)
            else:
                test = QualifiedNameTest(axis, prefix, localname)

        else: # Name test
            if self.cur_token == '*':
                test = PrincipalTypeTest(axis)
            elif self.cur_token == '.':
                test = NodeTest()
            else:
                test = LocalNameTest(axis, self.cur_token)

        if not self.at_end:
            self.next_token()
        return test

    def _node_type(self):
        name = self.cur_token
        self.next_token()

        args = []
        if self.cur_token != '()':
            # The processing-instruction() function optionally accepts the
            # name of the PI as argument, which must be a literal string
            self.next_token() # (
            if self.cur_token != ')':
                string = self.cur_token
                if (string[0], string[-1]) in self._QUOTES:
                    string = string[1:-1]
                args.append(string)

        cls = _nodetest_map.get(name)
        if not cls:
            raise PathSyntaxError('%s() not allowed here' % name, self.filename,
                                  self.lineno)
        return cls(*args)

    def _predicate(self):
        assert self.cur_token == '['
        self.next_token()
        expr = self._or_expr()
        if self.cur_token != ']':
            raise PathSyntaxError('Expected "]" to close predicate, '
                                  'but found "%s"' % self.cur_token,
                                  self.filename, self.lineno)
        if not self.at_end:
            self.next_token()
        return expr

    def _or_expr(self):
        expr = self._and_expr()
        while self.cur_token == 'or':
            self.next_token()
            expr = OrOperator(expr, self._and_expr())
        return expr

    def _and_expr(self):
        expr = self._equality_expr()
        while self.cur_token == 'and':
            self.next_token()
            expr = AndOperator(expr, self._equality_expr())
        return expr

    def _equality_expr(self):
        expr = self._relational_expr()
        while self.cur_token in ('=', '!='):
            op = _operator_map[self.cur_token]
            self.next_token()
            expr = op(expr, self._relational_expr())
        return expr

    def _relational_expr(self):
        expr = self._sub_expr()
        while self.cur_token in ('>', '>=', '<', '>='):
            op = _operator_map[self.cur_token]
            self.next_token()
            expr = op(expr, self._sub_expr())
        return expr

    def _sub_expr(self):
        token = self.cur_token
        if token != '(':
            return self._primary_expr()
        self.next_token()
        expr = self._or_expr()
        if self.cur_token != ')':
            raise PathSyntaxError('Expected ")" to close sub-expression, '
                                  'but found "%s"' % self.cur_token,
                                  self.filename, self.lineno)
        self.next_token()
        return expr

    def _primary_expr(self):
        token = self.cur_token
        if len(token) > 1 and (token[0], token[-1]) in self._QUOTES:
            self.next_token()
            return StringLiteral(token[1:-1])
        elif token[0].isdigit() or token[0] == '.':
            self.next_token()
            return NumberLiteral(as_float(token))
        elif token == '$':
            token = self.next_token()
            self.next_token()
            return VariableReference(token)
        elif not self.at_end and self.peek_token().startswith('('):
            return self._function_call()
        else:
            axis = None
            if token == '@':
                axis = ATTRIBUTE
                self.next_token()
            return self._node_test(axis)

    def _function_call(self):
        name = self.cur_token
        if self.next_token() == '()':
            args = []
        else:
            assert self.cur_token == '('
            self.next_token()
            args = [self._or_expr()]
            while self.cur_token == ',':
                self.next_token()
                args.append(self._or_expr())
            if not self.cur_token == ')':
                raise PathSyntaxError('Expected ")" to close function argument '
                                      'list, but found "%s"' % self.cur_token,
                                      self.filename, self.lineno)
        self.next_token()
        cls = _function_map.get(name)
        if not cls:
            raise PathSyntaxError('Unsupported function "%s"' % name,
                                  self.filename, self.lineno)
        return cls(*args)


# Type coercion

def as_scalar(value):
    """Convert value to a scalar. If a single element Attrs() object is passed
    the value of the single attribute will be returned."""
    if isinstance(value, Attrs):
        assert len(value) == 1
        return value[0][1]
    else:
        return value

def as_float(value):
    # FIXME - if value is a bool it will be coerced to 0.0 and consequently
    # compared as a float. This is probably not ideal.
    return float(as_scalar(value))

def as_long(value):
    return long(as_scalar(value))

def as_string(value):
    value = as_scalar(value)
    if value is False:
        return ''
    return unicode(value)

def as_bool(value):
    return bool(as_scalar(value))


# Node tests

class PrincipalTypeTest(object):
    """Node test that matches any event with the given principal type."""
    __slots__ = ['principal_type']
    def __init__(self, principal_type):
        self.principal_type = principal_type
    def __call__(self, kind, data, pos, namespaces, variables):
        if kind is START:
            if self.principal_type is ATTRIBUTE:
                return data[1] or None
            else:
                return True
    def __repr__(self):
        return '*'

class QualifiedPrincipalTypeTest(object):
    """Node test that matches any event with the given principal type in a
    specific namespace."""
    __slots__ = ['principal_type', 'prefix']
    def __init__(self, principal_type, prefix):
        self.principal_type = principal_type
        self.prefix = prefix
    def __call__(self, kind, data, pos, namespaces, variables):
        namespace = Namespace(namespaces.get(self.prefix))
        if kind is START:
            if self.principal_type is ATTRIBUTE and data[1]:
                return Attrs([(name, value) for name, value in data[1]
                              if name in namespace]) or None
            else:
                return data[0] in namespace
    def __repr__(self):
        return '%s:*' % self.prefix

class LocalNameTest(object):
    """Node test that matches any event with the given principal type and
    local name.
    """
    __slots__ = ['principal_type', 'name']
    def __init__(self, principal_type, name):
        self.principal_type = principal_type
        self.name = name
    def __call__(self, kind, data, pos, namespaces, variables):
        if kind is START:
            if self.principal_type is ATTRIBUTE and self.name in data[1]:
                return Attrs([(self.name, data[1].get(self.name))])
            else:
                return data[0].localname == self.name
    def __repr__(self):
        return self.name

class QualifiedNameTest(object):
    """Node test that matches any event with the given principal type and
    qualified name.
    """
    __slots__ = ['principal_type', 'prefix', 'name']
    def __init__(self, principal_type, prefix, name):
        self.principal_type = principal_type
        self.prefix = prefix
        self.name = name
    def __call__(self, kind, data, pos, namespaces, variables):
        qname = QName('%s}%s' % (namespaces.get(self.prefix), self.name))
        if kind is START:
            if self.principal_type is ATTRIBUTE and qname in data[1]:
                return Attrs([(self.name, data[1].get(self.name))])
            else:
                return data[0] == qname
    def __repr__(self):
        return '%s:%s' % (self.prefix, self.name)

class CommentNodeTest(object):
    """Node test that matches any comment events."""
    __slots__ = []
    def __call__(self, kind, data, pos, namespaces, variables):
        return kind is COMMENT
    def __repr__(self):
        return 'comment()'

class NodeTest(object):
    """Node test that matches any node."""
    __slots__ = []
    def __call__(self, kind, data, pos, namespaces, variables):
        if kind is START:
            return True
        return kind, data, pos
    def __repr__(self):
        return 'node()'

class ProcessingInstructionNodeTest(object):
    """Node test that matches any processing instruction event."""
    __slots__ = ['target']
    def __init__(self, target=None):
        self.target = target
    def __call__(self, kind, data, pos, namespaces, variables):
        return kind is PI and (not self.target or data[0] == self.target)
    def __repr__(self):
        arg = ''
        if self.target:
            arg = '"' + self.target + '"'
        return 'processing-instruction(%s)' % arg

class TextNodeTest(object):
    """Node test that matches any text event."""
    __slots__ = []
    def __call__(self, kind, data, pos, namespaces, variables):
        return kind is TEXT
    def __repr__(self):
        return 'text()'

_nodetest_map = {'comment': CommentNodeTest, 'node': NodeTest,
                 'processing-instruction': ProcessingInstructionNodeTest,
                 'text': TextNodeTest}

# Functions

class Function(object):
    """Base class for function nodes in XPath expressions."""

class BooleanFunction(Function):
    """The `boolean` function, which converts its argument to a boolean
    value.
    """
    __slots__ = ['expr']
    _return_type = bool
    def __init__(self, expr):
        self.expr = expr
    def __call__(self, kind, data, pos, namespaces, variables):
        val = self.expr(kind, data, pos, namespaces, variables)
        return as_bool(val)
    def __repr__(self):
        return 'boolean(%r)' % self.expr

class CeilingFunction(Function):
    """The `ceiling` function, which returns the nearest lower integer number
    for the given number.
    """
    __slots__ = ['number']
    def __init__(self, number):
        self.number = number
    def __call__(self, kind, data, pos, namespaces, variables):
        number = self.number(kind, data, pos, namespaces, variables)
        return ceil(as_float(number))
    def __repr__(self):
        return 'ceiling(%r)' % self.number

class ConcatFunction(Function):
    """The `concat` function, which concatenates (joins) the variable number of
    strings it gets as arguments.
    """
    __slots__ = ['exprs']
    def __init__(self, *exprs):
        self.exprs = exprs
    def __call__(self, kind, data, pos, namespaces, variables):
        strings = []
        for item in [expr(kind, data, pos, namespaces, variables)
                     for expr in self.exprs]:
            strings.append(as_string(item))
        return ''.join(strings)
    def __repr__(self):
        return 'concat(%s)' % ', '.join([repr(expr) for expr in self.exprs])

class ContainsFunction(Function):
    """The `contains` function, which returns whether a string contains a given
    substring.
    """
    __slots__ = ['string1', 'string2']
    def __init__(self, string1, string2):
        self.string1 = string1
        self.string2 = string2
    def __call__(self, kind, data, pos, namespaces, variables):
        string1 = self.string1(kind, data, pos, namespaces, variables)
        string2 = self.string2(kind, data, pos, namespaces, variables)
        return as_string(string2) in as_string(string1)
    def __repr__(self):
        return 'contains(%r, %r)' % (self.string1, self.string2)

class MatchesFunction(Function):
    """The `matches` function, which returns whether a string matches a regular
    expression.
    """
    __slots__ = ['string1', 'string2']
    flag_mapping = {'s': re.S, 'm': re.M, 'i': re.I, 'x': re.X}

    def __init__(self, string1, string2, flags=''):
        self.string1 = string1
        self.string2 = string2
        self.flags = self._map_flags(flags)
    def __call__(self, kind, data, pos, namespaces, variables):
        string1 = as_string(self.string1(kind, data, pos, namespaces, variables))
        string2 = as_string(self.string2(kind, data, pos, namespaces, variables))
        return re.search(string2, string1, self.flags)
    def _map_flags(self, flags):
        return reduce(operator.or_,
                      [self.flag_map[flag] for flag in flags], re.U)
    def __repr__(self):
        return 'contains(%r, %r)' % (self.string1, self.string2)

class FalseFunction(Function):
    """The `false` function, which always returns the boolean `false` value."""
    __slots__ = []
    def __call__(self, kind, data, pos, namespaces, variables):
        return False
    def __repr__(self):
        return 'false()'

class FloorFunction(Function):
    """The `ceiling` function, which returns the nearest higher integer number
    for the given number.
    """
    __slots__ = ['number']
    def __init__(self, number):
        self.number = number
    def __call__(self, kind, data, pos, namespaces, variables):
        number = self.number(kind, data, pos, namespaces, variables)
        return floor(as_float(number))
    def __repr__(self):
        return 'floor(%r)' % self.number

class LocalNameFunction(Function):
    """The `local-name` function, which returns the local name of the current
    element.
    """
    __slots__ = []
    def __call__(self, kind, data, pos, namespaces, variables):
        if kind is START:
            return data[0].localname
    def __repr__(self):
        return 'local-name()'

class NameFunction(Function):
    """The `name` function, which returns the qualified name of the current
    element.
    """
    __slots__ = []
    def __call__(self, kind, data, pos, namespaces, variables):
        if kind is START:
            return data[0]
    def __repr__(self):
        return 'name()'

class NamespaceUriFunction(Function):
    """The `namespace-uri` function, which returns the namespace URI of the
    current element.
    """
    __slots__ = []
    def __call__(self, kind, data, pos, namespaces, variables):
        if kind is START:
            return data[0].namespace
    def __repr__(self):
        return 'namespace-uri()'

class NotFunction(Function):
    """The `not` function, which returns the negated boolean value of its
    argument.
    """
    __slots__ = ['expr']
    def __init__(self, expr):
        self.expr = expr
    def __call__(self, kind, data, pos, namespaces, variables):
        return not as_bool(self.expr(kind, data, pos, namespaces, variables))
    def __repr__(self):
        return 'not(%s)' % self.expr

class NormalizeSpaceFunction(Function):
    """The `normalize-space` function, which removes leading and trailing
    whitespace in the given string, and replaces multiple adjacent whitespace
    characters inside the string with a single space.
    """
    __slots__ = ['expr']
    _normalize = re.compile(r'\s{2,}').sub
    def __init__(self, expr):
        self.expr = expr
    def __call__(self, kind, data, pos, namespaces, variables):
        string = self.expr(kind, data, pos, namespaces, variables)
        return self._normalize(' ', as_string(string).strip())
    def __repr__(self):
        return 'normalize-space(%s)' % repr(self.expr)

class NumberFunction(Function):
    """The `number` function that converts its argument to a number."""
    __slots__ = ['expr']
    def __init__(self, expr):
        self.expr = expr
    def __call__(self, kind, data, pos, namespaces, variables):
        val = self.expr(kind, data, pos, namespaces, variables)
        return as_float(val)
    def __repr__(self):
        return 'number(%r)' % self.expr

class RoundFunction(Function):
    """The `round` function, which returns the nearest integer number for the
    given number.
    """
    __slots__ = ['number']
    def __init__(self, number):
        self.number = number
    def __call__(self, kind, data, pos, namespaces, variables):
        number = self.number(kind, data, pos, namespaces, variables)
        return round(as_float(number))
    def __repr__(self):
        return 'round(%r)' % self.number

class StartsWithFunction(Function):
    """The `starts-with` function that returns whether one string starts with
    a given substring.
    """
    __slots__ = ['string1', 'string2']
    def __init__(self, string1, string2):
        self.string1 = string1
        self.string2 = string2
    def __call__(self, kind, data, pos, namespaces, variables):
        string1 = self.string1(kind, data, pos, namespaces, variables)
        string2 = self.string2(kind, data, pos, namespaces, variables)
        return as_string(string1).startswith(as_string(string2))
    def __repr__(self):
        return 'starts-with(%r, %r)' % (self.string1, self.string2)

class StringLengthFunction(Function):
    """The `string-length` function that returns the length of the given
    string.
    """
    __slots__ = ['expr']
    def __init__(self, expr):
        self.expr = expr
    def __call__(self, kind, data, pos, namespaces, variables):
        string = self.expr(kind, data, pos, namespaces, variables)
        return len(as_string(string))
    def __repr__(self):
        return 'string-length(%r)' % self.expr

class SubstringFunction(Function):
    """The `substring` function that returns the part of a string that starts
    at the given offset, and optionally limited to the given length.
    """
    __slots__ = ['string', 'start', 'length']
    def __init__(self, string, start, length=None):
        self.string = string
        self.start = start
        self.length = length
    def __call__(self, kind, data, pos, namespaces, variables):
        string = self.string(kind, data, pos, namespaces, variables)
        start = self.start(kind, data, pos, namespaces, variables)
        length = 0
        if self.length is not None:
            length = self.length(kind, data, pos, namespaces, variables)
        return string[as_long(start):len(as_string(string)) - as_long(length)]
    def __repr__(self):
        if self.length is not None:
            return 'substring(%r, %r, %r)' % (self.string, self.start,
                                              self.length)
        else:
            return 'substring(%r, %r)' % (self.string, self.start)

class SubstringAfterFunction(Function):
    """The `substring-after` function that returns the part of a string that
    is found after the given substring.
    """
    __slots__ = ['string1', 'string2']
    def __init__(self, string1, string2):
        self.string1 = string1
        self.string2 = string2
    def __call__(self, kind, data, pos, namespaces, variables):
        string1 = as_string(self.string1(kind, data, pos, namespaces, variables))
        string2 = as_string(self.string2(kind, data, pos, namespaces, variables))
        index = string1.find(string2)
        if index >= 0:
            return string1[index + len(string2):]
        return ''
    def __repr__(self):
        return 'substring-after(%r, %r)' % (self.string1, self.string2)

class SubstringBeforeFunction(Function):
    """The `substring-before` function that returns the part of a string that
    is found before the given substring.
    """
    __slots__ = ['string1', 'string2']
    def __init__(self, string1, string2):
        self.string1 = string1
        self.string2 = string2
    def __call__(self, kind, data, pos, namespaces, variables):
        string1 = as_string(self.string1(kind, data, pos, namespaces, variables))
        string2 = as_string(self.string2(kind, data, pos, namespaces, variables))
        index = string1.find(string2)
        if index >= 0:
            return string1[:index]
        return ''
    def __repr__(self):
        return 'substring-after(%r, %r)' % (self.string1, self.string2)

class TranslateFunction(Function):
    """The `translate` function that translates a set of characters in a
    string to target set of characters.
    """
    __slots__ = ['string', 'fromchars', 'tochars']
    def __init__(self, string, fromchars, tochars):
        self.string = string
        self.fromchars = fromchars
        self.tochars = tochars
    def __call__(self, kind, data, pos, namespaces, variables):
        string = as_string(self.string(kind, data, pos, namespaces, variables))
        fromchars = as_string(self.fromchars(kind, data, pos, namespaces, variables))
        tochars = as_string(self.tochars(kind, data, pos, namespaces, variables))
        table = dict(zip([ord(c) for c in fromchars],
                         [ord(c) for c in tochars]))
        return string.translate(table)
    def __repr__(self):
        return 'translate(%r, %r, %r)' % (self.string, self.fromchars,
                                          self.tochars)

class TrueFunction(Function):
    """The `true` function, which always returns the boolean `true` value."""
    __slots__ = []
    def __call__(self, kind, data, pos, namespaces, variables):
        return True
    def __repr__(self):
        return 'true()'

_function_map = {'boolean': BooleanFunction, 'ceiling': CeilingFunction,
                 'concat': ConcatFunction, 'contains': ContainsFunction,
                 'matches': MatchesFunction, 'false': FalseFunction, 'floor':
                 FloorFunction, 'local-name': LocalNameFunction, 'name':
                 NameFunction, 'namespace-uri': NamespaceUriFunction,
                 'normalize-space': NormalizeSpaceFunction, 'not': NotFunction,
                 'number': NumberFunction, 'round': RoundFunction,
                 'starts-with': StartsWithFunction, 'string-length':
                 StringLengthFunction, 'substring': SubstringFunction,
                 'substring-after': SubstringAfterFunction, 'substring-before':
                 SubstringBeforeFunction, 'translate': TranslateFunction,
                 'true': TrueFunction}

# Literals & Variables

class Literal(object):
    """Abstract base class for literal nodes."""

class StringLiteral(Literal):
    """A string literal node."""
    __slots__ = ['text']
    def __init__(self, text):
        self.text = text
    def __call__(self, kind, data, pos, namespaces, variables):
        return self.text
    def __repr__(self):
        return '"%s"' % self.text

class NumberLiteral(Literal):
    """A number literal node."""
    __slots__ = ['number']
    def __init__(self, number):
        self.number = number
    def __call__(self, kind, data, pos, namespaces, variables):
        return self.number
    def __repr__(self):
        return str(self.number)

class VariableReference(Literal):
    """A variable reference node."""
    __slots__ = ['name']
    def __init__(self, name):
        self.name = name
    def __call__(self, kind, data, pos, namespaces, variables):
        return variables.get(self.name)
    def __repr__(self):
        return str(self.name)

# Operators

class AndOperator(object):
    """The boolean operator `and`."""
    __slots__ = ['lval', 'rval']
    def __init__(self, lval, rval):
        self.lval = lval
        self.rval = rval
    def __call__(self, kind, data, pos, namespaces, variables):
        lval = as_bool(self.lval(kind, data, pos, namespaces, variables))
        if not lval:
            return False
        rval = self.rval(kind, data, pos, namespaces, variables)
        return as_bool(rval)
    def __repr__(self):
        return '%s and %s' % (self.lval, self.rval)

class EqualsOperator(object):
    """The equality operator `=`."""
    __slots__ = ['lval', 'rval']
    def __init__(self, lval, rval):
        self.lval = lval
        self.rval = rval
    def __call__(self, kind, data, pos, namespaces, variables):
        lval = as_scalar(self.lval(kind, data, pos, namespaces, variables))
        rval = as_scalar(self.rval(kind, data, pos, namespaces, variables))
        return lval == rval
    def __repr__(self):
        return '%s=%s' % (self.lval, self.rval)

class NotEqualsOperator(object):
    """The equality operator `!=`."""
    __slots__ = ['lval', 'rval']
    def __init__(self, lval, rval):
        self.lval = lval
        self.rval = rval
    def __call__(self, kind, data, pos, namespaces, variables):
        lval = as_scalar(self.lval(kind, data, pos, namespaces, variables))
        rval = as_scalar(self.rval(kind, data, pos, namespaces, variables))
        return lval != rval
    def __repr__(self):
        return '%s!=%s' % (self.lval, self.rval)

class OrOperator(object):
    """The boolean operator `or`."""
    __slots__ = ['lval', 'rval']
    def __init__(self, lval, rval):
        self.lval = lval
        self.rval = rval
    def __call__(self, kind, data, pos, namespaces, variables):
        lval = as_bool(self.lval(kind, data, pos, namespaces, variables))
        if lval:
            return True
        rval = self.rval(kind, data, pos, namespaces, variables)
        return as_bool(rval)
    def __repr__(self):
        return '%s or %s' % (self.lval, self.rval)

class GreaterThanOperator(object):
    """The relational operator `>` (greater than)."""
    __slots__ = ['lval', 'rval']
    def __init__(self, lval, rval):
        self.lval = lval
        self.rval = rval
    def __call__(self, kind, data, pos, namespaces, variables):
        lval = self.lval(kind, data, pos, namespaces, variables)
        rval = self.rval(kind, data, pos, namespaces, variables)
        return as_float(lval) > as_float(rval)
    def __repr__(self):
        return '%s>%s' % (self.lval, self.rval)

class GreaterThanOrEqualOperator(object):
    """The relational operator `>=` (greater than or equal)."""
    __slots__ = ['lval', 'rval']
    def __init__(self, lval, rval):
        self.lval = lval
        self.rval = rval
    def __call__(self, kind, data, pos, namespaces, variables):
        lval = self.lval(kind, data, pos, namespaces, variables)
        rval = self.rval(kind, data, pos, namespaces, variables)
        return as_float(lval) >= as_float(rval)
    def __repr__(self):
        return '%s>=%s' % (self.lval, self.rval)

class LessThanOperator(object):
    """The relational operator `<` (less than)."""
    __slots__ = ['lval', 'rval']
    def __init__(self, lval, rval):
        self.lval = lval
        self.rval = rval
    def __call__(self, kind, data, pos, namespaces, variables):
        lval = self.lval(kind, data, pos, namespaces, variables)
        rval = self.rval(kind, data, pos, namespaces, variables)
        return as_float(lval) < as_float(rval)
    def __repr__(self):
        return '%s<%s' % (self.lval, self.rval)

class LessThanOrEqualOperator(object):
    """The relational operator `<=` (less than or equal)."""
    __slots__ = ['lval', 'rval']
    def __init__(self, lval, rval):
        self.lval = lval
        self.rval = rval
    def __call__(self, kind, data, pos, namespaces, variables):
        lval = self.lval(kind, data, pos, namespaces, variables)
        rval = self.rval(kind, data, pos, namespaces, variables)
        return as_float(lval) <= as_float(rval)
    def __repr__(self):
        return '%s<=%s' % (self.lval, self.rval)

_operator_map = {'=': EqualsOperator, '!=': NotEqualsOperator,
                 '>': GreaterThanOperator, '>=': GreaterThanOrEqualOperator,
                 '<': LessThanOperator, '>=': LessThanOrEqualOperator}


_DOTSLASHSLASH = (DESCENDANT_OR_SELF, PrincipalTypeTest(None), ())
_DOTSLASH = (SELF, PrincipalTypeTest(None), ())
