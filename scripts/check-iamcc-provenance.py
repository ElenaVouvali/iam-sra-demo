#!/usr/bin/env python3
"""Verify the retained generated IAM-CC assets against the recorded donor hashes."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'docs/iam-iq-provenance.json').read_text())
assets = {'app/src/styles/tokens.css', 'app/src/styles/components.css',
          'app/src/styles/fonts.css', 'app/public/brand/icons.svg', 'app/public/brand/eu-emblem.svg'}
for row in manifest['files']:
    if row['destination'] in assets:
        value = hashlib.sha256((root / row['destination']).read_bytes()).hexdigest()
        if value != row['donor_sha256']:
            raise SystemExit('Generated donor asset changed: ' + row['destination'])
        assets.remove(row['destination'])
if assets:
    raise SystemExit('Missing generated-asset provenance entries')
print('PASS: generated IAM-CC styles, fonts, logo sprite and EU emblem match donor ' + manifest['commit'])
