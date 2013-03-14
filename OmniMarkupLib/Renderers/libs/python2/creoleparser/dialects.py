# dialects.py
# -*- coding: utf-8 -*-
#
# Copyright © Stephen Day
#
# This module is part of Creoleparser and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
#

import warnings
import string, keyword

from elements import *
from core import ArgParser


def creepy10_base():
    """Returns a dialect object (a class) to be used by :class:`~creoleparser.core.ArgParser`


    **How it Works**

    The "Creepy" dialect uses a syntax that can look much like that of
    attribute definition in xml. The most important differences are that
    positional arguments are allowed and quoting is optional.

    A Creepy dialect object is normally passed to
    :class:`~creoleparser.core.ArgParser` to create a new parser object.
    When called with a single argument, this outputs a two-tuple
    (a list of positional arguments and a dictionary of keyword arguments):

    >>> from core import ArgParser
    >>> my_parser = ArgParser(dialect=creepy10_base(), convert_implicit_lists=False)
    >>> my_parser(" foo='one' ")
    ([], {'foo': 'one'})
    >>> my_parser("  'one' ")
    (['one'], {})
    >>> my_parser("  'one' foo='two' ")
    (['one'], {'foo': 'two'})

    Positional arguments must come before keyword arguments. If they occur
    after a keyword argument, they will be combined with that value as a list:
    
    >>> my_parser("  foo='one' 'two' ")
    ([], {'foo': ['one', 'two']})

    Similarly, if two or more keywords are the same, the values will be combined
    into a list:

    >>> my_parser("  foo='one' foo='two' ")
    ([], {'foo': ['one', 'two']})

    The lists above are known as "Implicit" lists. They can automatically be
    converted to strings by setting ``convert_implicit_lists=True`` in the
    parser.

    Quotes can be single or double:
    
    >>> my_parser(''' foo="it's okay" ''')
    ([], {'foo': "it's okay"})

    Tildes can be used for escaping:

    >>> my_parser(''' foo='it~'s okay' ''')
    ([], {'foo': "it's okay"})
    
    Quotes are optional if an argument value doesn't contain spaces or
    unescaped special characters:
    
    >>> my_parser("  one foo = two ")
    (['one'], {'foo': 'two'})

    Keyword arguments lacking a value will be interpreted as an empty string:

    >>> my_parser(" '' foo=  boo= '' ")
    ([''], {'foo': '', 'boo': ''})

    """
    
    class Base(ArgDialect):

       kw_arg = KeywordArg(token='=')
       quoted_arg = QuotedArg(token='\'"')
       spaces = WhiteSpace()

       def __init__(self):
          self.kw_arg.child_elements = [self.spaces]
          self.quoted_arg.child_elements = []
          self.spaces.child_elements = []

       @property
       def top_elements(self):
          return [self.quoted_arg, self.kw_arg, self.spaces]

    return Base



def creepy20_base():
    """Extends creepy10_base to support an explicit list argument syntax.

    >>> from core import ArgParser
    >>> my_parser = ArgParser(dialect=creepy20_base(),convert_implicit_lists=False)
    >>> my_parser(" one [two three] foo=['four' 'five'] ")
    (['one', ['two', 'three']], {'foo': ['four', 'five']})

    You can test if a list is explicit by testing its class:

    >>> from core import ImplicitList
    >>> pos, kw = my_parser("  foo=['one' 'two'] boo = 'three' 'four'")
    >>> print kw
    {'foo': ['one', 'two'], 'boo': ['three', 'four']}
    >>> isinstance(kw['foo'], ImplicitList)
    False
    >>> isinstance(kw['boo'], ImplicitList)
    True
    
    Lists of length zero or one are **never** of type ImplicitList.

    """

    Creepy10Base = creepy10_base()
    class Base(Creepy10Base):

       list_arg = ListArg(token=['[',']'])
       explicit_list_arg = ExplicitListArg(token=['[',']'])

       def __init__(self):
          super(Base,self).__init__()
          self.kw_arg.child_elements = [self.explicit_list_arg,self.spaces]
          self.list_arg.child_elements = [self.spaces]
          self.explicit_list_arg.child_elements = [self.spaces]

       @property
       def top_elements(self):
          return [self.quoted_arg, self.kw_arg, self.list_arg,self.spaces]

    return Base



