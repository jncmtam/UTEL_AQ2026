# Historical cohort evidence and unresolved reconciliation

Reviewed 2026-11-03. This is a source review, not a passed investment-data audit.

## Complete historical holdings anchor

[DIA's October 31, 2013 annual report](https://www.sec.gov/Archives/edgar/data/1041130/000119312513486376/d643100dn30d.htm)
lists the 30 holdings and share/value amounts. The factual extract is
`data/us_equities/review/dia_2013_holdings.json`; the independent valuation-to-vendor
comparison is `results/data_assessment/independent_price_anchors.json`.
The observation date is not its EDGAR publication time. The filing index was
inaccessible; no precise acceptance timestamp or full-document checksum is invented.
The October snapshot alone does not establish September 23 membership.

The implied holding price is value divided by shares. Examples of filing/vendor
close ratios are approximately 2 for NKE, 4 for V, 3 for WMT, 1.196 for MMM,
and 0.209 for GE. Smaller discrepancies also appear for some Nasdaq names.
These differences need action/valuation reconciliation. A constant split-adjustment
factor does **not** invalidate adjacent returns: r=(aP_t)/(aP_{t-1})-1 cancels it.
Neither agreement at one anchor nor disagreement in nominal historical price proves
an entire adjusted-return series correct or incorrect.

## UTX/RTX mapping evidence

The issuer's [April 3, 2020 completion release](https://investors.rtx.com/static-files/1d0010bd-9a41-4be8-b797-0048967463ae)
states that United Technologies changed name/ticker to Raytheon Technologies/RTX,
after Carrier and Otis distributions; UTC owners retained their shares. The 2.3348
exchange factor applies to Raytheon holders, not a blanket factor for UTC shares.

This supports investigating a source-backed successor mapping. It does not certify
an RTX vendor series as the original UTX total-return history or reconcile the
spin-offs. The 2020 event is outside the proposed 2014–2018 test window, but later
vendor back-adjustments can affect displayed earlier price levels. DD and GE events
inside the window, dividend treatment, missing identity records and dated sectors
still require separate review.

## Access and decision

Direct SEC submissions/ticker/source requests returned HTTP403. Indexed filing
content was readable through the research tool. No paid source was purchased,
missing asset removed, or review flag set to bypass this limitation.

The investment-data gate remains blocked. The published INDEX_2010 corpus has a
separate, explicitly conditional algorithm-benchmark admission, described in
`data/published_us/ASSESSMENT.md`. It does not replace the historical cohort.
