from .base_renderer import *
import os.path


__file__ = os.path.normpath(os.path.abspath(__file__))
__path__ = os.path.dirname(__file__)


@renderer
class OrgRenderer(CommandlineRenderer):
    def __init__(self):
        super(OrgRenderer, self).__init__(
            executable='ruby',
            args=['-rubygems', os.path.join(__path__, 'bin/org.rb')])

    @classmethod
    def is_enabled(cls, filename, syntax):
        return filename.endswith('.org')
