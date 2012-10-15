from base_renderer import *
import creoleparser


@renderer
class CreoleRenderer(MarkupRenderer):
    @classmethod
    def is_enabled(cls, filename, syntax):
        if syntax == 'text.html.creole':
            return True
        return filename.endswith(".creole")

    def render(self, text, **kwargs):
        return creoleparser.text2html(text)
