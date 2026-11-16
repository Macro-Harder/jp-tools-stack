# regression-corpus-gate

The regression corpus gate judges proposed amendments to flow documents against the regression corpus before they take effect. A run selects the corpus rows an amendment touches, presents them for judging, verifies the verdicts and any claimed re-ruling, and writes a record of the outcome. The record informs a closure decision and makes none.

The tool is one Python program, `regression_corpus_gate.py`, standard library only. It requires Python 3.12 or later.

## Running the tool

```
python3 regression_corpus_gate.py --form FORM [arguments for that form]
```

FORM is one of `worksheet`, `remaining`, or `finalise`.

- The worksheet form issues a worksheet and a prefilled verdicts template for the rows the amendment touches. Required arguments: `--runner`, `--judge`, `--author`, `--ruler`, `--coordinator`, `--amendment`, `--declaration`, `--declared-mode`, `--tier`, the seven change kind flags, `--worksheet-out`, and `--template-out`. `--corpus` and `--queue` are optional; supplying `--queue` lists re-ruling candidates on the worksheet.
- The remaining form names the checked pairs that still lack a verdict. Required arguments: the identity and attestation arguments of the worksheet form, plus `--verdicts` and `--remaining-out`. `--reader-designate` and `--queue` are forbidden in this form.
- The finalise form recomputes the whole front end, verifies the verdicts binding, verifies any claimed re-ruling against the queue, applies the blocking arithmetic, and writes the text report and the JSON results. Required arguments: the identity and attestation arguments, plus `--reader-designate`, `--verdicts`, `--report-out`, and `--results-out`. `--queue` is optional and is read only where a claim block exists.

Identity and role arguments: `--runner`, `--judge` (the judge of record, never read from any input file), `--author`, `--ruler`, `--coordinator`, `--panel-judge` (repeatable, once per panel judge), and `--reader-designate` at the finalise form. Attestation arguments: `--declared-mode` (`subset` or `full`), `--tier` (`Low`, `Medium`, `High`, `Extra High`, `Plaid`), `--context` (`stated`, `unstated`, `mixed`, `disputed`; omission means `unstated`), and the seven change kind flags `--change-index-system`, `--change-gate-rule`, `--change-corpus`, `--change-definition`, `--change-counting-method`, `--change-verdict-form`, `--change-closure-rule`, each `yes` or `no`. A second attester set, prefixed with `second-`, is required where the runner is the wording author or the declarer is the wording author.

## Outcomes and exit statuses

| Status | Outcome |
|---|---|
| 0 | pass |
| 1 | fail |
| 2 | input error |
| 3 | incomplete |
| 4 | unverifiable |
| 5 | re-ruled pass |
| 6 | barred |
| 7 | declaration conflict |
| 8 | self test failure |
| 9 | remaining rows report |
| 10 | worksheet issued |

The plain sentences:

- pass: The amendment passed every checked row and may go forward to filing and reading.
- fail: The amendment is blocked because at least one checked row failed and no confirmed re-ruling excuses that fail.
- re-ruled pass: The amendment may go forward because every fail is excused by a confirmed re-ruling that names its incident.
- incomplete: The run is not finished because at least one checked row has no verdict, and an unfinished run is blocked.
- unverifiable: The run could not settle the amendment because at least one checked row could not be judged or could not be tested.
- barred: The run is barred because a judge is the author, the ruler, or the coordinator of the step, so no verdict may stand.
- input error: The run could not start because an input is missing, malformed, or inconsistent, and the error line names the exact fault.
- declaration conflict: The declaration does not cover an index that the wording itself names, so the declaration must be amended and confirmed again before any judging.
- self test failure: The tool failed its own synthetic checks, so the run stopped before judging and no result from this run may be relied on.

This tool exit status numbers differ from three-checks at 3, 4, and 6, naming the three pairs: status 3 is incomplete in this tool and UNVERIFIABLE in three-checks; status 4 is unverifiable in this tool and barred in three-checks; status 6 is barred in this tool, and three-checks has no status 6, its barred run being status 4.

## This gate and the Plaid replay suite

The distinction is plain: this gate judges proposed amendments against the corpus before they take effect, while the suite replays known failures against a built thing. The gate works on proposed wording and a declaration of the indexes it touches; the replay suite works on a built artefact. A gate pass is not a replay result, and a replay result is not a gate pass.

## File syntax summaries

The amendment file holds one wording item after another. Each item opens with a line of the form `item: LABEL`, followed by its wording text lines. A line that begins with the item marker at the first character always opens a new item.

The declaration file holds a header (`declarer:` and `amendment-fingerprint:` lines), one block per wording item, and a confirmation block. A block holds token lines of the form `token: TOKEN | basis: BASIS PROSE`, or one line of the form `no-touch: BASIS PROSE` asserting the item touches no index. The confirmation block opens with `confirmation:`, names the confirmer, repeats each item with a `tokens:` line, and closes with `end-confirmation:`.

The verdicts input holds a binding header (fingerprints, modes, triggers, one `checked:` line per checked corpus ID, the judge of record, and any panel judges), then one verdict block per checked pair. A block opens with `verdict: LABEL C-000` and holds `judge:`, `clause:`, `word:`, and `reason:` lines. A FAIL verdict that claims an excuse carries one `claim:` block holding `queue-item:`, `ruling-date:`, and `confirming-judge:` lines.

The corpus and the queue keep their own existing formats. The corpus is the register of incident rows with its two count statements. The queue is searched by corpus ID token and entry status, never field parsed.

## Input errors

Every input error carries its own identifier and wording: every input error is printed with its distinct wording and writes no file. An input error prints the input error sentence and the specific wording line to standard error and exits with status 2. Usage errors and delivery failures also exit with status 2, each in its own form. The tool never overwrites an output path that already exists.
