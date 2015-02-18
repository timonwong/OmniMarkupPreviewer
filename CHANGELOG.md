OmniMarkupPreviewer Changes
---------------------------

**v3.0.0 (02/28/2015)**

* Use new flat github style (old style renamed to github-v1).
* Upgrade pygments library to v2.0.2, with more lexers.
* Upgrade `Python-Markdown` package to v2.4.1 final.
* Add `.mmd` file extension support (MultiMarkdown).
* Upgrade jQuery to 2.1.3 (Say good bye to IE8).
* `server_host` setting is now taken into account when launching preview in browser.

**v2.0.9 (08/02/2014)**

* Add syntax highlighting support for reStructureText.
* Prefer to use `xdg-open` under linux environments.

**v2.0.8 (04/15/2014)**

* Fix Sublime Text 2 compatibility (crash).

**v2.0.7 (04/14/2014)**

* Fix unreliable default setting overriding, which confuses a lot of users when
  customizing their settings.
* Prevent preview from the console, which will simply lead to crash.

**v2.0.6 (01/27/2014)**

* Fix Sublime Text 2 compatibility (markdown).

**v2.0.5 (01/24/2014)**

* MathJax library is now bundled directly instead of on demand downloading.
* Python-Markdown module now upgraded to v2.4.
* Fix incompatibility when using Sublime Text 3 under XFCE.

**v2.0.4 (08/10/2013)**

* Fix ruby gems loading in OSX (Required by RDoc, AsciiDoc, Org Mode and MediaWiki).
* Add AsciiDoc syntax support.
* Ensure default setting for `export_options` when not available.

**v2.0.3 (07/18/2013)**

* Fix html exporting when file contains images in Sublime Text 3.
* Fix `smart_strong` and `meta_data` extention name for markdown.

**v2.0.2 (06/17/2013)**

* Update cherrypy server, add detail information if socket could not be created.
* Add support for file URIs in images path.

**v2.0.1 (05/12/2013)**

* Strip YAML frontmatter for Markdown files automatically.
* Check syntax name as well as filename extension for MediaWiki files.

**v2.0 (03/31/2013)**

* Added support for [Org Mode](http://orgmode.org) (Requires ruby, and gem
  `org-ruby` should be installed).
* Added support for [MediaWiki](http://www.mediawiki.org/) (Requires ruby, as
  well as gem `wikicloth`).
* Added support for [AsciiDoc](http://www.methods.co.nz/asciidoc/) (Requires ruby,
  as well as gem `asciidoctor`).
* Reviving view (redirecting to the new location) automatically after reconnected.
* Prevent Package Control for Sublime Text 3 installing this package as
  `.sublime-package` (zip archive).
* Fixed broken `ignored_renderer` setting.
* Improved Sublime Text 3 compatibility.

**v1.20 (03/15/2013)**

* Add support Sublime Text 3 (Experimental).
* Add new context command `Copy Markup as HTML`.
* Remove unused command `Sweep Cache (Remove Unused)`.
* Auto scroll now works correctly for documents contain images and MathJax equations.

**v1.12 (03/13/2013)**

* Renderes are now loaded asynchronously on startup (faster Sublime Text 2 startup).
* Add litcoffee support.

**v1.11 (12/24/2012)**

* Fix incorrect auto-scrolling behavior while pages contain images or mathjax equations.

**v1.10 (11/22/2012)**

* Fix `UnicodeEncodeError` exception while image file path conatins non-ascii characters.
* Fix missing background image for `hr` element from exported htmls.

**v1.9 (11/12/2012)**

* Provide support for exporting result to html file, images on disk will be inlined (data-url).
  You can customize the settings of the exporter through the `"export_options"` option.
* Fix incorrect code block detecting (due to wrong tab length setting) in
  markdown renderer.

**v1.8 (11/10/2012)**

* OmniMarkupPreview is now able to use user defined browser command for launching
  web browser, through the `"browser_command"` option.
* Unopened file can be previewed correctly in browser without returning "404" error.
* Update cherrypy module in order to fix a random server crash on startup in
  Windows (Refer to [CherrPy #1016])

[CherrPy #1016]: https://bitbucket.org/cherrypy/cherrypy/issue/1016/windowserror-error-6-the-handle-is-invalid

**v1.7 (11/07/2012)**

* Add option `"server_host"` for server listening address.
* Now OmniMarkupPreviewer doesn't require restart on some settings change anymore.
* On demand downloader for mathjax should work under Linux now (using `wget` or `curl`).
* Unsaved textile documents can now be previewed as well.

**v1.6 (11/03/2012)**

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

**v1.5.1 (11/01/2012)**

* Fixed a bug that all renderers wouldn't work if any renderer raised exception
  while loading.

**v1.5 (10/31/2012)**

* Images on local machine can now be displayed corectlly.
* New `"ajax_polling_interval"` option.
* Allow users to use their own templates.

**v1.4 (10/28/2012)**

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

**v1.3 (10/27/2012)**

* Added syntax highlight support for Markdown, through the [CodeHilite Extension].
* Unsaved buffer can now be previewed without error.
* Updated github template.

[CodeHilite Extension]: http://packages.python.org/Markdown/extensions/code_hilite.html

**v1.2 (10/16/2012)**

* OmniMarkupPreviewer now can be installed from Package Control under Linux.

**v1.1 (10/16/2012)**

* Added support for [RDoc](http://rdoc.sourceforge.net/) (Requires ruby).
* Added support for [Pod](http://search.cpan.org/dist/perl/pod/perlpod.pod) (Requires perl).
* Auto scroll while text added/deleted.

**v1.0.1 (10/14/2012)**

* OSX support added to Package Control.
* Added ability to clean cache.

**v1.0 (10/14/2012)**

* First release.
