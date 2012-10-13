"""
Copyright (c) 2012 Timon Wong

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import webbrowser
import sublime
import sublime_plugin
from OmniMarkupLib import log
from OmniMarkupLib.Server import Server
from OmniMarkupLib.RendererManager import RendererManager


g_server_port = 51004
g_server = None


class OmniMarkupPreviewCommand(sublime_plugin.TextCommand):
    def run(self, edit, immediate=True):
        RendererManager.queue_current_view(self.view, immediate=True)
        # Open browser
        try:
            global g_server_port
            webbrowser.open('http://localhost:%d/view/%d' % (g_server_port, self.view.buffer_id()))
        except:
            log.exception("Error on opening web browser")

    def is_enabled(self):
        return RendererManager.is_renderers_enabled_in_view(self.view)


def reload_settings():
    global g_server_port
    settings = sublime.load_settings("OmniMarkupPreviewer.sublime-settings")
    g_server_port = settings.get("server_port", 51004)
    RendererManager.load_renderers()


class ReloadOmniMarkupPreviewerCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        reload_settings()


class PluginEventListener(sublime_plugin.EventListener):
    def on_modified(self, view):
        pass

    def on_post_save(self, view):
        if RendererManager.is_renderers_enabled_in_view(view):
            RendererManager.queue_current_view(view)

    def on_query_context(self, view, key, operator, operand, match_all):
        if key == 'omp_is_enabled':
            return RendererManager.is_renderers_enabled_in_view(view)
        return None


reload_settings()
g_server = Server(g_server_port)


def unload_handler():
    # Stopping server
    global g_server
    log.info('Bottle server shuting down...')
    g_server.stop()
    # Stopping renderer worker
    RendererManager.WORKER.stop()

    # Reload modules
    import sys
    import types
    for key in sys.modules:
        if key.startswith('OmniMarkupLib'):
            try:
                mod = sys.modules[key]
                if type(mod) is types.ModuleType:
                    reload(mod)
            except:
                pass
