from datetime import datetime
import json
from fuzzywuzzy import process
from fuzzywuzzy.fuzz import QRatio
import random

db = {}

import platform
on_server = platform.system() != 'Windows'
db_file = '/home/stkwbot/db.json' if on_server else 'db.json'
queries_file = '/home/stkwbot/queries.log' if on_server else 'queries.log'
errors_file = '/home/stkwbot/errors.log' if on_server else 'errors.log'
usings_file = '/home/stkwbot/usings.csv' if on_server else 'usings.csv'


def json_dt_serial(obj):
    if isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M')
    raise TypeError ("Type %s not serializable" % type(obj))


def get_stickers_by_word(word:str, fuzzy=True, fuzz_cutoff=75, max_len_diff=3):
    res = []
    for k,v in db.items():
        if len(v['keywords']) == 0:
            continue
        if not fuzzy:
            if word in v['keywords']:
                res.append((k, v['send_times']))
        else:
            if word in v['keywords']:
                res.append((k, 100, v['send_times']))
            else:
                symbols = ['"', '^', '>', '\'', '3', '?', ':']
                no_symbols_keywords = [kws for kws in v['keywords'] if all([letter not in symbols for letter in kws])]
                no_symbols_keywords = [kw for kw in no_symbols_keywords if abs(len(kw) - len(word)) <= max_len_diff]
                if len(no_symbols_keywords) == 0:
                    continue
                ww = process.extractBests(word, no_symbols_keywords, limit=1, scorer=QRatio)[0]
                if ww[1] > fuzz_cutoff:
                    ww = (k, ww[1], v['send_times'])
                    res.append(ww)
    if fuzzy:
        res.sort(key=lambda x: x[1] * 10 + x[2] + random.random() / 2 , reverse=True)
    else:
        res.sort(key=lambda x: x[1] + random.random() / 2 , reverse=True)
    res = [r[0] for r in res]
    return res

def get_random_stickers(count:int = 12):
    return random.choices(list(db.keys()), k = count)

def db_save():
    with open(db_file, 'w+', encoding='utf-8') as f:
        json.dump(db, f, default=json_dt_serial, ensure_ascii=False, indent=1)

def db_load():
    global db
    with open(db_file, 'r+', encoding='utf-8') as f:
        db = json.load(f)
    for k,v in db.items():
        if v['last_using'] == "1-01-01 00:00":
            v['last_using'] = datetime.min
        else:
            v['last_using'] = datetime.strptime(v['last_using'], '%Y-%m-%d %H:%M')

def add_sticker(sticker_id:str, keywords:list, set_name:str):
    if sticker_id in db:
        return False
    db[sticker_id] = dict(keywords=keywords, last_using=datetime.min, send_times=0, pack=set_name)
    return True

def add_keywords(sticker_id:str, kw:list or str):
    if isinstance(kw, str):
        db[sticker_id]['keywords'].append(kw)
    elif isinstance(kw, list):
        db[sticker_id]['keywords'].extend(kw)

def delete_sticker(sticker_id:str):
    del db[sticker_id]

def delete_keyword(sticker_id:str, kw:str):
    db[sticker_id]['keywords'].remove(kw)

def use_sticker(sticker_id:str, who:int):
    with open(usings_file, 'a+') as f:
        f.write(f'{sticker_id},{who},{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
    db[sticker_id]['last_using'] = datetime.now()
    db[sticker_id]['send_times'] += 1

def get_sticker_info(sticker_id):
    return db[sticker_id]

def get_kw_stickers_list():
    res = dict()
    for k, v in db.items():
        for kw in v['keywords']:
            if kw not in res:
                res[kw] = [k]
            else:
                res[kw].append(k)
    ls = list(res.items())
    ls.sort(key=lambda x: len(x[1]), reverse=True)
    return ls

def get_kw_dict_count():
    return [(k,len(v)) for k,v in get_kw_stickers_list()]

def log_inline_query(user_id, query_text):
    with open(queries_file, 'a+', encoding='utf-8') as f:
        f.write(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {user_id}: {query_text}\n')

def log_errors(text):
    with open(errors_file, 'a+', encoding='utf-8') as f:
        f.write(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]\n{text}\n\n')

db_load()