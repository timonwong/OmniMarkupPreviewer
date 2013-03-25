# -*- coding: utf-8 -*-
require 'literati'

# Force utf-8 encoding
$stdin.set_encoding 'utf-8'
$stdout.set_encoding 'utf-8'

text = $stdin.read
$stdout.write Literati.render(text)
