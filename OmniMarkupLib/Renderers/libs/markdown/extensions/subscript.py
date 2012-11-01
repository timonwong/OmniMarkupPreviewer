"""Subscript extension for Markdown.

To subscript something, place a tilde symbol, '~', before and after the
text that you would like in subscript:  C~6~H~12~O~6~
The numbers in this example will be subscripted.  See below for more:

Examples:

>>> import markdown
>>> md = markdown.Markdown(extensions=['subscript'])
>>> md.convert('This is sugar: C~6~H~12~O~6~')
u'<p>This is sugar: C<sub>6</sub>H<sub>12</sub>O<sub>6</sub></p>'

Paragraph breaks will nullify subscripts across paragraphs. Line breaks
within paragraphs will not.
"""

import markdown
from markdown.inlinepatterns import SimpleTagPattern

# Global Vars
SUBSCRIPT_RE = r'(\~)([^\~]*)\2'  # the number is subscript~2~


class SubscriptExtension(markdown.Extension):
    """ Subscript Extension for Python-Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Replace subscript with SubscriptPattern """
        md.inlinePatterns.add('subscript', SimpleTagPattern(SUBSCRIPT_RE, 'sub'), '<not_strong')

def makeExtension(configs=None):
    return SubscriptExtension(configs=configs)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
