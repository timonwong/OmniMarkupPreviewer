"""
Copyright (c) 2013 Timon Wong

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

import sublime
import os
import sys


def cannot_import_some_modules_in_linux():
    if not sublime.ok_cancel_dialog("OmniMarkupPreviewer cannot work "
                                    "because some modules is missing from Sublime Text 2 Linux version.\n"
                                    "Click \"OK\" to see how to fix it"):
        return
    sublime_app_path = os.path.dirname(os.path.realpath(os.path.join('/proc', str(os.getpid()), 'exe')))
    script = """#!/bin/bash
# The purpose of this script is installing missing python libraries to Sublime Text 2
# NOTE: Make sure SUBLIME_TEXT2_FOLDER is assigned correctly.
# Once the script is executed, you have to restart SublimeText2 to get modules work.
SUBLIME_TEXT2_FOLDER="%s"
# Download and install pythonbrew, make sure you have curl installed.
curl -kL http://xrl.us/pythonbrewinstall | bash
source "$HOME/.pythonbrew/etc/bashrc"
pythonbrew install --configure="--enable-unicode=ucs4" 2.6
ln -s "$HOME/.pythonbrew/pythons/Python-2.6/lib/python2.6/" "${SUBLIME_TEXT2_FOLDER}/lib/python2.6"
""" % (sublime_app_path)
    # Open this script in a new view
    window = sublime.active_window()
    view = window.new_file()
    view.set_name('Fix-missing-modules.sh')
    view.set_scratch(True)
    edit = view.begin_edit()
    view.set_syntax_file('Packages/ShellScript/Shell-Unix-Generic.tmLanguage')
    try:
        region = sublime.Region(0, view.size())
        view.replace(edit, region, script)
        view.sel().clear()
    finally:
        view.end_edit(edit)


def check(force_check=False):
    if os.name == 'posix':  # For Linux only
        settings = sublime.load_settings('OmniMarkupPreviewer.sublime-settings')
        reported = settings.get('missing_module_reported', False)
        if reported and not force_check:
            # Check only once
            return
        settings.set('missing_module_reported', True)
        sublime.save_settings('OmniMarkupPreviewer.sublime-settings')
        try:
            # Prevent PEP8 warning
            exec('import pyexpat')
            exec('import ctypes')
        except ImportError:
            sublime.set_timeout(cannot_import_some_modules_in_linux, 500)


if sys.version_info < (3, 0):
    check()
