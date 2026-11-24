:type: level
:order: 2

=======
Level 2
=======

.. container:: lead

   Complete closure of all :math:`\binom{6}{2} = 15` pairs from :math:`L_1` — 203 points, 10 lines, 16 circles, and 50 golden sections (34 on explicit lines).

Overview
========

Every pair of the 6 points in :math:`L_1` is processed, yielding **10 unique lines**, **16 unique circles**, and **203 unique points** across :math:`\mathbb{Q}(\sqrt{3}, \sqrt{7}, \ldots)`. Within :math:`L_2`, **50 golden sections** emerge, **34** of which lie directly on the 10 constructed lines, forming **7 golden chains** (up to length 4) across **8 distinct scales**.

.. raw:: html

   <div class="geometor-svg-viewer"
        data-src="../../_static/svg/l2/l2_overview.svg"
        data-caption="Level 2 Overview — 203 points, 10 lines, 16 circles, 34 golden sections on explicit lines">
   </div>

Golden Section Ancestor Explorer
================================

Step through or play all **34** explicit-line golden sections in Level 2. Each frame isolates the minimal Euclidean ancestor tree back to :math:`A` and :math:`B`:

- **Cyan lines**: ancestor lines of the 3 golden section points.
- **Magenta circles**: ancestor circles of the 3 golden section points.
- **Gold / amber segments**: the highlighted golden section :math:`(P, Q, R)`.

Use **Scroll** to zoom, **Drag** to pan, or **Prev / Play / Next** (or arrow keys / spacebar) to inspect each construction.

.. raw:: html

   <div class="geometor-svg-switcher"
        data-manifest="../../_static/svg/l2/manifest.json"
        data-base="../../_static/svg/l2/"
        data-interval="1500">
   </div>
