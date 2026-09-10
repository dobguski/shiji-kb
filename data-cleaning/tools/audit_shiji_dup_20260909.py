# -*- coding: utf-8 -*-
"""审计：bu-wei(不韦) 同类问题全库扫描（只读）。

判定素材：
  - figures / figure_relations / figure_redirects.json / figure_corrections（works.db + data 下文件）
  - shiji-kb wiki/pages.json（别名证据：person 页互为别名）

分类输出：
  A. 总览规模
  B. shiji-kb 关系自环（figure_id==related_id）→ 确定噪声
  C. bu-wei 型：person 页 X 的名字是另一 person 页 Y 的 alias，且 X/Y 各自成 timeline figure → 同人重复候选
  D. shiji-kb 关系年代错位（两端均有生卒且无交集）→ 疑似噪声（下界）
  E. 低置信浏览桶：shiji-kb 空壳 figure（0作品0事件）其名是另一有作品 figure 名的子串（无别名证据，仅提示）

用法: python data/audit_shiji_dup_20260909.py [works.db]  （只读，不写库；仅输出 + 落两份 CSV）
"""
import sqlite3, json, os, sys, csv, datetime

DB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), 'works.db')
PAGES = r'E:\AI探索学习\shiji-kb\wiki\pages.json'
OUT_B = os.path.join(os.path.dirname(__file__), f'_audit_buweitype_{datetime.datetime.now():%Y%m%d}.csv')
OUT_R = os.path.join(os.path.dirname(__file__), f'_audit_relartifacts_{datetime.datetime.now():%Y%m%d}.csv')

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def load_redirects():
    p = os.path.join(os.path.dirname(__file__), 'figure_redirects.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


def figmeta_quality(md):
    try:
        d = json.loads(md or '{}')
        return d.get('quality')
    except Exception:
        return None


def main():
    c = sqlite3.connect('file:' + DB.replace('\\', '/') + '?mode=ro', uri=True)
    c.row_factory = sqlite3.Row
    redirects = load_redirects()
    print(f'DB: {DB}\n')

    def fig_by_name(nm, prefer_src='shiji-kb'):
        r = c.execute(
            'SELECT id,name,dynasty,birth_year,death_year,source,is_curated,works_count,events_count,'
            'poems_count,importance,metadata,alt_names FROM figures WHERE name=? ORDER BY '
            "(is_curated=1) DESC, (source=? ) DESC, works_count DESC, importance DESC LIMIT 5",
            (nm, prefer_src)).fetchall()
        return r

    # ── A. 总览 ──
    shiji_figs = c.execute("SELECT count(*) FROM figures WHERE source='shiji-kb'").fetchone()[0]
    shiji_rels = c.execute("SELECT count(*) FROM figure_relations WHERE source='shiji-kb'").fetchone()[0]
    rel_total = c.execute("SELECT count(*) FROM figure_relations").fetchone()[0]
    print(f'[A] 规模: figures总={c.execute("SELECT count(*) FROM figures").fetchone()[0]} '
          f'shiji-kb={shiji_figs} | relations总={rel_total} shiji-kb={shiji_rels} | '
          f'redirects={len(redirects)} | figure_corrections total='
          f'{c.execute("SELECT count(*) FROM figure_corrections").fetchone()[0]}')

    # ── B. 自环关系 ──
    print('\n[B] shiji-kb 关系自环 (figure_id==related_id):')
    loops = c.execute(
        "SELECT fr.id, fr.figure_id, fr.related_id, fr.relation_type, fr.description, fr.source, "
        "f.name AS n1, f2.name AS n2 FROM figure_relations fr "
        "JOIN figures f ON f.id=fr.figure_id JOIN figures f2 ON f2.id=fr.related_id "
        "WHERE fr.figure_id=fr.related_id AND fr.source='shiji-kb' ORDER BY fr.id").fetchall()
    print(f'   count = {len(loops)}')
    for r in loops[:60]:
        print(f'   {r["id"]}  {r["n1"]}({r["figure_id"]}) --{r["description"]}/{r["relation_type"]}--> {r["n2"]}')

    # ── C. bu-wei 型：别名互为 person 页 → 同人重复 ──
    print('\n[C] bu-wei 型：person 页名字是另一 person 页 alias（别名证据）→ timeline 重复候选')
    pages = json.load(open(PAGES, encoding='utf-8'))['pages']
    persons = {lab: meta for lab, meta in pages.items()
               if isinstance(meta, dict) and meta.get('type') == 'person'}
    alias_pairs = []  # (dup_label, canon_label)
    seen = set()
    for qlab, qmeta in persons.items():
        for a in qmeta.get('aliases') or []:
            a = a.strip()
            if not a or a == qlab:
                continue
            if a in persons and a != qlab:
                key = (a, qlab)
                if key not in seen:
                    seen.add(key)
                    alias_pairs.append(key)
    print(f'   别名重复对(pages) 共 {len(alias_pairs)}')

    def canon_key(x):
        return ((x['is_curated'] or 0), 0 if (x['source'] or '') != 'shiji-kb' else 1,
                (x['works_count'] or 0), (x['importance'] or 0),
                -(figmeta_quality(x['metadata']) or 0))

    dup_candidates = []
    for plab, qlab in alias_pairs:
        fp = fig_by_name(plab)
        fq = fig_by_name(qlab)
        if not fp or not fq:
            continue
        # 两个名字各自的全部 figures（可能同名多条）
        figset = {}
        for nm in (plab, qlab):
            for r in fig_by_name(nm):
                figset.setdefault(r['id'], r)
        ids = list(figset.keys())
        if len(ids) < 2:
            continue
        # 任一端已在 redirects（已并过）则跳过
        if any(i in redirects for i in ids):
            continue
        # 全组合，仅取两两不同 id
        for a in ids:
            for b in ids:
                if a >= b:
                    continue
                ra, rb = figset[a], figset[b]
                best, other = (ra, rb) if canon_key(ra) >= canon_key(rb) else (rb, ra)
                # 关联证据
                rel = c.execute(
                    "SELECT description FROM figure_relations WHERE source='shiji-kb' "
                    "AND ((figure_id=? AND related_id=?) OR (figure_id=? AND related_id=?))",
                    (best['id'], other['id'], other['id'], best['id'])).fetchall()
                dup_candidates.append({
                    'dup_id': other['id'], 'dup_name': other['name'], 'dup_src': other['source'],
                    'dup_works': other['works_count'], 'dup_events': other['events_count'],
                    'dup_curated': other['is_curated'],
                    'dup_q': figmeta_quality(other['metadata']),
                    'canon_id': best['id'], 'canon_name': best['name'], 'canon_src': best['source'],
                    'canon_works': best['works_count'], 'canon_curated': best['is_curated'],
                    'canon_q': figmeta_quality(best['metadata']),
                    'inter_rel': ';'.join(x['description'] for x in rel) or '',
                })
    # 去重（同 (dup_id,canon_id) 组合可能经多别名对重复出现）
    uniq = {}
    for d in dup_candidates:
        uniq[(d['dup_id'], d['canon_id'])] = d
    dup_candidates = list(uniq.values())

    # 分层置信：
    #   HIGH  bu-wei 精确同型：dup 为 shiji-kb 空壳，canon 为精制（curated / 非shiji源 / 有作品）
    #   MED   双方均 shiji-kb 0 作品（同人两 stub，别名证据）
    #   LOW   其余（同名别名但难定/疑跨人，如舜→刘舜）
    def conf(d):
        canon_rich = (d['canon_curated'] or d['canon_src'] != 'shiji-kb' or d['canon_works'] > 0)
        dup_bare = (d['dup_src'] == 'shiji-kb' and not d['dup_works'] and not d['dup_curated'])
        if dup_bare and canon_rich:
            return 'HIGH'
        if dup_bare and d['canon_src'] == 'shiji-kb' and not d['canon_works'] and not d['canon_curated']:
            return 'MED'
        return 'LOW'

    for d in dup_candidates:
        d['conf'] = conf(d)
    from collections import Counter
    cnt = Counter(d['conf'] for d in dup_candidates)
    print(f'   落到 timeline 的不同 id 重复候选 = {len(dup_candidates)}  '
          f'[{cnt.get("HIGH",0)} HIGH / {cnt.get("MED",0)} MED / {cnt.get("LOW",0)} LOW]')
    for d in [x for x in dup_candidates if x['conf'] in ('HIGH', 'MED')][:90]:
        print(f'   [{d["conf"]}] DUP {d["dup_name"]}({d["dup_id"]},src={d["dup_src"]},w={d["dup_works"]},e={d["dup_events"]})'
              f'  ->  CANON {d["canon_name"]}({d["canon_id"]},src={d["canon_src"]},w={d["canon_works"]},cur={d["canon_curated"]})')

    # ── D. shiji-kb 关系年代错位（两端均有生卒且无交集）──
    print('\n[D] shiji-kb 关系年代错位（两端生卒已知且不重叠, gap>30年）疑似噪声:')
    rows = c.execute(
        "SELECT fr.id, fr.figure_id, fr.related_id, fr.relation_type, fr.description, "
        "f.birth_year b1, f.death_year d1, f2.birth_year b2, f2.death_year d2, "
        "f.name n1, f2.name n2 FROM figure_relations fr "
        "JOIN figures f ON f.id=fr.figure_id JOIN figures f2 ON f2.id=fr.related_id "
        "WHERE fr.source='shiji-kb' AND fr.figure_id<>fr.related_id "
        "AND f.birth_year IS NOT NULL AND f.death_year IS NOT NULL "
        "AND f2.birth_year IS NOT NULL AND f2.death_year IS NOT NULL").fetchall()
    anach = []
    for r in rows:
        lo = max(r['b1'], r['b2'])
        hi = min(r['d1'], r['d2'])
        gap = lo - hi if lo > hi else 0
        if lo > hi and gap > 30:
            anach.append((gap, r))
    print(f'   count = {len(anach)}  (于 {len(rows)} 条两端均可断代的关系中)')
    for gap, r in sorted(anach, reverse=True)[:60]:
        print(f'   gap={gap:>5}  {r["n1"]}({r["b1"]}..{r["d1"]}) --{r["description"]}--> '
              f'{r["n2"]}({r["b2"]}..{r["d2"]})  rel#{r["id"]}')

    # ── E. 低置信浏览桶 ──
    print('\n[E] 低置信提示：shiji-kb 空壳(0作品)且名字是另一有作品 figure 名的子串（无别名证据，仅浏览）')
    subs = []
    all_figs = c.execute("SELECT id,name,source,works_count FROM figures").fetchall()
    name_to_ids = {}
    for x in all_figs:
        name_to_ids.setdefault(x['name'], []).append((x['id'], x['source'], x['works_count']))
    for x in all_figs:
        if x['source'] != 'shiji-kb' or x['works_count'] != 0:
            continue
        nm = x['name'] or ''
        if len(nm) < 2:
            continue
        for y in name_to_ids.get(nm, []):
            if y[0] == x['id']:
                continue
        # 找名字包含 x.name 且非 x 的、有作品 figure
        for o in all_figs:
            if o['id'] == x['id'] or o['name'] == nm:
                continue
            if nm in (o['name'] or '') and o['works_count'] > 0:
                subs.append((x, o))
                break
    print(f'   count = {len(subs)}')
    for x, o in subs[:60]:
        print(f'   STUB {x["name"]}({x["id"]},0作品)  ~contains-in~  {o["name"]}({o["id"]},w={o["works_count"]},src={o["source"]})')

    # 写 CSV
    with open(OUT_B, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(dup_candidates[0].keys()) if dup_candidates else ['dup_id'])
        w.writeheader()
        for d in dup_candidates:
            w.writerow(d)
    with open(OUT_R, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['rel_id', 'n1', 'range1', 'rel', 'n2', 'range2', 'gap'])
        for gap, r in anach:
            w.writerow([r['id'], r['n1'], f"{r['b1']}..{r['d1']}", r['description'], r['n2'], f"{r['b2']}..{r['d2']}", gap])
    print(f'\nCSV -> {OUT_B}\nCSV -> {OUT_R}')


if __name__ == '__main__':
    main()
