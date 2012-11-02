from base_renderer import *
import re
import markdown


@renderer
class MarkdownRenderer(MarkupRenderer):
    filename_pattern = re.compile(r'\.(md|mkdn?|mdwn|mdown|markdown)$')

    @classmethod
    def is_enabled(cls, filename, syntax):
        if syntax == "text.html.markdown":
            return True
        return cls.filename_pattern.search(filename)

    def render(self, text, **kwargs):
        renderer_options = kwargs['renderer_options']
        settings = kwargs['settings']
        if 'extensions' in renderer_options:
            extensions = renderer_options['extensions']
        else:
            # Default fallback to GFM style
            extensions = ['tables', 'strikeout', 'fenced_code', 'codehilite']

        if settings.mathjax_enabled:
            if not 'mathjax' in extensions:
                extensions.append('mathjax')

        return markdown.markdown(text, tab_length=2, output_format='html5',
            extensions=extensions
        )
