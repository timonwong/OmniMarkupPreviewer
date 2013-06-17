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

"""Support for "safe" evaluation of Python expressions."""

import builtins

from textwrap import dedent
from types import CodeType

from genshi.core import Markup
from genshi.template.astutil import ASTTransformer, ASTCodeGenerator, \
                                    _ast, parse
from genshi.template.base import TemplateRuntimeError
from genshi.util import flatten

from genshi.compat import get_code_params, build_code_chunk, IS_PYTHON2

__all__ = ['Code', 'Expression', 'Suite', 'LenientLookup', 'StrictLookup',
           'Undefined', 'UndefinedError']
__docformat__ = 'restructuredtext en'


# Check for a Python 2.4 bug in the eval loop
has_star_import_bug = False
try:
    class _FakeMapping(object):
        __getitem__ = __setitem__ = lambda *a: None
    exec('from sys import *', {}, _FakeMapping())
except SystemError:
    has_star_import_bug = True
del _FakeMapping


def _star_import_patch(mapping, modname):
    """This function is used as helper if a Python version with a broken
    star-import opcode is in use.
    """
    module = __import__(modname, None, None, ['__all__'])
    if hasattr(module, '__all__'):
        members = module.__all__
    else:
        members = [x for x in module.__dict__ if not x.startswith('_')]
    mapping.update([(name, getattr(module, name)) for name in members])


class Code(object):
    """Abstract base class for the `Expression` and `Suite` classes."""
    __slots__ = ['source', 'code', 'ast', '_globals']

    def __init__(self, source, filename=None, lineno=-1, lookup='strict',
                 xform=None):
        """Create the code object, either from a string, or from an AST node.
        
        :param source: either a string containing the source code, or an AST
                       node
        :param filename: the (preferably absolute) name of the file containing
                         the code
        :param lineno: the number of the line on which the code was found
        :param lookup: the lookup class that defines how variables are looked
                       up in the context; can be either "strict" (the default),
                       "lenient", or a custom lookup class
        :param xform: the AST transformer that should be applied to the code;
                      if `None`, the appropriate transformation is chosen
                      depending on the mode
        """
        if isinstance(source, str):
            self.source = source
            node = _parse(source, mode=self.mode)
        else:
            assert isinstance(source, _ast.AST), \
                'Expected string or AST node, but got %r' % source
            self.source = '?'
            if self.mode == 'eval':
                node = _ast.Expression()
                node.body = source
            else:
                node = _ast.Module()
                node.body = [source]

        self.ast = node
        self.code = _compile(node, self.source, mode=self.mode,
                             filename=filename, lineno=lineno, xform=xform)
        if lookup is None:
            lookup = LenientLookup
        elif isinstance(lookup, str):
            lookup = {'lenient': LenientLookup, 'strict': StrictLookup}[lookup]
        self._globals = lookup.globals

    def __getstate__(self):
        state = {'source': self.source, 'ast': self.ast,
                 'lookup': self._globals.__self__}
        state['code'] = get_code_params(self.code)
        return state

    def __setstate__(self, state):
        self.source = state['source']
        self.ast = state['ast']
        self.code = CodeType(0, *state['code'])
        self._globals = state['lookup'].globals

    def __eq__(self, other):
        return (type(other) == type(self)) and (self.code == other.code)

    def __hash__(self):
        return hash(self.code)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, self.source)


class Expression(Code):
    """Evaluates Python expressions used in templates.

    >>> data = dict(test='Foo', items=[1, 2, 3], dict={'some': 'thing'})
    >>> Expression('test').evaluate(data)
    'Foo'

    >>> Expression('items[0]').evaluate(data)
    1
    >>> Expression('items[-1]').evaluate(data)
    3
    >>> Expression('dict["some"]').evaluate(data)
    'thing'
    
    Similar to e.g. Javascript, expressions in templates can use the dot
    notation for attribute access to access items in mappings:
    
    >>> Expression('dict.some').evaluate(data)
    'thing'
    
    This also works the other way around: item access can be used to access
    any object attribute:
    
    >>> class MyClass(object):
    ...     myattr = 'Bar'
    >>> data = dict(mine=MyClass(), key='myattr')
    >>> Expression('mine.myattr').evaluate(data)
    'Bar'
    >>> Expression('mine["myattr"]').evaluate(data)
    'Bar'
    >>> Expression('mine[key]').evaluate(data)
    'Bar'
    
    All of the standard Python operators are available to template expressions.
    Built-in functions such as ``len()`` are also available in template
    expressions:
    
    >>> data = dict(items=[1, 2, 3])
    >>> Expression('len(items)').evaluate(data)
    3
    """
    __slots__ = []
    mode = 'eval'

    def evaluate(self, data):
        """Evaluate the expression against the given data dictionary.
        
        :param data: a mapping containing the data to evaluate against
        :return: the result of the evaluation
        """
        __traceback_hide__ = 'before_and_this'
        _globals = self._globals(data)
        return eval(self.code, _globals, {'__data__': data})


