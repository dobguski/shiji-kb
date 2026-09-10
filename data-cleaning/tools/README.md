# tools/ — 复现脚本

本轮处置所用脚本（来自下游 `timeline` 私有仓 `data/`），可在你自己的 shiji-kb 派生库上复现审计与清理。

| 脚本 | 作用 | 用法 |
|---|---|---|
| `audit_shiji_dup_20260909.py` | 只读全库扫描：自环/年代错位/别名重复分层/跨人污染提示 | `python3 audit_shiji_dup_20260909.py <works.db>` |
| `fix_shiji_buwei_20260909.py` | 单条处置范例：别名 stub 合并（不韦→吕不韦）+ 记账 + redirect | `python3 fix_shiji_buwei_20260909.py <works.db> [--dry]` |
| `fix_shiji_rel_noise_20260909.py` | 删除 shiji 关系自环 + 5 条年代错位 | `python3 fix_shiji_rel_noise_20260909.py <works.db> [--dry]` |
| `merge_shiji_stubs_20260909.py` | 批量别名 stub → 主档合并（12 条，含 redirect/corrections） | `python3 merge_shiji_stubs_20260909.py <works.db> [figure_redirects.json] [--dry]` |

## 依赖与约定

- Python 3 + 标准库 `sqlite3`（无需第三方；`audit_*` 读 `shiji-kb/wiki/pages.json`，路径在脚本顶部常量，按需修改）。
- 目标库为下游 **timeline** 的 `works.db` 结构（`figures` / `figure_relations` / `shiji_events` / `shiji_event_figures` / `figure_corrections` / `figure_redirects.json`）。
- **写库纪律**：脚本写库前自动 `sqlite backup API` 快照（`<db>.<动作>_bak_<ts>`）；`--dry` 只打印计划与落计划 CSV，不落库。
- 合并语义：别名 stub → 精制主档时，**shiji 源关系删除而非迁移**（防噪声污染主档）；事件按别名归属 `INSERT OR IGNORE` 并入。

## 注意

- 脚本内的合并清单（`merge_shiji_stubs_20260909.py` 的 `MERGES`）是本轮**已核证**的 12 条；MED 323 未纳入（待人工复核，见 `figure_duplicate_candidates.csv`）。
- 与本数据包配套阅读：`../ERRATA_20260909.md`、`../README.md`。
