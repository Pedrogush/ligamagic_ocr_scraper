# Ligamagic OCR scraper

Get card listings from individual stores listed in ligamagic.com.br, where the normal bs4 method for extracting the data fails.

## Why OCR?

This website uses a scrape obfuscation method where the digit characters in certain HTML tags are not present in the tag content, instead they are rendered using a combination of CSS rules that crops a base image such that the result looks like text. (e.g, some portions of the listings have *drawn* numbers, instead of written)

### Disclaimer:

This is currently not working, since tags have changed since

