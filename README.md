OmniMarkupPreviewer
===================

OmniMarkupPreviewer is a [Sublime Text 2](http://www.sublimetext.com/2) plugin
that preview markup languages in web browsers. OmniMarkupPreviewer renders markup
files to htmls and send them to web brwosers in the backgound, in order to preview
them in realtime.

OmniMarkupPreviewer has builtin support following markups:

* [Markdown](http://daringfireball.net/projects/markdown/)
* [reStructuredText](http://docutils.sourceforge.net/rst.html)
* [WikiCreole](http://wikicreole.org/)
* [Textile](http://www.textism.com/tools/textile/)
* [Pod](http://search.cpan.org/dist/perl/pod/perlpod.pod) (Requires Perl >= 5.10
  and can be found in `PATH`, if the perl version < 5.10, `Pod::Simple` should be
  installed from `CPAN`.)
* [RDoc](http://rdoc.sourceforge.net/) (Requires ruby in your `PATH`)


Installation
------------

### With the Package Control plugin
The easiest way to install OmniMarkupPreviewer is through [Package Control].

[Package Control]: http://wbond.net/sublime_packages/package_control

Once you have Package Control installed, restart Sublime Text 2.

1. Bring up the Command Palette (<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd>
   on Windows and Linux. <kbd>⌘</kbd>+<kbd>⇧</kbd>+<kbd>P</kbd> on OS X).
2. Type "Install" and select "Package Control: Install Package".
3. Select "OmniMarkupPreviewer" from list.

The advantage of using Package Control is that it will keep OmniMarkupPreviewer
up to date automatically.


### Manual Install
**Without Git:**
[Download](https://github.com/timonwong/OmniMarkupPreviewer) the latest source
code, and extract to the Packages directory.

**With Git:**
Type the following command in your Sublime Text 2 Packages directory:

`git clone git://github.com/timonwong/OmniMarkupPreviewer.git`

The "Packages" directory is located at:

* **Windows:**  `%APPDATA%\Sublime Text 2\Packages\`
* **Linux:**    `~/.config/sublime-text-2/Packages/`
* **OS X:**     `~/Library/Application Support/Sublime Text 2/Packages/`


Usage
-----

### Key Bindings

The default key bindings for this plugin:

**Windows, Linux:**

* <kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>O</kbd>: Preview current file.

**OSX:**

* <kbd>⌘</kbd>+<kbd>⌥</kbd>+<kbd>O</kbd>: Preview current file.


### Command Palette

Open the command palette, it apperas as `OmniMarkupPreviewer: Preview Current File`.

Known Issues
------------

* RDoc and Pod documents cannot be previewed utils they are saved to disk.


What's New
----------

v1.8 (11/10/2012)

* OmniMarkupPreview is now able to use user defined browser command for launching
  web browser, through the `"browser_command"` option.
* File which is previewing (not already open) can now be previewed correctly in
  browser without returning "404" error.
* Update cherrypy module in order to fix a random server crash on startup in
  Windows (Refer to [CherrPy #1016])

[CherrPy #1016]: https://bitbucket.org/cherrypy/cherrypy/issue/1016/windowserror-error-6-the-handle-is-invalid

v1.7 (11/07/2012)

* Add option `"server_host"` for server listening address.
* Now OmniMarkupPreviewer doesn't require restart on some settings change anymore.
* On demand downloader for mathjax should work under Linux now (using `wget` or `curl`).
* Unsaved textile documents can now be previewed as well.

v1.6 (11/03/2012)

* [MathJax] support is now added (through the `"mathjax_enabled"` option), you can
  use `$..$` and `\(..\)` delimiters for inline math, `$$..$$` and `\[..\]` delimiters
  for display math. [MathJax] libraries will be downloaded on demand. for more
  information, visit [my blog](http://theo.im/blog/2012/11/03/latex-support-in-omnimarkuppreviewer/).
* Add support to custom the behavior of markdown renderer (through the
  `"renderer_options-MarkdownRenderer"` option).
* Responsive width on browser width change.
* Much better http server performance (Thanks to the [CherryPy] project).

[MathJax]: http://www.mathjax.org
[CherryPy]: http://www.cherrypy.org

v1.5.1 (11/01/2012)

* Fixed a bug that all renderers wouldn't work if any renderer raised exception
  while loading.

v1.5 (10/31/2012)

* Images on local machine can now be displayed corectlly.
* New `"ajax_polling_interval"` option.
* Allow users to use their own templates.

v1.4 (10/28/2012)

* Code blocks from [GitHub flavored markdown] is supported now, through the
  [Fenced Code Blocks Extension].
* [PHP Markdown Tables] support is added, through the [Tables Extension].
* Support strikeout extension syntax (Pandoc and GitHub) for markdown: `This ~~is deleted text.~~`
* Added `"ignored_renderers"` option to settings, in order to ignore specific
  markup renderers.

[GitHub flavored markdown]: http://github.github.com/github-flavored-markdown/
[Fenced Code Blocks Extension]: http://packages.python.org/Markdown/extensions/fenced_code_blocks.html
[PHP Markdown Tables]: http://michelf.ca/projects/php-markdown/extra/#table
[Tables Extension]: http://packages.python.org/Markdown/extensions/tables.html

v1.3 (10/27/2012)

* Added syntax highlight support for Markdown, through the [CodeHilite Extension].
* Unsaved buffer can now be previewed without error.
* Updated github template.

[CodeHilite Extension]: http://packages.python.org/Markdown/extensions/code_hilite.html

v1.2 (10/16/2012)

* OmniMarkupPreviewer now can be installed from Package Control under Linux.

v1.1 (10/16/2012)

* Added support for [RDoc](http://rdoc.sourceforge.net/) (Requires ruby).
* Added support for [Pod](http://search.cpan.org/dist/perl/pod/perlpod.pod) (Requires perl).
* Auto scroll while text added/deleted.

v1.0.1 (10/14/2012)

* OSX support added to Package Control.
* Added ability to clean cache.

v1.0 (10/14/2012)

* First release.


License
-------

This plugin released under MIT License:

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
