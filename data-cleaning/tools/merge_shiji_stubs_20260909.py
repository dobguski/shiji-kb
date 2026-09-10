# -*- coding: utf-8 -*-
"""批量合并 shiji-kb 别名 stub → 既有主档（bu-wei 模板泛化，双端复用）。

本轮 12 条（HIGH，2026-09-09 用户核准，canon 身份已逐一核实）：
  墨翟 mo-di→墨子 author_25284；楚王韩信 chu-wang-han-xin→韩信 author_25302；
  汉高祖 han-gao-zu→刘邦 liubang；戚姬 qi-ji-2→戚夫人 qifuren；
  田完 tian-wan→陈完 chenwan；驺衍 zou-yan→邹衍 author_25294；
  鲁公 lu-gong→项羽 xiangyu；太史公 tai-shi-gong→司马迁 simaqian；
  司马长卿 si-ma-zhang-qing→司马相如 simaxiangru；长卿 zhang-qing→司马相如 simaxiangru；
  犬子 quan-zi→司马相如 simaxiangru；卫将军 wei-jiang-jun→卫青 author_25303。

用法: python data/merge_shiji_stubs_20260909.py <works.db> [figure_redirects.json] [--dry]
写库前自动 sqlite backup API → <db>.shiji_stubmerge_bak_<YYYYmmdd_HHMMSS>
dry 模式：不备份不落库，打印逐条明细 + 写计划 CSV。
"""
import sqlite3, json, sys, os, datetime, csv

MERGES = [
    ('mo-di', 'author_25284'), ('chu-wang-han-xin', 'author_25302'),
    ('han-gao-zu', 'liubang'), ('qi-ji-2', 'qifuren'),
    ('tian-wan', 'chenwan'), ('zou-yan', 'author_25294'),
    ('lu-gong', 'xiangyu'), ('tai-shi-gong', 'simaqian'),
    ('si-ma-zhang-qing', 'simaxiangru'), ('zhang-qing', 'simaxiangru'),
    ('quan-zi', 'simaxiangru'), ('wei-jiang-jun', 'author_25303'),
]
TAG = 'shiji-stubmerge-20260909'

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def backup(db):
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    dst = f'{db}.shiji_stubmerge_bak_{ts}'
    s = sqlite3.connect(db)
    d = sqlite3.connect(dst)
    with d:
        s.backup(d)
    d.close()
    s.close()
    print('[backup] ->', dst)


def load_redirects(p):
    if p and os.path.exists(p):
        return json.load(open(p, encoding='utf-8'))
    return {}


def save_redirects(p, rd):
    json.dump(rd, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)


def rec_corr(c, fid, field, original, corrected, note):
    ex = c.execute('SELECT 1 FROM figure_corrections WHERE figure_id=?', (fid,)).fetchone()
    if ex:
        c.execute("UPDATE figure_corrections SET notes=COALESCE(notes,'')||'; '||?, "
                  "verified_by=?, verified_at=datetime('now') WHERE figure_id=?", (note, TAG, fid))
    else:
        c.execute("INSERT INTO figure_corrections (figure_id,field,original_value,corrected_value,verified_by,notes) "
                  "VALUES (?,?,?,?,?,?)", (fid, field, original, corrected, TAG, note))


