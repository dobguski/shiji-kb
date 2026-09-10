# -*- coding: utf-8 -*-
"""清理 shiji-kb 关系噪声（纯删 figure_relations 行，不动 figures）。

两类：
  1. 自环：figure_id==related_id（61 条，source='shiji-kb'）→ 一律删除。
  2. 年代错位（两端生卒已知、无交集且 gap>30，5 条，source='shiji-kb'）：
     64129 子婴↔李牧(君臣)  65154 李信↔嬴政(师徒, 实为无/李信年份脏)
     64255 齐孝公↔蔡泽(祖孙) 64309 楚怀王↔楚庄王(师徒)  64058 齐襄公↔晋襄公(父子)
     按关系 id 删除（两端库行 id 一致）；如某 id 不存在则该端跳过（幂等）。

用法: python data/fix_shiji_rel_noise_20260909.py <works.db> [--dry]
写库前自动 sqlite backup API → <db>.shiji_relnoise_bak_<YYYYmmdd_HHMMSS>
"""
import sqlite3, sys, datetime

ANACH_IDS = (64129, 65154, 64255, 64309, 64058)
TAG = 'shiji-relnoise-20260909'


def backup(db):
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    dst = f'{db}.shiji_relnoise_bak_{ts}'
    s = sqlite3.connect(db)
    d = sqlite3.connect(dst)
    with d:
        s.backup(d)
    d.close()
    s.close()
    print('[backup] ->', dst)


def main(db, dry):
    c = sqlite3.connect(db)
    if not dry:
        backup(db)
    # 1) 自环
    n1 = c.execute("DELETE FROM figure_relations WHERE source='shiji-kb' AND figure_id=related_id").rowcount
    # 2) 年代错位（按 id，source 限制）
    rows = c.execute(f"SELECT id, figure_id, related_id FROM figure_relations WHERE id IN ({','.join('?'*len(ANACH_IDS))}) AND source='shiji-kb'", ANACH_IDS).fetchall()
    n2 = c.execute(f"DELETE FROM figure_relations WHERE id IN ({','.join('?'*len(ANACH_IDS))}) AND source='shiji-kb'", ANACH_IDS).rowcount
    print(f'self-loop deleted: {n1} | anach deleted: {n2}/{len(ANACH_IDS)} | ids matched: {[r[0] for r in rows]}')
    if not dry:
        c.commit()
    c.close()
    print(('DRY-RUN ' if dry else 'APPLIED ') + db)
    return 0


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    db = sys.argv[1] if len(sys.argv) > 1 else 'data/works.db'
    sys.exit(main(db, '--dry' in sys.argv))
