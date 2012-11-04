from base_renderer import *
import re
import markdown


@renderer
class MarkdownRenderer(MarkupRenderer):
    FILENAME_PATTERN_RE = re.compile(r'\.(md|mkdn?|mdwn|mdown|markdown)$')

    def load_settings(self, renderer_options, global_setting):
        super(MarkdownRenderer, self).load_settings(renderer_options, global_setting)
        if 'extensions' in renderer_options:
            self.extensions = renderer_options['extensions']
        else:
            # Fallback to the default GFM style
            self.extensions = ['tables', 'strikeout', 'fenced_code', 'codehilite']
        if global_setting.mathjax_enabled:
            if 'mathjax' not in self.extensions:
                self.extensions.append('mathjax')

    @classmethod
    def is_enabled(cls, filename, syntax):
        if syntax == "text.html.markdown":
            return True
        return cls.FILENAME_PATTERN_RE.search(filename)

    def render(self, text, **kwargs):
        return markdown.markdown(text, tab_length=2, output_format='html5',
            extensions=self.extensions
        )
