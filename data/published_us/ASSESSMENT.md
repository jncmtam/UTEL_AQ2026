# Published US corpus assessment

Source: [https://github.com/dppalomar/sparseIndexTracking](https://github.com/dppalomar/sparseIndexTracking), pinned revision `73a8d6016588634ba91f7e6d1667f343034ec9b8`.

Loaded 386 source-labelled assets and 252 daily observations, 2010-01-04 to 2010-12-31. Matrix and dates were decoded directly from R attributes; no calendar was guessed.

**Admission scope: conditional algorithm benchmark only. The original DJIA investment-data gate remains blocked.**

## Suitability and limits

- Actual US S&P500 source returns support a standard index-tracking algorithm comparison.
- Selection is conditioned on full-year membership; use the fixed provided universe without an unbiased investment claim.
- Preserve all publisher values, including exact 1e-6 entries. No missing-value imputation or silent cleaning.
- A predeclared hash-ordered subset is a resource-limited benchmark family, not LLM stock selection. Report its restriction against the full source universe.
- Scenario policy buckets are synthetic account categories, not historical industry classifications.
- No contemporary fundamentals, current ticker metadata or later-sector labels are inserted into 2010 inputs.
