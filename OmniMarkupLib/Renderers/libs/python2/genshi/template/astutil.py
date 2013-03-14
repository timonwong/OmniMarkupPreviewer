# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2010 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://genshi.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://genshi.edgewall.org/log/.

"""Support classes for generating code from abstract syntax trees."""

try:
    import _ast
except ImportError:
    from genshi.template.ast24 import _ast, parse
else:
    def parse(source, mode):
        return compile(source, '', mode, _ast.PyCF_ONLY_AST)


__docformat__ = 'restructuredtext en'


class ASTCodeGenerator(object):
    """General purpose base class for AST transformations.

    Every visitor method can be overridden to return an AST node that has been
    altered or replaced in some way.
    """
    def __init__(self, tree):
        self.lines_info = []
        self.line_info = None
        self.code = ''
        self.line = None
        self.last = None
        self.indent = 0
        self.blame_stack = []
        self.visit(tree)
        if self.line.strip():
            self.code += self.line + '\n'
            self.lines_info.append(self.line_info)
        self.line = None
        self.line_info = None

    def _change_indent(self, delta):
        self.indent += delta

    def _new_line(self):
        if self.line is not None:
            self.code += self.line + '\n'
            self.lines_info.append(self.line_info)
        self.line = ' '*4*self.indent
        if len(self.blame_stack) == 0:
            self.line_info = []
            self.last = None
        else:
            self.line_info = [(0, self.blame_stack[-1],)]
            self.last = self.blame_stack[-1]

    def _write(self, s):
        if len(s) == 0:
            return
        if len(self.blame_stack) == 0:
            if self.last is not None:
                self.last = None
                self.line_info.append((len(self.line), self.last))
        else:
            if self.last != self.blame_stack[-1]:
                self.last = self.blame_stack[-1]
                self.line_info.append((len(self.line), self.last))
        self.line += s

    def visit(self, node):
        if node is None:
            return None
        if type(node) is tuple:
            return tuple([self.visit(n) for n in node])
        try:
            self.blame_stack.append((node.lineno, node.col_offset,))
            info = True
        except AttributeError:
            info = False
        visitor = getattr(self, 'visit_%s' % node.__class__.__name__, None)
        if visitor is None:
            raise Exception('Unhandled node type %r' % type(node))
        ret = visitor(node)
        if info:
            self.blame_stack.pop()
        return ret

    def visit_Module(self, node):
        for n in node.body:
            self.visit(n)
    visit_Interactive = visit_Module
    visit_Suite = visit_Module

    def visit_Expression(self, node):
        self._new_line()
        return self.visit(node.body)

    # arguments = (expr* args, identifier? vararg,
    #              identifier? kwarg, expr* defaults)
    def visit_arguments(self, node):
        first = True
        no_default_count = len(node.args) - len(node.defaults)
        for i, arg in enumerate(node.args):
            if not first:
                self._write(', ')
            else:
                first = False
            self.visit(arg)
            if i >= no_default_count:
                self._write('=')
                self.visit(node.defaults[i - no_default_count])
        if getattr(node, 'vararg', None):
            if not first:
                self._write(', ')
            else:
                first = False
            self._write('*' + node.vararg)
        if getattr(node, 'kwarg', None):
            if not first:
                self._write(', ')
            else:
                first = False
            self._write('**' + node.kwarg)

    # FunctionDef(identifier name, arguments args,
    #                           stmt* body, expr* decorator_list)
    def visit_FunctionDef(self, node):
        decarators = ()
        if hasattr(node, 'decorator_list'):
            decorators = getattr(node, 'decorator_list')
        else: # different name in earlier Python versions
            decorators = getattr(node, 'decorators', ())
        for decorator in decorators:
            self._new_line()
            self._write('@')
            self.visit(decorator)
        self._new_line()
        self._write('def ' + node.name + '(')
        self.visit(node.args)
        self._write('):')
        self._change_indent(1)
        for statement in node.body:
            self.visit(statement)
        self._change_indent(-1)

    # ClassDef(identifier name, expr* bases, stmt* body)
    def visit_ClassDef(self, node):
        self._new_line()
        self._write('class ' + node.name)
        if node.bases:
            self._write('(')
            self.visit(node.bases[0])
            for base in node.bases[1:]:
                self._write(', ')
                self.visit(base)
            self._write(')')
        self._write(':')
        self._change_indent(1)
        for statement in node.body:
            self.visit(statement)
        self._change_indent(-1)

    # Return(expr? value)
    def visit_Return(self, node):
        self._new_line()
        self._write('return')
        if getattr(node, 'value', None):
            self._write(' ')
            self.visit(node.value)

    # Delete(expr* targets)
    def visit_Delete(self, node):
        self._new_line()
        self._write('del ')
        self.visit(node.targets[0])
        for target in node.targets[1:]:
            self._write(', ')
            self.visit(target)

    # Assign(expr* targets, expr value)
    def visit_Assign(self, node):
        self._new_line()
        for target in node.targets:
            self.visit(target)
            self._write(' = ')
        self.visit(node.value)

    # AugAssign(expr target, operator op, expr value)
    def visit_AugAssign(self, node):
        self._new_line()
        self.visit(node.target)
        self._write(' ' + self.binary_operators[node.op.__class__] + '= ')
        self.visit(node.value)

    # Print(expr? dest, expr* values, bool nl)
    def visit_Print(self, node):
        self._new_line()
        self._write('print')
        if getattr(node, 'dest', None):
            self._write(' >> ')
            self.visit(node.dest)
            if getattr(node, 'values', None):
                self._write(', ')
        else:
            self._write(' ')
        if getattr(node, 'values', None):
            self.visit(node.values[0])
            for value in node.values[1:]:
                self._write(', ')
                self.visit(value)
        if not node.nl:
            self._write(',')

    # For(expr target, expr iter, stmt* body, stmt* orelse)
    def visit_For(self, node):
        self._new_line()
        self._write('for ')
        self.visit(node.target)
        self._write(' in ')
        self.visit(node.iter)
        self._write(':')
        self._change_indent(1)
        for statement in node.body:
            self.visit(statement)
        self._change_indent(-1)
        if getattr(node, 'orelse', None):
            self._new_line()
            self._write('else:')
            self._change_indent(1)
            for statement in node.orelse:
                self.visit(statement)
            self._change_indent(-1)

    # While(expr test, stmt* body, stmt* orelse)
    def visit_While(self, node):
        self._new_line()
        self._write('while ')
        self.visit(node.test)
        self._write(':')
        self._change_indent(1)
        for statement in node.body:
            self.visit(statement)
        self._change_indent(-1)
        if getattr(node, 'orelse', None):
            self._new_line()
            self._write('else:')
            self._change_indent(1)
            for statement in node.orelse:
                self.visit(statement)
            self._change_indent(-1)

    # If(expr test, stmt* body, stmt* orelse)
    def visit_If(self, node):
        self._new_line()
        self._write('if ')
        self.visit(node.test)
        self._write(':')
        self._change_indent(1)
        for statement in node.body:
            self.visit(statement)
        self._change_indent(-1)
        if getattr(node, 'orelse', None):
            self._new_line()
            self._write('else:')
            self._change_indent(1)
            for statement in node.orelse:
                self.visit(statement)
            self._change_indent(-1)

    # With(expr context_expr, expr? optional_vars, stmt* body)
    def visit_With(self, node):
        self._new_line()
        self._write('with ')
        self.visit(node.context_expr)
        if getattr(node, 'optional_vars', None):
            self._write(' as ')
            self.visit(node.optional_vars)
        self._write(':')
        self._change_indent(1)
        for statement in node.body:
            self.visit(statement)
        self._change_indent(-1)


    # Raise(expr? type, expr? inst, expr? tback)
    def visit_Raise(self, node):
        self._new_line()
        self._write('raise')
        if not node.type:
            return
        self._write(' ')
        self.visit(node.type)
        if not node.inst:
            return
        self._write(', ')
        self.visit(node.inst)
        if not node.tback:
            return
        self._write(', ')
        self.visit(node.tback)

    # TryExcept(stmt* body, excepthandler* handlers, stmt* orelse)
    def visit_TryExcept(self, node):
        self._new_line()
        self._write('try:')
        self._change_indent(1)
        for statement in node.body:
            self.visit(statement)
        self._change_indent(-1)
        if getattr(node, 'handlers', None):
            for handler in node.handlers:
                self.visit(handler)
        self._new_line()
        if getattr(node, 'orelse', None):
            self._write('else:')
            self._change_indent(1)
            for statement in node.orelse:
                self.visit(statement)
            self._change_indent(-1)

    # excepthandler = (expr? type, expr? name, stmt* body)
    def visit_ExceptHandler(self, node):
        self._new_line()
        self._write('except')
        if getattr(node, 'type', None):
            self._write(' ')
            self.visit(node.type)
        if getattr(node, 'name', None):
            self._write(', ')
            self.visit(node.name)
        self._write(':')
        self._change_indent(1)
        for statement in node.body:
            self.visit(statement)
        self._change_indent(-1)
    visit_excepthandler = visit_ExceptHandler

    # TryFinally(stmt* body, stmt* finalbody)
    def visit_TryFinally(self, node):
        self._new_line()
        self._write('try:')
        self._change_indent(1)
        for statement in node.body:
            self.visit(statement)
        self._change_indent(-1)

        if getattr(node, 'finalbody', None):
            self._new_line()
            self._write('finally:')
            self._change_indent(1)
            for statement in node.finalbody:
                self.visit(statement)
            self._change_indent(-1)

    # Assert(expr test, expr? msg)
    def visit_Assert(self, node):
        self._new_line()
        self._write('assert ')
        self.visit(node.test)
        if getattr(node, 'msg', None):
            self._write(', ')
            self.visit(node.msg)

    def visit_alias(self, node):
        self._write(node.name)
        if getattr(node, 'asname', None):
            self._write(' as ')
            self._write(node.asname)

    # Import(alias* names)
    def visit_Import(self, node):
        self._new_line()
        self._write('import ')
        self.visit(node.names[0])
        for name in node.names[1:]:
            self._write(', ')
            self.visit(name)

    # ImportFrom(identifier module, alias* names, int? level)
    def visit_ImportFrom(self, node):
        self._new_line()
        self._write('from ')
        if node.level:
            self._write('.' * node.level)
        self._write(node.module)
        self._write(' import ')
        self.visit(node.names[0])
        for name in node.names[1:]:
            self._write(', ')
            self.visit(name)

    # Exec(expr body, expr? globals, expr? locals)
    def visit_Exec(self, node):
        self._new_line()
        self._write('exec ')
        self.visit(node.body)
        if not node.globals:
            return
        self._write(', ')
        self.visit(node.globals)
        if not node.locals:
            return
        self._write(', ')
        self.visit(node.locals)

    # Global(identifier* names)
    def visit_Global(self, node):
        self._new_line()
        self._write('global ')
        self.visit(node.names[0])
        for name in node.names[1:]:
            self._write(', ')
            self.visit(name)

    # Expr(expr value)
    def visit_Expr(self, node):
        self._new_line()
        self.visit(node.value)

    # Pass
    def visit_Pass(self, node):
        self._new_line()
        self._write('pass')

    # Break
    def visit_Break(self, node):
        self._new_line()
        self._write('break')

    # Continue
    def visit_Continue(self, node):
        self._new_line()
        self._write('continue')

    ### EXPRESSIONS
    def with_parens(f):
        def _f(self, node):
            self._write('(')
            f(self, node)
            self._write(')')
        return _f

    bool_operators = {_ast.And: 'and', _ast.Or: 'or'}

    # BoolOp(boolop op, expr* values)
    @with_parens
    def visit_BoolOp(self, node):
        joiner = ' ' + self.bool_operators[node.op.__class__] + ' '
        self.visit(node.values[0])
        for value in node.values[1:]:
            self._write(joiner)
            self.visit(value)

    binary_operators = {
        _ast.Add: '+',
        _ast.Sub: '-',
        _ast.Mult: '*',
        _ast.Div: '/',
        _ast.Mod: '%',
        _ast.Pow: '**',
        _ast.LShift: '<<',
        _ast.RShift: '>>',
        _ast.BitOr: '|',
        _ast.BitXor: '^',
        _ast.BitAnd: '&',
        _ast.FloorDiv: '//'
    }

    # BinOp(expr left, operator op, expr right)
    @with_parens
    def visit_BinOp(self, node):
        self.visit(node.left)
        self._write(' ' + self.binary_operators[node.op.__class__] + ' ')
        self.visit(node.right)

    unary_operators = {
        _ast.Invert: '~',
        _ast.Not: 'not',
        _ast.UAdd: '+',
        _ast.USub: '-',
    }

    # UnaryOp(unaryop op, expr operand)
    def visit_UnaryOp(self, node):
        self._write(self.unary_operators[node.op.__class__] + ' ')
        self.visit(node.operand)

    # Lambda(arguments args, expr body)
    @with_parens
    def visit_Lambda(self, node):
        self._write('lambda ')
        self.visit(node.args)
        self._write(': ')
        self.visit(node.body)

    # IfExp(expr test, expr body, expr orelse)
    @with_parens
    def visit_IfExp(self, node):
        self.visit(node.body)
        self._write(' if ')
        self.visit(node.test)
        self._write(' else ')
        self.visit(node.orelse)

    # Dict(expr* keys, expr* values)
    def visit_Dict(self, node):
        self._write('{')
        for key, value in zip(node.keys, node.values):
            self.visit(key)
            self._write(': ')
            self.visit(value)
            self._write(', ')
        self._write('}')

    # ListComp(expr elt, comprehension* generators)
    def visit_ListComp(self, node):
        self._write('[')
        self.visit(node.elt)
        for generator in node.generators:
            # comprehension = (expr target, expr iter, expr* ifs)
            self._write(' for ')
            self.visit(generator.target)
            self._write(' in ')
            self.visit(generator.iter)
            for ifexpr in generator.ifs:
                self._write(' if ')
                self.visit(ifexpr)
        self._write(']')

    # GeneratorExp(expr elt, comprehension* generators)
    def visit_GeneratorExp(self, node):
        self._write('(')
        self.visit(node.elt)
        for generator in node.generators:
            # comprehension = (expr target, expr iter, expr* ifs)
            self._write(' for ')
            self.visit(generator.target)
            self._write(' in ')
            self.visit(generator.iter)
            for ifexpr in generator.ifs:
                self._write(' if ')
                self.visit(ifexpr)
        self._write(')')

    # Yield(expr? value)
    def visit_Yield(self, node):
        self._write('yield')
        if getattr(node, 'value', None):
            self._write(' ')
            self.visit(node.value)

    comparision_operators = {
        _ast.Eq: '==',
        _ast.NotEq: '!=',
        _ast.Lt: '<',
        _ast.LtE: '<=',
        _ast.Gt: '>',
        _ast.GtE: '>=',
        _ast.Is: 'is',
        _ast.IsNot: 'is not',
        _ast.In: 'in',
        _ast.NotIn: 'not in',
    }

    # Compare(expr left, cmpop* ops, expr* comparators)
    @with_parens
    def visit_Compare(self, node):
        self.visit(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            self._write(' ' + self.comparision_operators[op.__class__] + ' ')
            self.visit(comparator)

    # Call(expr func, expr* args, keyword* keywords,
    #                         expr? starargs, expr? kwargs)
    def visit_Call(self, node):
        self.visit(node.func)
        self._write('(')
        first = True
        for arg in node.args:
            if not first:
                self._write(', ')
            first = False
            self.visit(arg)

        for keyword in node.keywords:
            if not first:
                self._write(', ')
            first = False
            # keyword = (identifier arg, expr value)
            self._write(keyword.arg)
            self._write('=')
            self.visit(keyword.value)
        if getattr(node, 'starargs', None):
            if not first:
                self._write(', ')
            first = False
            self._write('*')
            self.visit(node.starargs)

        if getattr(node, 'kwargs', None):
            if not first:
                self._write(', ')
            first = False
            self._write('**')
            self.visit(node.kwargs)
        self._write(')')

    # Repr(expr value)
    def visit_Repr(self, node):
        self._write('`')
        self.visit(node.value)
        self._write('`')

    # Num(object n)
    def visit_Num(self, node):
        self._write(repr(node.n))

    # Str(string s)
    def visit_Str(self, node):
        self._write(repr(node.s))

    # Attribute(expr value, identifier attr, expr_context ctx)
    def visit_Attribute(self, node):
        self.visit(node.value)
        self._write('.')
        self._write(node.attr)

    # Subscript(expr value, slice slice, expr_context ctx)
    def visit_Subscript(self, node):
        self.visit(node.value)
        self._write('[')
        def _process_slice(node):
            if isinstance(node, _ast.Ellipsis):
                self._write('...')
            elif isinstance(node, _ast.Slice):
                if getattr(node, 'lower', 'None'):
                    self.visit(node.lower)
                self._write(':')
                if getattr(node, 'upper', None):
                    self.visit(node.upper)
                if getattr(node, 'step', None):
                    self._write(':')
                    self.visit(node.step)
            elif isinstance(node, _ast.Index):
                self.visit(node.value)
            elif isinstance(node, _ast.ExtSlice):
                self.visit(node.dims[0])
                for dim in node.dims[1:]:
                    self._write(', ')
                    self.visit(dim)
            else:
                raise NotImplemented('Slice type not implemented')
        _process_slice(node.slice)
        self._write(']')

    # Name(identifier id, expr_context ctx)
    def visit_Name(self, node):
        self._write(node.id)

    # List(expr* elts, expr_context ctx)
    def visit_List(self, node):
        self._write('[')
        for elt in node.elts:
            self.visit(elt)
            self._write(', ')
        self._write(']')

    # Tuple(expr *elts, expr_context ctx)
    def visit_Tuple(self, node):
        self._write('(')
        for elt in node.elts:
            self.visit(elt)
            self._write(', ')
        self._write(')')


class ASTTransformer(object):
    """General purpose base class for AST transformations.
    
    Every visitor method can be overridden to return an AST node that has been
    altered or replaced in some way.
    """

    def visit(self, node):
        if node is None:
            return None
        if type(node) is tuple:
            return tuple([self.visit(n) for n in node])
        visitor = getattr(self, 'visit_%s' % node.__class__.__name__, None)
        if visitor is None:
            return node
        return visitor(node)

    def _clone(self, node):
        clone = node.__class__()
        for name in getattr(clone, '_attributes', ()):
            try:
                setattr(clone, 'name', getattr(node, name))
            except AttributeError:
                pass
        for name in clone._fields:
            try:
                value = getattr(node, name)
            except AttributeError:
                pass
            else:
                if value is None:
                    pass
                elif isinstance(value, list):
                    value = [self.visit(x) for x in value]
                elif isinstance(value, tuple):
                    value = tuple(self.visit(x) for x in value)
                else: 
                    value = self.visit(value)
                setattr(clone, name, value)
        return clone

    visit_Module = _clone
    visit_Interactive = _clone
    visit_Expression = _clone
    visit_Suite = _clone

    visit_FunctionDef = _clone
    visit_ClassDef = _clone
    visit_Return = _clone
    visit_Delete = _clone
    visit_Assign = _clone
    visit_AugAssign = _clone
    visit_Print = _clone
    visit_For = _clone
    visit_While = _clone
    visit_If = _clone
    visit_With = _clone
    visit_Raise = _clone
    visit_TryExcept = _clone
    visit_TryFinally = _clone
    visit_Assert = _clone
    visit_ExceptHandler = _clone

    visit_Import = _clone
    visit_ImportFrom = _clone
    visit_Exec = _clone
    visit_Global = _clone
    visit_Expr = _clone
    # Pass, Break, Continue don't need to be copied

    visit_BoolOp = _clone
    visit_BinOp = _clone
    visit_UnaryOp = _clone
    visit_Lambda = _clone
    visit_IfExp = _clone
    visit_Dict = _clone
    visit_ListComp = _clone
    visit_GeneratorExp = _clone
    visit_Yield = _clone
    visit_Compare = _clone
    visit_Call = _clone
    visit_Repr = _clone
    # Num, Str don't need to be copied

    visit_Attribute = _clone
    visit_Subscript = _clone
    visit_Name = _clone
    visit_List = _clone
    visit_Tuple = _clone

    visit_comprehension = _clone
    visit_excepthandler = _clone
    visit_arguments = _clone
    visit_keyword = _clone
    visit_alias = _clone

    visit_Slice = _clone
    visit_ExtSlice = _clone
    visit_Index = _clone

    del _clone
