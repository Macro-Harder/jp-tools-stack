# tier-test

## What it is

tier-test applies the tier rule and size test of R-4 to one attested product fact record and reports the tier the test gives, with the line by line basis a tier record requires. It is a pure evaluator: one program, one job, named input, named output, no standing state. One record describes one product, and the tool never aggregates several products into one evaluation and never gives a build level result.

### Input record

The input record is a JSON object with a closed field set. Any field outside the set is an input error. The fields, in order, are: build_ref (string, non-empty, required), product_ref (string, non-empty, required), handles_money ("yes", "no", or "unknown", required), security_surface ("yes", "no", or "unknown", required), public_surface ("yes", "no", or "unknown", required), private ("yes", "no", or "unknown", required), module_count (integer 0 or above, or "unknown", required), single_deployable_unit ("yes", "no", or "unknown", required when module_count is an integer at most 3 and optional otherwise), captain_invoked_tier (one of Low, Medium, High, Extra High, Plaid, optional), claimed_tier (one of Low, Medium, High, Extra High, Plaid, optional), and facts_note (string, non-empty, required). facts_note names who attested the facts and what they rest on, including the module inventory counted. The file must be UTF-8 text with no byte order mark, at most 2000000 bytes, with no duplicated key, and no null values. The tool reads its input once, composes its whole output before writing anything, never overwrites its input file, and writes nothing outside the named output.

### Input contract

Suppliers attest the facts against these six predicate definitions, which are the contract in force.

Module: a distinct unit in the product's own design or module inventory, counted once each. Files, lines of code, teams, and features are not modules unless the product's design lists them as modules, and the supplier names the inventory counted in facts_note.

Money surface: any part of the product through which money or payment value is received, held, moved, charged, refunded, or reconciled, including where payment instructions or payment credentials are taken, stored, or acted on. Under Q4 Option A this same definition governs the single handles_money field; under Q4 Option B it governs the money_surface field only.

Security surface: any part of the product whose failure, misuse, or compromise could expose, change, or block access to the product, its data, its users, or a connected system. Authentication, authorisation, secrets handling, trust boundaries, and privileged operations always count as a security surface.

Public surface: any part of the product that a person outside Captain JP and the people and agents she appoints can reach, read, call, download, or see without being given private access. Public pages, public application programming interfaces, published packages, and public repositories count.

Private: the product is intended and arranged for Captain JP and the people and agents she appoints only, with access limited to that group. Private is judged on who the product is for and how access is limited, not on whether it also has a public surface, which is attested separately under Q5 Option A.

Deployable unit: a set of modules that is built, shipped or installed, and run as one thing, under one release and one running boundary. If modules ship, install, or run separately, they form more than one deployable unit.

### Exit statuses

Three outcomes only: 0: tier given, 1: unsettled, 2: input error, delivery failure, or usage error. On exit 0 or 1 the report is written to the output file and printed identically to standard output. An unsettled report gives no tier and names every unsettled cause with its settlement instruction. On exit 2 nothing is printed on standard output and no report is delivered as a result: an input error names each failure of the input record or of the paths given, a delivery failure names the channel that could not be written, and a usage error states the expected argument form. The three exit 2 cases are distinctly named and never use each other's wording.

### The report and the tier record

The report is the size test basis component of a tier record, not a tier record. The remaining tier record duties sit outside this tool. The selected tier where it differs from the test result, an invocation as the basis form, and the Plaid ruling and its basis rest with Captain JP, at selection. The capacity clearance rests with the Project Manager, at the grill. Lowerings and raisings with their authority rest with Captain JP by recorded ruling and with the Manager, at the change, and the raise notification to Captain JP is made by the Manager when the raise is made. The staffing reviews a lowering or a raising triggers rest with the build's roles, at the change. Closed stage entries are not restated on a raise, a duty of the tier record's keeper at the change. Staffing shortfall or excess entries, and any statement of which protections and instruments are in force under the DQ-142 disagreement rule, rest with the tier record's keeper, from rosters and spawn records, when staffing is known. Any build level tier filing drawn from per product results is the caller's own determination, is never presented as a test result, and is filed with each product's report beside it.

### Filing rule

The report, its echoed input included, is filed alongside the tier record in the project's private design repo, and a changed fact set is a new run whose report is filed beside the earlier one. Filing the report files the facts with it, because the report echoes the full input record.

### Measures overrule

The measures are compiled constants with no run time option: few is at most 6 modules, small is at most 3 modules, and tiny is at most 3 modules forming one deployable unit. A recorded overrule by Captain JP is applied as a constants change by the maintainer, expected the same day, and changes the version. In the interval between a recorded overrule and the tool catching up, callers hand-apply the ruling and cite the ruling, not the stale tool.

## Example

### Worked example

The shipped worked example pair, example-input.json and example-report.txt, reproduced in full. The record describes a product of five modules with no money, security, or public surface and not private, so the result is Medium: L1 and L2 do not fire, L3 is met, and L4 is not met because private is "no".

```
{
  "build_ref": "example-build",
  "product_ref": "example-product",
  "handles_money": "no",
  "security_surface": "no",
  "public_surface": "no",
  "private": "no",
  "module_count": 5,
  "facts_note": "Example facts attested by the tier-test maintainers for illustration. The module inventory counted is the example product's design module list of five modules."
}
```