class ArgDialect(object):
    """Base class for argument string dialect objects."""
    pass

parse_args = ArgParser(dialect=creepy10_base(),key_func=string.lower,
                       illegal_keys=keyword.kwlist + ['macro_name',
                         'arg_string', 'body', 'isblock', 'environ', 'macro'])
"""Function for parsing macro arg_strings using a relaxed xml style"""




def create_dialect(dialect_base, **kw_args):
    """Factory function for dialect objects (for parameter defaults,
    see :func:`~creoleparser.dialects.creole10_base` and/or
    :func:`~creoleparser.dialects.creole11_base`)

    :parameters:
      add_heading_ids
        If `True`, user friendly, lowercase, unique, id attributes will be
        automatically added to headings. To prevent clashes with other page
        ids, all will be prefixed with a "!". This prefix may be changed by
        passing a string rather than a boolean. *``environ`` needs to be a
        dicionary-like object for this to function*
        (see :meth:`creoleparser.core.Parser.parse`) and a key named `ids`
        will be added.
      argument_parser
        Parser used for automatic parsing of macro arg strings. Must take a
        single string argument and return a two-tuple with the first element
        a list (for positional arguments) and the second a dictionary (for
        keyword arguments). A default is supplied. Individual macros may
        override this parser by providing their own as a function attribute
        named `arg_parser`.
      blog_style_endings
        If `True`, each newline character in a paragraph will be converted to
        a <br />. Note that the escaping mechanism (tilde) does not work
        for newlines.
      bodied_macros
        Dictionary of macros (functions). If a bodied macro is found that is not
        in this dictionary, ``macro_func`` (below) will be called instead. Each
        function must accept the following positional arguments:

        1. macro object. This dictionary-like object has attributes
           ``macro_name``, ``body``,
           ``isblock``, and ``arg_string`` (see ``macro_func`` (below) for more
           information). Additionally, the macro object has a ``parsed_body()``
           method, that will return the parsed ``macro.body`` as a
           genshi.Fragment. ``parsed_body()`` takes an optional ``context``
           argument, that defaults to `auto`, see :meth:`creoleparser.core.Parser.parse`
           for other possible values.
        2. the `environ` object (see :meth:`creoleparser.core.Parser.parse`)

        If the found macro includes arguments, they will be included in
        the function call. Creoleparser will handle exceptions by returning an
        error message in place of the macro (possibly including a traceback).
        Python's syntax for accepting arbitrary arguments is often used for
        macros (e.g.,def mymacro(macro, env, \\*pos, \\**kw)).   

        For information on return values, see macro_func (below).
      non_bodied_macros
        Same as ``bodied_macros`` but used for non-bodied macros.        
      custom_markup
        List of tuples that can each define arbitrary custom wiki markup such
        as WikiWords and emoticons. Each tuple must have two elements,
        as follows:

        1. Compiled regular expression or string (*not* an re pattern) to match.
        2. Function that takes two postional arguments, as follows:

           1. the match object
           2. the `environ` object (see :meth:`creoleparser.core.Parser.parse`)

           The function must return a Genshi object (Stream, Markup,
           builder.Fragment, or builder.Element). Returning a string will
           raise an error.

        As a shortcut for simple cases, the second tuple element may be
        a string rather than a function. The string will be wrapped in a Markup
        object (to allow pass-through of HTML) and a Fragment object (to prevent
        Creoleparser from creating a new paragraph). 
      dialect_base
        The class factory to use for creating the dialect object.
        ``creoleparser.dialects.creole10_base`` and  
        ``creoleparser.dialects.creole11_base`` are possible values.
      disable_external_content
        If True, an error message will be inserted when an externally
        hosted image is found.
      external_links_class
        Class attribute to add to external links (i.e., not wiki or interwiki
        links).
      indent_class
        Class attribute to add to indented regions.
      indent_style
        Style attribute to add to indented regions.
      interwiki_links_base_urls
        Dictionary of urls for interwiki links. Works like
        ``wiki_links_base_url``.
      interwiki_links_class_funcs
        Dictionary of functions that will be called for interwiki link
        names and return class attributes. Works like
        ``wiki_links_class_func``.
      interwiki_links_path_funcs
        Dictionary of functions that will be called for interwiki link
        names and return url paths. Works like ``wiki_links_path_func``.
      interwiki_links_space_chars
        Dictionary of characters that that will be used to replace spaces
        that occur in interwiki_links. Works like ``wiki_links_space_char``.
        If no key is present for an interwiki name, the
        ``wiki_links_space_char`` will be used. 
      macro_func
        If supplied, this fuction will be called when macro markup is found,
        unless the macro is in one of macro dictionaries above. The
        function must accept the following postional arguments:
        
        1. macro name (string)
        2. the argument, including any delimter (string)
        3. the macro body (string or None for a macro without a body)
        4. macro type (boolean, True for block macros, False for normal macros)
        5. the `environ` object (see :meth:`creoleparser.core.Parser.parse`)
        
        The function may return a string (which will be subject to further wiki
        processing) or a Genshi object (Stream, Markup, builder.Fragment, or
        builder.Element). If None is
        returned, the markup will be rendered unchanged.
      no_wiki_monospace
        If `False`, inline no_wiki will be rendered as <span> not <code>
      simple_markup
        List of tuples that each define markup such as `strong` and `em`
        that can nest. Each tuple must have two elements, as follows:

        1. String to match start and end of text to be enclosed. 
        2. HTML tag

      wiki_links_base_url
        The page name found in wiki links will be smartly appended to this to
        form the href. To use a different base url for images, supply a two
        element list; the second element will be used.
      wiki_links_class_func
        If supplied, this fuction will be called when a wiki link is found and
        the return value (should be a string) will be added as a class attribute
        of the corresponding link. The function must accept the page name (any
        spaces will have been replaced) as it's only argument.
        If no class attribute is to be added, return `None`.
      wiki_links_path_func
        If supplied, this fuction will be called when a wiki link is found and
        the return value (should be a string) will be joined to the base_url
        to form the url for href. The function must accept the page name (any
        spaces will have been replaced) as it's only argument. Special characters
        should be url encoded. To use a different function for images, supply a
        two element list; the second element will be used.
      wiki_links_space_char
        When wiki_links have spaces, this character replaces those spaces in
        the url. To use a different character for images, supply a two element
        list; the second element will be used.
 
    """

    if 'interwiki_links_funcs' in kw_args:
        warnings.warn("""
The "interwiki_links_funcs" parameter has been renamed
to "interwiki_links_path_funcs"
""")
        kw_args.setdefault('interwiki_links_path_funcs',kw_args.pop('interwiki_links_funcs'))
    return dialect_base(**kw_args)



