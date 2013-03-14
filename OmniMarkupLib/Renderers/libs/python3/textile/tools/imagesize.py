def getimagesize(url):
    """
    Attempts to determine an image's width and height, and returns a string
    suitable for use in an <img> tag, or an empty string in case of failure.
    Requires that PIL is installed.

    >>> getimagesize("http://www.google.com/intl/en_ALL/images/logo.gif")
    ... #doctest: +ELLIPSIS
    'width="..." height="..."'

    >>> getimagesize("http://bad.domain/")
    ''

    """

    try:
        from PIL import ImageFile
        import urllib.request, urllib.error, urllib.parse
    except ImportError:
        return ''

    try:
        p = ImageFile.Parser()
        f = urllib.request.urlopen(url)
        while True:
            s = f.read(1024)
            if not s:
                break
            p.feed(s)
            if p.image:
                return 'width="%i" height="%i"' % p.image.size
    except (IOError, ValueError):
        return ''


def setup_module(module):
    from nose.plugins.skip import SkipTest
    try:
        from PIL import ImageFile
    except ImportError:
        raise SkipTest()
