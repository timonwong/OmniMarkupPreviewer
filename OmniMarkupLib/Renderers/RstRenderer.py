from .base_renderer import *
import os
import re
import docutils.writers.html4css1
from docutils.core import publish_parts
from docutils.writers.html4css1 import Writer, HTMLTranslator

docutils_dir = os.path.dirname(docutils.writers.html4css1.__file__)


class GitHubHTMLTranslator(HTMLTranslator):
    def visit_literal_block(self, node):
        classes = node.attributes['classes']
        if len(classes) >= 2 and classes[0] == 'code':
            language = classes[1]
            del classes[:]
            self.body.append(self.starttag(node, 'pre', lang=language, CLASS='codehilite'))
        else:
            self.body.append(self.starttag(node, 'pre', CLASS='codehilite'))


@renderer
class RstRenderer(MarkupRenderer):
    FILENAME_PATTERN_RE = re.compile(r'\.re?st$')

    @classmethod
    def is_enabled(cls, filename, syntax):
        if syntax == "text.restructuredtext":
            return True
        return cls.FILENAME_PATTERN_RE.search(filename) is not None

    def render(self, text, **kwargs):
        settings_overrides = {
            'cloak_email_addresses': True,
            'file_insertion_enabled': False,
            'raw_enabled': False,
            'strip_comments': True,
            'doctitle_xform': False,
            'report_level': 5,
            'syntax_highlight': 'short',
            'math_output': 'latex',
            'input_encoding': 'utf-8',
            'output_encoding': 'utf-8',
            'stylesheet_dirs': [os.path.normpath(os.path.join(docutils_dir, Writer.default_stylesheet))],
            'template': os.path.normpath(os.path.join(docutils_dir, Writer.default_template))
        }

        writer = Writer()
        writer.translator_class = GitHubHTMLTranslator
        output = publish_parts(
            text, writer=writer, settings_overrides=settings_overrides
        )
        if 'html_body' in output:
            return output['html_body']
        return ''
