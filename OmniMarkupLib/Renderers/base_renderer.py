import subprocess
import os
import os.path
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
    def __init__(self, input_method=InputMethod.STDIN, executable=None, args=[]):
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
        text = self.post_process(text, **kwargs)
        return self.post_process_encoding(text, **kwargs)

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
        finally:
            if tempfile_ is not None:
                tempfile_.close()  # Also delete file
        return result.strip()

    def get_executable(self):
        if os.name == 'nt':
            # On Windows, popen won't support unicode args
            if isinstance(self.executable, unicode):
                encoding = locale.getpreferredencoding()
                return self.executable.encode(encoding)
        return self.executable

    def get_args(self, filename=None):
        if os.name == 'nt':
            # On Windows, popen won't support unicode args
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
