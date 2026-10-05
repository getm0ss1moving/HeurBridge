"""Cell stage on Track B: how the flow places the standard cells around an imported macro layout.

recipe     CellRecipe (ORFS settings, global-placement arguments, the cells' start, placement and routing hints) and
           CellStage, the OrfsEvaluator hook that applies one recipe to every run of an evaluator
positions  standard-cell start positions for a recipe (HB-GP, or a file written by another placer)
select     racing at f1, the J_safe pick over equal positions, and the headroom demo's go rule
"""

from .recipe import CellRecipe, CellStage, DensityCap, RouteAdjust, merge_gpl_args, merge_make_vars  # noqa: F401
