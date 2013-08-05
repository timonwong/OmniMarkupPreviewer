# -*- coding: utf-8 -*-
require 'rdoc'
require 'rdoc/markup/to_html'

# Force utf-8 encoding
begin
    $stdin.set_encoding 'utf-8'
    $stdout.set_encoding 'utf-8'
rescue
end

text = $stdin.read
conv = RDoc::Markup::ToHtml.new
$stdout.write conv.convert(text)
