from scraper import Search
import os
import shutil
from loguru import logger


if __name__ == '__main__':
    if not os.path.exists('./imgs'):
        os.mkdir('./imgs')
    card_name = input('type card name to search\n')
    s = Search(card_name)
    listings = s.get_listings()
    logger.debug(f'got {listings}')
    input('press any key to exit...\n')
    shutil.rmtree('./imgs')
