import markdown
from markdown.inlinepatterns import SimpleTagPattern


STRIKEOUT_RE = r'(\~\~)([^\s](?:.*))(\~\~)'


class StrikeoutExtension(markdown.Extension):
    """ Strikeout extension for Python-Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Modifies inline patterns. """
        md.inlinePatterns.add('del', SimpleTagPattern(STRIKEOUT_RE, 'del'), '<not_strong')


def makeExtension(configs=None):
    return StrikeoutExtension(configs=configs)
