# corrected/ — 修正后数据副本

本目录是**依据明确规则**由上游原件生成的派生副本；上游 `wiki/pages.json`、`kg/relations/*.json` **原文件未被改动**。

## 1. `pages.clean.json`

- 依据：`merges.csv` 中 **13 条已确证同人合并**（别名页 → 主档页）。
- 操作：把 dup 页名并入 canon 页 `aliases`（去重）→ 删除 dup `person` 页 → `alias_index[dup] = canon`。
- 记录：文件内 `_cleaning.folded_person_pages` 列出全部折叠对。
- 未做：MED 双空壳同人 323、aliases 跨人污染（舜↔刘舜）均**未**在此副本处理（避免误并）。

## 2. `kg_all_relations.clean.json` / `kg_family_relations.clean.json`

仅删除三类**可确证**噪声行（逐类计数见文件内 `_cleaning.removed`）：

| 类别 | 规则 | all_relations | family_relations |
|---|---|---|---|
| 自环 | `person1 == person2` | 77 | 24 |
| 别名对 | `{person1,person2}` ∈ 13 条合并的 {dup, canon} | 1 | 1 |
| 年代错位 | 5 组两端断代无交集的对（子婴↔李牧、李信↔嬴政、齐孝公↔蔡泽、楚怀王↔楚庄王、齐襄公↔晋襄公） | 1 | 0 |

## 3. 未删除但已量化：person 字段碎片

`kg_field_quality.json` 给出「person 字段含标记/半句碎片」的比例：

- `family_relations.json`：**86.7%**（3904 / 4503）
- `all_relations.json`：21.9%（172 / 787）

即原始关系抽取产物**质量堪忧**；本副本**不删**这些行（保留供上游重加工），仅如实报告。