class Suite(Code):
    """Executes Python statements used in templates.

    >>> data = dict(test='Foo', items=[1, 2, 3], dict={'some': 'thing'})
    >>> Suite("foo = dict['some']").execute(data)
    >>> data['foo']
    'thing'
    """
    __slots__ = []
    mode = 'exec'

    def execute(self, data):
        """Execute the suite in the given data dictionary.
        
        :param data: a mapping containing the data to execute in
        """
        __traceback_hide__ = 'before_and_this'
        _globals = self._globals(data)
        exec(self.code, _globals, data)


UNDEFINED = object()


class UndefinedError(TemplateRuntimeError):
    """Exception thrown when a template expression attempts to access a variable
    not defined in the context.
    
    :see: `LenientLookup`, `StrictLookup`
    """
    def __init__(self, name, owner=UNDEFINED):
        if owner is not UNDEFINED:
            message = '%s has no member named "%s"' % (repr(owner), name)
        else:
            message = '"%s" not defined' % name
        TemplateRuntimeError.__init__(self, message)


class Undefined(object):
    """Represents a reference to an undefined variable.
    
    Unlike the Python runtime, template expressions can refer to an undefined
    variable without causing a `NameError` to be raised. The result will be an
    instance of the `Undefined` class, which is treated the same as ``False`` in
    conditions, but raise an exception on any other operation:
    
    >>> foo = Undefined('foo')
    >>> bool(foo)
    False
    >>> list(foo)
    []
    >>> print(foo)
    undefined
    
    However, calling an undefined variable, or trying to access an attribute
    of that variable, will raise an exception that includes the name used to
    reference that undefined variable.
    
    >>> try:
    ...     foo('bar')
    ... except UndefinedError as e:
    ...     print(e.msg)
    "foo" not defined

    >>> try:
    ...     foo.bar
    ... except UndefinedError as e:
    ...     print(e.msg)
    "foo" not defined
    
    :see: `LenientLookup`
    """
    __slots__ = ['_name', '_owner']

    def __init__(self, name, owner=UNDEFINED):
        """Initialize the object.
        
        :param name: the name of the reference
        :param owner: the owning object, if the variable is accessed as a member
        """
        self._name = name
        self._owner = owner

    def __iter__(self):
        return iter([])

    def __bool__(self):
        return False

    def __repr__(self):
        return '<%s %r>' % (type(self).__name__, self._name)

    def __str__(self):
        return 'undefined'

    def _die(self, *args, **kwargs):
        """Raise an `UndefinedError`."""
        __traceback_hide__ = True
        raise UndefinedError(self._name, self._owner)
    __call__ = __getattr__ = __getitem__ = _die

    # Hack around some behavior introduced in Python 2.6.2
    # http://genshi.edgewall.org/ticket/324
    __length_hint__ = None


class LookupBase(object):
    """Abstract base class for variable lookup implementations."""

    @classmethod
    def globals(cls, data):
        """Construct the globals dictionary to use as the execution context for
        the expression or suite.
        """
        return {
            '__data__': data,
            '_lookup_name': cls.lookup_name,
            '_lookup_attr': cls.lookup_attr,
            '_lookup_item': cls.lookup_item,
            '_star_import_patch': _star_import_patch,
            'UndefinedError': UndefinedError,
        }

    @classmethod
    def lookup_name(cls, data, name):
        __traceback_hide__ = True
        val = data.get(name, UNDEFINED)
        if val is UNDEFINED:
            val = BUILTINS.get(name, val)
            if val is UNDEFINED:
                val = cls.undefined(name)
        return val

    @classmethod
    def lookup_attr(cls, obj, key):
        __traceback_hide__ = True
        try:
            val = getattr(obj, key)
        except AttributeError:
            if hasattr(obj.__class__, key):
                raise
            else:
                try:
                    val = obj[key]
                except (KeyError, TypeError):
                    val = cls.undefined(key, owner=obj)
        return val

    @classmethod
    def lookup_item(cls, obj, key):
        __traceback_hide__ = True
        if len(key) == 1:
            key = key[0]
        try:
            return obj[key]
        except (AttributeError, KeyError, IndexError, TypeError) as e:
            if isinstance(key, str):
                val = getattr(obj, key, UNDEFINED)
                if val is UNDEFINED:
                    val = cls.undefined(key, owner=obj)
                return val
            raise

    @classmethod
    def undefined(cls, key, owner=UNDEFINED):
        """Can be overridden by subclasses to specify behavior when undefined
        variables are accessed.
        
        :param key: the name of the variable
        :param owner: the owning object, if the variable is accessed as a member
        """
        raise NotImplementedError


