# Table column widths in the PDF

In the PDF, a markdown pipe table's column widths come **only** from the dash row under the
header. Pandoc writes each column as

```
p{(\columnwidth - 2(n-1)\tabcolsep) * \real{d_i / sum(d)}}
```

where `d_i` is the number of dashes in column `i` and `n` the number of columns. The text in the
cells is ignored. So a column with short content (a term column) next to columns of long prose
gets a fraction too small for its own longest word, and that word runs into the next column as an
overfull `\hbox`.

A manuscript that pads every cell to its own content width makes the dash row follow the content
length, not the width each column needs, which is exactly how this happens.

## Fix

1. Find the longest unbreakable string in the narrow column (a word, an identifier, a number with
   its unit).
2. Work out the usable width: `\textwidth - 2(n-1) x \tabcolsep` (`\tabcolsep` is 6pt by default).
   Compute the text width from the geometry line the build prints
   (`paperwidth - inner - outer`, in inches; times 72.27 for points).
3. Add dashes to the narrow column (and trailing spaces to its cells, so the pipes stay aligned)
   until `d_i / sum(d) x usable width` covers that string at the table's font size.
4. Check with a throwaway LaTeX run (pandoc to `.tex` with the build's template, then XeLaTeX)
   and `grep Overfull` in its log, not by eye: a 1pt overhang is real but invisible in a
   thumbnail.

Worked example: a 6 x 9 in trim at 11pt has a text width of about 324pt; a 4-column table
then has 324 - 2 x 3 x 6 = 288pt to share, a 3-column table 300pt. A dash row of `32/57/39/50`
gives the first column 32/178 x 288 = 52pt.
