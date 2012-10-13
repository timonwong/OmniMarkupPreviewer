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

import sys
import os
import os.path
import re
import log
import threading
import inspect
from collections import namedtuple
from Common import RenderedMarkupCache, RenderedMarkupCacheEntry, generate_timestamp
import LibraryPathManager


__file__ = os.path.normpath(os.path.abspath(__file__))
__path__ = os.path.dirname(__file__)


WorkerQueueItem = namedtuple('WorkerQueueItem',
    ['timestamp', 'fullpath', 'lang', 'text']
)


class RendererWorker(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.mutex = threading.Lock()
        self.cond = threading.Condition(self.mutex)
        self.que = {}
        self._stopping = False
        self._stopped = True

    def queue(self, buffer_id, fullpath, lang, text, immediate=False):
        item = WorkerQueueItem(
            timestamp=generate_timestamp(),
            fullpath=fullpath,
            lang=lang,
            text=text
        )
        if not immediate:
            with self.cond:
                self.que[buffer_id] = item
                self.cond.notify()
        else:
            self.run_queue_item(buffer_id, item)

    def run_queue_item(self, buffer_id, item):
        try:
            filename = os.path.basename(item.fullpath)
            dirname = os.path.dirname(item.fullpath)
            html_part = RendererManager._render_text(filename, item.lang, item.text)
            entry = RenderedMarkupCacheEntry(
                timestamp=generate_timestamp(),
                filename=filename,
                dirname=dirname,
                html_part=html_part
            )
            RenderedMarkupCache.instance().set_entry(buffer_id, entry)
        except NotImplementedError:
            pass
        except:
            log.exception("")

    def run(self):
        self._stopped = False
        while not self._stopping:
            with self.cond:
                self.cond.wait(1)
                if len(self.que) == 0:
                    continue
                items = self.que.items()
                self.que.clear()
            for buffer_id, item in items:
                self.run_queue_item(buffer_id, item)
        self._stopped = True

    def stop(self):
        self._stopping = True
        self.join()


class RendererManager:
    WORKER = RendererWorker()
    LANG_RE = re.compile(r"^[^\s]+(?=\s+)")
    RENDERER_TYPES = []

    @classmethod
    def is_renderers_enabled(cls, filename, lang):
        # filename may be None, so prevent it
        filename = filename or ""
        for renderer_type in cls.RENDERER_TYPES:
            if renderer_type.is_enabled(filename, lang):
                return True
        return False

    @classmethod
    def get_lang_by_scope_name(cls, scope_name):
        m = cls.LANG_RE.search(scope_name)
        if m is None:
            lang = ""
        else:
            lang = m.group(0).lower()
        return lang

    @classmethod
    def is_renderers_enabled_in_view(cls, view):
        filename = view.file_name()
        lang = cls.get_lang_by_scope_name(view.scope_name(0))
        return cls.is_renderers_enabled(filename, lang)

    @classmethod
    def _render_text(cls, filename, lang, text):
        for renderer_type in cls.RENDERER_TYPES:
            try:
                if renderer_type.is_enabled(filename, lang):
                    renderer = renderer_type()
                    return renderer.render(text)
            except:
                log.exception('Exception occured while rendering using %s', renderer_type)
        raise NotImplementedError()

    @classmethod
    def queue_current_view(cls, view, immediate=False):
        import sublime
        region = sublime.Region(0, view.size())
        text = view.substr(region)
        lang = cls.get_lang_by_scope_name(view.scope_name(0))
        cls.WORKER.queue(view.buffer_id(), view.file_name(), lang, text, immediate=immediate)

    @classmethod
    def load_renderers(cls):
        # Clean old renderers
        cls.RENDERER_TYPES[:] = []

        # Add library path to sys.path
        st2_dir = LibraryPathManager.add_search_path(os.path.dirname(sys.executable))
        libs_dir = LibraryPathManager.add_search_path(os.path.join(__path__, './Renderers/libs/'))

        # Change the current directory to that of the module. It's not safe to just
        # add the modules directory to sys.path, as that won't accept unicode paths
        # on Windows
        renderers_path = os.path.join(__path__, './Renderers/')
        oldpath = os.getcwdu()
        os.chdir(os.path.join(__path__, '..'))
        try:
            module_list = [f
                for f in os.listdir(renderers_path) if f.endswith("Renderer.py")
            ]
            # Load each renderer
            for module_file in module_list:
                module_name = 'OmniMarkupLib.Renderers.' + module_file[:-3]
                try:
                    log.info("Loading renderer: %s", module_name)
                    __import__(module_name)
                    mod = sys.modules[module_name] = reload(sys.modules[module_name])
                    # Get classes
                    classes = inspect.getmembers(mod, inspect.isclass)
                    for classname, classtype in classes:
                        # Register renderer into manager
                        if hasattr(classtype, 'IS_VALID_RENDERER__'):
                            cls.RENDERER_TYPES.append(classtype)
                except:
                    log.exception("Failed to load renderer: %s", module_name)

        finally:
            # Restore the current directory
            os.chdir(oldpath)
            LibraryPathManager.remove_search_path(libs_dir)
            # Clean sys path for library loading
            LibraryPathManager.remove_search_path(st2_dir)


RendererManager.WORKER.daemon = True
RendererManager.WORKER.start()
