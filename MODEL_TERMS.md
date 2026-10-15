# Model identity, role and terms

Checked against Google's official documentation on 15 October 2026. This records the configured integration; it does not claim a successful model request.

| Item | Implementation |
|---|---|
| Model family | Google Gemma 4 |
| Default identifier | `gemma-4-26b-a4b-it` |
| Override | Server-side `GEMMA_MODEL`; engine requires a `gemma-4-` identifier |
| Access | Hosted Gemini API through the `google-genai` Python SDK |
| Credentials | Server environment only: `GEMINI_API_KEY` or `GOOGLE_API_KEY` |
| Input | Bounded selected findings, evidence, usage excerpts and replacements from the public target |
| Role | Recommend migration rationale, steps, suggested checks and limitations |
| Execution | Model text does not run commands; the implemented verification adapter determines supported checks |
| Provenance | Successful proposals are labeled `gemma4`; fallback recipes remain `reference_recipe` |
| Local evidence | `ai.state=not_run`: no model key was configured for recorded runs |

Google documents this identifier for [hosted Gemma access](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api). Actual availability, access and quota require a successful request. A hosted identifier is not a claim of an immutable weight revision; each analysis retains its reported model identity and state.

## License and hosted access

Google publishes [Gemma 4 under Apache License 2.0](https://ai.google.dev/gemma/apache_2), linked from its [Gemma terms page](https://ai.google.dev/gemma/terms/). Older versions may have different terms. No model weights or derivatives are bundled. DepBridge's MIT license applies to the team's original code and does not replace third-party licenses or service terms.

Hosted use is subject separately to the [Google APIs Terms](https://developers.google.com/terms) and [Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms), including linked usage policies and eligibility/region requirements. Review the current terms for the account used; DepBridge does not accept them or establish eligibility on a user's behalf.

The API terms describe processing of inputs and outputs; unpaid services may use them for improvement and human review. Do not submit confidential material, credentials or personal information through this public-repository prototype. Public source still retains its owner's rights. Model output requires review and is not execution evidence.

## Remaining validation

A new configured-key analysis must record `ai.state=completed` with actual Gemma proposals before claiming a live model demonstration. Missing keys, provider errors and invalid output remain visible as partial results. Local selected verification passes do not establish model success, full-suite compatibility or deployment readiness. No price, permanent free access or quota guarantee is made.
