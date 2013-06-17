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

"""Various utility classes and functions."""

import html.entities as entities
import re

from .compat import any, all, stringrepr

__docformat__ = 'restructuredtext en'


class LRUCache(dict):
    """A dictionary-like object that stores only a certain number of items, and
    discards its least recently used item when full.
    
    >>> cache = LRUCache(3)
    >>> cache['A'] = 0
    >>> cache['B'] = 1
    >>> cache['C'] = 2
    >>> len(cache)
    3
    
    >>> cache['A']
    0
    
    Adding new items to the cache does not increase its size. Instead, the least
    recently used item is dropped:
    
    >>> cache['D'] = 3
    >>> len(cache)
    3
    >>> 'B' in cache
    False
    
    Iterating over the cache returns the keys, starting with the most recently
    used:
    
    >>> for key in cache:
    ...     print(key)
    D
    A
    C

    This code is based on the LRUCache class from ``myghtyutils.util``, written
    by Mike Bayer and released under the MIT license. See:

      http://svn.myghty.org/myghtyutils/trunk/lib/myghtyutils/util.py
    """

    class _Item(object):
        def __init__(self, key, value):
            self.prv = self.nxt = None
            self.key = key
            self.value = value
        def __repr__(self):
            return repr(self.value)

    def __init__(self, capacity):
        self._dict = dict()
        self.capacity = capacity
        self.head = None
        self.tail = None

    def __contains__(self, key):
        return key in self._dict

    def __iter__(self):
        cur = self.head
        while cur:
            yield cur.key
            cur = cur.nxt

    def __len__(self):
        return len(self._dict)

    def __getitem__(self, key):
        item = self._dict[key]
        self._update_item(item)
        return item.value

    def __setitem__(self, key, value):
        item = self._dict.get(key)
        if item is None:
            item = self._Item(key, value)
            self._dict[key] = item
            self._insert_item(item)
        else:
            item.value = value
            self._update_item(item)
            self._manage_size()

    def __repr__(self):
        return repr(self._dict)

    def _insert_item(self, item):
        item.prv = None
        item.nxt = self.head
        if self.head is not None:
            self.head.prv = item
        else:
            self.tail = item
        self.head = item
        self._manage_size()

    def _manage_size(self):
        while len(self._dict) > self.capacity:
            olditem = self._dict[self.tail.key]
            del self._dict[self.tail.key]
            if self.tail != self.head:
                self.tail = self.tail.prv
                self.tail.nxt = None
            else:
                self.head = self.tail = None

    def _update_item(self, item):
        if self.head == item:
            return

        prv = item.prv
        prv.nxt = item.nxt
        if item.nxt is not None:
            item.nxt.prv = prv
        else:
            self.tail = prv

        item.prv = None
        item.nxt = self.head
        self.head.prv = self.head = item


def flatten(items):
    """Flattens a potentially nested sequence into a flat list.
    
    :param items: the sequence to flatten
    
    >>> flatten((1, 2))
    [1, 2]
    >>> flatten([1, (2, 3), 4])
    [1, 2, 3, 4]
    >>> flatten([1, (2, [3, 4]), 5])
    [1, 2, 3, 4, 5]
    """
    retval = []
    for item in items:
        if isinstance(item, (frozenset, list, set, tuple)):
            retval += flatten(item)
        else:
            retval.append(item)
    return retval


def plaintext(text, keeplinebreaks=True):
    """Return the text with all entities and tags removed.
    
    >>> plaintext('<b>1 &lt; 2</b>')
    '1 < 2'
    
    The `keeplinebreaks` parameter can be set to ``False`` to replace any line
    breaks by simple spaces:
    
    >>> plaintext('''<b>1
    ... &lt;
    ... 2</b>''', keeplinebreaks=False)
    '1 < 2'
    
    :param text: the text to convert to plain text
    :param keeplinebreaks: whether line breaks in the text should be kept intact
    :return: the text with tags and entities removed
    """
    text = stripentities(striptags(text))
    if not keeplinebreaks:
        text = text.replace('\n', ' ')
    return text


_STRIPENTITIES_RE = re.compile(r'&(?:#((?:\d+)|(?:[xX][0-9a-fA-F]+));?|(\w+);)')
def stripentities(text, keepxmlentities=False):
    """Return a copy of the given text with any character or numeric entities
    replaced by the equivalent UTF-8 characters.
    
    >>> stripentities('1 &lt; 2')
    '1 < 2'
    >>> stripentities('more &hellip;')
    'more \u2026'
    >>> stripentities('&#8230;')
    '\u2026'
    >>> stripentities('&#x2026;')
    '\u2026'
    
    If the `keepxmlentities` parameter is provided and is a truth value, the
    core XML entities (&amp;, &apos;, &gt;, &lt; and &quot;) are left intact.
    
    >>> stripentities('1 &lt; 2 &hellip;', keepxmlentities=True)
    '1 &lt; 2 \u2026'
    """
    def _replace_entity(match):
        if match.group(1): # numeric entity
            ref = match.group(1)
            if ref.startswith('x'):
                ref = int(ref[1:], 16)
            else:
                ref = int(ref, 10)
            return chr(ref)
        else: # character entity
            ref = match.group(2)
            if keepxmlentities and ref in ('amp', 'apos', 'gt', 'lt', 'quot'):
                return '&%s;' % ref
            try:
                return chr(entities.name2codepoint[ref])
            except KeyError:
                if keepxmlentities:
                    return '&amp;%s;' % ref
                else:
                    return ref
    return _STRIPENTITIES_RE.sub(_replace_entity, text)


_STRIPTAGS_RE = re.compile(r'(<!--.*?-->|<[^>]*>)')
def striptags(text):
    """Return a copy of the text with any XML/HTML tags removed.
    
    >>> striptags('<span>Foo</span> bar')
    'Foo bar'
    >>> striptags('<span class="bar">Foo</span>')
    'Foo'
    >>> striptags('Foo<br />')
    'Foo'
    
    HTML/XML comments are stripped, too:
    
    >>> striptags('<!-- <blub>hehe</blah> -->test')
    'test'
    
    :param text: the string to remove tags from
    :return: the text with tags removed
    """
    return _STRIPTAGS_RE.sub('', text)

