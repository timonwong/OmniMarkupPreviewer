# -*- coding: utf-8 -*-
require 'asciidoctor'

# Force utf-8 encoding
$stdin.set_encoding 'utf-8'
$stdout.set_encoding 'utf-8'

text = $stdin.read
$stdout.write Asciidoctor::Document.new(text).render
