from .base_renderer import *
import os.path


__file__ = os.path.normpath(os.path.abspath(__file__))
__path__ = os.path.dirname(__file__)


@renderer
class MediaWikiRenderer(CommandlineRenderer):
    def __init__(self):
        super(MediaWikiRenderer, self).__init__(
            executable='ruby',
            args=['-rubygems', os.path.join(__path__, 'bin/mw2html.rb')])

    @classmethod
    def is_enabled(cls, filename, syntax):
        if syntax == 'text.html.mediawiki':
            return True
        return filename.endswith('.mediawiki') or filename.endswith('.wiki')
