# Privacy omission development check

This mapping-only pack covers the plain FN baseline, the exact PDF-pasted response (including line breaks and `orsee`), an unnamed privacy objection, explicit privacy acceptance, uncertainty, conditional acceptance, noise without privacy, camera facts without an evaluation, low altitude alone, generic refusal, and medical support without a distribution judgment. These are development targets, not validated population labels. The existing fresh-validation cases T25–T32 are unchanged.

Run against the actual model from the host terminal:

```bash
.venv/bin/python scripts/run-initial-manual-tests.py --mapping-only \
  --case-file manual-tests/privacy-mapping-cases.json \
  --output .runtime/privacy-live-check.json
```

`success: true` means the application completed; only `comparison.matches_expected: true` means coverage, positions and conditions matched this case's targets. Review extra facets as well as omissions. The report includes latency, all inference traces, preliminary nominations and the coverage review. One passing case does not establish generalization. After these diagnostics, rerun the full original development pack and then the untouched fresh-validation pack. No live improvement is claimed from the scripted engineering tests.

Policy 7.0.0 uses one direct model interpretation request, with one retry for invalid structure or references. There are no nomination or coverage-review chains before confirmation. The model determines meanings and supporting passage IDs; Python validates structure and provenance. Interpretation still needs explicit citizen confirmation. Judge the direct model output on both omissions and false positives; do not infer an objection from camera facts alone.