```
tier-test 1.0.0
Tier test report
This report applies the tier rule and size test of R-4.

Result
Result: Medium.
Basis: requirement line L3 was met.

Outcome table
L1: A money, security, or public surface gives High at minimum. Outcome: not fired.
L2: More than a few modules gives High at minimum. Outcome: not fired.
L3: Medium requires no money surface, no security surface, and a few modules only. Outcome: met.
L4: Low requires a private product with no money surface, no security surface, no public surface, and a tiny module count. Outcome: not met.
L5: Extra High is selected only by Captain JP. Outcome: stated.
L6: Plaid is above the size test entirely. Outcome: stated.

Line by line basis

L1: A money, security, or public surface gives High at minimum.
Facts used: handles_money = "no"; security_surface = "no"; public_surface = "no".
Outcome: not fired.
Effect: this line imposes no minimum.

L2: More than a few modules gives High at minimum.
Facts used: module_count = 5.
Outcome: not fired.
Effect: this line imposes no minimum.

L3: Medium requires no money surface, no security surface, and a few modules only.
Facts used: handles_money = "no"; security_surface = "no"; module_count = 5.
Outcome: met.
Effect: the product is eligible for Medium under this line.

L4: Low requires a private product with no money surface, no security surface, no public surface, and a tiny module count.
Facts used: private = "no"; handles_money = "no"; security_surface = "no"; public_surface = "no"; module_count = 5; single_deployable_unit = not applicable (module_count is above 3).
Outcome: not met.
Effect: the product is not eligible for Low under this line.

L5: Extra High is selected only by Captain JP.
Facts used: none.
Outcome: stated.
Effect: Extra High is never a result of this test.

L6: Plaid is above the size test entirely.
Facts used: none.
Outcome: stated.
Effect: Plaid is never a result of this test.

Facts as supplied
Input fingerprint (SHA-256 of the input file bytes): 6dc66ac3b876745c4ff3c40ff98567fced2e3d93d0d60d1dd4a19fde3aeff448.
The digest identifies the input file exactly; the same facts written with different spacing or key order give a different digest.
build_ref = "example-build"
product_ref = "example-product"
handles_money = "no"
security_surface = "no"
public_surface = "no"
private = "no"
module_count = 5
single_deployable_unit = not supplied
captain_invoked_tier = not supplied
claimed_tier = not supplied
Facts as supplied; the tool evaluates the record, it does not verify the facts.
facts_note
Example facts attested by the tier-test maintainers for illustration. The module inventory counted is the example product's design module list of five modules.

Measures applied
Few is at most 6 modules. Small is at most 3 modules. Tiny is at most 3 modules forming one deployable unit. These measures are cited to DQ-054.
The single handles_money field serves both source phrases: "handles money" in L1 and "money surface" in L3 and L4.
The input contract in force is the six predicate definitions printed in the README.
Tool version: 1.0.0.

Standing notes
Extra High and Plaid are selected only by Captain JP, and the test never gives either.
This report is the size test basis component of a tier record, not a tier record.

Counts
Lines fired or met: 1.
Lines not fired or not met: 3.
Lines unsettled: 0.
Restrictions stated: 2.

Exit status: 0.
```

### Worked attestation examples

The example pack in the examples folder works borderline calls through the Input contract definitions. One note per entry follows.

- refunds-only: The money surface definition covers any part of the product through which payment value is refunded, so a product that only refunds payments, takes no payments, and holds no balances still attests handles_money as "yes". Line L1 fires on handles_money and the result is High.
- secrets-only: The security surface definition names secrets handling as always counting as a security surface, so a product whose only security surface is its handling of the secrets it runs with attests security_surface as "yes". Line L1 fires on security_surface and the result is High.
- two-inventories: The module definition is a counting convention: a distinct unit in the product's own design or module inventory, counted once each, with the inventory counted named in facts_note. Attested against the design's coarse module list, the same product counts 3 modules forming one deployable unit and the result is Low. Attested against the design's fine module list, it counts 8 modules and line L2 fires, so the result is High. The count follows the named inventory, not the product alone.
- two-units: The deployable unit definition counts a set of modules that is built, shipped or installed, and run as one thing; modules that ship and run separately form more than one deployable unit. Three modules that ship and run as two deployable units attest single_deployable_unit as "no", so tiny fails on the unity condition: L3 is met, L4 is not met, and the result is Medium.

## How to use it

Run the program with exactly two positional arguments:

    tier-test INPUT OUTPUT

INPUT is the path of the input record (JSON) and OUTPUT is the path the report is written to. The report is also printed to standard output, identical to the file. The tool has no options and no configuration; any argument, including one starting with a dash, is treated as a path when exactly two arguments are given.

## For agents

Agent use differs in what surrounds the run. The agent attests the facts against the six predicate definitions in the Input contract, names who attested them and the module inventory counted in facts_note, runs the tool, and files the report alongside the tier record in the project's private design repo. Where the facts change, the agent runs the tool again and files the new report beside the earlier one. A build level tier filing drawn from per product results is the agent's own determination, never presented as a test result, and is filed with each product's report beside it.

Example: an agent preparing a tier record for a five module product with no money, security, or public surface writes the input record shown in the worked example, runs `tier-test input.json report.txt`, and files report.txt beside the tier record. The result is Medium at exit status 0.
