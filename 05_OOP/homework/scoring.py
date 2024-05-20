""" Расчет скоринга """

import hashlib
import json

from store import KVStore


# pylint: disable=too-many-arguments
def get_score(store: KVStore, phone, email,
              birthday=None, gender=None, first_name=None, last_name=None):
    """ Пытаемся получить скоринг из кеша,
    если там нет, то расчет скоринга
    в зависимости от заполненных полей """
    key_parts = [
        first_name or "",
        last_name or "",
        phone or "",
        birthday.strftime("%Y%m%d") if birthday is not None else "",
    ]
    key = "uid:" + hashlib.md5("".join(key_parts).encode()).hexdigest()
    # try get from cache,
    # fallback to heavy calculation in case of cache miss
    score = store.cache_get(key) or 0
    if score:
        return score
    if phone:
        score += 1.5
    if email:
        score += 1.5
    if birthday and gender:
        score += 1.5
    if first_name and last_name:
        score += 0.5
    # cache for 60 minutes
    store.cache_set(key, score, 60 * 60)
    return score


def get_interests(store: KVStore, cid):
    """ Получение списка интересов клиента """
    # interests = ["cars", "pets", "travel", "hi-tech", "sport", "music", "books", "tv", "cinema",
    #              "geek", "otus"]
    # return random.sample(interests, 2)
    r = store.get(f"i:{cid}")
    return r if r else []
