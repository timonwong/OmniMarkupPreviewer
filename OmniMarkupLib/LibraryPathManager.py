"""
Copyright (c) 2013 Timon Wong

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import sys
import os

from .Common import PY3K


def _try_get_short_path(path):
    path = os.path.normpath(path)
    if not PY3K and os.name == 'nt' and isinstance(path, unicode):
        try:
            import locale
            path = path.encode(locale.getpreferredencoding())
        except:
            from ctypes import windll, create_unicode_buffer
            buf = create_unicode_buffer(512)
            if windll.kernel32.GetShortPathNameW(path, buf, len(buf)):
                path = buf.value
    return path


def add_search_path(lib_path):
    lib_path = _try_get_short_path(lib_path)
    if lib_path not in sys.path:
        sys.path.append(lib_path)
