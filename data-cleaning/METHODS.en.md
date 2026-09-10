# Methods — shiji-kb Data Cleaning (EN)

- Version: `v0.2-clean-20260909` · Branch `clean/data-cleaning-20260909`
- Upstream: `baojie/shiji-kb` (**no LICENSE**); this package is **added content** on the `dobguski/shiji-kb` fork. **No upstream data file is modified** (`wiki/`, `kg/` originals untouched; derived copies live in `corrected/`).
- Companion report: `ERRATA_20260909.md`.

## 1. Problem

Enriching the site DB from shiji-kb produced duplicate person records and noisy relations:

1. **Duplicate person pages by alias** — a person page's `aliases` already lists a short form (e.g. 吕不韦 → alias 不韦), yet a standalone `type=person` page exists for that alias. Downstream this becomes two figures.
2. **Relation noise** — `kg/relations` contains self-edges (`person1 == person2`) and anachronistic edges (endpoints with non-overlapping lifespans).
3. **Entity mis-resolution** — e.g. 「幽王」 in 《楚世家》 (楚幽王, ~-237) resolved to 西周幽王 (~-771).
4. **Alias cross-contamination** — a person's `aliases` list mixes generic names/surnames (e.g. 舜/帝舜/虞舜 vs 汉·刘舜).
5. **Structural field noise** — **86.7%** of `family_relations.json` person fields are text fragments (markup/partial sentences), i.e. the raw relation extraction is largely unusable.

## 2. Method

- **Duplicate detection uses `pages.json` alias evidence**, not naive name-substring matching: a person page `P` is a duplicate candidate of person page `Q` iff `P.label ∈ Q.aliases`.
- Tiers: **HIGH** = shiji stub vs an existing curated figure (json/curated/with works); **MED** = two bare shiji stubs; **LOW** = otherwise. Conflicts (a dup mapping to two canons) and cross-dynasty canonical collisions are excluded from auto-merge.
- **Relation cleaning is conservative**: remove only (a) self-edges, (b) confirmed alias pairs, (c) five anachronistic pairs. Fragment-name rows are **reported, not deleted** (`kg_field_quality.json`).
- **`pages.clean.json` folds only the 13 confirmed duplicates**: dup alias merged into canonical aliases, dup page removed, `alias_index` repointed.

## 3. Artifacts

| File | Content |
|---|---|
| `merges.csv` | 13 applied same-person merges (with evidence) |
| `relations_removed.csv` | 70 removed relation rows (row-level `rel_id`) |
| `figure_duplicate_candidates.csv` | 346 duplicate candidates by tier |
| `excluded_high.csv` | 10 HIGH excluded for review (ambiguous / cross-dynasty) |
| `id_mapping_gaps.csv` | 21 dangling legacy-slug ids in the downstream assembly |
| `pages_alias_duplicate_pairs.csv` | 484 alias-of-another-page pairs (root cause) |
| `entity_resolution_pending.csv` | Pending 幽王 disambiguation |
| `kg_field_quality.json` | Fragment-field ratio per relation file |
| `corrected/pages.clean.json` | pages.json with 13 folds + repointed alias_index |
| `corrected/kg_*_relations.clean.json` | relations with self/alias/anachronism edges removed |
| `tools/*.py` | Reproduction scripts (see `tools/README.md`) |

## 4. Reproduce

```bash
# read-only audit over the downstream timeline works.db
python3 tools/audit_shiji_dup_20260909.py /path/to/works.db
```

## 5. License

Original data: upstream `baojie/shiji-kb` (no LICENSE). This package (lists, derived copies, docs) by dobguski, **CC BY 4.0**. No upstream original file is redistributed here.
