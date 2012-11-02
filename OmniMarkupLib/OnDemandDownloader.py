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

import os
import io
import threading
import contextlib
import zipfile
import log
import urllib2
import sublime


__g_mathjax_thread = None


def on_demand_download_mathjax():
    def background_worker(plugin_folder):
        try:
            archive_url = 'https://github.com/downloads/timonwong/OmniMarkupPreviewer/mathjax.zip'

            urllib2.install_opener(urllib2.build_opener(urllib2.ProxyHandler()))
            log.info('Downloading MathJax from "%s"', archive_url)

            with contextlib.closing(urllib2.urlopen(archive_url)) as archive_file:
                archive_stream = io.BytesIO(archive_file.read())
                archive_stream.seek(0)
                with contextlib.closing(zipfile.ZipFile(archive_stream)) as zip_file:
                    # Check archive first
                    for path in zip_file.namelist():
                        if path[0] == '/' or path.find('../') != -1 or path.find('..\\') != -1:
                            # Not a safe zip file
                            log.error('"%s" contains invalid files', archive_url)
                            return
                    # Install
                    public_folder = os.path.join(plugin_folder, 'public')
                    if not os.path.exists(public_folder):
                        os.makedirs(public_folder)
                    for path in zip_file.namelist():
                        if path.endswith('/'):
                            # Create directory
                            folder = os.path.join(public_folder, path)
                            if not os.path.exists(folder):
                                os.makedirs(folder)
                        else:
                            # Write file
                            with open(os.path.join(public_folder, path), 'wb') as f:
                                f.write(zip_file.read(path))
                    # Complete
                    with open(os.path.join(plugin_folder, '.MATHJAX.DOWNLOADED'), 'w') as f:
                        f.write('')
                    log.info('MathJax succesfully extracted into "%s"', public_folder)
        except:
            log.exception("Error on downloading MathJax")
        finally:
            global __g_mathjax_thread
            __g_mathjax_thread = None

    plugin_folder = os.path.join(sublime.packages_path(), 'OmniMarkupPreviewer')
    if os.path.exists(os.path.join(plugin_folder, '.MATHJAX.DOWNLOADED')):
        # No need to re-download
        return
    global __g_mathjax_thread
    if __g_mathjax_thread is not None:
        # In progress
        return
    __g_mathjax_thread = threading.Thread(
        name='Thread-on_demand_download_mathjax', target=background_worker,
        args=[plugin_folder]
    )
    __g_mathjax_thread.start()
