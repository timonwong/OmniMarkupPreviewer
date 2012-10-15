import subprocess
import os
import locale
import tempfile


class MarkupRenderer(object):
    @classmethod
    def is_enabled(cls, filename, lang):
        return False

    def render(self, text, **kwargs):
        raise NotImplementedError()


class InputMethod(object):
    STDIN = 1
    TEMPFILE = 2
    FILE = 3


class CommandlineRenderer(MarkupRenderer):
    def __init__(self, executable=None):
        self.executable=executable

    def render(self, text, **kwargs):
        self.executable_check()

    def executable_check(self, text, filename):
        tempfile_ = None
        result = u''

        try:
            args = [self.get_executable()]
            if self.input_method == InputMethod.STDIN:
                args.extend(self.get_args())
            elif self.input_method == InputMethod.TEMPFILE:
                tempfile_ = tempfile.NamedTemporaryFile()
                tempfile_.write(text)
                tempfile_.flush()

                args.extend(self.get_args(filename=tempfile_.name()))
                text = u''
            elif self.input_method == InputMethod.FILE:
                args.extend(self.get_args(filename=filename))
                text = u''
            else:
                return u''

            proc = subprocess.Popen(args, stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    startupinfo=self.get_startupinfo())
            result, _ = proc.communicate(text)
        finally:
            if tempfile_ is not None:
                tempfile_.close()  # Also delete file
        return result.strip()

    def get_executable(self):
        if os.name == 'nt':
            # On windows, popen won't support unicode args
            if isinstance(self.executable, unicode):
                encoding = locale.getpreferredencoding()
                return self.executable.encode(encoding)
        return self.executable

    def get_args(self, filename=None):
        if os.name == 'nt':
            # On windows, popen won't support unicode args
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


def renderer(renderer_type):
    renderer_type.IS_VALID_RENDERER__ = True
    return renderer_type
