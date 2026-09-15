# H1g plan — hyphenated legal-name `.no` fallback

H1f compact `.com` recall was rejected after 0/250 promotions on a fresh cohort. The next bounded hypothesis is the already-supported second deterministic H1c form: `<legal-name-tokens-separated-by-hyphens>.no`.

Production currently calls `deterministic_domain_candidates(..., max_candidates=1)`, so only the compact `.no` form is tried. H1g will evaluate the hyphenated `.no` form only when:

- no verified website exists after unchanged production discovery;
- at least two of the existing four logical site-request slots remain unused;
- the hyphenated candidate differs from the compact `.no` candidate.

Publication will require the same strict single-homepage proof used for the rejected H1f experiment: exact target organisation number, or full legal name plus BRREG location, with explicit conflicting organisation numbers quarantined. No title/domain-only promotion and no request-ceiling increase.

H1g must use a new zero-overlap cohort excluding the H1f 300 as well, increasing the historical exclusion set from 4,000 to 4,300 companies.
