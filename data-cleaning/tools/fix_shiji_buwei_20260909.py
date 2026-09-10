# -*- coding: utf-8 -*-
"""处置 shiji-kb 缩写别名 stub：bu-wei(不韦) → author_25295(吕不韦)。

证据（2026-09-09 定案，双端：本地 data/works.db 与线上 /opt/timeline/data/works.db 对等执行）：
  1. shiji-kb 语料 wiki/pages.json 里 吕不韦 页面的 aliases 自带「不韦」；
     却另立空壳实体 pages/不韦（无生卒、quality 23）→ 导入成为 figures.bu-wei（source=shiji-kb）。
  2. bu-wei 唯一 shiji 事件 = shiji_events 405「吕不韦之死/政治整顿/-235」（秦始皇本纪：
     『〖文信侯〗〖不韦〗死』——原文以「不韦」简称吕不韦），故事件属吕不韦而非独立人物。
  3. figure_relations 64070 称「bu-wei --父子--> author_25295」系抽取噪声：语境为吕不韦列传中
     『@吕不韦@曰…@不韦@虽贫』(自称)，同一人被当成两人并配父子 → 合并时删除。
  4. 幽王伪关系（本脚本顺带处置）：figure_relations 64143 吕不韦--君臣-->西周幽王，出自 kg 噪声边，
     语境为楚世家『…&秦&相@吕不韦@卒…@幽王@卒』逐年记事并列，无君臣关系；且该「幽王」为楚幽王(~-237)，
     被错误消解到西周幽王(约-771) → 删除 64143。

用法: python data/fix_shiji_buwei_20260909.py <works.db> [--dry]
写库前自动 sqlite backup API → <db>.shiji_buwei_bak_<YYYYmmdd_HHMMSS>
幂等：bu-wei 已不存在则跳过合并；64143 已删除则跳过。
"""
import sqlite3, sys, datetime

HOST = 'author_25295'          # 吕不韦（主档）
DUP = 'bu-wei'                 # 不韦（shiji-kb 缩写别名 stub）
YOU_WANG = 'xi-zhou-you-wang'  # 西周幽王（伪关系对端）
TAG = 'shiji-buwei-20260909'
NOTE_MERGE = (
    'merge shiji-kb 缩写别名 bu-wei(不韦) -> author_25295(吕不韦)：'
    '语料吕不韦 aliases 自带不韦；shiji_events 405 吕不韦之死(quote 〖不韦〗死) relink 至主档；'
    '删除别名自指关系 64070(shiji:父子,吕不韦列传自称@不韦@噪声)。'
)
NOTE_YOU_WANG = (
    '删除伪关系吕不韦<->西周幽王(shiji:君臣, 关系64143)：kg 噪声边，语境=楚世家「秦相吕不韦卒…幽王卒」'
    '逐年并列，无君臣关系，且该幽王系楚幽王(~-237)被错消解至西周幽王(~-771)。'
    '同类待核：xi-zhou-you-wang 自环 64172(shiji:敌对) 与 64207(春申君) 疑同源消解噪声。'
)


def backup(db):
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    dst = f'{db}.shiji_buwei_bak_{ts}'
    src = sqlite3.connect(db)
    d = sqlite3.connect(dst)
    with d:
        src.backup(d)
    d.close()
    src.close()
    print('[backup] ->', dst)
    return dst


def record_correction(c, figure_id, field, original, corrected, note):
    """figure_corrections 主键 = figure_id；已有则追加 notes。"""
    ex = c.execute('SELECT 1 FROM figure_corrections WHERE figure_id=?', (figure_id,)).fetchone()
    if ex:
        c.execute(
            "UPDATE figure_corrections SET notes=COALESCE(notes,'') || '; ' || ?, "
            "verified_by=?, verified_at=datetime('now') WHERE figure_id=?",
            (note, TAG, figure_id))
        print(f'  [corr] append {figure_id}')
    else:
        c.execute(
            "INSERT INTO figure_corrections (figure_id, field, original_value, corrected_value, verified_by, notes) "
            "VALUES (?,?,?,?,?,?)",
            (figure_id, field, original, corrected, TAG, note))
        print(f'  [corr] insert {figure_id} field={field}')


