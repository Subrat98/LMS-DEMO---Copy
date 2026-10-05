"""Fixed headline numbers representing the college's full physical holdings.

Ported from `LMS/src/data/seedConfig.ts` — intentionally NOT derived from the actual
generated rows (the frontend's comment: generating literal thousands of dummy rows has
no UI benefit). Displayed directly on the Dashboard as the "real" library scale a full
production catalogue would eventually report.
"""

DASHBOARD_TOTALS = {
    "totalBookTitles": 4250,
    "totalBookCopies": 8750,
    "activeMembers": 2340,
}