def creole10_base(wiki_links_base_url='',wiki_links_space_char='_',
                 interwiki_links_base_urls={},
                 no_wiki_monospace=True,
                 wiki_links_class_func=None, external_links_class=None,
                 wiki_links_path_func=None, interwiki_links_path_funcs={},
                 interwiki_links_class_funcs={},interwiki_links_space_chars={},
                 blog_style_endings=False,
                 disable_external_content=False,
                 custom_markup=[],
                 simple_markup=[('**','strong'),('//','em')],
                 add_heading_ids=False 
                 ):
    """Returns a base class for extending
    (for parameter descriptions, see :func:`~creoleparser.dialects.create_dialect`)

    The returned class does not implement any of the proposed additions to
    to Creole 1.0 specification.

    """
    
    if isinstance(wiki_links_base_url,(list, tuple)):
        wiki_links_base_url, embed_base_url = wiki_links_base_url
    else:
        embed_base_url = wiki_links_base_url
    if isinstance(wiki_links_path_func,(list, tuple)):
        wiki_links_path_func, embed_path_func = wiki_links_path_func
    else:
        embed_path_func = wiki_links_path_func
    if isinstance(wiki_links_space_char,(list, tuple)):
        wiki_links_space_char, embed_space_char = wiki_links_space_char
    else:
        embed_space_char = wiki_links_space_char

    embed_interwiki_base_urls = {}
    for k,v in interwiki_links_base_urls.items():
        if isinstance(v,(list, tuple)):
            interwiki_links_base_urls[k], embed_interwiki_base_urls[k] = v
        else:
            embed_interwiki_base_urls[k] = v
    embed_interwiki_path_funcs = {}
    for k,v in interwiki_links_path_funcs.items():
        if isinstance(v,(list, tuple)):
            interwiki_links_path_funcs[k], embed_interwiki_path_funcs[k] = v
        else:
            embed_interwiki_path_funcs[k] = v
    embed_interwiki_space_chars = {}
    for k,v in interwiki_links_space_chars.items():
        if isinstance(v,(list, tuple)):
            interwiki_links_space_chars[k], embed_interwiki_space_chars[k] = v
        else:
            embed_interwiki_space_chars[k] = v
            
    id_prefix=add_heading_ids is True and '!' or add_heading_ids
    if id_prefix is False:
        fragment_pattern = None
    else:
        fragment_pattern = '#' + re.escape(id_prefix) + r'[a-z0-9-_]+'
      
    class Base(Dialect):

        br = LineBreak('br', r'\\',blog_style=blog_style_endings)
        headings = Heading(['h1','h2','h3','h4','h5','h6'],'=', id_prefix=id_prefix)
        no_wiki = NoWikiElement(no_wiki_monospace and 'code' or 'span',['{{{','}}}'])
        simple_element = SimpleElement(token_dict=dict(simple_markup))
        hr = HrElement()
        blank_line = BlankLine()
        p = Paragraph('p')
        pre = PreBlock('pre',['{{{','}}}'])
        raw_link = RawLink('a')
        link = AnchorElement('a',('[[',']]'),delimiter = '|',interwiki_delimiter=':',
                                            base_urls=interwiki_links_base_urls,
                                            links_funcs=interwiki_links_path_funcs,
                                            interwiki_class_funcs=interwiki_links_class_funcs, 
                                            default_space_char=wiki_links_space_char,
                                            space_chars=interwiki_links_space_chars,
                                       base_url=wiki_links_base_url,
                              space_char=wiki_links_space_char,class_func=wiki_links_class_func,
                              path_func=wiki_links_path_func,fragment_pattern=fragment_pattern,
                             external_links_class=external_links_class)
                             

        img = ImageElement('img',('{{','}}'),delimiter = '|',interwiki_delimiter=':',
                                            base_urls=embed_interwiki_base_urls,
                                            links_funcs=embed_interwiki_path_funcs,
                                            interwiki_class_funcs=interwiki_links_class_funcs, 
                                            default_space_char=embed_space_char,
                                            space_chars=embed_interwiki_space_chars,
                                       base_url=embed_base_url,
                              space_char=embed_space_char,class_func=wiki_links_class_func,
                              path_func=embed_path_func,fragment_pattern=fragment_pattern,
                              disable_external=disable_external_content)        


        td = TableCell('td','|')
        th = TableCell('th','|=')
        tr = TableRow('tr','|')
        table = Table('table','|')

        li = ListItem('li',list_tokens='*#')
        ol = List('ol','#',stop_tokens='*')
        ul = List('ul','*',stop_tokens='#')
        nested_ol = NestedList('ol','#')
        nested_ul = NestedList('ul','*')

        custom_elements = [CustomElement(reg_exp, func) for reg_exp, func in custom_markup] 

        def __init__(self):
            self.link.child_elements = [self.simple_element]
            self.simple_element.child_elements = [self.simple_element]
            self.headings.child_elements = self.inline_elements
            self.p.child_elements = self.inline_elements
            self.td.child_elements = [self.br, self.raw_link, self.simple_element]
            self.th.child_elements = [self.br, self.raw_link, self.simple_element]
            self.tr.child_elements = [self.no_wiki,self.img,self.link,self.custom_elements,self.th,self.td]
            self.table.child_elements = [self.tr]
            self.ol.child_elements = [self.li]
            self.ul.child_elements = [self.li]
            self.nested_ol.child_elements = [self.li]
            self.nested_ul.child_elements = [self.li]
            self.li.child_elements = [(self.nested_ol,self.nested_ul)] + self.inline_elements

        @property 
        def inline_elements(self):
            return [self.no_wiki, self.img, self.link] + self.custom_elements \
                   + [self.br, self.raw_link, self.simple_element]

        @property 
        def block_elements(self):
            return [self.pre,self.blank_line,self.table,self.headings,
                               self.hr,self.ul,self.ol,self.p]
            """self.block_elements are the wiki elements that are searched at the top level of text to be
            processed. The order matters because elements later in the list need not have any
            knowledge of those before (as those were parsed out already). This makes the
            regular expression patterns for later elements very simple.
            """        



    return Base



