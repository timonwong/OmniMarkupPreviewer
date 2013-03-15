from .base_renderer import *
import re


@renderer
class PodRenderer(CommandlineRenderer):
    def __init__(self):
        super(PodRenderer, self).__init__(
            executable='perl',
            args=['-MPod::Simple::HTML', '-e', 'Pod::Simple::HTML::go'])

    @classmethod
    def is_enabled(cls, filename, syntax):
        if syntax == 'source.perl':
            return True
        return filename.endswith('.pod')

    def post_process(self, rendered_text, **kwargs):
        match = re.search(r'<!-- start doc -->\s*(.+)\s*<!-- end doc -->',
                          rendered_text, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        if match is not None:
            rendered_text = match.group(1)
        return rendered_text
