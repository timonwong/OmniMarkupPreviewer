"""Superscipt extension for Markdown.

To superscript something, place a carat symbol, '^', before and after the
text that you would like in superscript:  6.02 x 10^23^
The '23' in this example will be superscripted.  See below.

Examples:

>>> import markdown
>>> md = markdown.Markdown(extensions=['superscript'])
>>> md.convert('This is a reference to a footnote^1^.')
u'<p>This is a reference to a footnote<sup>1</sup>.</p>'

>>> md.convert('This is scientific notation: 6.02 x 10^23^')
u'<p>This is scientific notation: 6.02 x 10<sup>23</sup></p>'

>>> md.convert('This is scientific notation: 6.02 x 10^23. Note lack of second carat.')
u'<p>This is scientific notation: 6.02 x 10^23. Note lack of second carat.</p>'

>>> md.convert('Scientific notation: 6.02 x 10^23. Add carat at end of sentence.^')
u'<p>Scientific notation: 6.02 x 10<sup>23. Add a carat at the end of sentence.</sup>.</p>'

Paragraph breaks will nullify superscripts across paragraphs. Line breaks
within paragraphs will not.

"""

import markdown
from markdown.inlinepatterns import SimpleTagPattern

# Global Vars
SUPERSCRIPT_RE = r'(\^)([^\^]*)\2'  # the number is a superscript^2^


class SuperscriptExtension(markdown.Extension):
    """ Superscript Extension for Python-Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Replace superscript with SuperscriptPattern """
        md.inlinePatterns.add('superscript', SimpleTagPattern(SUPERSCRIPT_RE, 'sup'), '<not_strong')

def makeExtension(configs=None):
    return SuperscriptExtension(configs=configs)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
