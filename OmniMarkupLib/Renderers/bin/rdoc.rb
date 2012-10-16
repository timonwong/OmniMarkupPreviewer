# -*- coding: utf-8 -*-
require 'rdoc'
require 'rdoc/markup/to_html'

# Force utf-8 encoding
$stdin.set_encoding 'utf-8'
$stdout.set_encoding 'utf-8'

text = $stdin.read
conv = RDoc::Markup::ToHtml.new
$stdout.write conv.convert(text)
