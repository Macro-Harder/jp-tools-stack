# JP tools stack

Small deterministic tools. Each tool is one program with fixed inputs and fixed outputs: it reads named inputs, writes named outputs, and reports a clear pass, fail, or count. Every tool here is Python standard library only and ships with its tests and examples in its folder.

- [tier-test](tier-test/) applies the tier rule and size test to one attested product fact record and reports the tier, with the line by line basis.
- [three-checks](three-checks/) runs the authenticity, chain, and completeness checks over the records of one stage closure and reports every missing or broken link.
- [regression-corpus-gate](regression-corpus-gate/) judges proposed amendments to flow documents against the regression corpus before they take effect and writes a record of the outcome.
- [test-queue](test-queue/) serialises heavy test suite runs on one machine so builds take turns instead of slowing each other down, with a priority rule for which project goes first.

Licensed under Apache 2.0. Copyright 2026 J.P. Picard aka Macro-Harder.
