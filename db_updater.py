import json
from app.api.scraper import Search
from loguru import logger


def should_scrape_fastest(card: dict):
    condition_1 = card['prices']['usd'] and float(card['prices']['usd']) >= 5.0
    condition_2 = card['prices']['tix'] and float(card['prices']['tix']) >= 0.5
    return condition_1 and condition_2


def cards_to_scrape():
    scryfall_card_records = json.load(open('scryfall_card_records.json', encoding='utf-8'))
    legal_cards = [r for r in scryfall_card_records if is_legal_in_some_format(r)]
    fast_scrapes = [r for r in legal_cards if should_scrape_fastest(r)]
    slow_scrapes = [r for r in legal_cards if not should_scrape_fastest(r)]
    return fast_scrapes, slow_scrapes


def is_legal_in_some_format(card: dict):
    return any([c == 'legal' for c in card['legalities'].values()])


def make_scrape_queue(fast_scrapes, slow_scrapes):
    queue = []
    for index, card in enumerate(slow_scrapes):
        queue.append(fast_scrapes[index % len(fast_scrapes)])
        queue.append(card)
    return queue


def do_scrapes():
    while True:
        cards_to_scrape_fast, cards_to_scrape_slow = cards_to_scrape()
        scrape_queue = make_scrape_queue(cards_to_scrape_fast, cards_to_scrape_slow)
        for card in scrape_queue:
            try:
                logger.debug(f'Scraping {card["name"]}')
                if '//' in card['name']:
                    card['name'] = card['name'].split('//')[0].strip()
                s = Search(card['name'])
                s.get_listings()
            except Exception:
                import traceback
                logger.exception(f'Error scraping {card["name"]}')
                print(traceback.format_exc(), file=open('db_updater_errors.log', 'a'))


if __name__ == '__main__':
    do_scrapes()
