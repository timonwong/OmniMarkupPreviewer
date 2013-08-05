# -*- coding: utf-8 -*-
require 'literati'

# Force utf-8 encoding
begin
    $stdin.set_encoding 'utf-8'
    $stdout.set_encoding 'utf-8'
rescue
end

text = $stdin.read
$stdout.write Literati.render(text)
