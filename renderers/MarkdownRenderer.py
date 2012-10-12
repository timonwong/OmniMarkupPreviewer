from base_renderer import *
import markdown


@renderer
class Renderer(MarkupRenderer):
    def is_enabled(self, filename, syntax):
        return syntax == "text.html.markdown"

    def render(self, text):
        return markdown.markdown(text, tab_length=2, output_format='html5')
