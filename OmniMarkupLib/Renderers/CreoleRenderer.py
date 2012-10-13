from base_renderer import *
import creoleparser


@renderer
class CreoleRenderer(MarkupRenderer):
    def is_enabled(self, filename, syntax):
        if syntax == 'text.html.creole':
            return True
        return filename.endswith(".creole")

    def render(self, text):
        return creoleparser.text2html(text)
