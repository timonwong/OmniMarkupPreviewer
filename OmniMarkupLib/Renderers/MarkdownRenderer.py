from .base_renderer import *
import re
import markdown


@renderer
class MarkdownRenderer(MarkupRenderer):
    FILENAME_PATTERN_RE = re.compile(r'\.(md|mkdn?|mdwn|mdown|markdown|litcoffee)$')
    YAML_FRONTMATTER_RE = re.compile(r'\A---\s*\n.*?\n?^---\s*$\n?', re.DOTALL | re.MULTILINE)

    def load_settings(self, renderer_options, global_setting):
        super(MarkdownRenderer, self).load_settings(renderer_options, global_setting)
        if 'extensions' in renderer_options:
            extensions = renderer_options['extensions']
        else:
            # Fallback to the default GFM style
            extensions = ['tables', 'strikeout', 'fenced_code', 'codehilite']
        extensions = set(extensions)
        if global_setting.mathjax_enabled:
            if 'mathjax' not in extensions:
                extensions.add('mathjax')
        if 'smartypants' in extensions:
            extensions.remove('smartypants')
            extensions.add('smarty')
        self.extensions = list(extensions)

    @classmethod
    def is_enabled(cls, filename, syntax):
        if syntax == "text.html.markdown":
            return True
        return cls.FILENAME_PATTERN_RE.search(filename) is not None

    def render(self, text, **kwargs):
        text = self.YAML_FRONTMATTER_RE.sub('', text)
        return markdown.markdown(text, output_format='html5',
                                 extensions=self.extensions)
