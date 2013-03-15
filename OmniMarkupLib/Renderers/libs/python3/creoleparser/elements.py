# elements.py
# -*- coding: utf-8 -*-
#
# Copyright © Stephen Day
#
# This module is part of Creoleparser and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
#

import re
import urllib.parse
import urllib.request, urllib.parse, urllib.error
import keyword
import warnings
import traceback
import unicodedata

import genshi.builder as bldr
from genshi.core import Stream, Markup

from .core import (escape_char, esc_neg_look, fragmentize,
                  ImplicitList, AttrDict, MacroError) 

BLOCK_ONLY_TAGS = ['h1','h2','h3','h4','h5','h6',
              'ul','ol','dl',
              'pre','hr','blockquote','address',
              'p','div','form','fieldset','table',
              'noscript']

BLOCK_TAGS = BLOCK_ONLY_TAGS + ['ins','del','script']

MACRO_NAME = r'(?P<name>[a-zA-Z][a-zA-Z0-9]*([-.][a-zA-Z0-9]+)*)'
"""allows any number of non-repeating hyphens or periods.
Underscore is not included because hyphen is"""


# use Genshi's HTMLSanitizer if possible (i.e., not on Google App Engine)
try:
    from genshi.filters import HTMLSanitizer
except:
    SAFE_SCHEMES = frozenset(['file', 'ftp', 'http', 'https', 'mailto', None])
    class HTMLSanitizer(object):
        def is_safe_uri(self,uri):
            if ':' not in uri:
                return True # This is a relative URI
            chars = [char for char in uri.split(':', 1)[0] if char.isalnum()]
            return ''.join(chars).lower() in SAFE_SCHEMES

sanitizer = HTMLSanitizer()

__docformat__ = 'restructuredtext en'

class WikiElement(object):
    
    """Baseclass for all wiki elements."""
    
    append_newline = False
    """Determines if newlines are appended to Element(s) during processing.
    Should only affect readability of source xml.
    """
    
    def __init__(self, tag, token, child_elements=None):
        """Constructor for WikiElement objects.

        Subclasses may have other keyword arguments.   

        :parameters:
          tag
            The xhtml tag associated with the element.
          token
            The character string (or strings) that identifies the element
            in wiki markup.
          child_elements
            A list of wiki_elements that will be searched for in the body of the
            element.  The order of these elements matters, because if an element is
            found before the element that encloses it, the enclosing element will
            never be found.  In cases where this imposes limits (e.g, ``strong`` and
            ``em`` should be allowed to nest each other), place the conflicting
            elements in a sublist. The parser will then find which comes first.
        """
        self.tag = tag
        self.token = token
        if child_elements is None:
            child_elements = []
        self.child_elements = child_elements


    def _build(self,mo,element_store, environ):
        """Returns a genshi Element that has ``self.tag`` as the
        outermost tag.

        This methods if called exclusively by ``_process``

        :parameters:
          mo
            match object, usually the one returned by
            self.regexp.search(s) 
        """
        return bldr.tag.__getattr__(self.tag)(fragmentize(mo.group(1),
                                                          self.child_elements,
                                                          element_store, environ))

    def re_string(self):
        """The regular expression pattern that is compiled into ``self.regexp``.

        The regular expression must consume the entire wiki element,
        including the tokens. For block elements, the newline on the last
        line must be consumed also. group(1) should normally be the
        entire string inside the tokens. If not, a custom ``_build``
        method will be needed.
        """
        pass

        
    def __repr__(self):
        return "<"+self.__class__.__name__ + " " + str(self.tag)+">"



    def _process(self, mos, text, wiki_elements,element_store, environ):
        """Returns genshi Fragments (Elements and text)

        This is mainly for block level markup. See InlineElement
        for the other method.
        """
        frags = []
        end = 0
        for mo in mos:
            if end != mo.start():
            # call again for leading text and extend the result list 
                frags.extend(fragmentize(text[end:mo.start()],wiki_elements[1:],
                                         element_store, environ))
            # append the found wiki element to the result list
            built = self._build(mo,element_store, environ)
            if built is not None:
                frags.append(built)
            # make the source output easier to read
            if self.append_newline:
                frags.append('\n')
            end = mo.end()
        # call again for trailing text and extend the result list
        if end < len(text):
            if not isinstance(wiki_elements[0],(list,tuple)):
                wiki_elements = wiki_elements[1:]
            frags.extend(fragmentize(text[end:],wiki_elements,
                                         element_store, environ))

        return frags


class BlockElement(WikiElement):

    """Block elements inherit form this class

    Wiki elements wanting ``append_newline = True`` should use this
    as the base also.

    """

    append_newline = True
    

class InlineElement(WikiElement):

    r"""For finding generic inline elements

    >>> em = InlineElement('em','//')
    >>> mo1 = em.regexp.search('a //word// in a line')
    >>> mo2 = em.regexp.search('a //word in a line\n or two\n')
    >>> mo1.group(0),mo1.group(1)
    ('//word//', 'word')
    >>> mo2.group(0),mo2.group(1)
    ('//word in a line\n or two', 'word in a line\n or two')

    Use a list for the ``token`` argument to have different start
    and end strings. These must be closed.

    >>> foo = InlineElement('foo',['<<','>>'])
    >>> mo = foo.regexp.search('blaa <<here it is >>\n')
    >>> mo.group(1)
    'here it is '
        
    """

    def __init__(self, tag='', token=''):
        super(InlineElement,self).__init__(tag,token)
        self.regexp = re.compile(self.re_string(),re.DOTALL)

    def re_string(self):
        if isinstance(self.token,str):
            content = '(.+?)'
            end = '(' + esc_neg_look + re.escape(self.token) + r'|$)'
            return esc_neg_look + re.escape(self.token) + content + end
        else:
            content = '(.+?)'
            return esc_neg_look + re.escape(self.token[0]) + content + esc_neg_look + re.escape(self.token[1])

    def _process(self, mos, text, wiki_elements, element_store, environ):
        """Returns genshi Fragments (Elements and text)"""
        parts = []
        end = 0
        for mo in mos:
            processed = self._build(mo,element_store, environ)
            store_id = str(id(processed)) 
            element_store[store_id] = processed
            parts.append(''.join([text[end:mo.start()],'<<<',store_id,'>>>']))
            end = mo.end()
        # call again for trailing text and extend the result list
        if end < len(text):
            parts.append(text[end:])
        new_text = ''.join(parts)
        if not isinstance(wiki_elements[0],(list,tuple)):
            wiki_elements = wiki_elements[1:]
        frags = fragmentize(new_text,wiki_elements,element_store, environ)
        return frags


