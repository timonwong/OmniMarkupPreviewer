from base_renderer import *
import re
from docutils.core import publish_parts
from docutils.writers.html4css1 import Writer, HTMLTranslator


class GitHubHTMLTranslator(HTMLTranslator):
    def visit_literal_block(self, node):
        classes = node.attributes['classes']
        if len(classes) >= 2 and classes[0] == 'code':
            language = classes[1]
            del classes[:]
            self.body.append(self.starttag(node, 'pre', lang=language))
        else:
            self.body.append(self.starttag(node, 'pre'))


@renderer
class RstRenderer(MarkupRenderer):
    filename_pattern = re.compile(r'\.re?st$')

    @classmethod
    def is_enabled(cls, filename, syntax):
        if syntax == "text.restructuredtext":
            return True
        return cls.filename_pattern.search(filename)

    def render(self, text):
        settings_overrides = {
            'cloak_email_addresses': True,
            'file_insertion_enabled': False,
            'raw_enabled': False,
            'strip_comments': True,
            'doctitle_xform': False,
            'report_level': 5,
            'syntax_highlight': 'none',
            'math_output': 'latex',
            'input_encoding': 'utf-8',
            'output_encoding': 'utf-8'
        }

        writer = Writer()
        writer.translator_class = GitHubHTMLTranslator
        output = publish_parts(
            text, writer=writer, settings_overrides=settings_overrides
        )
        if 'html_body' in output:
            return output['html_body']
        return ''
