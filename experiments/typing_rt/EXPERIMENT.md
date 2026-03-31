# Typing RT Experiment

## Status: monkey-tested

## Description
A 4-letter typing reaction time task. A random 4-letter string appears on screen and the participant types all four letters as fast as possible. After the 4th keypress, total reaction time is displayed for 1.5 seconds. Includes practice (5 trials) and test (20 trials) blocks.

## Plan
- Single monolithic script (no modules)
- Random 4-letter strings generated from letter lists
- Each keypress recorded; trial RT = time from stimulus to 4th keypress
- Practice block with feedback, then test block

## Modules
| File | Role |
|------|------|
| `typing_rt.iqx` | Complete experiment (monolithic) |

## Stimuli
None — letter strings are generated at runtime.

## Changelog
- 2026-03-30: Initial build and monkey-tested

## Known Issues
- Monolithic script — not yet decomposed into modules
- No human verification run documented