class SimpleElement(InlineElement):

    r"""For finding generic inline elements like ``strong`` and ``em``.

    >>> em = SimpleElement({'//':'em'})
    >>> mo1 = em.regexp.search('a //word// in a line')
    >>> mo2 = em.regexp.search('a //word in a line\n or two\n')
    >>> mo1.group(0),mo1.group(2)
    ('//word//', 'word')
    >>> mo2.group(0),mo2.group(2)
    ('//word in a line\n or two', 'word in a line\n or two')
       
    """

    def __init__(self, token_dict={}):
        self.token_dict = token_dict
        self.tokens = list(token_dict.keys())
        super(SimpleElement,self).__init__('','')
        self.regexp = re.compile(self.re_string(),re.DOTALL)

    def re_string(self):
        if isinstance(self.token,str):
            tokens = '(' + '|'.join([re.escape(token) for token in self.tokens]) + ')'
            content = '(.+?)'
            end = '(' + esc_neg_look + r'\1|$)'
            return esc_neg_look + tokens + content + end

    def _build(self,mo,element_store, environ):
        return bldr.tag.__getattr__(self.token_dict[mo.group(1)])(fragmentize(mo.group(2),
                                                          self.child_elements,
                                                          element_store, environ))

class CustomElement(InlineElement):

    """Finds markup defined by provided custom regexp."""

    def __init__(self, reg_exp, func):
        super(CustomElement,self).__init__('','')
        if isinstance(reg_exp, str):
            self.regexp = re.compile(esc_neg_look + re.escape(reg_exp), re.DOTALL)
        else:
            self.regexp = reg_exp
        self.func = func


    def _build(self,mo,element_store, environ):
        if isinstance(self.func, str) and not isinstance(self.func, bldr.Markup):
            value = bldr.tag(bldr.Markup(self.func))
        else:
            value = self.func(mo, environ)
            if isinstance(value, str) and not isinstance(value, bldr.Markup):
                raise Exception("Custom markup functions can only return Genshi objects.")

        return value
        

class LinkElement(InlineElement):

    """Superclass for AnchorLinks and ImageLinks. Parses internal, external,
    and interwiki links.
    
    """
    
    def __init__(self,tag, token, delimiter,
                 interwiki_delimiter,base_urls,links_funcs,
                 interwiki_class_funcs,default_space_char,space_chars,
                 base_url,space_char,class_func,path_func,fragment_pattern):
        super(LinkElement,self).__init__(tag,token)
        self.regexp = re.compile(self.re_string(),re.DOTALL)
        self.delimiter = delimiter
        self.interwiki_delimiter = interwiki_delimiter
        self.base_urls = base_urls
        self.links_funcs = links_funcs
        self.class_funcs = interwiki_class_funcs
        self.default_space_char = default_space_char
        self.space_chars = space_chars
        self.base_url = base_url
        self.space_char = space_char
        self.class_func = class_func
        self.path_func = path_func
        self.fragment_pattern = fragment_pattern
        self.content_regexp = re.compile(self.content_re_string(),re.DOTALL)
        self.interwikilink_regexp = re.compile(self.interwikilink_re_string())
        self.urllink_regexp = re.compile(self.urllink_re_string(), re.DOTALL)
        self.wikilink_regexp = re.compile(self.wikilink_re_string())

    def content_re_string(self):
        return r'(?P<body>.*?)(' + re.escape(self.delimiter) + '(?P<arg_string>.*?))?$'

    def interwikilink_re_string(self):
        all_wikis = set(list(self.links_funcs.keys()) + list(self.base_urls.keys()))
        wiki_id = '(?P<wiki_id>' + '|'.join(all_wikis) + ')'
        optional_spaces = ' *'
        page_name = r'(?P<page_name>\S+?( \S+?)*)' #allows any number of single spaces
        return '^' + optional_spaces + wiki_id + \
               re.escape(self.interwiki_delimiter) + ' *' + page_name + \
               optional_spaces + '$'

    def urllink_re_string(self):
        protocol = r'^\s*((\w+?:|/)' 
        rest_of_url = r'[\S\n]*?)\s*$'
        return protocol + rest_of_url

    def wikilink_re_string(self):
        optional_spaces = ' *'
        if self.fragment_pattern:
            page_name = r'(?P<page_name>\S*?( \S+?)*?)(?P<fragment>' + \
                        self.fragment_pattern + ')?'
        else:
            page_name = r'(?P<page_name>\S+?( \S+?)*?)' #allows any number of single spaces
        return '^' + optional_spaces + page_name + optional_spaces + '$'

    def page_name(self,mo):
        if 'wiki_id' in mo.groupdict():
            space_char = self.space_chars.get(mo.group('wiki_id'),self.default_space_char)
        else:
            space_char = self.space_char
        return mo.group('page_name').replace(' ',space_char)

    def _build(self,mo,element_store, environ):
        content_mo = self.content_regexp.match(mo.group(1))
        body = content_mo.group('body')
        arg_string = content_mo.group('arg_string')
        the_class = None
        if self.interwikilink_regexp.match(body):
            interwikilink_mo = self.interwikilink_regexp.match(body)
            link_type = 'interwiki'
            base_url = self.base_urls.get(interwikilink_mo.group('wiki_id'))
            link_func = self.links_funcs.get(interwikilink_mo.group('wiki_id'))
            class_func = self.class_funcs.get(interwikilink_mo.group('wiki_id'))
            page_name = self.page_name(interwikilink_mo)
            if link_func:
                url = link_func(page_name)
            else:
                url = urllib.parse.quote(page_name.encode('utf-8'))
            if base_url:
                url = urllib.parse.urljoin(base_url, url)
            if class_func:
                the_class = class_func(page_name)
        elif self.urllink_regexp.match(body):
            urllink_mo = self.urllink_regexp.match(body)
            link_type = 'external'
            if sanitizer.is_safe_uri(urllink_mo.group(1)):
                url = urllink_mo.group(1)
            else:
                url = None
        elif self.wikilink_regexp.match(body):
            wikilink_mo = self.wikilink_regexp.match(body)
            link_type = 'wiki'
            page_name = self.page_name(wikilink_mo)
            if self.path_func and page_name:
                the_path = self.path_func(page_name)
            else:
                the_path = urllib.parse.quote(page_name.encode('utf-8'))
            if wikilink_mo.groupdict().get('fragment'):
                the_path = ''.join([the_path,wikilink_mo.group('fragment')])
            if self.class_func:
                the_class = self.class_func(page_name)
            url = urllib.parse.urljoin(self.base_url, the_path)
        else:
            url = None

        if not url:
            return mo.group(0)
        else:
            if arg_string is not None:
                args, kw_args = [arg_string.strip()], {} 
            else:
                args, kw_args = [], {}
            try:
                return self.emit(element_store, environ,link_type,body,url,the_class, *args, **kw_args)
            except TypeError:
                return mo.group(0)
                


