# core.py
# -*- coding: utf-8 -*-
#
# Copyright © Stephen Day
#
# This module is part of Creoleparser and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
#

import re
import warnings

import genshi.builder as bldr

__docformat__ = 'restructuredtext en'

escape_char = '~'
esc_neg_look = '(?<!' + re.escape(escape_char) + ')'
esc_to_remove = re.compile(''.join([r'(?<!',re.escape(escape_char),')',re.escape(escape_char),r'(?!([ \n]|$))']))
place_holder_re = re.compile(r'<<<(-?\d+?)>>>')


class Parser(object):
    
    def __init__(self,dialect, method='xhtml', strip_whitespace=False, encoding='utf-8'):
        """Constructor for Parser objects

        :parameters:
          dialect
            Usually created using :func:`creoleparser.dialects.create_dialect`
          method
            This value is passed to Genshies Steam.render(). Possible values
            include ``xhtml``, ``html``, ``xml``, and ``text``.
          strip_whitespace
            This value is passed to Genshies Steam.render().
          encoding
            This value is passed to Genshies Steam.render(). If ``None``, the ouput
            will be a unicode object.
            
        """
    
        if isinstance(dialect,type):
            self.dialect = dialect()
        else:
            warnings.warn("""
'dialect' should be a type object.
"""
                  )
            self.dialect = dialect
        self.method = method
        self.strip_whitespace = strip_whitespace
        self.encoding=encoding


    def parse(self,text,element_store=None,context='block', environ=None, preprocess=True):
        """Returns a Genshi Fragment (basically a list of Elements and text nodes).

        :parameters:
          text
            The text to be parsed.
          context
            This is useful for marco development where (for example) supression
            of paragraph tags is desired. Can be 'inline', 'block', or a list
            of WikiElement objects (use with caution).
          element_store
            Internal dictionary that's passed around a lot ;)
          environ
            This can be any type of object. It will be passed to ``macro_func``
            unchanged (for a description of ``macro_func``, see
            :func:`~creoleparser.dialects.create_dialect`).
          preprocess
            Passes text through preprocess method that replaces Windows style
            line breaks.
            
        """
        
        if element_store is None:
            element_store = {}
        if environ is None:
            environ = {}
        if not isinstance(context,list):
            if context == 'block':
                top_level_elements = self.dialect.block_elements
            elif context == 'inline':
                top_level_elements = self.dialect.inline_elements
        else:
            top_level_elements = context

        if preprocess:
            text = self.preprocess(text)

        return bldr.tag(fragmentize(text,top_level_elements,element_store, environ))



    def generate(self,text,element_store=None,context='block', environ=None, preprocess=True):
        """Returns a Genshi Stream. See
        :meth:`~creoleparser.core.Parser.parse` for named parameter descriptions.

        """

        return self.parse(text, element_store, context, environ, preprocess).generate()


    def render(self, text, element_store=None, context='block', environ=None, preprocess=True, **kwargs):
        """Returns the final output string (e.g., xhtml). See
        :meth:`~creoleparser.core.Parser.parse` for named parameter descriptions.

        Left over keyword arguments (``kwargs``) will be passed to Genshi's Stream.render() method,
        overriding the corresponding attributes of the Parser object. For more infomation on Streams,
        see the `Genshi documentation <http://genshi.edgewall.org/wiki/Documentation/streams.html#serialization-options>`_.
        
        """

        kwargs.setdefault('method',self.method)
        kwargs.setdefault('encoding',self.encoding)
        if kwargs['method'] != "text":
            kwargs.setdefault('strip_whitespace',self.strip_whitespace)
        stream = self.generate(text, element_store, context, environ, preprocess)
        return stream.render(**kwargs)

    def __call__(self,text, **kwargs):
        """Wrapper for the render method. Returns final output string.

        """

        return self.render(text, **kwargs)

    def preprocess(self,text):
        """This should generally be called before fragmentize().

        :parameter text: text to be processsed.

        """
        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        return text    



