# -*- coding: utf-8 -*-
require 'wikicloth'

# Force utf-8 encoding
begin
    $stdin.set_encoding 'utf-8'
    $stdout.set_encoding 'utf-8'
rescue
end

text = $stdin.read
conv = WikiCloth::WikiCloth.new(:data => text)
$stdout.write conv.to_html(:noedit => true)