class AnchorElement(LinkElement):

    """Finds and builds internal, external, and interwiki links.

    >>> link = AnchorElement('a',('[[',']]'),delimiter='|',
    ... interwiki_delimiter=':', 
    ... base_urls=dict(somewiki='http://somewiki.org/',
    ...                bigwiki='http://bigwiki.net/'),
    ... links_funcs={},interwiki_class_funcs={},default_space_char='-',
    ... space_chars={'bigwiki':' '},base_url='http://somewiki.org/',
    ... space_char='_',class_func=None,path_func=None,external_links_class=None,
    ... fragment_pattern=r'#![a-z0-9-_]+')
    
    >>> mo = link.regexp.search("[[http://www.google.com| here]]")
    >>> link._build(mo,{},None).generate().render()
    '<a href="http://www.google.com">here</a>'

    >>> mo = link.regexp.search(" [[somewiki:Home Page|steve]] ")
    >>> link._build(mo,{},None).generate().render()
    '<a href="http://somewiki.org/Home-Page">steve</a>'

    >>> mo = link.regexp.search(" [[bigwiki:Home Page]] ")
    >>> link._build(mo,{},None).generate().render()
    '<a href="http://bigwiki.net/Home%20Page">bigwiki:Home Page</a>'

    >>> mo = link.regexp.search(" [[Home Page |Home]]")
    >>> link._build(mo,{},None).generate().render()
    '<a href="http://somewiki.org/Home_Page">Home</a>'

    >>> mo = link.regexp.search(" [[#!my-header|Subpage]]")
    >>> link._build(mo,{},None).generate().render()
    '<a href="http://somewiki.org/#!my-header">Subpage</a>'

    >>> mo = link.regexp.search(" [[Home Page#!a-header |Home]]")
    >>> link._build(mo,{},None).generate().render()
    '<a href="http://somewiki.org/Home_Page#!a-header">Home</a>'
    
    """

    def __init__(self, tag, token, external_links_class, *args, **kw_args):
        super(AnchorElement,self).__init__(tag, token, *args, **kw_args)
        self.external_links_class = external_links_class


    def emit(self,element_store, environ,link_type,body,url,the_class, alias=None):
        if alias:
            alias = fragmentize(alias,self.child_elements,element_store, environ)
        else:
            alias = body.strip()
        if link_type == 'external':
            the_class = self.external_links_class
        return bldr.tag.__getattr__(self.tag)(alias,
                                              href=url,
                                              class_=the_class)

        
class ImageElement(LinkElement):

    """Processes image elements.

    >>> img = ImageElement('img',('{{','}}'), delimiter='|',
    ... interwiki_delimiter=':', 
    ... base_urls=dict(somewiki='http://somewiki.org/',
    ...                bigwiki='http://bigwiki.net/'),
    ... links_funcs={},interwiki_class_funcs={},default_space_char='-',
    ... space_chars={'bigwiki':' '},base_url='/images/',
    ... space_char='_',class_func=None,path_func=None,disable_external=False,
    ... fragment_pattern=False)

    >>> mo = img.regexp.search('{{ picture.jpg | An image of a house }}')
    >>> img._build(mo,{},None).generate().render()
    '<img src="/images/picture.jpg" alt="An image of a house" title="An image of a house"/>'

    """


    def __init__(self, tag, token, disable_external, *args, **kw_args):
        super(ImageElement,self).__init__(tag, token, *args, **kw_args)
        self.disable_external = disable_external

    def emit(self,element_store, environ,link_type,body,url,the_class, alt=None):

        if self.disable_external and link_type == 'external':
            return bldr.tag.span('External images are disabled', class_='external_image')

        if alt is None:
            if link_type == 'external':
                alt = urllib.parse.urlsplit(url).path.split('/')[-1]
            else:
                alt = body.strip()

            
        return bldr.tag.__getattr__(self.tag)(src=url ,alt=alt, title=alt,
                                              #class_=the_class
                                              )           
        

class Link(InlineElement):

    """DEPRECIATED    """
    
    def __init__(self,tag, token):
        super(Link,self).__init__(tag,token)
        self.regexp = re.compile(self.re_string(),re.DOTALL)
        warnings.warn("""
Use of elements.Link is depreciated. 
"""
                  )

    def _build(self,mo,element_store, environ):
        
        for tag in self.child_elements:
            m = tag.regexp.search(mo.group(1))
            if m:
                link = tag._build(m,element_store, environ)
                if link:
                    break
        else:
            link = None

        if link:
            return bldr.tag(link)
        else:
            return mo.group(0)


class Macro(WikiElement):
    r"""Finds and processes inline macro elements."""

    def __init__(self, tag, token, func, macros, arg_parser):
        super(Macro,self).__init__(tag,token , [])
        self.func = func
        self.macros = macros
        self.arg_parser = arg_parser
        self.regexp = re.compile(self.re_string())


    def _process(self, mos, text, wiki_elements,element_store, environ):
        """Returns genshi Fragments (Elements and text)"""
        assert len(mos) == 1
        mo = mos[0]
        processed = self._build(mo,element_store, environ)
        if isinstance(processed, list):
            tail = processed[1]
            processed = processed[0]
        else:
            tail = ''
        if isinstance(processed, str) and not isinstance(processed,Markup):
            text = ''.join([text[:mo.start()],processed,tail,
                        text[mo.end():]])
        else:
            store_id = str(id(processed))
            element_store[store_id] = processed
            text = ''.join([text[:mo.start()],'<<<',store_id,'>>>',tail,
                        text[mo.end():]])
        frags = fragmentize(text,wiki_elements,element_store, environ)
        return frags


    def re_string(self):
        content = '(.*?)'
        return esc_neg_look + re.escape(self.token[0]) + r'(' + MACRO_NAME + \
               content + ')' + esc_neg_look + re.escape(self.token[1])

    def _macro_func(self,macro_name,arg_string,body,isblock,environ):

        func = self.macros[macro_name]
        arg_parser = func.__dict__.get('arg_parser') or self.arg_parser
        if arg_parser:
            pos, kw = arg_parser(arg_string)
        else:
            pos, kw = [], {}

        def parsed_body(context='auto'):
            if context == 'auto':
                if isblock:
                    child_elements = self.dialect.block_elements
                else:
                    child_elements = self.dialect.inline_elements
            elif context == 'inline':
                child_elements = self.dialect.inline_elements
            elif context == 'block':
                child_elements = self.dialect.block_elements
            else:
                child_elements = context
            return bldr.tag(fragmentize(body, child_elements, {}, environ))

                    
        macro = AttrDict(name=macro_name,arg_string=arg_string,
                         body=body, isblock=isblock, parsed_body=parsed_body)
        
        try:
            value = func(macro,environ,*pos,**kw)
        except TypeError as detail:
            tag = isblock and 'pre' or 'code'
            e = str(detail)
            msg = re.sub(r"^\w*\(\) ", '', e)
            mo = re.match(r'(.+)(\d+)(.+)(\d+) given\)$',msg)
            if mo: #re.search(r'given\)$',msg):
                #mo = re.match(r'(.+)(\d+)(.+)(\d+)(.+)$',msg)
                msg = mo.group(1) + str(int(mo.group(2))-2) \
                      + re.sub('arguments?','argument(s)',mo.group(3)) \
                      + str(int(mo.group(4))-2) + ' given)'
            value = bldr.tag.__getattr__(tag)("Macro error: '%s' %s"% (macro_name, msg),class_='macro_error')
        except MacroError as detail:
            tag = isblock and 'pre' or 'code'
            value = bldr.tag.__getattr__(tag)("Error in macro '%s': %s"% (macro_name,str(detail.value)),class_='macro_error')
        except:
            value = bldr.tag.pre('Unexpected error during macro execution!\n'
                                 + traceback.format_exc(20) ,
                                 class_='macro_error')

        return value    


    trailing_slash = re.compile(r'(?<=[ "\'\]])/$')
    def _build(self,mo,element_store, environ):
        arg_string = re.sub(self.trailing_slash,'',mo.group(4))

        if mo.group('name') in self.macros:
            value = self._macro_func(mo.group('name'),arg_string,None,False,environ)    
        elif self.func:
            value = self.func(mo.group('name'),arg_string,None,False,environ)
        else:
            value = None

        if value is None:
            return bldr.tag.code(self.token[0],bldr.tag.span(mo.group('name'),class_="macro_name"),
                           bldr.tag.span(arg_string,class_="macro_arg_string"),
                           self.token[1],class_="unknown_macro")
        elif isinstance(value, (str,bldr.Fragment,bldr.Element, Stream)):
            return value
        else:
            raise Exception("macros can only return strings and genshi objects") 
        