class ArgParser(object):
    """Creates a callable object for parsing macro argument strings

    >>> from dialects import creepy20_base
    >>> my_parser = ArgParser(dialect=creepy20_base())
    >>> my_parser(" one two foo='three' boo='four' ")
    (['one', 'two'], {'foo': 'three', 'boo': 'four'})
 
    A parser returns a two-tuple, the first item being a list of positional
    arguments and the second a dictionary of keyword arguments. Argument
    values are either strings or lists.
    
    """
    
    def __init__(self,dialect, convert_implicit_lists=True,
                 key_func=None, illegal_keys=(), convert_unicode_keys=True):
        """Constructor for ArgParser objects

        :parameters:
          convert_unicode_keys
            If *True*, keys will be converted using ``str(key)`` before being
            added to the output dictionary. This allows the dictionary to be
            safely passed to functions using the special ``**`` form (i.e.,
            ``func(**kwargs)``).
          dialect
            Usually created using :func:`~creoleparser.dialects.creepy10_base`
            or :func:`~creoleparser.dialects.creepy20_base`
          convert_implicit_lists
            If *True*, all implicit lists will be converted to strings
            using ``' '.join(list)``. "Implicit" lists are created when
            positional arguments follow keyword arguments
            (see :func:`~creoleparser.dialects.creepy10_base`). 
          illegal_keys
            A tuple of keys that will be post-fixed with an underscore if found
            during parsing. 
          key_func
            If supplied, this function will be used to transform the names of
            keyword arguments. It must accept a single positional argument.
            For example, this can be used to make keywords case insensitive:
            
            >>> from string import lower
            >>> from dialects import creepy20_base
            >>> my_parser = ArgParser(dialect=creepy20_base(),key_func=lower)
            >>> my_parser(" Foo='one' ")
            ([], {'foo': 'one'})
            
        """
    
        self.dialect = dialect()
        self.convert_implicit_lists = convert_implicit_lists
        self.key_func = key_func
        self.illegal_keys = illegal_keys
        self.convert_unicode_keys = convert_unicode_keys


    def __call__(self, arg_string, **kwargs): 
        """Parses the ``arg_string`` returning a two-tuple 

        Keyword arguments (``kwargs``) can be used to override the corresponding
        attributes of the ArgParser object (see above). However, the
        ``dialect`` attribute **cannot** be overridden.
        
        """
        
        kwargs.setdefault('convert_implicit_lists',self.convert_implicit_lists)
        kwargs.setdefault('key_func',self.key_func)
        kwargs.setdefault('illegal_keys',self.illegal_keys)
        kwargs.setdefault('convert_unicode_keys',self.convert_unicode_keys)

        return self._parse(arg_string,**kwargs)


    def _parse(self,arg_string, convert_implicit_lists, key_func, illegal_keys,
               convert_unicode_keys):
        
        frags = fragmentize(arg_string,self.dialect.top_elements,{},{})
        positional_args = []
        kw_args = {}
        for arg in frags:
           if isinstance(arg,tuple):
             k, v  = arg
             if convert_unicode_keys:
                 k = str(k)
             if key_func:
                 k =  key_func(k)
             if k in illegal_keys:
                 k = k + '_'
             if k in kw_args:
                if isinstance(v,list):
                   try:
                      kw_args[k].extend(v)
                   except AttributeError:
                      v.insert(0,kw_args[k])
                      kw_args[k] = v
                elif isinstance(kw_args[k],list):
                   kw_args[k].append(v)
                else:
                   kw_args[k] = [kw_args[k], v]
                kw_args[k] = ImplicitList(kw_args[k])
             else:
                kw_args[k] = v
             if isinstance(kw_args[k],ImplicitList) and convert_implicit_lists:
                 kw_args[k] = ' ' .join(kw_args[k])
           else:
             positional_args.append(arg)

        return (positional_args, kw_args)
        



def fragmentize(text,wiki_elements, element_store, environ, remove_escapes=True):

    """Takes a string of wiki markup and outputs a list of genshi
    Fragments (Elements and strings).

    This recursive function, with help from the WikiElement objects,
    does almost all the parsing.

    When no WikiElement objects are supplied, escapes are removed from
    ``text`` (except if remove_escapes=True)  and it is
    returned as-is. This is the only way for recursion to stop.

    :parameters:
      text
        the text to be parsed
      wiki_elements
        list of WikiElement objects to be searched for
      environ
        object that may by used by macros
      remove_escapes
        If False, escapes will not be removed
    
    """

    while wiki_elements:
        # If the first supplied wiki_element is actually a list of elements, \
        # search for all of them and match the closest one only.
        if isinstance(wiki_elements[0],(list,tuple)):
            x = None
            mos = None
            for element in wiki_elements[0]:
                mo = element.regexp.search(text)
                if mo:
                    if x is None or mo.start() < x:
                        x,wiki_element,mos = mo.start(),element,[mo]
        else:
            wiki_element = wiki_elements[0]
            mos = [mo for mo in wiki_element.regexp.finditer(text)]
             
        if mos:
            frags = wiki_element._process(mos, text, wiki_elements, element_store, environ)
            break
        else:
            wiki_elements = wiki_elements[1:]

    # remove escape characters 
    else: 
        if remove_escapes:
            text = esc_to_remove.sub('',text)
        frags = fill_from_store(text,element_store)
        
    return frags


def fill_from_store(text,element_store):
    frags = []
    mos = place_holder_re.finditer(text)
    start = 0
    for mo in mos:
        if mo.start() > start:
            frags.append(text[start:mo.start()])
        frags.append(element_store.get(mo.group(1),
                       mo.group(1).join(['<<<','>>>'])))
        start = mo.end()
    if start < len(text):
        frags.append(text[start:])
    return frags


class ImplicitList(list):
    """This class marks argument lists as implicit"""
    pass

class AttrDict(dict):
    def __getattr__(self, attr):
        return self[attr] 

        
class MacroError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()

