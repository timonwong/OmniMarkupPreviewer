# __init__.py
# -*- coding: utf-8 -*-
#
# Copyright © Stephen Day
#
# This module is part of Creoleparser and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
#
import string
import keyword

from core import Parser, ArgParser
from dialects import (creole11_base, creole10_base, creepy10_base,
                    create_dialect, parse_args)

__docformat__ = 'restructuredtext en'

__version__ = '0.7.4'

creole2html = Parser(dialect=create_dialect(creole10_base), method='html')
"""This is a pure Creole 1.0 parser created for convenience"""

text2html = Parser(dialect=create_dialect(creole11_base), method='html')
"""This is a Creole 1.0 parser (+ additions) created for convenience"""

#parse_args = ArgParser(dialect=creepy10_base(),key_func=string.lower,
#                       illegal_keys=keyword.kwlist + ['macro_name',
#                         'arg_string', 'body', 'isblock', 'environ', 'macro'])
#"""Function for parsing macro arg_strings using a relaxed xml style"""

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()
