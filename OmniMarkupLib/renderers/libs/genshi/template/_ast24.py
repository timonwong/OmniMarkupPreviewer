# Generated automatically, please do not edit
# Generator can be found in Genshi SVN, scripts/ast-generator.py

__version__ = 43614

class AST(object):
	_fields = None
	__doc__ = None

class operator(AST):
	_fields = None
	__doc__ = None
	_attributes = []
class Add(operator):
	_fields = None
	__doc__ = None

class boolop(AST):
	_fields = None
	__doc__ = None
	_attributes = []
class And(boolop):
	_fields = None
	__doc__ = None

class stmt(AST):
	_fields = None
	__doc__ = None
	_attributes = ['lineno', 'col_offset']
class Assert(stmt):
	_fields = ('test', 'msg')
	__doc__ = None

class Assign(stmt):
	_fields = ('targets', 'value')
	__doc__ = None

class expr(AST):
	_fields = None
	__doc__ = None
	_attributes = ['lineno', 'col_offset']
class Attribute(expr):
	_fields = ('value', 'attr', 'ctx')
	__doc__ = None

class AugAssign(stmt):
	_fields = ('target', 'op', 'value')
	__doc__ = None

class expr_context(AST):
	_fields = None
	__doc__ = None
	_attributes = []
class AugLoad(expr_context):
	_fields = None
	__doc__ = None

class AugStore(expr_context):
	_fields = None
	__doc__ = None

class BinOp(expr):
	_fields = ('left', 'op', 'right')
	__doc__ = None

class BitAnd(operator):
	_fields = None
	__doc__ = None

class BitOr(operator):
	_fields = None
	__doc__ = None

class BitXor(operator):
	_fields = None
	__doc__ = None

class BoolOp(expr):
	_fields = ('op', 'values')
	__doc__ = None

class Break(stmt):
	_fields = None
	__doc__ = None

class Call(expr):
	_fields = ('func', 'args', 'keywords', 'starargs', 'kwargs')
	__doc__ = None

class ClassDef(stmt):
	_fields = ('name', 'bases', 'body')
	__doc__ = None

class Compare(expr):
	_fields = ('left', 'ops', 'comparators')
	__doc__ = None

class Continue(stmt):
	_fields = None
	__doc__ = None

class Del(expr_context):
	_fields = None
	__doc__ = None

class Delete(stmt):
	_fields = ('targets',)
	__doc__ = None

class Dict(expr):
	_fields = ('keys', 'values')
	__doc__ = None

class Div(operator):
	_fields = None
	__doc__ = None

class slice(AST):
	_fields = None
	__doc__ = None
	_attributes = []
class Ellipsis(slice):
	_fields = None
	__doc__ = None

class cmpop(AST):
	_fields = None
	__doc__ = None
	_attributes = []
class Eq(cmpop):
	_fields = None
	__doc__ = None

class Exec(stmt):
	_fields = ('body', 'globals', 'locals')
	__doc__ = None

class Expr(stmt):
	_fields = ('value',)
	__doc__ = None

class mod(AST):
	_fields = None
	__doc__ = None
	_attributes = []
class Expression(mod):
	_fields = ('body',)
	__doc__ = None

class ExtSlice(slice):
	_fields = ('dims',)
	__doc__ = None

class FloorDiv(operator):
	_fields = None
	__doc__ = None

class For(stmt):
	_fields = ('target', 'iter', 'body', 'orelse')
	__doc__ = None

class FunctionDef(stmt):
	_fields = ('name', 'args', 'body', 'decorators')
	__doc__ = None

class GeneratorExp(expr):
	_fields = ('elt', 'generators')
	__doc__ = None

class Global(stmt):
	_fields = ('names',)
	__doc__ = None

class Gt(cmpop):
	_fields = None
	__doc__ = None

class GtE(cmpop):
	_fields = None
	__doc__ = None

class If(stmt):
	_fields = ('test', 'body', 'orelse')
	__doc__ = None

class IfExp(expr):
	_fields = ('test', 'body', 'orelse')
	__doc__ = None

class Import(stmt):
	_fields = ('names',)
	__doc__ = None

class ImportFrom(stmt):
	_fields = ('module', 'names', 'level')
	__doc__ = None

class In(cmpop):
	_fields = None
	__doc__ = None

class Index(slice):
	_fields = ('value',)
	__doc__ = None

class Interactive(mod):
	_fields = ('body',)
	__doc__ = None

class unaryop(AST):
	_fields = None
	__doc__ = None
	_attributes = []