class LenientLookup(LookupBase):
    """Default variable lookup mechanism for expressions.
    
    When an undefined variable is referenced using this lookup style, the
    reference evaluates to an instance of the `Undefined` class:
    
    >>> expr = Expression('nothing', lookup='lenient')
    >>> undef = expr.evaluate({})
    >>> undef
    <Undefined 'nothing'>
    
    The same will happen when a non-existing attribute or item is accessed on
    an existing object:
    
    >>> expr = Expression('something.nil', lookup='lenient')
    >>> expr.evaluate({'something': dict()})
    <Undefined 'nil'>
    
    See the documentation of the `Undefined` class for details on the behavior
    of such objects.
    
    :see: `StrictLookup`
    """

    @classmethod
    def undefined(cls, key, owner=UNDEFINED):
        """Return an ``Undefined`` object."""
        __traceback_hide__ = True
        return Undefined(key, owner=owner)


class StrictLookup(LookupBase):
    """Strict variable lookup mechanism for expressions.
    
    Referencing an undefined variable using this lookup style will immediately
    raise an ``UndefinedError``:
    
    >>> expr = Expression('nothing', lookup='strict')
    >>> try:
    ...     expr.evaluate({})
    ... except UndefinedError as e:
    ...     print(e.msg)
    "nothing" not defined
    
    The same happens when a non-existing attribute or item is accessed on an
    existing object:
    
    >>> expr = Expression('something.nil', lookup='strict')
    >>> try:
    ...     expr.evaluate({'something': dict()})
    ... except UndefinedError as e:
    ...     print(e.msg)
    {} has no member named "nil"
    """

    @classmethod
    def undefined(cls, key, owner=UNDEFINED):
        """Raise an ``UndefinedError`` immediately."""
        __traceback_hide__ = True
        raise UndefinedError(key, owner=owner)


def _parse(source, mode='eval'):
    source = source.strip()
    if mode == 'exec':
        lines = [line.expandtabs() for line in source.splitlines()]
        if lines:
            first = lines[0]
            rest = dedent('\n'.join(lines[1:])).rstrip()
            if first.rstrip().endswith(':') and not rest[0].isspace():
                rest = '\n'.join(['    %s' % line for line in rest.splitlines()])
            source = '\n'.join([first, rest])
    if isinstance(source, str):
        source = ('\ufeff' + source).encode('utf-8')
    return parse(source, mode)


def _compile(node, source=None, mode='eval', filename=None, lineno=-1,
             xform=None):
    if not filename:
        filename = '<string>'
    if IS_PYTHON2:
        # Python 2 requires non-unicode filenames
        if isinstance(filename, str):
            filename = filename.encode('utf-8', 'replace')
    else:
        # Python 3 requires unicode filenames
        if not isinstance(filename, str):
            filename = filename.decode('utf-8', 'replace')
    if lineno <= 0:
        lineno = 1

    if xform is None:
        xform = {
            'eval': ExpressionASTTransformer
        }.get(mode, TemplateASTTransformer)
    tree = xform().visit(node)

    if mode == 'eval':
        name = '<Expression %r>' % (source or '?')
    else:
        lines = source.splitlines()
        if not lines:
            extract = ''
        else:
            extract = lines[0]
        if len(lines) > 1:
            extract += ' ...'
        name = '<Suite %r>' % (extract)
    new_source = ASTCodeGenerator(tree).code
    code = compile(new_source, filename, mode)

    try:
        # We'd like to just set co_firstlineno, but it's readonly. So we need
        # to clone the code object while adjusting the line number
        return build_code_chunk(code, filename, name, lineno)
    except RuntimeError:
        return code


def _new(class_, *args, **kwargs):
    ret = class_()
    for attr, value in zip(ret._fields, args):
        if attr in kwargs:
            raise ValueError('Field set both in args and kwargs')
        setattr(ret, attr, value)
    for attr, value in kwargs:
        setattr(ret, attr, value)
    return ret


BUILTINS = builtins.__dict__.copy()
BUILTINS.update({'Markup': Markup, 'Undefined': Undefined})
CONSTANTS = frozenset(['False', 'True', 'None', 'NotImplemented', 'Ellipsis'])


