:type: level
:order: 3

=======
Level 3
=======

.. container:: lead

   Frontier exploration across :math:`\binom{203}{2} = 20,503` pairs — 17,562 unique lines, 32,719 unique circles, and ~2.37 billion intersection slots.

Combinatorial Frontier
======================

At Level 3, the 203 points of :math:`L_2` generate **20,503** unordered pairs, **17,562 unique lines**, and **32,719 unique circles** (**50,281** structures total). Because full sequential closure requires evaluating ~2.37 billion intersection slots, we explore Level 3 through targeted traversal orders, parallel intersection, and checkpointed runs (see :doc:`../../approaches/index`).

In **Round-Robin Pair 70** (interleaved across lines 0–9), the model reaches **27,251 points**, **56 lines**, **145 circles**, and **1,216 golden sections**.

Recursive Ancestor Explorer
===========================

The switcher below cycles through **24** golden sections from **Round-Robin Pair 70**, spanning shallow, mid, and deep ancestor trees. Each frame traces the exact parent-structure DAG from the 3 golden section points back to :math:`A` and :math:`B`, with full zoom-to-fit framing that includes every ancestor circle.

.. raw:: html

   <div class="geometor-svg-switcher"
        data-manifest="../../_static/svg/l3/manifest.json"
        data-base="../../_static/svg/l3/"
        data-interval="1500">
   </div>
