def sanitize(string, html_type):
    """
    >>> sanitize("\\t<p>a paragraph</p>","html")
    u'\\t<p>a paragraph</p>'

    >>> sanitize("\\t<script>alert('evil script');</script>", "xhtml")
    u"\\t&lt;script&gt;alert('evil script');&lt;/script&gt;"

    """
    try:
        import html5lib
        from html5lib import sanitizer, serializer, treewalkers, treebuilders
    except ImportError:
        raise Exception("html5lib not available")

    p = html5lib.HTMLParser(tokenizer=sanitizer.HTMLSanitizer)
    tree = p.parseFragment(string)

    walker = treewalkers.getTreeWalker("simpletree")
    stream = walker(tree)

    if html_type == 'xhtml':
        s = serializer.xhtmlserializer.XHTMLSerializer()
    else:
        s = serializer.htmlserializer.HTMLSerializer(omit_optional_tags=False,
                                                     quote_attr_values=True)
    return s.render(stream)


def setup_module(module):
    from nose.plugins.skip import SkipTest
    try:
        import html5lib
    except ImportError:
        raise SkipTest()