def creole11_base(macro_func=None,
                  indent_class=None,
                  indent_style='margin-left:2em',
                  simple_markup=[('**','strong'),('//','em'),(',,','sub'),
                                 ('^^','sup'),('__','u'),('##','code')],
                  non_bodied_macros={},
                  bodied_macros={}, 
                  argument_parser=parse_args, 
                  **kwargs):
    """Returns a base class for extending (for parameter descriptions, see :func:`~creoleparser.dialects.create_dialect`)

    The returned class implements most of the *officially* proposed additions to
    to Creole 1.0 specification:

        * superscript, subscript, underline, and monospace
        * definition lists
        * indentation
        * macros
            
        (see http://purl.oclc.org/creoleparser/cheatsheet)

   **A Basic Extending Example**

   Extending Creoleparser through subclassing is usually only needed when
   custom WikiElement objects are incorporated. However, it is also
   needed for other special jobs, like entirely disabling certain markup.
   Here we create a dialect that removes image support::

       >>> Base = creole11_base()
       >>> class MyDialect(Base):
       ...     @property
       ...     def inline_elements(self):
       ...         l = super(MyDialect,self).inline_elements
       ...         l.remove(self.img)
       ...         return l
       >>> from core import Parser
       >>> parser = Parser(MyDialect) 
       >>> print parser.render("{{this}} is not an image!"),
       <p>{{this}} is not an image!</p>
           
   For a more complex example, see the `source code
   <http://code.google.com/p/creoleparser/source/browse/trunk/creoleparser/dialects.py>`_
   of this function. It extends the class created from creole10_base().

   .. note::

       It is generally safest to create only one dialect class per base
       class. This is because WikiElement objects are bound as class
       attributes and would therefor be shared between multiple instances,
       which could lead to unexpected behaviour.

    
    """
    
    Creole10Base = creole10_base(simple_markup=simple_markup, **kwargs)
    
    class Base(Creole10Base):
        
        indented = IndentedBlock('div','>', class_=indent_class, style=indent_style)
        
        dd = DefinitionDef('dd',':')
        dt = DefinitionTerm('dt',';',stop_token=':')
        dl = List('dl',';',stop_tokens='*#')

        macro = Macro('',('<<','>>'),func=macro_func, macros=non_bodied_macros,
                      arg_parser= argument_parser)
        bodiedmacro = BodiedMacro('',('<<','>>'),func=macro_func,
                                  macros=bodied_macros, arg_parser= argument_parser)
        bodied_block_macro = BodiedBlockMacro('',('<<','>>'),func=macro_func,
                                              macros=bodied_macros,arg_parser= argument_parser)    

        def __init__(self):
            super(Base,self).__init__()
            self.tr.child_elements[0] = (self.no_wiki,self.bodiedmacro,self.macro)
            self.dd.child_elements = self.custom_elements + [self.br, self.raw_link, self.simple_element]
            self.dt.child_elements = self.custom_elements + [self.br, self.raw_link, self.simple_element]
            self.dl.child_elements = [(self.no_wiki,self.bodiedmacro,self.macro),self.img,self.link,self.dt,self.dd]
            self.indented.child_elements = self.block_elements
            self.bodiedmacro.dialect = self
            self.bodied_block_macro.dialect = self
            
        @property 
        def inline_elements(self):
            return [(self.no_wiki,self.bodiedmacro,self.macro), self.img,
                    self.link] + self.custom_elements + [self.br, self.raw_link,
                    self.simple_element]

        @property 
        def block_elements(self):
            return [(self.bodied_block_macro,self.pre),self.blank_line,self.table,self.headings,
                           self.hr,self.indented,self.dl,self.ul,self.ol,self.p]
        
    return Base



class Dialect(object):
    """Base class for dialect objects."""
    pass


 
def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()    
