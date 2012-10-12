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

import sublime_plugin
from OmniMarkupLib.Server import Server
from OmniMarkupLib.RendererManager import RendererManager


class OmniMarkupPreviewCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        RendererManager.queue_current_view(self.view)

    def is_enabled(self):
        return RendererManager.is_renderers_enabled_in_view(self.view)


class PluginEventListener(sublime_plugin.EventListener):
    def __init__(self):
        RendererManager.load_renderers()
        self.server = Server(51004)

    def __del__(self):
        self.server.stop()

    def on_post_save(self, view):
        if RendererManager.is_renderers_enabled_in_view(view):
            RendererManager.queue_current_view(view)

    def on_query_context(self, view, key, operator, operand, match_all):
        if key == 'omp_is_enabled':
            return RendererManager.is_renderers_enabled_in_view(view)
        return None


def unload_handler():
    import sys
    # Reload all necessary modules
    for key in sys.modules.keys():
        if key.startswith('OmniMarkupLib.') or key == 'OmniMarkupLib':
            del sys.modules[key]
