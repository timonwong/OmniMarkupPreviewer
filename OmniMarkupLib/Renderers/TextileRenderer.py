from base_renderer import *
import textile


@renderer
class TextileRenderer(MarkupRenderer):
    def is_enabled(self, filename, syntax):
        return filename.endswith(".textile")

    def render(self, text):
        return textile.textile(text)