def main(db, dry):
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    dup = c.execute('SELECT * FROM figures WHERE id=?', (DUP,)).fetchone()
    host = c.execute('SELECT * FROM figures WHERE id=?', (HOST,)).fetchone()
    if not host:
        print('[ABORT] host missing:', HOST)
        return 1
    print(f'host: {host["name"]}({HOST})   dup:', (dict(dup) if dup else None))

    if not dry:
        backup(db)

    # ── 1. 幽王伪关系 64143（独立于合并，幂等）──
    rc = c.execute(
        "DELETE FROM figure_relations WHERE source='shiji-kb' AND description='shiji:君臣' "
        "AND ((figure_id=? AND related_id=?) OR (figure_id=? AND related_id=?))",
        (HOST, YOU_WANG, YOU_WANG, HOST))
    print(f'[幽王伪关系] deleted {rc.rowcount} row(s)')

    if dup:
        # ── 2. 宿主 alt_names 补「不韦」 ──
        import json
        cur = []
        if host['alt_names']:
            try:
                cur = json.loads(host['alt_names']) or []
            except Exception:
                cur = []
        if '不韦' not in cur:
            cur.append('不韦')
            c.execute("UPDATE figures SET alt_names=?, updated_at=datetime('now') WHERE id=?",
                      (json.dumps(cur, ensure_ascii=False), HOST))
            print(f'  [alt] {HOST} alt_names -> {cur}')
        else:
            print('  [alt] 已含 不韦，跳过')

        # ── 3. shiji_event_figures 迁移（OR IGNORE 防重，唯一 (shiji_event_id,figure_id)）──
        n_ins = 0
        for r in c.execute('SELECT shiji_event_id, confidence FROM shiji_event_figures WHERE figure_id=?', (DUP,)):
            cc = c.execute('INSERT OR IGNORE INTO shiji_event_figures (shiji_event_id, figure_id, confidence) VALUES (?,?,?)',
                           (r['shiji_event_id'], HOST, r['confidence']))
            n_ins += cc.rowcount
        c.execute('DELETE FROM shiji_event_figures WHERE figure_id=?', (DUP,))
        print(f'  [shiji_event_figures] migrated-ins {n_ins}, deleted {DUP} rows')

        # ── 4. figure_relations 迁移（nf==nr 即别名自指 → 丢弃；其余 OR IGNORE）──
        rel_ins = rel_drop = 0
        rels = c.execute('SELECT * FROM figure_relations WHERE figure_id=? OR related_id=?', (DUP, DUP)).fetchall()
        for r in rels:
            nf = HOST if r['figure_id'] == DUP else r['figure_id']
            nr = HOST if r['related_id'] == DUP else r['related_id']
            if nf == nr:
                rel_drop += 1
                continue
            rn = r['related_name'] or ''
            if nr == HOST:
                rn = host['name']
            cc = c.execute(
                "INSERT OR IGNORE INTO figure_relations "
                "(figure_id, related_id, relation_type, description, start_year, end_year, source, created_at, related_name) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (nf, nr, r['relation_type'], r['description'], r['start_year'], r['end_year'],
                 r['source'], r['created_at'], rn))
            rel_ins += cc.rowcount
        c.execute('DELETE FROM figure_relations WHERE figure_id=? OR related_id=?', (DUP, DUP))
        print(f'  [relations] migrated {rel_ins}, alias-self dropped {rel_drop}')

        # ── 5. 其它含 figure_id 的表迁移（bu-wei 均为 0，防御性）──
        for t in ('works', 'poems', 'figure_works', 'figure_events', 'events', 'k12_exam_points', 'i18n_bios'):
            try:
                cols = [x['name'] for x in c.execute(f'PRAGMA table_info({t})').fetchall()]
                if 'figure_id' in cols:
                    n = c.execute(f'UPDATE {t} SET figure_id=? WHERE figure_id=?', (HOST, DUP)).rowcount
                    if n:
                        print(f'  [migrate {t}] {n} rows')
            except Exception as e:
                print(f'  [warn {t}] {e}')

        # ── 6. FTS 清理 + 删行 ──
        try:
            rid = c.execute("SELECT rowid FROM figures WHERE id=?", (DUP,)).fetchone()
            if rid:
                c.execute('DELETE FROM figures_fts WHERE rowid=?', (rid[0],))
        except Exception as e:
            print('  [warn fts]', e)
        c.execute('DELETE FROM figures WHERE id=?', (DUP,))
        print(f'  [figures] deleted {DUP}({dup["name"]})')

        # ── 7. 记账 ──
        record_correction(c, HOST, 'dedup', f'dup {DUP}', 'single', NOTE_MERGE)
    else:
        print('  [skip] 合并主体 bu-wei 已不存在（幂等）')

    record_correction(c, YOU_WANG, 'relations', '吕不韦(君臣) removed', '', NOTE_YOU_WANG)

    if not dry:
        c.commit()
    c.close()
    print(('DRY-RUN ' if dry else 'APPLIED ') + f'{db}')
    return 0


if __name__ == '__main__':
    import os
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    db = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), 'works.db')
    dry = '--dry' in sys.argv
    sys.exit(main(db, dry))
