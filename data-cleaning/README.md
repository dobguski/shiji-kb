# shiji-kb 数据清洗包（data-cleaning）

- 版本：`v0.2-clean-20260909`（分支 `clean/data-cleaning-20260909`）
- 日期：2026-09-09
- 上游：`baojie/shiji-kb`（**无 LICENSE**）；本包为 `dobguski/shiji-kb` fork 上的**新增内容**，**未改动上游数据文件**（`wiki/`、`kg/` 原件不动；修正副本另置于 `corrected/`）。
- 配套报告：`ERRATA_20260909.md`（问题清单与证据）

## 目录

| 文件 | 内容 |
|---|---|
| `merges.csv` | 已确认并执行的**同人合并** 13 条（stub → 主档），含证据字段 |
| `relations_removed.csv` | 已删除的**关系噪声** 70 条：shiji 自环 61 + 年代错位 5 + 别名自指/幽王伪关系（`rel_id` 精确到行） |
| `figure_duplicate_candidates.csv` | 全库扫描出的**重复候选 346**（HIGH 22 / MED 323 / LOW 1，含并列信息），供复核 |
| `excluded_high.csv` | 从 HIGH 中**排除待核 10 条**（一词双解 / canon 跨代同名）及原因 |
| `id_mapping_gaps.csv` | 下游装配层**旧 slug 悬挂 21 个**（`yingzheng`/`kongzi`/`li-bai`… 真人在库、用另一 id） |
| `pages_alias_duplicate_pairs.csv` | `pages.json` 中「某页名是另一 person 页 alias」的对 **484**（重复建页根因） |
| `entity_resolution_pending.csv` | 称谓**误消解**待核（幽王簇：楚幽王 vs 西周幽王） |
| `kg_field_quality.json` | `kg/relations` **person 字段碎片率**（family 86.7%！/ all 21.9%）——原抽取质量问题量化 |
| `corrected/` | **修正后数据副本**（见 `corrected/README.md`） |
| `tools/` | **复现脚本**（见 `tools/README.md`） |

## 方法（一句话）

以 `wiki/pages.json` 的 **aliases 证据** 判定「同一人被拆成多页」（而非仅靠名字子串），叠加关系/事件证据处置；`kg/relations` 按**自环 / 别名对 / 年代错位**三类确定性规则清洗；对 `pages.json` 仅折叠**已确证**的 13 条重复 person 页。

## 数据来源与许可

- 数据源：本 fork 内 `wiki/pages.json`、`kg/relations/*.json`。
- 本包（清单 / 副本 / 文档）由 dobguski 整理，采用 **CC BY 4.0**。
- 上游无 LICENSE 声明；本包不重分发上游原件，仅在 `corrected/` 提供**依据明确规则生成的派生副本**。

## 复现

见 `tools/README.md`。核心：`python3 tools/audit_shiji_dup_20260909.py <works.db>`（下游 `timeline` 库，只读）。

## 版本

- `v0.1-clean-20260909`：仅 `ERRATA_20260909.md`
- `v0.2-clean-20260909`：+ 本 `data-cleaning/` 数据包（清单/工具/修正副本/英文 METHODS）
