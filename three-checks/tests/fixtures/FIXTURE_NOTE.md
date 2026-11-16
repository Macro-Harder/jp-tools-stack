# Fixture note

## Copied real text fixtures

- copied_brief_excerpt.txt: copied from the three-checks design brief at workspace/build-flow-skills/tool-builds/three-checks/brief.md, first 40 lines, frozen at creation on 2026-11-14, never refreshed. Line traits checked against its bytes: ends with a trailing newline; contains no carriage return at a line end; contains no empty final line beyond the trailing newline.
- copied_plan_excerpt.txt: copied from the three-checks design plan at workspace/build-flow-skills/tool-builds/three-checks/plan.md, first 40 lines, frozen at creation on 2026-11-14, never refreshed. Line traits checked against its bytes: ends with a trailing newline; contains no carriage return at a line end; contains no empty final line beyond the trailing newline.
- No copied fixture contains a carriage return line end, so no test claims that trait for a copied fixture. The carriage return trait is covered only by the synthetic crlf.txt fixture.

## Synthetic fixtures

All bundle fixtures are synthetic, built to the closed field sets of brief section 3. No real stage record bundle exists to copy. Artifact fixtures other than the two copied excerpts are synthetic, for exact control of bytes, lines, digests, and sizes.

## Unreadable cases, condition C-5

This environment runs as uid 0, where a file with mode 0 still reads, so a permission based unreadable fixture cannot fail here. Unreadable cases in groups T2, T18, and T22 use a directory path or a missing file instead, for the bundle, for artifacts, and for output paths.
