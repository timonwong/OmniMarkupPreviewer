
import fnmatch
import sys
import types

PY3K = sys.version_info >= (3, 0, 0)

if PY3K:
    from imp import reload


def _reload():
    mod_prefix = 'OmniMarkupLib'
    if PY3K:
        mod_prefix = 'OmniMarkupPreviewer.' + mod_prefix

    reload_mods = []
    for modname in sys.modules:
        if (modname.startswith(mod_prefix) or
                sys.modules[modname] is not None):
            reload_mods.append(modname)

    mods_order_patterns = [
        '',

        '.log',
        '.Common',
        '.LinuxModuleChecker'

        '.Setting',
        '.LibraryPathManager',

        '.Downloader',
        '.OnDemandDownloader',

        '.Renderers',
        '.RendererManager',
        '.Renderers.base_renderer',
        '.Renderers.*'
    ]

    reload_mods_order = []

    for pattern in mods_order_patterns:
        for modname in reload_mods:
            if fnmatch.fnmatchcase(modname, mod_prefix + pattern):
                reload_mods_order.append(modname)

    for modname in reload_mods_order:
        mod = sys.modules[modname]
        if isinstance(mod, types.ModuleType):
            reload(mod)

_reload()