class BodiedMacro(Macro):
    """Finds and processes macros with bodies.

    Does not span across top level block markup
    (see BodiedBlockMacro's for that)."""

    def __init__(self, tag, token, func, macros, arg_parser):
        super(BodiedMacro,self).__init__(tag,token , func, macros, arg_parser)
        self.regexp = re.compile(self.re_string(),re.DOTALL)

    def re_string(self):
        content = r'(?P<arg_string>[ \S]*?)'
        body = '(?P<body>.+)'
        return esc_neg_look + re.escape(self.token[0]) + MACRO_NAME + \
               content + '(?<!/)' + re.escape(self.token[1]) + \
               body + esc_neg_look + re.escape(self.token[0]) + \
               r'/(?P=name)' + '(?<!/)' + re.escape(self.token[1])

    def _build(self,mo,element_store, environ):
        start = ''.join([esc_neg_look, re.escape(self.token[0]), re.escape(mo.group('name')),
                         r'(?P<arg_string>[ \S]*?)', re.escape(self.token[1])])
        end = ''.join([esc_neg_look, re.escape(self.token[0]), '/', re.escape(mo.group('name')),
                       re.escape(self.token[1])])
        count = 0
        for mo2 in re.finditer(start + '|' + end, mo.group('body')):
            if re.match(end,mo2.group(0)):
                count = count + 1
            else:
                count = count - 1
            if count > 0:
                body = mo.group('body')[:mo2.start()]
                tail = ''.join([mo.group('body')[mo2.end():], self.token[0],
                                '/', mo.group('name'), self.token[1]])
                break
        else:
            body = mo.group('body')
            tail = ''
                
        if mo.group('name') in self.macros:
            value = self._macro_func(mo.group('name'),mo.group('arg_string'),body,False,environ)    
        elif self.func:
            value = self.func(mo.group('name'),mo.group('arg_string'),body,False,environ)
        else:
            value = None

        if value is None:
            content_out = [self.token[0],bldr.tag.span(mo.group('name'),class_="macro_name"),
                           bldr.tag.span(mo.group('arg_string'),class_="macro_arg_string"),
                           self.token[1],bldr.tag.span(mo.group('body'),class_="macro_body"),
                           self.token[0] + '/' + mo.group('name') + self.token[1]]
            output = bldr.tag.code(content_out,class_="unknown_macro", style="white-space:pre-wrap")
        elif isinstance(value, (str,bldr.Fragment, Stream)):
            output = value
        else:
            raise Exception("macros can only return strings and genshi objects")

        return [output, tail]

       

class BodiedBlockMacro(Macro):
    """Finds and processes block macros with bodies.

    The opening and closing tokens must be are each on a line alone without
    leading spaces. These macros can enclose other block level markup
    including pre blocks and other BodiedBlockMacro's."""
    def __init__(self, tag, token, func, macros, arg_parser):
        super(BodiedBlockMacro,self).__init__(tag,token , func, macros, arg_parser)
        self.regexp = re.compile(self.re_string(),re.DOTALL+re.MULTILINE)

    def re_string(self):
        arg_string = r'(?P<arg_string>(?![^\n]*>>[^\n]*>>)[ \S]*?)'
        start = '^' + re.escape(self.token[0])
        body = r'(?P<body>.*\n)'
        end = re.escape(self.token[0]) + \
               r'/(?P=name)' + '(?<!/)' + re.escape(self.token[1]) + r'\s*?$'
        
        return start + '(' + MACRO_NAME + arg_string + ')' + '(?<!/)' + \
               re.escape(self.token[1]) + r'\s*?\n' + body + end

    def _process(self, mos, text, wiki_elements,element_store, environ):
        """Returns genshi Fragments (Elements and text)

        This is mainly for block level markup. See InlineElement
        for the other method.
        """
        assert len(mos) == 1
        mo = mos[0]
        processed = self._build(mo,element_store, environ)
        if isinstance(processed, list):
            tail = processed[1]
            processed = processed[0]
        else:
            tail = ''
        if isinstance(processed, str) and not isinstance(processed,Markup):
            text = ''.join([text[:mo.start()],processed,tail,
                        text[mo.end():]])
            frags = fragmentize(text,wiki_elements,element_store, environ)
        else:
        
            frags = []
            # call again for leading text and extend the result list 
            if mo.start():
                frags.extend(fragmentize(text[:mo.start()],wiki_elements[1:],
                                         element_store, environ))
            # append the found wiki element to the result list
            frags.append(processed)
            # make the source output easier to read
            if self.append_newline:
                frags.append('\n')
            # call again for trailing text and extend the result list
            if tail or mo.end() < len(text):
                frags.extend(fragmentize(tail + text[mo.end():],wiki_elements,
                                         element_store, environ))
        return frags

    def _build(self,mo,element_store, environ):
        start = ''.join(['^', re.escape(self.token[0]), re.escape(mo.group('name')),
                         r'(?P<arg_string>(?![^\n]*>>[^\n]*>>)[ \S]*?)', re.escape(self.token[1]),r'\s*?\n'])
        end = ''.join(['^', re.escape(self.token[0]), '/', re.escape(mo.group('name')),
                       re.escape(self.token[1]),r'\s*?$'])
        count = 0
        for mo2 in re.finditer(start + '|' + end, mo.group('body'),re.MULTILINE):
            if re.match(end,mo2.group(0)):
                count = count + 1
            else:
                count = count - 1
            if count > 0:
                body = mo.group('body')[:mo2.start()]
                tail = ''.join([mo.group('body')[mo2.end():], self.token[0],
                                '/', mo.group('name'), self.token[1],'\n'])
                break
        else:
            body = mo.group('body')
            tail = ''


        if mo.group('name') in self.macros:
            value = self._macro_func(mo.group('name'),mo.group('arg_string'),body,True,environ)    
        elif self.func:
            value = self.func(mo.group('name'),mo.group('arg_string'),body,True,environ)
        else:
            value = None

        if value is None:
            output = bldr.tag.pre(self.token[0],bldr.tag.span(mo.group('name'),class_="macro_name"),
                           bldr.tag.span(mo.group('arg_string'),class_="macro_arg_string"),
                           self.token[1],'\n',bldr.tag.span(mo.group('body'),class_="macro_body"),
                           self.token[0] + '/' + mo.group('name') + self.token[1],
                           class_="unknown_macro")
        elif (isinstance(value, (Stream, str)) or
             (isinstance(value,bldr.Element) and value.tag in BLOCK_TAGS)):
            output = value
        # Add a p tag if the value is a Fragment or Element that needs one
        elif isinstance(value, bldr.Fragment):
            output = bldr.tag.p(value)
        else:
            raise Exception("macros can only return strings and genshi objects")

        return [output, tail]
        
    
