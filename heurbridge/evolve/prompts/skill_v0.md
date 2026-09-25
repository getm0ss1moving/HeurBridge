# Skill document S (v0) — writing macro heuristics that a learned bridge can refine

1. Your program is scored AFTER a learned bridge refines its output and a legalizer projects it; the
   cost is measured on the final layout. Raw quality of your output is not the objective.
2. Make your errors systematic, not erratic. A heuristic whose displacement to good layouts is
   predictable from the design (always the same kind of shift) is refined far better than a slightly
   better one that is noisy (predictability beats small error).
3. Decide what the bridge cannot fix: discrete, non-local structure. The bridge moves macros
   continuously and locally; it does not flip orientations, reorder groups across the die, swap
   identical macros far apart, or change which side of the die a group sits on. Get these right.
4. Leave continuous fine-tuning (exact offsets, spacing, small shifts) to the bridge; do not spend
   runtime on it.
5. Keep macros inside the core and avoid overlaps; the legalizer fixes small overlaps but large
   ones move macros far from where you put them.
6. Group macros that talk to each other (macro_aff) and place groups near the fixed objects they
   connect to (io_pull, io_w). Boundary placement of large macros usually frees the centre for cells.
7. Determinism and symmetry: use only ``rng`` for randomness, iterate objects in
   ``design.canonical_order`` / ``design.macro_order``, never rely on object indices for tie-breaks.
8. Runtime matters (a penalty above 30 s); prefer O(M^2) numpy over Python loops over nets.
9. Known failure modes: all macros in one corner (channel congestion), macros in the core centre
   (blocks cell placement), identical macros scattered (long datapaths), orientation ignored for
   macros with pins on one side.
