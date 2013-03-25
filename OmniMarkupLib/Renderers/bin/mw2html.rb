# -*- coding: utf-8 -*-
require 'wikicloth'

# Force utf-8 encoding
$stdin.set_encoding 'utf-8'
$stdout.set_encoding 'utf-8'

text = $stdin.read
conv = WikiCloth::WikiCloth.new(:data => text)
$stdout.write conv.to_html(:noedit => true)
