from dbq import get_db
from loguru import logger


def get_card_doc(card_name: str, end: str):
    db = get_db()
    card_docs = db.scrapes.find({'card_name': card_name, 'scraped_at': {'$lte': end}})
    if not card_docs:
        logger.warning('invalid query')
        return None
    doc = list(card_docs)[-1]
    return doc


def get_total_card_amount(card_name: str, end: str, filter: dict = None):
    doc = get_card_doc(card_name, end)
    if not filter:
        return sum([listing['amount'] for listing in doc['prices']])
    return sum([listing['amount'] for listing in doc['prices'] if all([listing[k] == v for k, v in filter.items()])])


def get_median_card_price(card_name: str, end: str, filter: dict = None):
    doc = get_card_doc(card_name, end)
    if not filter:
        return doc['prices'][len(doc['prices']) // 2]['price']
    return doc['prices'][len(doc['prices']) // 2]['price']


def get_average_card_price(card_name: str, end: str, filter: dict = None):
    doc = get_card_doc(card_name, end)
    if not filter:
        return sum([listing['price'] for listing in doc['prices']]) / len(doc['prices'])
    filtered_listings = [listing for listing in doc['prices'] if all([listing[k] == v for k, v in filter.items()])]
    return sum([listing['price'] for listing in filtered_listings]) / len(filtered_listings)


def get_lowest_card_price(card_name: str, end: str, filter: dict = None):
    doc = get_card_doc(card_name, end)
    if not filter:
        return doc['prices'][0]['price']
    filtered_listings = [listing for listing in doc['prices'] if all([listing[k] == v for k, v in filter.items()])]
    return filtered_listings[0]['price']


def get_highest_card_price(card_name: str, end: str, filter: dict = None):
    doc = get_card_doc(card_name, end)
    if not filter:
        return doc['prices'][-1]['price']
    filtered_listings = [listing for listing in doc['prices'] if all([listing[k] == v for k, v in filter.items()])]
    return filtered_listings[-1]['price']


def get_price_range(card_name: str, end: str, filter: dict = None):
    hp = get_highest_card_price(card_name, end, filter)
    lp = get_lowest_card_price(card_name, end, filter)
    return hp - lp


def get_diff(card_name: str, time1: str, time2: str):
    doc_1 = get_card_doc(card_name, time1)
    doc_2 = get_card_doc(card_name, time2)
    changed_listings = [listing for listing in doc_1['prices'] if listing not in doc_2['prices']]
    return changed_listings


def test():
    logger.debug('Card amount:')
    logger.debug(get_total_card_amount('Solitude', '2024-12-01 00:00:00', {'foil': False}))
    logger.debug('Median Price:')
    logger.debug(get_median_card_price('Solitude', '2024-12-01 00:00:00', {'foil': False}))
    logger.debug('Average Price:')
    logger.debug(get_average_card_price('Solitude', '2024-12-01 00:00:00', {'foil': False}))
    logger.debug('Lowest Price:')
    logger.debug(get_lowest_card_price('Solitude', '2024-12-01 00:00:00', {'foil': False}))
    logger.debug('Highest Price:')
    logger.debug(get_highest_card_price('Solitude', '2024-12-01 00:00:00', {'foil': False}))

if __name__ == '__main__':
    test()