class RawLink(InlineElement):
    
    """Used to find raw urls in wiki text and build xml from them.

    >>> raw_link = RawLink(tag='a')
    >>> mo = raw_link.regexp.search(" a http://www.google.com url ")
    >>> raw_link.href(mo)
    'http://www.google.com'
    >>> raw_link._build(mo,{},None).generate().render()
    '<a href="http://www.google.com">http://www.google.com</a>'
    
    """
    linking_protocols = ['http','https']
    
    def __init__(self, tag):
        super(RawLink,self).__init__(tag=tag, token=None)
        self.regexp = re.compile(self.re_string())

    def re_string(self):
        escape = '(' + re.escape(escape_char) + ')?'
        protocol = '((https?|ftp)://'
        rest_of_url = r'\S+?)'
        #allow one punctuation character or '**' or '//'. Don't include a placeholder.
        look_ahead = r'(?=([>)}\]]?[,.?!:;"\']?(([^a-zA-Z0-9])\6)?(\s|$))|<<<)'
        return escape + protocol + rest_of_url + look_ahead

    def _build(self,mo,element_store, environ):
        if (not mo.group(1)) and (mo.group(3) in self.linking_protocols):
            return bldr.tag.__getattr__(self.tag)(self.alias(mo,element_store),
                                              href=self.href(mo))
        else:
            return self.href(mo)
        
    def href(self,mo):
        """Returns the string for the href attribute of the Element."""
        if sanitizer.is_safe_uri(mo.group(2)):
            return mo.group(2)
        else:
            return "unsafe_uri_detected"

    def alias(self,mo,element_store):
        """Returns the string for the content of the Element."""
        return self.href(mo)


class URLLink(WikiElement):
    
    """DEPRECIATED    """

    def __init__(self, tag,delimiter):
        super(URLLink,self).__init__(tag, '')
        self.delimiter = delimiter
        self.regexp = re.compile(self.re_string(),re.DOTALL)
        warnings.warn("""
Use of elements.URLLink is depreciated. 
"""
                  )

    def re_string(self):
        protocol = r'^\s*((\w+?:|/)' 
        rest_of_url = r'[\S\n]*?)\s*'
        alias = r'(' + re.escape(self.delimiter) + r' *(.*?))? *$'
        return protocol + rest_of_url + alias

    def _build(self,mo,element_store, environ):
        if not self.href(mo):
            return None
        return bldr.tag.__getattr__(self.tag)(self.alias(mo,element_store, environ),
                                              href=self.href(mo))
       
    def href(self,mo):
        """Returns the string for the href attribute of the Element."""
        if sanitizer.is_safe_uri(mo.group(1)):
            return mo.group(1)
        else:
            return None 
            

    def alias(self,mo,element_store, environ):
        """Returns the string for the content of the Element."""
        if not mo.group(4):
            return self.href(mo)
        else:
            return fragmentize(mo.group(4),self.child_elements,element_store, environ)



class InterWikiLink(WikiElement):

    """DEPRECIATED    """

    def __init__(self, tag, delimiter1,
                 delimiter2,base_urls,links_funcs,default_space_char,space_chars):
        super(InterWikiLink,self).__init__(tag, '')
        self.delimiter1 = delimiter1
        self.delimiter2 = delimiter2
        #self.regexp = re.compile(self.re_string())
        self.base_urls = base_urls
        self.links_funcs = links_funcs
        self.default_space_char = default_space_char
        self.space_chars = space_chars
        self.regexp = re.compile(self.re_string())
        warnings.warn("""
Use of elements.InterWikiLink is depreciated. 
"""
                  )

    def re_string(self):
        #all_wikis = set(self.links_funcs.keys() + self.base_urls.keys())
        #wiki_id = '(' + '|'.join(all_wikis) + ')'

        wiki_id = r'(\w+)'
        optional_spaces = ' *'
        page_name = r'(\S+?( \S+?)*)' #allows any number of single spaces
        alias = r'(' + re.escape(self.delimiter2) + r' *(.*?))? *$'
        return '^' + optional_spaces + wiki_id + optional_spaces + \
               re.escape(self.delimiter1) + optional_spaces + page_name + \
               optional_spaces + alias

    def page_name(self,mo):
        space_char = self.space_chars.get(mo.group(1),self.default_space_char)
        return mo.group(2).replace(' ',space_char)

    def href(self,mo):
        linktype = mo.group(1)
        base_url = self.base_urls.get(linktype)
        link_func = self.links_funcs.get(linktype)
        if not (link_func or base_url):
            return None
        else:
            href = self.page_name(mo)
            if link_func:
                href = link_func(href)
            else:
                href = urllib.parse.quote(href.encode('utf-8'))
            if base_url:
                href = urllib.parse.urljoin(base_url, href)
            return href

    def _build(self,mo,element_store, environ):
        if not self.href(mo):
            return '[[' + mo.group(0) + ']]'
        return bldr.tag.__getattr__(self.tag)(self.alias(mo,element_store, environ),
                                              href=self.href(mo))
    def alias(self,mo,element_store, environ):
        """Returns the string for the content of the Element."""
        if not mo.group(5):
            return ''.join([mo.group(1),self.delimiter1,mo.group(2)])
        else:
            return fragmentize(mo.group(5),self.child_elements,element_store, environ)



class WikiLink(WikiElement):

    """DEPRECIATED    """

    def __init__(self, tag, delimiter,
                 base_url,space_char,class_func,path_func):
        super(WikiLink,self).__init__(tag, '')
        self.delimiter = delimiter
        self.base_url = base_url
        self.space_char = space_char
        self.class_func = class_func
        self.path_func = path_func
        self.regexp = re.compile(self.re_string())
        warnings.warn("""
Use of elements.WikiLink is depreciated. 
"""
                  )


    def re_string(self):
        optional_spaces = ' *'
        page_name = r'(\S+?( \S+?)*?)' #allows any number of single spaces
        alias = r'(' + re.escape(self.delimiter) + r' *(.*?))? *$'
        return '^' + optional_spaces + page_name + optional_spaces + \
               alias

    def page_name(self,mo):
        return mo.group(1).replace(' ',self.space_char)
    
    def href(self,mo):
        if self.path_func:
            the_path = self.path_func(self.page_name(mo))
        else:
            the_path = urllib.parse.quote(self.page_name(mo).encode('utf-8'))
        return urllib.parse.urljoin(self.base_url, the_path)

    def _build(self,mo,element_store, environ):
        if self.class_func:
            the_class = self.class_func(self.page_name(mo))
        else:
            the_class = None
        return bldr.tag.__getattr__(self.tag)(self.alias(mo,element_store, environ),
                                              href=self.href(mo),
                                              class_=the_class)
    
    def alias(self,mo,element_store, environ):
        """Returns the string for the content of the Element."""
        if not mo.group(3):
            return mo.group(1)
        else:
            return fragmentize(mo.group(4),self.child_elements,element_store, environ)


