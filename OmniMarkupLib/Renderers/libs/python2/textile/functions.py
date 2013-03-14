#!/usr/bin/env python
# -*- coding: utf-8 -*-

__copyright__ = """
Copyright (c) 2009, Jason Samsa, http://jsamsa.com/
Copyright (c) 2010, Kurt Raschke <kurt@kurtraschke.com>
Copyright (c) 2004, Roberto A. F. De Almeida, http://dealmeida.net/
Copyright (c) 2003, Mark Pilgrim, http://diveintomark.org/

Original PHP Version:
Copyright (c) 2003-2004, Dean Allen <dean@textism.com>
All rights reserved.

Thanks to Carlo Zottmann <carlo@g-blog.net> for refactoring
Textile's procedural code into a class framework

Additions and fixes Copyright (c) 2006 Alex Shiels http://thresholdstate.com/

"""

import re
import uuid
import string
from urlparse import urlparse

from textile.tools import sanitizer, imagesize


def _normalize_newlines(string):
    out = string.strip()
    out = re.sub(r'\r\n', '\n', out)
    out = re.sub(r'\n{3,}', '\n\n', out)
    out = re.sub(r'\n\s*\n', '\n\n', out)
    out = re.sub(r'"$', '" ', out)
    return out


class Textile(object):
    horizontal_align_re = r'(?:\<(?!>)|(?<!<)\>|\<\>|\=|[()]+(?! ))'
    vertical_align_re = r'[\-^~]'
    class_re = r'(?:\([^)]+\))'
    language_re = r'(?:\[[^\]]+\])'
    style_re = r'(?:\{[^}]+\})'
    colspan_re = r'(?:\\\d+)'
    rowspan_re = r'(?:\/\d+)'
    align_re = r'(?:%s|%s)*' % (horizontal_align_re, vertical_align_re)
    table_span_re = r'(?:%s|%s)*' % (colspan_re, rowspan_re)
    c = r'(?:%s)*' % '|'.join([class_re, style_re,
                               language_re, horizontal_align_re])

    pnct = r'[-!"#$%&()*+,/:;<=>?@\'\[\\\]\.^_`{|}~]'
    urlch = '[\w"$\-_.+*\'(),";\/?:@=&%#{}|\\^~\[\]`]'

    url_schemes = ('http', 'https', 'ftp', 'mailto')

    btag = ('bq', 'bc', 'notextile', 'pre', 'h[1-6]', 'fn\d+', 'p')
    btag_lite = ('bq', 'bc', 'p')

    iAlign = {'<': 'float: left;',
              '>': 'float: right;',
              '=': 'display: block; margin: 0 auto;'}
    vAlign = {'^': 'top', '-': 'middle', '~': 'bottom'}
    hAlign = {'<': 'left', '=': 'center', '>': 'right', '<>': 'justify'}

    glyph_defaults = (
        ('txt_quote_single_open',  '&#8216;'),
        ('txt_quote_single_close', '&#8217;'),
        ('txt_quote_double_open',  '&#8220;'),
        ('txt_quote_double_close', '&#8221;'),
        ('txt_apostrophe',         '&#8217;'),
        ('txt_prime',              '&#8242;'),
        ('txt_prime_double',       '&#8243;'),
        ('txt_ellipsis',           '&#8230;'),
        ('txt_emdash',             '&#8212;'),
        ('txt_endash',             '&#8211;'),
        ('txt_dimension',          '&#215;'),
        ('txt_trademark',          '&#8482;'),
        ('txt_registered',         '&#174;'),
        ('txt_copyright',          '&#169;'),
    )

    def __init__(self, restricted=False, lite=False, noimage=False,
                 auto_link=False, get_sizes=False):
        """docstring for __init__"""
        self.restricted = restricted
        self.lite = lite
        self.noimage = noimage
        self.get_sizes = get_sizes
        self.auto_link = auto_link
        self.fn = {}
        self.urlrefs = {}
        self.shelf = {}
        self.rel = ''
        self.html_type = 'xhtml'

    def textile(self, text, rel=None, head_offset=0, html_type='xhtml',
                sanitize=False):
        """
        >>> import textile
        >>> textile.textile('some textile')
        '\\t<p>some textile</p>'
        """
        self.html_type = html_type

        # text = unicode(text)
        text = _normalize_newlines(text)

        if self.restricted:
            text = self.encode_html(text, quotes=False)

        if rel:
            self.rel = ' rel="%s"' % rel

        text = self.getRefs(text)

        text = self.block(text, int(head_offset))

        text = self.retrieve(text)

        if sanitize:
            text = sanitizer.sanitize(text, self.html_type)

        return text

    def pba(self, block_attributes, element=None):
        """
        Parse block attributes.

        >>> t = Textile()
        >>> t.pba(r'\3')
        ''
        >>> t.pba(r'\\3', element='td')
        ' colspan="3"'
        >>> t.pba(r'/4', element='td')
        ' rowspan="4"'
        >>> t.pba(r'\\3/4', element='td')
        ' colspan="3" rowspan="4"'

        >>> t.pba('^', element='td')
        ' style="vertical-align:top;"'

        >>> t.pba('{line-height:18px}')
        ' style="line-height:18px;"'

        >>> t.pba('(foo-bar)')
        ' class="foo-bar"'

        >>> t.pba('(#myid)')
        ' id="myid"'

        >>> t.pba('(foo-bar#myid)')
        ' class="foo-bar" id="myid"'

        >>> t.pba('((((')
        ' style="padding-left:4em;"'

        >>> t.pba(')))')
        ' style="padding-right:3em;"'

        >>> t.pba('[fr]')
        ' lang="fr"'

        >>> rt = Textile()
        >>> rt.restricted = True
        >>> rt.pba('[en]')
        ' lang="en"'

        >>> rt.pba('(#id)')
        ''

        """
        style = []
        aclass = ''
        lang = ''
        colspan = ''
        rowspan = ''
        block_id = ''

        if not block_attributes:
            return ''

        matched = block_attributes
        if element == 'td':
            m = re.search(r'\\(\d+)', matched)
            if m:
                colspan = m.group(1)

            m = re.search(r'/(\d+)', matched)
            if m:
                rowspan = m.group(1)

        if element == 'td' or element == 'tr':
            m = re.search(r'(%s)' % self.vertical_align_re, matched)
            if m:
                style.append("vertical-align:%s;" % self.vAlign[m.group(1)])

        m = re.search(r'\{([^}]*)\}', matched)
        if m:
            style.append(m.group(1).rstrip(';') + ';')
            matched = matched.replace(m.group(0), '')

        m = re.search(r'\[([^\]]+)\]', matched, re.U)
        if m:
            lang = m.group(1)
            matched = matched.replace(m.group(0), '')

        m = re.search(r'\(([^()]+)\)', matched, re.U)
        if m:
            aclass = m.group(1)
            matched = matched.replace(m.group(0), '')

        m = re.search(r'([(]+)', matched)
        if m:
            style.append("padding-left:%sem;" % len(m.group(1)))
            matched = matched.replace(m.group(0), '')

        m = re.search(r'([)]+)', matched)
        if m:
            style.append("padding-right:%sem;" % len(m.group(1)))
            matched = matched.replace(m.group(0), '')

        m = re.search(r'(%s)' % self.horizontal_align_re, matched)
        if m:
            style.append("text-align:%s;" % self.hAlign[m.group(1)])

        m = re.search(r'^(.*)#(.*)$', aclass)
        if m:
            block_id = m.group(2)
            aclass = m.group(1)

        if self.restricted:
            if lang:
                return ' lang="%s"' % lang
            else:
                return ''

        result = []
        if style:
            result.append(' style="%s"' % "".join(style))
        if aclass:
            result.append(' class="%s"' % aclass)
        if lang:
            result.append(' lang="%s"' % lang)
        if block_id:
            result.append(' id="%s"' % block_id)
        if colspan:
            result.append(' colspan="%s"' % colspan)
        if rowspan:
            result.append(' rowspan="%s"' % rowspan)
        return ''.join(result)

    def hasRawText(self, text):
        """
        checks whether the text has text not already enclosed by a block tag

        >>> t = Textile()
        >>> t.hasRawText('<p>foo bar biz baz</p>')
        False

        >>> t.hasRawText(' why yes, yes it does')
        True

        """
        r = re.compile(r'<(p|blockquote|div|form|table|ul|ol|pre|h\d)[^>]*?>.*</\1>',
                       re.S).sub('', text.strip()).strip()
        r = re.compile(r'<(hr|br)[^>]*?/>').sub('', r)
        return '' != r

    def table(self, text):
        r"""
        >>> t = Textile()
        >>> t.table('(rowclass). |one|two|three|\n|a|b|c|')
        '\t<table>\n\t\t<tr class="rowclass">\n\t\t\t<td>one</td>\n\t\t\t<td>two</td>\n\t\t\t<td>three</td>\n\t\t</tr>\n\t\t<tr>\n\t\t\t<td>a</td>\n\t\t\t<td>b</td>\n\t\t\t<td>c</td>\n\t\t</tr>\n\t</table>\n\n'
        """
        text = text + "\n\n"
        pattern = re.compile(r'^(?:table(_?%(s)s%(a)s%(c)s)\. ?\n)?^(%(a)s%(c)s\.? ?\|.*\|)\n\n'
                             % {'s': self.table_span_re,
                                'a': self.align_re,
                                'c': self.c},
                             re.S | re.M | re.U)
        return pattern.sub(self.fTable, text)

    def fTable(self, match):
        tatts = self.pba(match.group(1), 'table')
        rows = []
        for row in [x for x in match.group(2).split('\n') if x]:
            rmtch = re.search(r'^(%s%s\. )(.*)'
                              % (self.align_re, self.c), row.lstrip())
            if rmtch:
                ratts = self.pba(rmtch.group(1), 'tr')
                row = rmtch.group(2)
            else:
                ratts = ''

            cells = []
            for cell in row.split('|')[1:-1]:
                ctyp = 'd'
                if re.search(r'^_', cell):
                    ctyp = "h"
                cmtch = re.search(r'^(_?%s%s%s\. )(.*)'
                                  % (self.table_span_re,
                                     self.align_re,
                                     self.c),
                                  cell)
                if cmtch:
                    catts = self.pba(cmtch.group(1), 'td')
                    cell = cmtch.group(2)
                else:
                    catts = ''

                cell = self.graf(self.span(cell))
                cells.append('\t\t\t<t%s%s>%s</t%s>'
                             % (ctyp, catts, cell, ctyp))
            rows.append("\t\t<tr%s>\n%s\n\t\t</tr>"
                        % (ratts, '\n'.join(cells)))
            cells = []
            catts = None
        return "\t<table%s>\n%s\n\t</table>\n\n" % (tatts, '\n'.join(rows))

    def lists(self, text):
        """
        >>> t = Textile()
        >>> t.lists("* one\\n* two\\n* three")
        '\\t<ul>\\n\\t\\t<li>one</li>\\n\\t\\t<li>two</li>\\n\\t\\t<li>three</li>\\n\\t</ul>'
        """

        #Replace line-initial bullets with asterisks
        bullet_pattern = re.compile(u'^•', re.U | re.M)

        pattern = re.compile(r'^([#*]+%s .*)$(?![^#*])'
                             % self.c, re.U | re.M | re.S)
        return pattern.sub(self.fList, bullet_pattern.sub('*', text))

    def fList(self, match):
        text = match.group(0).split("\n")
        result = []
        lists = []
        for i, line in enumerate(text):
            try:
                nextline = text[i + 1]
            except IndexError:
                nextline = ''

            m = re.search(r"^([#*]+)(%s%s) (.*)$" % (self.align_re,
                                                     self.c), line, re.S)
            if m:
                tl, atts, content = m.groups()
                nl = ''
                nm = re.search(r'^([#*]+)\s.*', nextline)
                if nm:
                    nl = nm.group(1)
                if tl not in lists:
                    lists.append(tl)
                    atts = self.pba(atts)
                    line = "\t<%sl%s>\n\t\t<li>%s" % (self.listType(tl),
                                                      atts, self.graf(content))
                else:
                    line = "\t\t<li>" + self.graf(content)

                if len(nl) <= len(tl):
                    line = line + "</li>"
                for k in reversed(lists):
                    if len(k) > len(nl):
                        line = line + "\n\t</%sl>" % self.listType(k)
                        if len(k) > 1:
                            line = line + "</li>"
                        lists.remove(k)

            result.append(line)
        return "\n".join(result)

    def listType(self, list_string):
        if re.search(r'^#+', list_string):
            return 'o'
        else:
            return 'u'

    def doPBr(self, in_):
        return re.compile(r'<(p)([^>]*?)>(.*)(</\1>)', re.S).sub(self.doBr,
                                                                 in_)

    def doBr(self, match):
        if self.html_type == 'html':
            content = re.sub(r'(.+)(?:(?<!<br>)|(?<!<br />))\n(?![#*\s|])', '\\1<br>',
                             match.group(3))
        else:
            content = re.sub(r'(.+)(?:(?<!<br>)|(?<!<br />))\n(?![#*\s|])', '\\1<br />',
                             match.group(3))
        return '<%s%s>%s%s' % (match.group(1), match.group(2),
                               content, match.group(4))

    def block(self, text, head_offset=0):
        """
        >>> t = Textile()
        >>> t.block('h1. foobar baby')
        '\\t<h1>foobar baby</h1>'
        """
        if not self.lite:
            tre = '|'.join(self.btag)
        else:
            tre = '|'.join(self.btag_lite)
        text = text.split('\n\n')

        tag = 'p'
        atts = cite = graf = ext = ''
        c1 = ''

        out = []

        anon = False
        for line in text:
            pattern = r'^(%s)(%s%s)\.(\.?)(?::(\S+))? (.*)$' % (tre,
                                                                self.align_re,
                                                                self.c)
            match = re.search(pattern, line, re.S)
            if match:
                if ext:
                    out.append(out.pop() + c1)

                tag, atts, ext, cite, graf = match.groups()
                h_match = re.search(r'h([1-6])', tag)
                if h_match:
                    head_level, = h_match.groups()
                    tag = 'h%i' % max(1,
                                      min(int(head_level) + head_offset,
                                          6))
                o1, o2, content, c2, c1 = self.fBlock(tag, atts, ext,
                                                      cite, graf)
                # leave off c1 if this block is extended,
                # we'll close it at the start of the next block

                if ext:
                    line = "%s%s%s%s" % (o1, o2, content, c2)
                else:
                    line = "%s%s%s%s%s" % (o1, o2, content, c2, c1)

            else:
                anon = True
                if ext or not re.search(r'^\s', line):
                    o1, o2, content, c2, c1 = self.fBlock(tag, atts, ext,
                                                          cite, line)
                    # skip $o1/$c1 because this is part of a continuing
                    # extended block
                    if tag == 'p' and not self.hasRawText(content):
                        line = content
                    else:
                        line = "%s%s%s" % (o2, content, c2)
                else:
                    line = self.graf(line)

            line = self.doPBr(line)
            if self.html_type == 'xhtml':
                line = re.sub(r'<br>', '<br />', line)

            if ext and anon:
                out.append(out.pop() + "\n" + line)
            else:
                out.append(line)

            if not ext:
                tag = 'p'
                atts = ''
                cite = ''
                graf = ''

        if ext:
            out.append(out.pop() + c1)
        return '\n\n'.join(out)

    def fBlock(self, tag, atts, ext, cite, content):
        """
        >>> t = Textile()
        >>> t.fBlock("bq", "", None, "", "Hello BlockQuote")
        ('\\t<blockquote>\\n', '\\t\\t<p>', 'Hello BlockQuote', '</p>', '\\n\\t</blockquote>')

        >>> t.fBlock("bq", "", None, "http://google.com", "Hello BlockQuote")
        ('\\t<blockquote cite="http://google.com">\\n', '\\t\\t<p>', 'Hello BlockQuote', '</p>', '\\n\\t</blockquote>')

        >>> t.fBlock("bc", "", None, "", 'printf "Hello, World";') # doctest: +ELLIPSIS
        ('<pre>', '<code>', ..., '</code>', '</pre>')

        >>> t.fBlock("h1", "", None, "", "foobar")
        ('', '\\t<h1>', 'foobar', '</h1>', '')
        """
        atts = self.pba(atts)
        o1 = o2 = c2 = c1 = ''

        m = re.search(r'fn(\d+)', tag)
        if m:
            tag = 'p'
            if m.group(1) in self.fn:
                fnid = self.fn[m.group(1)]
            else:
                fnid = m.group(1)
            atts = atts + ' id="fn%s"' % fnid
            if atts.find('class=') < 0:
                atts = atts + ' class="footnote"'
            content = ('<sup>%s</sup>' % m.group(1)) + content

        if tag == 'bq':
            cite = self.checkRefs(cite)
            if cite:
                cite = ' cite="%s"' % cite
            else:
                cite = ''
            o1 = "\t<blockquote%s%s>\n" % (cite, atts)
            o2 = "\t\t<p%s>" % atts
            c2 = "</p>"
            c1 = "\n\t</blockquote>"

        elif tag == 'bc':
            o1 = "<pre%s>" % atts
            o2 = "<code%s>" % atts
            c2 = "</code>"
            c1 = "</pre>"
            content = self.shelve(self.encode_html(content.rstrip("\n") +
                                                   "\n"))

        elif tag == 'notextile':
            content = self.shelve(content)
            o1 = o2 = ''
            c1 = c2 = ''

        elif tag == 'pre':
            content = self.shelve(self.encode_html(content.rstrip("\n") +
                                                   "\n"))
            o1 = "<pre%s>" % atts
            o2 = c2 = ''
            c1 = '</pre>'

        else:
            o2 = "\t<%s%s>" % (tag, atts)
            c2 = "</%s>" % tag

        content = self.graf(content)
        return o1, o2, content, c2, c1

    def footnoteRef(self, text):
        """
        >>> t = Textile()
        >>> t.footnoteRef('foo[1] ') # doctest: +ELLIPSIS
        'foo<sup class="footnote"><a href="#fn...">1</a></sup> '
        """
        return re.compile(r'\b\[([0-9]+)\](\s)?', re.U).sub(self.footnoteID,
                                                            text)

    def footnoteID(self, match):
        footnoteNum, text = match.groups()
        if footnoteNum not in self.fn:
            self.fn[footnoteNum] = str(uuid.uuid4())
        footnoteID = self.fn[footnoteNum]
        if not text:
            text = ''
        return '<sup class="footnote"><a href="#fn%s">%s</a></sup>%s' % (
            footnoteID, footnoteNum, text)

    def glyphs(self, text):
        """
        >>> t = Textile()

        >>> t.glyphs("apostrophe's")
        'apostrophe&#8217;s'

        >>> t.glyphs("back in '88")
        'back in &#8217;88'

        >>> t.glyphs('foo ...')
        'foo &#8230;'

        >>> t.glyphs('--')
        '&#8212;'

        >>> t.glyphs('FooBar[tm]')
        'FooBar&#8482;'

        >>> t.glyphs("<p><cite>Cat's Cradle</cite> by Vonnegut</p>")
        '<p><cite>Cat&#8217;s Cradle</cite> by Vonnegut</p>'

        """
         # fix: hackish
        text = re.sub(r'"\Z', '\" ', text)

        glyph_search = (
            # apostrophe's
            re.compile(r"(\w)\'(\w)"),
            # back in '88
            re.compile(r'(\s)\'(\d+\w?)\b(?!\')'),
            # single closing
            re.compile(r'(\S)\'(?=\s|' + self.pnct + '|<|$)'),
            # single opening
            re.compile(r'\'/'),
            # double closing
            re.compile(r'(\S)\"(?=\s|' + self.pnct + '|<|$)'),
            # double opening
            re.compile(r'"'),
            # 3+ uppercase acronym
            re.compile(r'\b([A-Z][A-Z0-9]{2,})\b(?:[(]([^)]*)[)])'),
            # 3+ uppercase
            re.compile(r'\b([A-Z][A-Z\'\-]+[A-Z])(?=[\s.,\)>])'),
            # ellipsis
            re.compile(r'\b(\s{0,1})?\.{3}'),
            # em dash
            re.compile(r'(\s?)--(\s?)'),
            # en dash
            re.compile(r'\s-(?:\s|$)'),
            # dimension sign
            re.compile(r'(\d+)( ?)x( ?)(?=\d+)'),
            # trademark
            re.compile(r'\b ?[([]TM[])]', re.I),
            # registered
            re.compile(r'\b ?[([]R[])]', re.I),
            # copyright
            re.compile(r'\b ?[([]C[])]', re.I),
         )

        glyph_replace = [x % dict(self.glyph_defaults) for x in (
            r'\1%(txt_apostrophe)s\2',            # apostrophe's
            r'\1%(txt_apostrophe)s\2',            # back in '88
            r'\1%(txt_quote_single_close)s',      # single closing
            r'%(txt_quote_single_open)s',         # single opening
            r'\1%(txt_quote_double_close)s',      # double closing
            r'%(txt_quote_double_open)s',         # double opening
            r'<acronym title="\2">\1</acronym>',  # 3+ uppercase acronym
            r'<span class="caps">\1</span>',      # 3+ uppercase
            r'\1%(txt_ellipsis)s',                # ellipsis
            r'\1%(txt_emdash)s\2',                # em dash
            r' %(txt_endash)s ',                  # en dash
            r'\1\2%(txt_dimension)s\3',           # dimension sign
            r'%(txt_trademark)s',                 # trademark
            r'%(txt_registered)s',                # registered
            r'%(txt_copyright)s',                 # copyright
        )]

        result = []
        for line in re.compile(r'(<.*?>)', re.U).split(text):
            if not re.search(r'<.*>', line):
                for s, r in zip(glyph_search, glyph_replace):
                    line = s.sub(r, line)
            result.append(line)
        return ''.join(result)

    def getRefs(self, text):
        """
        Capture and store URL references in self.urlrefs.

        >>> t = Textile()
        >>> t.getRefs("some text [Google]http://www.google.com")
        'some text '
        >>> t.urlrefs
        {'Google': 'http://www.google.com'}

        """
        pattern = re.compile(r'(?:(?<=^)|(?<=\s))\[(.+)\]((?:http(?:s?):\/\/|\/)\S+)(?=\s|$)', re.U)
        text = pattern.sub(self.refs, text)
        return text

    def refs(self, match):
        flag, url = match.groups()
        self.urlrefs[flag] = url
        return ''

    def checkRefs(self, url):
        return self.urlrefs.get(url, url)

    def isRelURL(self, url):
        """
        Identify relative urls.

        >>> t = Textile()
        >>> t.isRelURL("http://www.google.com/")
        False
        >>> t.isRelURL("/foo")
        True

        """
        (scheme, netloc) = urlparse(url)[0:2]
        return not scheme and not netloc

    def relURL(self, url):
        """
        >>> t = Textile()
        >>> t.relURL("http://www.google.com/")
        'http://www.google.com/'
        >>> t.restricted = True
        >>> t.relURL("gopher://gopher.com/")
        '#'

        """
        scheme = urlparse(url)[0]
        if self.restricted and scheme and scheme not in self.url_schemes:
            return '#'
        return url

    def shelve(self, text):
        itemID = str(uuid.uuid4())
        self.shelf[itemID] = text
        return itemID

    def retrieve(self, text):
        """
        >>> t = Textile()
        >>> id = t.shelve("foobar")
        >>> t.retrieve(id)
        'foobar'
        """
        while True:
            old = text
            for k, v in self.shelf.items():
                text = text.replace(k, v)
            if text == old:
                break
        return text

    def encode_html(self, text, quotes=True):
        a = (
            ('&', '&#38;'),
            ('<', '&#60;'),
            ('>', '&#62;'))

        if quotes:
            a = a + (("'", '&#39;'),
                     ('"', '&#34;'))

        for k, v in a:
            text = text.replace(k, v)
        return text

    def graf(self, text):
        if not self.lite:
            text = self.noTextile(text)
            text = self.code(text)

        if self.auto_link:
            text = self.autoLink(text)
        text = self.links(text)

        if not self.noimage:
            text = self.image(text)

        text = self.lists(text)

        if not self.lite:
            text = self.table(text)

        text = self.span(text)
        text = self.footnoteRef(text)
        text = self.glyphs(text)

        return text.rstrip('\n')

    def autoLink(self, text):
        """
        >>> t = Textile()
        >>> t.autoLink("http://www.ya.ru")
        '"http://www.ya.ru":http://www.ya.ru'
        """

        pattern = re.compile(r"""\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))""", re.U | re.I)
        return pattern.sub(r'"\1":\1', text)

    def links(self, text):
        """
        >>> t = Textile()
        >>> t.links('fooobar "Google":http://google.com/foobar/ and hello world "flickr":http://flickr.com/photos/jsamsa/ ') # doctest: +ELLIPSIS
        'fooobar ... and hello world ...'
        """

        punct = '!"#$%&\'*+,-./:;=?@\\^_`|~'

        pattern = r'''
            (?P<pre>[\s\[{(]|[%s])?         #leading text
            "                               #opening quote
            (?P<atts>%s)                    #block attributes
            (?P<text>[^"]+?)                #link text
            \s?
            (?:\((?P<title>[^)]+?)\)(?="))? #optional title
            ":                              #closing quote, colon
            (?P<url>(?:ftp|https?)?         #URL
                        (?: :// )?
                        [-A-Za-z0-9+&@#/?=~_()|!:,.;%%]*
                        [-A-Za-z0-9+&@#/=~_()|]
            )
            (?P<post>[^\w\/;]*?)	    #trailing text
            (?=<|\s|$)
        ''' % (re.escape(punct), self.c)

        text = re.compile(pattern, re.X).sub(self.fLink, text)

        return text

    def fLink(self, match):
        pre, atts, text, title, url, post = match.groups()

        if pre == None:
            pre = ''

        # assume ) at the end of the url is not actually part of the url
        # unless the url also contains a (
        if url.endswith(')') and not url.find('(') > -1:
            post = url[-1] + post
            url = url[:-1]

        url = self.checkRefs(url)

        atts = self.pba(atts)
        if title:
            atts = atts + ' title="%s"' % self.encode_html(title)

        if not self.noimage:
            text = self.image(text)

        text = self.span(text)
        text = self.glyphs(text)

        url = self.relURL(url)
        out = '<a href="%s"%s%s>%s</a>' % (self.encode_html(url),
                                           atts, self.rel, text)
        out = self.shelve(out)
        return ''.join([pre, out, post])

    def span(self, text):
        """
        >>> t = Textile()
        >>> t.span(r"hello %(bob)span *strong* and **bold**% goodbye")
        'hello <span class="bob">span <strong>strong</strong> and <b>bold</b></span> goodbye'
        """
        qtags = (r'\*\*', r'\*', r'\?\?', r'\-', r'__',
                 r'_', r'%', r'\+', r'~', r'\^')
        pnct = ".,\"'?!;:("

        for qtag in qtags:
            pattern = re.compile(r"""
                (?:^|(?<=[\s>%(pnct)s])|([\[{]))
                (%(qtag)s)(?!%(qtag)s)
                (%(c)s)
                (?::\(([^)]+?)\))?
                ([^\s%(qtag)s]+|\S[^%(qtag)s\n]*[^\s%(qtag)s\n])
                ([%(pnct)s]*)
                %(qtag)s
                (?:$|([\]}])|(?=%(selfpnct)s{1,2}|\s))
            """ % {'qtag': qtag, 'c': self.c, 'pnct': pnct,
                   'selfpnct': self.pnct}, re.X)
            text = pattern.sub(self.fSpan, text)
        return text

    def fSpan(self, match):
        _, tag, atts, cite, content, end, _ = match.groups()

        qtags = {'*': 'strong',
                '**': 'b',
                '??': 'cite',
                 '_': 'em',
                '__': 'i',
                 '-': 'del',
                 '%': 'span',
                 '+': 'ins',
                 '~': 'sub',
                 '^': 'sup'}

        tag = qtags[tag]
        atts = self.pba(atts)
        if cite:
            atts = atts + ' cite="%s"' % cite

        content = self.span(content)

        out = "<%s%s>%s%s</%s>" % (tag, atts, content, end, tag)
        return out

    def image(self, text):
        """
        >>> t = Textile()
        >>> t.image('!/imgs/myphoto.jpg!:http://jsamsa.com')
        '<a href="http://jsamsa.com" class="img"><img src="/imgs/myphoto.jpg" alt="" /></a>'
        >>> t.image('!</imgs/myphoto.jpg!')
        '<img src="/imgs/myphoto.jpg" style="float: left;" alt="" />'
        """
        pattern = re.compile(r"""
            (?:[\[{])?         # pre
            \!                 # opening !
            (\<|\=|\>)?        # optional alignment atts
            (%s)               # optional style,class atts
            (?:\. )?           # optional dot-space
            ([^\s(!]+)         # presume this is the src
            \s?                # optional space
            (?:\(([^\)]+)\))?  # optional title
            \!                 # closing
            (?::(\S+))?        # optional href
            (?:[\]}]|(?=\s|$)) # lookahead: space or end of string
        """ % self.c, re.U | re.X)
        return pattern.sub(self.fImage, text)

    def fImage(self, match):
        # (None, '', '/imgs/myphoto.jpg', None, None)
        align, atts, url, title, href = match.groups()
        atts = self.pba(atts)

        if align:
            atts = atts + ' style="%s"' % self.iAlign[align]

        if title:
            atts = atts + ' title="%s" alt="%s"' % (title, title)
        else:
            atts = atts + ' alt=""'

        if not self.isRelURL(url) and self.get_sizes:
            size = imagesize.getimagesize(url)
            if size:
                atts += " %s" % size

        if href:
            href = self.checkRefs(href)

        url = self.checkRefs(url)
        url = self.relURL(url)

        out = []
        if href:
            out.append('<a href="%s" class="img">' % href)
        if self.html_type == 'html':
            out.append('<img src="%s"%s>' % (url, atts))
        else:
            out.append('<img src="%s"%s />' % (url, atts))
        if href:
            out.append('</a>')

        return ''.join(out)

    def code(self, text):
        text = self.doSpecial(text, '<code>', '</code>', self.fCode)
        text = self.doSpecial(text, '@', '@', self.fCode)
        text = self.doSpecial(text, '<pre>', '</pre>', self.fPre)
        return text

    def fCode(self, match):
        before, text, after = match.groups()
        if after == None:
            after = ''
        # text needs to be escaped
        if not self.restricted:
            text = self.encode_html(text, quotes=False)
        return ''.join([before, self.shelve('<code>%s</code>' % text), after])

    def fPre(self, match):
        before, text, after = match.groups()
        if after == None:
            after = ''
        # text needs to be escaped
        if not self.restricted:
            text = self.encode_html(text)
        return ''.join([before, '<pre>', self.shelve(text), '</pre>', after])

    def doSpecial(self, text, start, end, method):
        pattern = re.compile(r'(^|\s|[\[({>|])%s(.*?)%s($|[\])}])?'
                             % (re.escape(start), re.escape(end)), re.M | re.S)
        return pattern.sub(method, text)

    def noTextile(self, text):
        text = self.doSpecial(text, '<notextile>', '</notextile>',
                              self.fTextile)
        return self.doSpecial(text, '==', '==', self.fTextile)

    def fTextile(self, match):
        before, notextile, after = match.groups()
        if after == None:
            after = ''
        return ''.join([before, self.shelve(notextile), after])


def textile(text, head_offset=0, html_type='xhtml', auto_link=False,
            encoding=None, output=None):
    """
    Apply Textile to a block of text.

    This function takes the following additional parameters:

    auto_link - enable automatic linking of URLs (default: False)
    head_offset - offset to apply to heading levels (default: 0)
    html_type - 'xhtml' or 'html' style tags (default: 'xhtml')

    """
    return Textile(auto_link=auto_link).textile(text, head_offset=head_offset,
                                                  html_type=html_type)


def textile_restricted(text, lite=True, noimage=True, html_type='xhtml',
                       auto_link=False):
    """
    Apply Textile to a block of text, with restrictions designed for weblog
    comments and other untrusted input.  Raw HTML is escaped, style attributes
    are disabled, and rel='nofollow' is added to external links.

    This function takes the following additional parameters:

    auto_link - enable automatic linking of URLs (default: False)
    html_type - 'xhtml' or 'html' style tags (default: 'xhtml')
    lite - restrict block tags to p, bq, and bc, disable tables (default: True)
    noimage - disable image tags (default: True)

    """
    return Textile(restricted=True, lite=lite,
                   noimage=noimage, auto_link=auto_link).textile(
        text, rel='nofollow', html_type=html_type)
