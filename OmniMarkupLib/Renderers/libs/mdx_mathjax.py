import markdown


class MathJaxPattern1(markdown.inlinepatterns.Pattern):
    def __init__(self):
        markdown.inlinepatterns.Pattern.__init__(self, r'(?<!\\)(\$\$?)(.+?)\2')

    def handleMatch(self, m):
        node = markdown.util.etree.Element('mathjax')
        node.text = markdown.util.AtomicString(m.group(2) + m.group(3) + m.group(2))
        return node


class MathJaxPattern2(markdown.inlinepatterns.Pattern):
    def __init__(self):
        markdown.inlinepatterns.Pattern.__init__(self, r'(?<!\\)(\\\()(.+?)(\\\))')

    def handleMatch(self, m):
        node = markdown.util.etree.Element('mathjax')
        node.text = markdown.util.AtomicString(m.group(2) + m.group(3) + m.group(4))
        return node


class MathJaxExtension(markdown.Extension):
    def extendMarkdown(self, md, md_globals):
        # Needs to come before escape matching because \ is pretty important in LaTeX
        md.inlinePatterns.add('mathjax', MathJaxPattern1(), '<escape')
        md.inlinePatterns.add('mathjax', MathJaxPattern2(), '<escape')


def makeExtension(configs=None):
    return MathJaxExtension(configs)