class List(BlockElement):

    """Finds list (ordered, unordered, and definition) wiki elements.

    group(1) of the match object includes all lines from the list
    including newline characters.
        
    """

    def __init__(self, tag, token,stop_tokens=None):
        self.stop_tokens = stop_tokens
        super(List,self).__init__(tag, token)
        #self.stop_tokens = stop_tokens
        self.regexp = re.compile(self.re_string(),re.DOTALL+re.MULTILINE)

    def re_string(self):
        """This re_string is for finding generic block elements like
        lists (ordered, unordered, and definition) that start with a
        single token.
        """
        leading_whitespace = r'^([ \t]*'
        only_one_token = re.escape(self.token)+ '(?!' + re.escape(self.token) + ')'
        rest_of_list = r'.*?(?:\n|\Z))'
        only_one_stop_token = '([' + re.escape(self.stop_tokens) + r'])(?!\3)'        
        look_ahead = '(?=([ \t]*' + only_one_stop_token + '|$))'
        return leading_whitespace + only_one_token + rest_of_list + \
               look_ahead



class ListItem(BlockElement):
    r"""Matches the current list item.

    Everything up to the next same-level list item is matched.

    >>> list_item = ListItem('li','#*')
    >>> mo = list_item.regexp.search("*one\n**one.1\n**one.2\n*two\n")
    >>> mo.group(3)
    'one\n**one.1\n**one.2\n'
    >>> mo.group(0)
    '*one\n**one.1\n**one.2\n'
    
    """
    
    append_newline = False

    def __init__(self, tag, list_tokens):
        """Constructor for list items.

        :parameters"
          list_tokens
            A string that includes the tokens used for lists
        """
        self.list_tokens = list_tokens
        super(ListItem,self).__init__(tag, None)
        self.regexp = re.compile(self.re_string(),re.DOTALL)

    def re_string(self):
        whitespace = r'[ \t]*'
        item_start = '(([' + self.list_tokens + r'])\2*)'
        rest_of_item = r'(.*?(?:\n|\Z))'
        start_of_same_level_item = r'\1(?!\2)'
        look_ahead = r'(?=(' + whitespace + start_of_same_level_item + '|$))'
        return whitespace + item_start + whitespace + \
               rest_of_item + look_ahead

    def _build(self,mo,element_store, environ):
        return bldr.tag.__getattr__(self.tag)(fragmentize(mo.group(3),
                                                          self.child_elements,
                                                          element_store, environ))


class NestedList(WikiElement):

    r"""Finds a list in the current list item.

    >>> nested_ul = NestedList('ul','*')
    >>> mo = nested_ul.regexp.search('one\n**one.1\n**one.2\n')
    >>> mo.group(1)
    '**one.1\n**one.2\n'
    >>> mo.group(0) == mo.group(1)
    True

    """

    def __init__(self, tag, token):
        super(NestedList,self).__init__(tag, token)
        self.regexp = re.compile(self.re_string(),re.DOTALL+re.MULTILINE)

    def re_string(self):
        look_behind = r'(?<=\n)' # have to avoid finding a list on the first line
        whitespace = r'(\s*'
        rest_of_list = '.*$)'
        return look_behind + '^' + whitespace + re.escape(self.token) + \
               rest_of_list


class DefinitionTerm(BlockElement):

    r"""Processes definition terms.

    >>> term = DefinitionTerm('dt',';',stop_token=':')
    >>> mo1,mo2 = term.regexp.finditer(";term1\n:def1\n;term2:def2\n")
    >>> mo1.group(1), mo2.group(1)
    ('term1', 'term2')
    >>> mo1.group(0), mo2.group(0)
    (';term1\n', ';term2')

    group(1) of the match object is the term line or up to the first ':'
        
    """

    def __init__(self, tag, token,stop_token):
        super(DefinitionTerm,self).__init__(tag, token)
        self.stop_token = stop_token
        self.regexp = re.compile(self.re_string(),re.DOTALL+re.MULTILINE)

    def re_string(self):
        look_ahead = r'(\n|(?=(' + esc_neg_look + re.escape(self.stop_token) + r'|$)))'
        return r'^[ \t]*' + re.escape(self.token) + r'[ \t]*(.*?' + \
               re.escape(self.stop_token) +  '?)\s*' + look_ahead 


class DefinitionDef(BlockElement):

    r"""Processes definitions.

    >>> definition = DefinitionDef('dd',':')
    >>> mo1,mo2 = definition.regexp.finditer(":def1a\ndef1b\n:def2\n")
    >>> mo1.group(1), mo2.group(1)
    ('def1a\ndef1b', 'def2')
    >>> mo1.group(0), mo2.group(0)
    (':def1a\ndef1b\n', ':def2\n')

    group(1) of the match object includes all lines from the defintion
    up to the next definition.
        
    """

    def __init__(self, tag, token):
        super(DefinitionDef,self).__init__(tag, token)
        self.regexp = re.compile(self.re_string(),re.DOTALL+re.MULTILINE)

    def re_string(self):
        look_ahead = r'(?=(^[ \t]*' + re.escape(self.token) + r')|\Z)'
        return r'^[ \t]*' + re.escape(self.token) + r'?[ \t]*(.+?)\s*' + look_ahead 

class Paragraph(BlockElement):
    """"This should be the last outer level wiki element to be searched.

    Anything that is left over will be placed in a paragraphs unless it looks
    like block content according to xhtml1 strict. Block content is defined
    here as valid children of the <body> element (see BLOCK_TAGS). Only genshi
    Element objects will be evaluated (see BLOCK_TAGS). Fragments and stings
    are treated as inline while Streams are block content.
    
    """

    def __init__(self, tag):
        super(Paragraph,self).__init__(tag,None)
        self.regexp = re.compile(self.re_string(),re.DOTALL)#+re.MULTILINE)

    def re_string(self):
        return r'^(.*?)\n?$' 

    def _build(self,mo,element_store, environ):
        content = fragmentize(mo.group(1), self.child_elements, element_store, environ)
        # Check each list item and record those that are block only
        block_only_frags = []
        for i,element in enumerate(content):
            if ((isinstance(element, bldr.Element) and
                element.tag in BLOCK_ONLY_TAGS) or
                isinstance(element,(Stream,Markup))):
                block_only_frags.append(i)
        # Build a new result list if needed
        if block_only_frags:
            new_content = []
            last_i = -1
            for i in block_only_frags:
                if content[last_i+1:i]:
                    if not (len(content[last_i+1:i])==1 and
                                                content[last_i+1] == '\n'):
                        new_content.append(bldr.tag.__getattr__(self.tag)(content[last_i+1:i]))
                    else:
                        new_content.append('\n')
                new_content.append(content[i])
                last_i = i
            if content[last_i+1:]:
                new_content.append(bldr.tag.__getattr__(self.tag)(content[last_i+1:]))
            return bldr.tag(new_content)
        else:
            return bldr.tag.__getattr__(self.tag)(content)
            

