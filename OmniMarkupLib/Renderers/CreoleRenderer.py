from .base_renderer import *
import sys
import creoleparser

g_is_py3k = sys.version_info >= (3, 0, 0)


@renderer
class CreoleRenderer(MarkupRenderer):
    @classmethod
    def is_enabled(cls, filename, syntax):
        if syntax == 'text.html.creole':
            return True
        return filename.endswith(".creole")

    def render(self, text, **kwargs):
        result = creoleparser.text2html(text)
        if g_is_py3k and isinstance(result, bytes):
            result = result.decode('utf-8')
        return result
