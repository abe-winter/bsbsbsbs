# PDF417 decoder for python

Small python project that can decode, to an extent, 2D PDF417 barcodes from a PNG image.

I wrote this because I wanted to know what was in the barcode in my emailed driver's license and I couldn't find another OSS package to do this.

Some caveats:

* yes it works on PNG images, but it won't work on photos -- they have to be screenshots of a high-quality source (no, screenshot of a photo doesn't count. you can't wish for more wishes)
* only has been tested on a single screenshot I took of my driver's license
* doesn't fully implement the standard
* I sourced the spec from [wikipedia](https://en.wikipedia.org/wiki/PDF417) and [this pdf](https://www.expresscorp.com/uploads/specifications/44/USS-PDF-417.pdf) and copied and pasted the lookup tables from OCR -- they may be incomplete or wrong

That said, it has lots of asserts and has worked at least once.

## PDF417 lookup tables

There are some CSVs in here with PDF417 lookup tables.

* cluster-{index}-bs.csv have bsbsbsbs (bar-space) lookups for clusters (0, 3, 6)
* text-codes.csv has the lookup for converting hi & low text codes to ascii chars / state commands

## Contributions welcome

In particular:

* tests. can be unit tests of individual routines or link it up to a barcode generator
* more fully decode the standard, or use another library to decode the standard once codewords have been parsed
* bugfixes as always
* link to a better command-line barcode reader so I can archive this repo
* support non-screenshot images (i.e. photos), preferably by using an external library to do the image scanning
