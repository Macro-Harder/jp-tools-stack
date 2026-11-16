# Fixture note: copied real text fixtures

These fixtures are copied excerpts of real files, frozen at creation on
2026-11-15 and never refreshed. Each entry lists its source and the traits
its bytes actually hold, checked against the bytes.

## real_corpus_excerpt.md

Source: ~/workspace/build-flow-expansion/REGRESSION-CORPUS.md, front matter
lines 1 to 20, register rows C-001, C-005, C-019, C-112, C-147, C-187, and
C-194 at their source lines, and the count check section lines 246 to 252.

Traits its bytes hold: the front matter count statement in the real prose
form, beginning with the words This corpus contains and stating 224 before
the words incident entries; the closing count check in the real bullet form,
with per annex bullet lines for Annex 1 to Annex 4 and a total line reading
111 + 35 + 40 + 38 = 224 rows; seven register rows only, so the excerpt as a
whole is not a valid corpus and a run over it is refused under IE-11
naming C-002, because the missing ID test stands before the count test in
the fixed integrity order, so the count facts, front matter 224, closing
check 224, and rows found 7, are never reached; one Gap only row, one
row carrying both Gap and FM tokens, and one cross referenced row, C-019,
whose incident cell carries a Cross-ref suffix naming C-186.

## real_queue_open_excerpt.md

Source: ~/workspace/build-flow-expansion/DECISION-QUEUE.md, the DQ-070 entry
at source lines 1114 to 1161.

Traits its bytes hold: one open entry with a status line reading Banked,
standing before any passage heading; the entry text names the corpus IDs
C-137 and C-160.

## real_queue_ruled_excerpt.md

Source: ~/workspace/build-flow-expansion/DECISION-QUEUE.md, the DQ-138 entry
at source lines 4042 to 4063, inside the ruled record section.

Traits its bytes hold: one ruled record entry with a status line reading
RULED, closed; the entry text names the corpus IDs C-137 and C-160.

## real_queue_settled_excerpt.md

Source: ~/workspace/build-flow-expansion/DECISION-QUEUE.md, the DQ-034 entry
at source lines 4009 to 4041, inside the ruled record section.

Traits its bytes hold: one entry with a status line beginning SETTLED,
closed, stating in prose that the entry is a Manager settlement and not a
ruling; the entry names no corpus ID token in the C-000 form.

## real_queue_tail_excerpt.md

Source: ~/workspace/build-flow-expansion/DECISION-QUEUE.md, heading lines
only, at source lines 4560, 4588, 4592, and 4596.

Traits its bytes hold: four tail entry headings with no status line in the
excerpt; the DQ-158 heading carries the word SETTLED, and the DQ-165, DQ-166,
and DQ-167 headings each carry the word RULED; no heading in the excerpt
names a corpus ID token in the C-000 form, so no candidate presentation can
arise from these bytes.