def main(db, redir_path, dry):
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    rd = load_redirects(redir_path) if not dry else {}
    plan = []
    if not dry:
        backup(db)

    for dup_id, canon_id in MERGES:
        dup = c.execute('SELECT * FROM figures WHERE id=?', (dup_id,)).fetchone()
        canon = c.execute('SELECT * FROM figures WHERE id=?', (canon_id,)).fetchone()
        if not dup:
            print(f'[skip] dup {dup_id} 不存在(已并?)')
            continue
        if not canon:
            print(f'[skip] canon {canon_id} 不存在!')
            continue
        if dup_id == canon_id:
            continue
        # 既有 alias
        import json as _j
        alts = []
        try:
            alts = _j.loads(canon['alt_names']) or [] if canon['alt_names'] else []
        except Exception:
            alts = []
        add_alias = dup['name']
        alias_todo = add_alias not in alts and add_alias != canon['name']

        # 事件明细（迁移前）
        ev_rows = c.execute(
            "SELECT se.id, se.name, se.year, se.event_type FROM shiji_event_figures sef "
            "JOIN shiji_events se ON se.id=sef.shiji_event_id WHERE sef.figure_id=?", (dup_id,)).fetchall()
        ev_exist = set(r[0] for r in c.execute(
            "SELECT shiji_event_id FROM shiji_event_figures WHERE figure_id=?", (canon_id,)).fetchall())
        ev_add = [r for r in ev_rows if r['id'] not in ev_exist]

        # 关系明细：别名 stub 合并进精制 canon 时，shiji-kb 关系一律删除（抽取噪声，如 太史公 上的
        # 比干-父子/商纣王-敌对，迁移会污染主档）；仅非 shiji 源关系才迁移。
        rels = c.execute('SELECT * FROM figure_relations WHERE figure_id=? OR related_id=?', (dup_id, dup_id)).fetchall()
        rel_drop = [r for r in rels if r['source'] == 'shiji-kb']
        rel_mig = [r for r in rels if r['source'] != 'shiji-kb']

        # 其它表引用
        other_refs = {}
        for t in ('works', 'poems', 'figure_works', 'figure_events', 'events', 'k12_exam_points', 'i18n_bios'):
            try:
                cols = [x['name'] for x in c.execute(f'PRAGMA table_info({t})').fetchall()]
                if 'figure_id' in cols:
                    n = c.execute(f'SELECT count(*) FROM {t} WHERE figure_id=?', (dup_id,)).fetchone()[0]
                    if n:
                        other_refs[t] = n
            except Exception:
                pass

        row = {
            'dup_id': dup_id, 'dup_name': dup['name'], 'canon_id': canon_id, 'canon_name': canon['name'],
            'alias_todo': alias_todo, 'events_total': len(ev_rows), 'events_add': len(ev_add),
            'rel_drop': len(rel_drop), 'rel_migrate': len(rel_mig), 'other_refs': ';'.join(f'{k}:{v}' for k, v in other_refs.items()),
            'ev_names': ' | '.join(f'{r["name"]}({r["year"]})' for r in ev_add[:12]),
            'rel_detail': ' | '.join(
                f'{("drop " if r in rel_drop else "mig ")}{r["figure_id"]}-{r["description"]}->{r["related_id"]}' for r in rels[:8]),
        }
        plan.append(row)
        print(f"\n== {dup['name']}({dup_id}) -> {canon['name']}({canon_id})")
        print(f"   alias补: {alias_todo} | 事件: 共{len(ev_rows)} 迁增{len(ev_add)} | 关系: drop{len(rel_drop)} migrate{len(rel_mig)} | 其它表引用: {other_refs or '无'}")
        if ev_add:
            for r in ev_add:
                print(f"      +event {r['name']}({r['year']}/{r['event_type']})")
        for r in rels:
            kind = 'DROP(shiji噪声)' if r['source'] == 'shiji-kb' else 'MIG'
            print(f"      rel {r['figure_id']} -{r['description']}-> {r['related_id']}  [{kind}]")

        if not dry:
            # 执行
            if alias_todo:
                alts.append(add_alias)
                c.execute("UPDATE figures SET alt_names=?, updated_at=datetime('now') WHERE id=?",
                          (_j.dumps(alts, ensure_ascii=False), canon_id))
            for t, n in other_refs.items():
                c.execute(f'UPDATE {t} SET figure_id=? WHERE figure_id=?', (canon_id, dup_id))
            for r in ev_rows:  # INSERT OR IGNORE 全部，再删 dup 行
                c.execute('INSERT OR IGNORE INTO shiji_event_figures (shiji_event_id, figure_id, confidence) VALUES (?,?,?)',
                          (r['id'], canon_id, 0.8))
            c.execute('DELETE FROM shiji_event_figures WHERE figure_id=?', (dup_id,))
            for r in rel_mig:
                nf = canon_id if r['figure_id'] == dup_id else r['figure_id']
                nr = canon_id if r['related_id'] == dup_id else r['related_id']
                rn = r['related_name'] or ''
                if nr == canon_id:
                    rn = canon['name']
                c.execute("INSERT OR IGNORE INTO figure_relations (figure_id,related_id,relation_type,description,start_year,end_year,source,created_at,related_name) "
                          "VALUES (?,?,?,?,?,?,?,?,?)",
                          (nf, nr, r['relation_type'], r['description'], r['start_year'], r['end_year'], r['source'], r['created_at'], rn))
            c.execute('DELETE FROM figure_relations WHERE figure_id=? OR related_id=?', (dup_id, dup_id))
            try:
                rid = c.execute('SELECT rowid FROM figures WHERE id=?', (dup_id,)).fetchone()
                if rid:
                    c.execute('DELETE FROM figures_fts WHERE rowid=?', (rid[0],))
            except Exception:
                pass
            c.execute('DELETE FROM figures WHERE id=?', (dup_id,))
            note = f'merge shiji-kb 别名 stub {dup_id}({dup["name"]}) -> {canon_id}({canon["name"]})'
            rec_corr(c, canon_id, 'dedup', f'dup {dup_id}', 'single', note)
            rd[dup_id] = canon_id
            print('   [APPLIED]')

    if plan:
        csvp = os.path.join(os.path.dirname(__file__), f'_shiji_stubmerge_plan_{datetime.datetime.now():%Y%m%d}.csv')
        with open(csvp, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=list(plan[0].keys()))
            w.writeheader()
            w.writerows(plan)
        print(f'\nplan CSV -> {csvp}  (merges={len(plan)})')

    if not dry:
        c.commit()
        if redir_path:
            save_redirects(redir_path, rd)
            print(f'redirects -> {redir_path} (新增 {len([k for k in rd if k in dict(MERGES)])})')
    c.close()
    print(('DRY-RUN ' if dry else 'APPLIED ') + db)


if __name__ == '__main__':
    db = sys.argv[1] if len(sys.argv) > 1 else 'data/works.db'
    redir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), 'figure_redirects.json')
    main(db, redir, '--dry' in sys.argv)