class TemplateASTTransformer(ASTTransformer):
    """Concrete AST transformer that implements the AST transformations needed
    for code embedded in templates.
    """

    def __init__(self):
        self.locals = [CONSTANTS]

    def _extract_names(self, node):
        names = set()
        def _process(node):
            if not IS_PYTHON2 and isinstance(node, _ast.arg):
                names.add(node.arg)
            if isinstance(node, _ast.Name):
                names.add(node.id)
            elif isinstance(node, _ast.alias):
                names.add(node.asname or node.name)
            elif isinstance(node, _ast.Tuple):
                for elt in node.elts:
                    _process(elt)
        if hasattr(node, 'args'):
            for arg in node.args:
                _process(arg)
            if hasattr(node, 'vararg'):
                names.add(node.vararg)
            if hasattr(node, 'kwarg'):
                names.add(node.kwarg)
        elif hasattr(node, 'names'):
            for elt in node.names:
                _process(elt)
        return names

    def visit_Str(self, node):
        if not isinstance(node.s, str):
            try: # If the string is ASCII, return a `str` object
                node.s.decode('ascii')
            except ValueError: # Otherwise return a `unicode` object
                return _new(_ast.Str, node.s.decode('utf-8'))
        return node

    def visit_ClassDef(self, node):
        if len(self.locals) > 1:
            self.locals[-1].add(node.name)
        self.locals.append(set())
        try:
            return ASTTransformer.visit_ClassDef(self, node)
        finally:
            self.locals.pop()

    def visit_Import(self, node):
        if len(self.locals) > 1:
            self.locals[-1].update(self._extract_names(node))
        return ASTTransformer.visit_Import(self, node)

    def visit_ImportFrom(self, node):
        if [a.name for a in node.names] == ['*']:
            if has_star_import_bug:
                # This is a Python 2.4 bug. Only if we have a broken Python
                # version do we need to apply this hack
                node = _new(_ast.Expr, _new(_ast.Call,
                    _new(_ast.Name, '_star_import_patch'), [
                        _new(_ast.Name, '__data__'),
                        _new(_ast.Str, node.module)
                    ], (), ()))
            return node
        if len(self.locals) > 1:
            self.locals[-1].update(self._extract_names(node))
        return ASTTransformer.visit_ImportFrom(self, node)

    def visit_FunctionDef(self, node):
        if len(self.locals) > 1:
            self.locals[-1].add(node.name)

        self.locals.append(self._extract_names(node.args))
        try:
            return ASTTransformer.visit_FunctionDef(self, node)
        finally:
            self.locals.pop()

    # GeneratorExp(expr elt, comprehension* generators)
    def visit_GeneratorExp(self, node):
        gens = []
        for generator in node.generators:
            # comprehension = (expr target, expr iter, expr* ifs)
            self.locals.append(set())
            gen = _new(_ast.comprehension, self.visit(generator.target),
                       self.visit(generator.iter),
                       [self.visit(if_) for if_ in generator.ifs])
            gens.append(gen)

        # use node.__class__ to make it reusable as ListComp
        ret = _new(node.__class__, self.visit(node.elt), gens)
        #delete inserted locals
        del self.locals[-len(node.generators):]
        return ret

    # ListComp(expr elt, comprehension* generators)
    visit_ListComp = visit_GeneratorExp

    def visit_Lambda(self, node):
        self.locals.append(self._extract_names(node.args))
        try:
            return ASTTransformer.visit_Lambda(self, node)
        finally:
            self.locals.pop()

    def visit_Name(self, node):
        # If the name refers to a local inside a lambda, list comprehension, or
        # generator expression, leave it alone
        if isinstance(node.ctx, _ast.Load) and \
                node.id not in flatten(self.locals):
            # Otherwise, translate the name ref into a context lookup
            name = _new(_ast.Name, '_lookup_name', _ast.Load())
            namearg = _new(_ast.Name, '__data__', _ast.Load())
            strarg = _new(_ast.Str, node.id)
            node = _new(_ast.Call, name, [namearg, strarg], [])
        elif isinstance(node.ctx, _ast.Store):
            if len(self.locals) > 1:
                self.locals[-1].add(node.id)

        return node


class ExpressionASTTransformer(TemplateASTTransformer):
    """Concrete AST transformer that implements the AST transformations needed
    for code embedded in templates.
    """

    def visit_Attribute(self, node):
        if not isinstance(node.ctx, _ast.Load):
            return ASTTransformer.visit_Attribute(self, node)

        func = _new(_ast.Name, '_lookup_attr', _ast.Load())
        args = [self.visit(node.value), _new(_ast.Str, node.attr)]
        return _new(_ast.Call, func, args, [])

    def visit_Subscript(self, node):
        if not isinstance(node.ctx, _ast.Load) or \
                not isinstance(node.slice, _ast.Index):
            return ASTTransformer.visit_Subscript(self, node)

        func = _new(_ast.Name, '_lookup_item', _ast.Load())
        args = [
            self.visit(node.value),
            _new(_ast.Tuple, (self.visit(node.slice.value),), _ast.Load())
        ]
        return _new(_ast.Call, func, args, [])

