from base_renderer import *
import re
import markdown


@renderer
class Renderer(MarkupRenderer):
    filename_pattern = re.compile(r'\.(md|mkdn?|mdwn|mdown|markdown)$')

    @classmethod
    def is_enabled(cls, filename, syntax):
        if syntax == "text.html.markdown":
            return True
        return cls.filename_pattern.search(filename)

    def render(self, text):
        return markdown.markdown(text, tab_length=2, output_format='html5')
