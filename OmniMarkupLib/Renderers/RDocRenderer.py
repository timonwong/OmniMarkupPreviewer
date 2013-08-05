from .base_renderer import *
import os.path


__file__ = os.path.normpath(os.path.abspath(__file__))
__path__ = os.path.dirname(__file__)


@renderer
class RDocRenderer(CommandlineRenderer):
    def __init__(self):
        super(RDocRenderer, self).__init__(
            executable='ruby',
            args=['-rubygems', os.path.join(__path__, 'bin/rdoc.rb')])

    @classmethod
    def is_enabled(cls, filename, syntax):
        if syntax == 'text.rdoc':  # RDoc.tmLanguage
            return True
        return filename.endswith('.rdoc')
