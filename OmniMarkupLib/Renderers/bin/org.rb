# -*- coding: utf-8 -*-
require 'org-ruby'

# Force utf-8 encoding
begin
    $stdin.set_encoding 'utf-8'
    $stdout.set_encoding 'utf-8'
rescue
end

text = $stdin.read
$stdout.write Orgmode::Parser.new(text).to_html
