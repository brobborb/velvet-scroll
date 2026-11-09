#!/usr/bin/env python3
"""Builds Velvet Scroll's offline dictionary from two openly licensed sources:

  * WordNet 3.1 (Princeton University, WordNet licence): modern meanings, in order of how common they are,
    with an example and a few words that mean the same. The npm package wordnet-db 3.1.14 has the data files;
    wndb-with-exceptions 3.0.2 has the lists of irregular forms (went -> go, mice -> mouse).
  * Webster's Revised Unabridged Dictionary (1913), from Project Gutenberg ebook 29765, public domain in the
    United States: older meanings, which suit the words in classic books. As JSON from
    github.com/matthewreagan/WebstersEnglishDictionary (dictionary.json).

    python3 make_dictionary.py WORDNET_DICT_DIR EXCEPTIONS_DICT_DIR webster.json OUT_DIR

Writes OUT_DIR/a.json.gz ... z.json.gz and other.json.gz, one per first letter, each {word: entry}, where entry is
  {"w": [[part of speech, meaning, example, [same words]], ...], "o": "Webster's 1913 text"}
and forms.json.gz, {irregular form: [base words]}. The reader downloads them once, with permission, and keeps them.
"""
import gzip, json, os, re, sys
from collections import defaultdict

WN, EXC, WEB, OUT = sys.argv[1:5]
POS = {'n': 'noun', 'v': 'verb', 'a': 'adjective', 's': 'adjective', 'r': 'adverb'}
FILES = {'noun': 'noun', 'verb': 'verb', 'adj': 'adjective', 'adv': 'adverb'}
MAX_SENSES = 6        # meanings per part of speech
MAX_OLD = 700         # characters of Webster's 1913 per word

def synsets(fname):
    """offset -> (part of speech, [words], meaning, example)"""
    out = {}
    for line in open(os.path.join(WN, 'data.' + fname), encoding='utf-8', errors='replace'):
        if line.startswith('  '): continue
        head, _, gloss = line.partition(' | ')
        f = head.split(); off, pos, n = f[0], f[2], int(f[3], 16)
        words = [f[4 + 2 * i].replace('_', ' ') for i in range(n)]
        words = [re.sub(r'\((a|p|ip)\)$', '', w) for w in words]
        parts = [p.strip() for p in gloss.strip().split(';')]
        mean = [p for p in parts if not p.startswith('"')]
        ex = [p.strip('"') for p in parts if p.startswith('"')]
        out[off] = (POS[pos], words, '; '.join(mean), ex[0] if ex else '')
    return out

dic = defaultdict(lambda: {'w': []})
for fname in FILES:
    ss = synsets(fname)
    for line in open(os.path.join(WN, 'index.' + fname), encoding='utf-8', errors='replace'):
        if line.startswith('  '): continue
        f = line.split(); lemma = f[0].replace('_', ' ')
        n_ptr = int(f[3]); n_sense = int(f[2]); offs = f[6 + n_ptr:6 + n_ptr + n_sense]
        for off in offs[:MAX_SENSES]:
            pos, words, mean, ex = ss[off]
            same = [w for w in words if w.lower() != lemma][:4]
            dic[lemma]['w'].append([pos, mean, ex, same])

web = json.load(open(WEB))
for word, text in web.items():
    w = word.lower().strip()
    if not w or len(w) > 40: continue
    t = re.sub(r'\s+', ' ', text).strip()
    if len(t) > MAX_OLD:
        cut = t.rfind('. ', 0, MAX_OLD)
        t = t[:cut + 1 if cut > 200 else MAX_OLD].rstrip() + ' …'
    dic[w]['o'] = t

forms = defaultdict(list)
for name in ('noun', 'verb', 'adj', 'adv'):
    for line in open(os.path.join(EXC, name + '.exc')):
        f = line.split()
        if len(f) >= 2:
            for base in f[1:]:
                b = base.replace('_', ' ')
                if b not in forms[f[0].replace('_', ' ')]: forms[f[0].replace('_', ' ')].append(b)

os.makedirs(OUT, exist_ok=True)
shards = defaultdict(dict)
for w, e in dic.items():
    if not e['w']: del e['w']
    k = w[0] if 'a' <= w[0] <= 'z' else 'other'
    shards[k][w] = e
total = 0
for k, d in shards.items():
    data = gzip.compress(json.dumps(d, ensure_ascii=False, separators=(',', ':')).encode(), 9, mtime=0)
    open(os.path.join(OUT, k + '.json.gz'), 'wb').write(data); total += len(data)
data = gzip.compress(json.dumps(forms, ensure_ascii=False, separators=(',', ':')).encode(), 9, mtime=0)
open(os.path.join(OUT, 'forms.json.gz'), 'wb').write(data); total += len(data)
print(f'{len(dic)} words in {len(shards)} files, {len(forms)} irregular forms, {total / 1e6:.1f} MB')
