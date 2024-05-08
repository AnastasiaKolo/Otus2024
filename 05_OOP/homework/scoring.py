""" Расчет скоринга """

import random

# pylint: disable=too-many-arguments
# pylint: disable=unused-argument
def get_score(store, phone, email, birthday=None, gender=None, first_name=None, last_name=None):
    """ Расчет скоринга в зависимости от заполненных полей """
    score = 0
    if phone:
        score += 1.5
    if email:
        score += 1.5
    if birthday and gender:
        score += 1.5
    if first_name and last_name:
        score += 0.5
    return score


def get_interests(store, cid):
    """ Получение списка интересов клиента """
    interests = ["cars", "pets", "travel", "hi-tech", "sport", "music", "books", "tv", "cinema",
                 "geek", "otus"]
    return random.sample(interests, 2)
