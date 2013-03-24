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

from __future__ import print_function

import locale
import os
import subprocess
import sys
import tempfile

PY3K = sys.version_info >= (3, 0, 0)


class MarkupRenderer(object):
    def __init__(self):
        self.renderer_options = {}

    def load_settings(self, global_setting, renderer_options):
        self.renderer_options = renderer_options

    @classmethod
    def is_enabled(cls, filename, syntax):
        return False

    def render(self, text, **kwargs):
        raise NotImplementedError()


class InputMethod(object):
    STDIN = 1
    TEMPFILE = 2
    FILE = 3


class CommandlineRenderer(MarkupRenderer):
    def __init__(self, input_method=InputMethod.STDIN, executable=None, args=[]):
        super(CommandlineRenderer, self).__init__()
        self.input_method = input_method
        self.executable = executable
        self.args = args

    def pre_process_encoding(self, text, **kwargs):
        return text.encode('utf-8')

    def pre_process(self, text, **kwargs):
        return text

    def post_process(self, rendered_text, **kwargs):
        return rendered_text

    def post_process_encoding(self, rendered_text, **kwargs):
        return rendered_text.decode('utf-8')

    def render(self, text, **kwargs):
        text = self.pre_process_encoding(text, **kwargs)
        text = self.pre_process(text, **kwargs)
        text = self.executable_check(text, kwargs['filename'])
        text = self.post_process_encoding(text, **kwargs)
        return self.post_process(text, **kwargs)

    def executable_check(self, text, filename):
        tempfile_ = None
        result = ''

        try:
            args = [self.get_executable()]
            if self.input_method == InputMethod.STDIN:
                args.extend(self.get_args())
            elif self.input_method == InputMethod.TEMPFILE:
                _, ext = os.path.splitext(filename)
                tempfile_ = tempfile.NamedTemporaryFile(suffix=ext)
                tempfile_.write(text)
                tempfile_.flush()

                args.extend(self.get_args(filename=tempfile_.name()))
                text = None
            elif self.input_method == InputMethod.FILE:
                args.extend(self.get_args(filename=filename))
                text = None
            else:
                return u''

            proc = subprocess.Popen(args, stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    startupinfo=self.get_startupinfo())
            result, errdata = proc.communicate(text)
            if len(errdata) > 0:
                print(errdata)
        finally:
            if tempfile_ is not None:
                tempfile_.close()  # Also delete file
        return result.strip()

    def get_executable(self):
        if not PY3K and os.name == 'nt':
            # [PY2K] On Windows, popen won't support unicode args
            if isinstance(self.executable, unicode):
                encoding = locale.getpreferredencoding()
                return self.executable.encode(encoding)
        return self.executable

    def get_args(self, filename=None):
        if not PY3K and os.name == 'nt':
            # [PY2K] On Windows, popen won't support unicode args
            encoding = locale.getpreferredencoding()
            args = [arg if isinstance(arg, str) else arg.encode(encoding) for arg in self.args]
        else:
            args = self.args
        return [arg.format(filename=filename) for arg in args]

    def get_startupinfo(self):
        if os.name != 'nt':
            return None
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = subprocess.SW_HIDE
        return info


def renderer(renderer_type):
    renderer_type.IS_VALID_RENDERER__ = True
    return renderer_type