class Invert(unaryop):
	_fields = None
	__doc__ = None

class Is(cmpop):
	_fields = None
	__doc__ = None

class IsNot(cmpop):
	_fields = None
	__doc__ = None

class LShift(operator):
	_fields = None
	__doc__ = None

class Lambda(expr):
	_fields = ('args', 'body')
	__doc__ = None

class List(expr):
	_fields = ('elts', 'ctx')
	__doc__ = None

class ListComp(expr):
	_fields = ('elt', 'generators')
	__doc__ = None

class Load(expr_context):
	_fields = None
	__doc__ = None

class Lt(cmpop):
	_fields = None
	__doc__ = None

class LtE(cmpop):
	_fields = None
	__doc__ = None

class Mod(operator):
	_fields = None
	__doc__ = None

class Module(mod):
	_fields = ('body',)
	__doc__ = None

class Mult(operator):
	_fields = None
	__doc__ = None

class Name(expr):
	_fields = ('id', 'ctx')
	__doc__ = None

class Not(unaryop):
	_fields = None
	__doc__ = None

class NotEq(cmpop):
	_fields = None
	__doc__ = None

class NotIn(cmpop):
	_fields = None
	__doc__ = None

class Num(expr):
	_fields = ('n',)
	__doc__ = None

class Or(boolop):
	_fields = None
	__doc__ = None

class Param(expr_context):
	_fields = None
	__doc__ = None

class Pass(stmt):
	_fields = None
	__doc__ = None

class Pow(operator):
	_fields = None
	__doc__ = None

class Print(stmt):
	_fields = ('dest', 'values', 'nl')
	__doc__ = None

class RShift(operator):
	_fields = None
	__doc__ = None

class Raise(stmt):
	_fields = ('type', 'inst', 'tback')
	__doc__ = None

class Repr(expr):
	_fields = ('value',)
	__doc__ = None

class Return(stmt):
	_fields = ('value',)
	__doc__ = None

class Slice(slice):
	_fields = ('lower', 'upper', 'step')
	__doc__ = None

class Store(expr_context):
	_fields = None
	__doc__ = None

class Str(expr):
	_fields = ('s',)
	__doc__ = None

class Sub(operator):
	_fields = None
	__doc__ = None

class Subscript(expr):
	_fields = ('value', 'slice', 'ctx')
	__doc__ = None

class Suite(mod):
	_fields = ('body',)
	__doc__ = None

class TryExcept(stmt):
	_fields = ('body', 'handlers', 'orelse')
	__doc__ = None

class TryFinally(stmt):
	_fields = ('body', 'finalbody')
	__doc__ = None

class Tuple(expr):
	_fields = ('elts', 'ctx')
	__doc__ = None

class UAdd(unaryop):
	_fields = None
	__doc__ = None

class USub(unaryop):
	_fields = None
	__doc__ = None

class UnaryOp(expr):
	_fields = ('op', 'operand')
	__doc__ = None

class While(stmt):
	_fields = ('test', 'body', 'orelse')
	__doc__ = None

class With(stmt):
	_fields = ('context_expr', 'optional_vars', 'body')
	__doc__ = None

class Yield(expr):
	_fields = ('value',)
	__doc__ = None

class alias(AST):
	_fields = ('name', 'asname')
	__doc__ = None

class arguments(AST):
	_fields = ('args', 'vararg', 'kwarg', 'defaults')
	__doc__ = None

class boolop(AST):
	_fields = None
	__doc__ = None
	_attributes = []

class cmpop(AST):
	_fields = None
	__doc__ = None
	_attributes = []

class comprehension(AST):
	_fields = ('target', 'iter', 'ifs')
	__doc__ = None

class excepthandler(AST):
	_fields = ('type', 'name', 'body', 'lineno', 'col_offset')
	__doc__ = None

class expr(AST):
	_fields = None
	__doc__ = None
	_attributes = ['lineno', 'col_offset']

class expr_context(AST):
	_fields = None
	__doc__ = None
	_attributes = []

class keyword(AST):
	_fields = ('arg', 'value')
	__doc__ = None

class mod(AST):
	_fields = None
	__doc__ = None
	_attributes = []

class operator(AST):
	_fields = None
	__doc__ = None
	_attributes = []

class slice(AST):
	_fields = None
	__doc__ = None
	_attributes = []

class stmt(AST):
	_fields = None
	__doc__ = None
	_attributes = ['lineno', 'col_offset']

class unaryop(AST):
	_fields = None
	__doc__ = None
	_attributes = []

