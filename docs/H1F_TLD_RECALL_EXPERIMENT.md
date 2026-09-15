# H1f — compact legal-name `.com` fallback experiment

## Decision

**Reject / do not promote.** The bounded compact `.com` fallback transferred safely but produced no useful recall gain on a fresh zero-overlap 300-company cohort.

H1f remains experimental branch evidence only. Production `main` is unchanged.

## Hypothesis

The production site-discovery stack tries a compact legal-name `.no` deterministic candidate but does not probe an equivalent `.com` candidate. H1f tested whether otherwise-unused site-request headroom could safely recover exact company websites at `<compact-legal-name>.com`.

The experiment was intentionally stricter than H1c. A guessed `.com` homepage could publish only if the independently fetched page showed either:

- the exact target Norwegian organisation number; or
- the full legal name plus BRREG location.

Explicit conflicting organisation numbers quarantined. Existing verified websites were never replaced. H1f was not allowed to exceed the existing four logical site requests per profile.

## Fresh qualification

Workflow: `H1f Zero-Cost TLD Recall Qualification`

Successful run: `35004197331`

Head: `840f35b63fc3d393e681b1c3e23e09eb245bb861`

Artifact:

- ID: `10410114738`
- digest: `sha256:a5c7485bfeb9b05c1cc35d9c091d095a14a410a43678e6e9e61c0e844a9694ec`

Fresh selector:

- seed: `20260925`
- count: 300
- excluded previously touched companies: 4,000
- overlap: 0
- evaluation split: `h1f_zero_cost_tld_recall`
- sample slice: `fresh_compact_com_fallback_validation`
- manifest SHA-256: `da9584073e526207d2bfe52c525509c2852daaa8fb85f26fd9c586a5e4ee4a6e`

## Result

Unchanged production baseline:

- 300/300 completed
- production report passed
- 36 verified company websites before H1f

H1f:

- 300 safe compact `.com` candidates generated
- 250 candidates eligible for a headroom-only attempt
- 36 skipped because a verified website already existed
- 14 skipped because the existing site-request budget was already consumed
- 96 additional logical requests actually reached the network
- 17 candidate pages were available
- 29 candidate attempts returned source errors
- 204 were blocked/unusable before publication
- **0 exact websites promoted**
- **0 net-new H2a profile handles**
- **0 net-new H2c contact emails**
- third-party cost added: **$0**
- post-H1f conservative challenge request charge: 3,802 / 5,406
- structural ceiling remained unchanged at 5,406 / 300 (= 1,802/100)
- no observation validation errors
- no request-budget violations

## Failure-mode audit

The identity guard prevented multiple obvious wrong-entity collisions among the 17 available `.com` pages. Examples included:

- `beck.com` — official site for the musician Beck, not the Norwegian legal entity `BECK AS`;
- `circumflex.com` — Dutch IT company, not `CIRCUMFLEX AS`;
- `snomann.com` — Lithuanian company contact/location, not `SNØMANN AS`;
- `biodiscovery.com` — redirected to Bionano, not `BIODISCOVERY AS`;
- `nihi.com` — international NIHI hospitality properties, not `NIHI AS`;
- `rainbowspirit.com` — US photography site, not `RAINBOW SPIRIT AS`.

Several other candidates were parked, generic, or lacked exact legal-entity proof. Weakening the identity rule to accept name/domain similarity would therefore trade recall for material wrong-company publication and is rejected.

## Conclusion

H1f demonstrated that compact `.com` guessing is not a useful zero-cost recall path for this population under the challenge's precision requirements. The correct action is to keep it out of production and move to a different bounded hypothesis rather than spend more request budget or weaken entity identity.