class Heading(BlockElement):

    r"""Processes heading wiki elements. Optionally adds id attributes.

    >>> h1 = Heading(['h1','h2'],'=',id_prefix=False)
    >>> mo = h1.regexp.search('before\n = An important thing = \n after')
    >>> mo.group(2)
    'An important thing'
    >>> mo.group(0)
    ' = An important thing = \n'

    >>> h1 = Heading(['h1','h2'],'=',id_prefix='!')
    >>> mo = h1.regexp.search(u'before\n = An important thing = \n after')
    >>> mo.group(2)
    u'An important thing'
    >>> h1.make_id('!',mo.group(2),[])
    '!an-important-thing'
    >>> h1.make_id('!',mo.group(2),['!an-important-thing'])
    '!an-important-thing_1'
    >>> h1.make_id('!',mo.group(2),{})
    '!an-important-thing'
    >>> h1.make_id('!',mo.group(2) + '!@#$%&*()_[]+=/?|-- TO    SAY',{})
    '!an-important-thing-to-say'

    """

    def __init__(self, tag, token, id_prefix):
        super(Heading,self).__init__('',token)
        self.id_prefix = id_prefix
        self.tags = tag
        self.regexp = re.compile(self.re_string(),re.MULTILINE)


    def make_id(self, prefix, heading_text,used_ids):
        slug = unicodedata.normalize('NFKD', heading_text).encode('ascii', 'ignore').lower()
        slug = re.sub('-+', '-', re.sub('[^a-z0-9-]+', '-', slug)).strip('-')
        slug = ''.join([prefix,slug]) or '!'
        # Restrict length without breaking words.
        while len(slug) > 40:
            if slug.find('-') == -1:
                slug = slug[:40]
            else:
                slug = slug.rsplit('-', 1)[0]
        i = 1
        original_slug = slug 
        while True:
            if slug not in used_ids:
                break
            slug = '%s_%d' % (original_slug, i)
            i += 1
        
        return slug

  
    def re_string(self):
        whitespace = r'[ \t]*'
        tokens = '(' + re.escape(self.token) + '{1,' + str(len(self.tags)) +'})'
        content = '(.*?)'
        trailing_markup = '(' + re.escape(self.token) + r'+[ \t]*)?(\n|\Z)'
        return '^' + whitespace + tokens + \
               whitespace + content + whitespace + trailing_markup

    def _build(self,mo,element_store, environ):
        heading_tag = self.tags[len(mo.group(1))-1]
        heading_body = fragmentize(mo.group(2),
                                   self.child_elements,
                                   element_store, environ)
        if self.id_prefix is False:
            id_=None
        else:
            heading_text = bldr.tag(heading_body).generate().render(method='text',encoding=None)
            used_ids = environ.setdefault('ids', [])
            id_ = self.make_id(self.id_prefix,heading_text,used_ids)
            used_ids.append(id_)
            #toc = environ.setdefault('toc', [])
            #toc.append((heading_tag, bldr.tag(heading_body), id_))            
        return bldr.tag.__getattr__(heading_tag)(heading_body,
                                                 id_=id_)




class Table(BlockElement):

    r"""Find tables.

    >>> table = Table('table','|')
    >>> mo = table.regexp.search("before\n | one | two |\n|one|two \n hi")
    >>> mo.group(1)
    ' | one | two |\n|one|two \n'
    >>> mo.group(0) == mo.group(1)
    True
    
    """

    def __init__(self, tag, token):
        super(Table,self).__init__(tag,token)
        self.regexp = re.compile(self.re_string(),re.MULTILINE)

    def re_string(self):
        whitespace = r'[ \t]*'
        rest_of_line = r'.*?(\n|\Z)'
        return '^((' + whitespace + re.escape(self.token) + \
               rest_of_line + ')+)'



class TableRow(BlockElement):

    r"""Finds rows in a table.

    >>> row = TableRow('tr','|')
    >>> mo = row.regexp.search(' | one | two |\n|one|two \n')
    >>> mo.group(1)
    '| one | two '
    >>> mo.group(0)
    ' | one | two |\n'
    
    """

    def __init__(self, tag, token):
        super(TableRow,self).__init__(tag,token)
        self.regexp = re.compile(self.re_string(),re.MULTILINE)

    def re_string(self):
        whitespace = r'[ \t]*'
        content = '(' + re.escape(self.token) + '.*?)'
        trailing_token = re.escape(self.token) + '?'
        return '^' + whitespace + content + trailing_token + \
               whitespace + r'(\n|\Z)'


class TableCell(WikiElement):

    r"""Finds cells in a table row.

    >>> cell = TableCell('td','|')
    >>> mo = cell.regexp.search('| one | two ')
    >>> mo.group(1)
    'one'
    >>> mo.group(0)
    '| one '
    
    """

    def __init__(self, tag, token):
        super(TableCell,self).__init__(tag,token )
        self.regexp = re.compile(self.re_string())

    def re_string(self):
        whitespace = r'[ \t]*'
        content = '(.*?)'
        look_ahead = '((?=' + esc_neg_look + re.escape(self.token[0]) + ')|$)'
        return esc_neg_look + re.escape(self.token) + whitespace + \
               content + whitespace + look_ahead    

class Image(InlineElement):

    """DEPRECIATED    """

    def __init__(self, tag, token, delimiter):
        super(Image,self).__init__(tag,token )
        self.regexp = re.compile(self.re_string())
        self.delimiter = delimiter
        self.src_regexp = re.compile(r'^\s*(\S+)\s*$')
        warnings.warn("""
Use of elements.Image is depreciated. 
"""
                  )

    def _build(self,mo,element_store, environ):
        body = mo.group(1).split(self.delimiter,1)
        src_mo = self.src_regexp.search(body[0])
        if not src_mo:
            return bldr.tag.span('Bad Image src')
        if sanitizer.is_safe_uri(src_mo.group(1)):
            link = src_mo.group(1)
        else:
            link = "unsafe_uri_detected"
        if len(body) == 1:
            alias = link
        else:
            alias = body[1].strip()
        return bldr.tag.__getattr__(self.tag)(src=link ,alt=alias, title=alias)


class NoWikiElement(InlineElement):

    """Inline no-wiki.

    When two or more end tokens are found together, only last marks
    the end of the element.
    
    """

    def __init__(self, tag, token):
        super(NoWikiElement,self).__init__(tag,token )
        self.regexp = re.compile(self.re_string(),re.DOTALL) 

    def _build(self,mo,element_store, environ):
        if self.tag:
            return bldr.tag.__getattr__(self.tag)(
                   fragmentize(mo.group(1), self.child_elements,
                               element_store,environ,
                               remove_escapes=False))
        else:
            return bldr.tag(fragmentize(mo.group(1),self.child_elements,
                                        element_store, environ,
                                        remove_escapes=False))

    def re_string(self):
        if isinstance(self.token,str):
            content = '(.+?' + re.escape(self.token[-1]) + '*)'
            return esc_neg_look + re.escape(self.token) + \
                   content + re.escape(self.token)
        else:
            content = '(.+?' + re.escape(self.token[1][-1]) + '*)'
            return esc_neg_look + re.escape(self.token[0]) + \
                   content + re.escape(self.token[1])


