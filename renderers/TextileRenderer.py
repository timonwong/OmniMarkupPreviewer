from OmniMarkupLib.RendererManager import *
import textile


@RendererManager.register
class TextileRenderer(MarkupRenderer):
    def is_enabled(self, filename, syntax):
        return filename.endswith(".textile")

    def render(self, text):
        return textile.textile(text)
