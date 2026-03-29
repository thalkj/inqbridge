# Inquisit Script Library Index

## Library Summary

| Library | Path | Script Folders | Script Files | Format | Total Files |
|---------|------|---------------|--------------|--------|-------------|
| Inquisit 6 (v6) | `scripts/library_v6/` | -- (flat) | 202 .iqx | .iqx (XML-style) | 202 |
| Inquisit 7 (v7) | `scripts/library_v7/` | 385 | 998 .iqjs + 3 .iqx | .iqjs (JS-style) | 14,827 |

### Notes
- **library_v6** contains single-file .iqx scripts (Inquisit 6 format), one file per script.
- **library_v7** was extracted from .iqzip archives (Inquisit 7 format). Each script is in its own subfolder and may include multiple .iqjs files plus media assets (images, audio, HTML instructions).
- The original .iqzip archives are preserved in `scripts/library/` (385 files).

## Grep Examples

Search both libraries for Inquisit syntax or patterns:

```bash
# Find scripts using stimulustimes (v6)
grep -r "stimulustimes" scripts/library_v6/

# Find scripts using correctresponse (v6)
grep -r "correctresponse" scripts/library_v6/

# Find scripts using stimulustimes (v7)
grep -r "stimulustimes" scripts/library_v7/ --include="*.iqjs"

# Find scripts using correctresponse (v7)
grep -r "correctresponse" scripts/library_v7/ --include="*.iqjs"

# Search both libraries at once
grep -r "screenCapture" scripts/library_v6/ scripts/library_v7/ --include="*.iqx" --include="*.iqjs"

# Find specific element types (e.g., all trial definitions)
grep -rn "<trial " scripts/library_v6/
grep -rn "<trial " scripts/library_v7/ --include="*.iqjs"

# List which scripts use a particular feature
grep -rl "monkey" scripts/library_v6/
grep -rl "monkey" scripts/library_v7/ --include="*.iqjs"
```
