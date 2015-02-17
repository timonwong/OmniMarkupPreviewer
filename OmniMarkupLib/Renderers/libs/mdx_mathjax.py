import markdown


def _mathjax_handleMatch(obj, m):
    node = markdown.util.etree.Element('mathjax')
    node.text = markdown.util.AtomicString(m.group(2) + m.group(3) + m.group(4))
    return node


class MathJaxPattern(markdown.inlinepatterns.Pattern):
    def __init__(self):
        markdown.inlinepatterns.Pattern.__init__(self, r'(?<!\\)(\$\$?)(.+?)(\2)')

    def handleMatch(self, m):
        return _mathjax_handleMatch(self, m)


class MathJaxNativeInlinePattern(markdown.inlinepatterns.Pattern):
    def __init__(self):
        markdown.inlinepatterns.Pattern.__init__(self, r'(\\\()(.+?)(\\\))')

    def handleMatch(self, m):
        return _mathjax_handleMatch(self, m)


class MathJaxNativeDisplayPattern(markdown.inlinepatterns.Pattern):
    def __init__(self):
        markdown.inlinepatterns.Pattern.__init__(self, r'(\\\[)(.+?)(\\\])')

    def handleMatch(self, m):
        return _mathjax_handleMatch(self, m)


class MathJaxExtension(markdown.Extension):
    def extendMarkdown(self, md, md_globals):
        # Needs to come before escape matching because \ is pretty important in LaTeX
        md.inlinePatterns.add('mathjax1', MathJaxPattern(), '<escape')
        md.inlinePatterns.add('mathjax2', MathJaxNativeInlinePattern(), '<escape')
        md.inlinePatterns.add('mathjax3', MathJaxNativeDisplayPattern(), '<escape')


def makeExtension(configs=None):
    return MathJaxExtension(configs)
