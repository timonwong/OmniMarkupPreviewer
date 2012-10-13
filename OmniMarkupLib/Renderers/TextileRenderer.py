from base_renderer import *
import textile


@renderer
class TextileRenderer(MarkupRenderer):
    @classmethod
    def is_enabled(cls, filename, syntax):
        return filename.endswith(".textile")

    def render(self, text):
        return textile.textile(text)
