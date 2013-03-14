from .base_renderer import *
import textile


@renderer
class TextileRenderer(MarkupRenderer):
    @classmethod
    def is_enabled(cls, filename, syntax):
        if syntax == 'text.html.textile':
            return True
        return filename.endswith(".textile")

    def render(self, text, **kwargs):
        return textile.textile(text)