class PreBlock(BlockElement):
    """A preformatted block.

    If a closing token is found on a line with a space as the first
    character, the space will be removed from the output.
    
    """

    def __init__(self, tag, token ):
        super(PreBlock,self).__init__(tag,token )
        self.regexp = re.compile(self.re_string(),re.DOTALL+re.MULTILINE)
        self.regexp2 = re.compile(self.re_string2(),re.MULTILINE)

    def re_string(self):
        if isinstance(self.token,str):
            return '^' + re.escape(self.token) + r'\s*?\n(.*?\n)' + \
                   re.escape(self.token) + r'\s*?\n'
        else:
            start = '^' + re.escape(self.token[0]) + r'\s*?\n'
            content = r'(.+?\n)'
            end = re.escape(self.token[1]) + r'\s*?$'
            return start + content + end

    def re_string2(self):
        """Finds a closing token with a space at the start of the line."""
        if isinstance(self.token,str):
            return r'^ (\s*?' + re.escape(self.token) + r'\s*?\n)'
        else:
            return r'^ (\s*?' + re.escape(self.token[1]) + r'\s*?\n)'

    def _build(self,mo,element_store, environ):
        match = self.regexp2.sub(r'\1',mo.group(1))
        
        return bldr.tag.__getattr__(self.tag)(
            fragmentize(match,self.child_elements,
                        element_store, environ,remove_escapes=False))


class IndentedBlock(BlockElement):
    """An  indented block.

    """

    def __init__(self, tag, token, class_ , style ):
        super(IndentedBlock,self).__init__(tag,token )
        self.regexp = re.compile(self.re_string(),re.MULTILINE)
        self.regexp2 = re.compile(self.re_string2(),re.MULTILINE)
        self.class_ = class_
        self.style = style

    def re_string(self):
        return r'^((' + re.escape(self.token) \
               + r'.*?(\n|\Z))+)'

    def re_string2(self):
        """Finds a token at the start of the line."""
        return r'^' + re.escape(self.token)

    def _build(self,mo,element_store, environ):
        match = self.regexp2.sub(r'',mo.group(1)) # removes tokens during processing
        return bldr.tag.__getattr__(self.tag)(
            fragmentize(match,self.child_elements,
                        element_store, environ),class_=self.class_,style=self.style)


class LoneElement(BlockElement):
    """Element on a line by itself with no content (e.g., <hr/>)"""

    def __init__(self, tag, token):
        super(LoneElement,self).__init__(tag,token )
        self.regexp = re.compile(self.re_string(),re.DOTALL+re.MULTILINE)

    def re_string(self):
        return r'^(\s*?' + re.escape(self.token) + r'\s*?(\n|\Z))'

    def _build(self,mo,element_store, environ):
        return bldr.tag.__getattr__(self.tag)()


class HrElement(LoneElement):
    def __init__(self):
        super(LoneElement, self).__init__('hr', '----')
        self.regexp = re.compile(r'^(\s*?-{4,}\s*?(\n|\Z))', re.DOTALL + re.MULTILINE)


class BlankLine(WikiElement):

    """Blank lines divide elements but don't add any output."""

    def __init__(self):
        super(BlankLine,self).__init__(tag=None,token='' , child_elements=[])
        self.regexp = re.compile(self.re_string(),re.MULTILINE)

    def re_string(self):
        return r'^\s*(\Z|\n)' # r'^(\s*\n)+'
     
    def _build(self,mo,element_store, environ):
        return None

    def _process(self, mos, text, wiki_elements,element_store, environ):
        """Returns genshi Fragments (Elements and text)

        Custom _process method here just to avoid unnecessary calling of
        _build.
        """
        
        frags = []
        end = 0
        for mo in mos:
            if end != mo.start():
            # call again for leading text and extend the result list 
                frags.extend(fragmentize(text[end:mo.start()],wiki_elements[1:],
                                         element_store, environ))
            end = mo.end()
        # call again for trailing text and extend the result list
        if end < len(text):
            if not isinstance(wiki_elements[0],(list,tuple)):
                wiki_elements = wiki_elements[1:]
            frags.extend(fragmentize(text[end:],wiki_elements,
                 element_store, environ))

        return frags


    
class LineBreak(InlineElement):
    """An inline line break."""

    def __init__(self,tag, token, blog_style=False):
        self.blog_style = blog_style
        super(LineBreak,self).__init__(tag,token )
        self.regexp = re.compile(self.re_string(),re.DOTALL)

    def re_string(self):
        if self.blog_style:
            return '(' + esc_neg_look + re.escape(self.token) + r'\n?|\n(?!$))'
        else:
            return esc_neg_look + re.escape(self.token)
    
    def _build(self,mo,element_store, environ):
        return bldr.tag.__getattr__(self.tag)()

#############################################################################
# The WikeElement classes below are used for parsing macro argument strings # 
#############################################################################

class ArgString(WikiElement):
    """Base class for elements used on argument strings"""
    def __init__(self, tag='', token=''):
        super(ArgString,self).__init__(tag,token)
        self.regexp = re.compile(self.re_string(),re.DOTALL)


class KeywordArg(ArgString):
   """Finds keyword arguments"""

   def re_string(self):
      return r'(?P<key>\w[\w0-9]*) *'+re.escape(self.token) + \
               r' *(?P<body>.*?) *(?=\w[\w0-9]* *' + re.escape(self.token) +'|$)'

   def _build(self,mo,element_store, environ):
      if mo.group('body') == '':
         value = ''
      else:
         value = fragmentize(mo.group('body'),self.child_elements,
                             element_store, environ)
         if len(value) == 1:
             value = value[0]
         else:
             value = ImplicitList(value)
      name = mo.group('key')
      return (name, value)


class QuotedArg(InlineElement):
   """Finds quoted arguments"""

   def re_string(self):
      return esc_neg_look + r'(?P<quote>['+ re.escape(self.token) \
             +'])(?P<body>.*?)' + esc_neg_look + '(?P=quote)'

   def _build(self,mo,element_store, environ):
      if mo.group('body') == '':
          value = ''
      else:
          frags = fragmentize(mo.group('body'),self.child_elements,element_store, environ)
          assert len(frags) == 1
          value = frags[0]
      return value
         
class ListArg(ArgString):
   """Finds lists in argument strings 

   This is used for positional arguments only.
    
   """
    
   def re_string(self):
      return esc_neg_look + re.escape(self.token[0]) + r'(?P<body>.*?)' + esc_neg_look + re.escape(self.token[1])

   def _build(self,mo,element_store, environ):
      if mo.group('body') == '':
         value = []
      else:
         value = fragmentize(mo.group('body'),self.child_elements,element_store, environ)
      return value

class ExplicitListArg(ListArg):
    """Only finds lists where the string to be searched is fully enclosed

    This is used for keyword values in argument strings.
    
    """

    def re_string(self):
       return '^' + esc_neg_look + re.escape(self.token[0]) +r'(?P<body>.*?)' \
             + esc_neg_look+ re.escape(self.token[1]) + '$'


class WhiteSpace(ArgString):
   """Breaks up elements but doesn't add any output"""

   def re_string(self):
      return r'[ \n]+'

   def _build(self,mo,element_store, environ):
      return None



def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()    
