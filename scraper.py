from curl_cffi import requests
import pytesseract
import bs4
import io
from PIL import Image
from loguru import logger
from common import Listing, Card
import datetime
from dbq import update_scrape_records
'''scraper for individual store listings on ligamagic.com.br'''


def filter_image(image: Image.Image) -> Image.Image:
    resized_im = image.resize(size=(image.width*15, image.height*15))
    data = resized_im.getdata()
    mod_data = []
    for d in data:
        if all([i > 215 for i in d]):
            mod_data.append((0, 0, 0))
        else:
            mod_data.append((255, 255, 255))
    resized_im.putdata(mod_data)
    filtered_im = resized_im.resize(size=(image.width*5, image.height*5))
    return filtered_im


def get_int_from(tsr_output: str) -> int:
    c_count = sum([1 for char in tsr_output if char.isdigit()])
    for char in tsr_output:
        if char.isdigit() and c_count == 1:
            return int(char)
    return None


def get_bg_pos(rule: str) -> tuple:
    return tuple(
        [abs(int(i.replace('px', ''))) for i in rule.split('background-position:')[1].split(';')[0].split(' ')]
    )


def get_card_search_soup(card_name: str) -> bs4.BeautifulSoup:
    res = requests.get(
        f'https://www.ligamagic.com.br/?view=cards/card&card={card_name}&aux={card_name}',
        impersonate='chrome'
    )
    return bs4.BeautifulSoup(res.text, 'lxml')


class Search:

    def __init__(self, card_name: str):
        self.scraped_at = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')
        self.card_name = card_name
        self.soup = get_card_search_soup(card_name)
        self.integer_correspondence = {}
        self.style = self.soup.select('style')[0]
        self.rules = self.get_css_rules()
        self.base_images = self.load_base_images()
        self.positions = self.get_positions()
        self.number_images = {}
        self.prices = []
        self.search_data = Card(card_name=card_name, prices=[], scraped_at=self.scraped_at)

    def get_image_from(style) -> Image.Image:
        url = 'https:'+style.text.split('background-image:url(')[1].split(')')[0]
        res = requests.get(url, impersonate='chrome')
        image = Image.open(io.BytesIO(res.content))
        return image

    def load_base_images(self):
        self.base_images = {}
        base_image_rules = [rule for rule in self.rules if 'background-image' in rule]
        for rule in base_image_rules:
            base_image_class = rule.split('{')[0].strip('.')
            self.base_images[base_image_class] = self.load_base_image(base_image_class, self.rules)
        return self.base_images

    def get_css_rules(self):
        rules = self.style.text.split('}')
        return {rule.split('{')[0].strip('.'): rule.split('{')[1] for rule in rules if rule}

    def load_base_image(self, base_image_class, rules) -> Image.Image:
        if base_image_class in self.base_images:
            return self.base_images[base_image_class]
        url = 'https:'+rules[base_image_class].split('url(')[1].split(')')[0]
        res = requests.get(url, impersonate='chrome')
        image = Image.open(io.BytesIO(res.content))
        self.base_images[base_image_class] = image
        return image

    def load_number_image(self, background_pos_class, base_image_class, rules) -> Image.Image:
        if '{base_image_class}_{background_pos_class}' in self.number_images:
            return self.number_images[f'{base_image_class}_{background_pos_class}']
        base_image = self.load_base_image(base_image_class, rules)
        pos = get_bg_pos(rules[background_pos_class])
        cropped_image: Image = base_image.crop((pos[0], pos[1], pos[0]+7, pos[1]+15))
        cropped_image = filter_image(cropped_image)
        self.number_images[f'{base_image_class}_{background_pos_class}'] = cropped_image
        return cropped_image

    def get_positions(self) -> dict:
        positions = {}
        for css_class, rule in self.rules.items():
            if not rule:
                continue
            if 'background-position' not in rule:
                continue
            positions[css_class] = get_bg_pos(rule)
        return positions

    def separate_div_classes_by_type(self, div_classes: list[str]) -> tuple:
        ''' div_classes is always a list of 3 elements, one of which is not relevant'''
        base_class = [d for d in div_classes if 'background-image' in self.rules[d]][0]
        pos_class = [d for d in div_classes if 'background-position' in self.rules[d]][0]
        return base_class, pos_class

    def get_integer(self, div_classes: list[str]) -> dict:
        base_class, pos_class = self.separate_div_classes_by_type(div_classes)
        if f"{base_class}-{pos_class}" in self.integer_correspondence:
            return self.integer_correspondence[f"{base_class}-{pos_class}"]
        pos = get_bg_pos(self.rules[pos_class])
        pos = (pos[0], pos[1])
        image = self.load_base_image(base_class, self.rules)
        cropped_image: Image = image.crop((pos[0], pos[1], pos[0]+8, pos[1]+15))
        cropped_image = filter_image(cropped_image)
        tesseract_output_string = pytesseract.image_to_string(
            image=cropped_image,
            config='--psm 10 tessedit_char_whitelist=0123456789'
            )
        integer = get_int_from(tesseract_output_string)
        if integer != 0 and not integer:
            logger.warning(f'assuming 8 for {base_class}-{pos_class}!')
            self.integer_correspondence[f"{base_class}-{pos_class}"] = str('8')
            return '8'
        self.integer_correspondence[f"{base_class}-{pos_class}"] = str(integer)
        return str(integer)

    def get_listings(self) -> list[Listing]:
        listings_tab = self.soup.select_one('#marketplace-stores')
        logger.debug(listings_tab)
        listings = listings_tab.select('div.store')
        logger.debug(listings)
        for listing in listings:
            price = self.get_listing(listing)
            if not price:
                continue
            self.prices.append(price)
        self.search_data = Card(card_name=self.card_name, prices=self.prices, scraped_at=self.scraped_at)
        update_scrape_records(self.search_data)
        return self.prices

    def get_listing(self, listing: bs4.Tag) -> Listing:
        try:
            card_name = self.card_name
            price = self.get_price(listing)
            if not price:
                return None
            amount = self.get_amount(listing)
            seller = self.get_seller_str(listing)
            condition = self.get_condition_str(listing)
            edition = self.get_edition(listing)
            foil = self.get_foil(listing)
            language = self.get_language(listing)
            scraped_at = self.scraped_at
            return Listing(
                card_name=card_name,
                price=price,
                amount=amount,
                seller=seller,
                condition=condition,
                scraped_at=scraped_at,
                edition=edition,
                foil=foil,
                language=language
            )
        except Exception:
            logger.exception(f'Error getting listing {listing}')
            return None

    def get_price(self, listing: bs4.Tag) -> float:
        price_tag = listing.select_one('div.price')
        if not price_tag:
            return
        if price_tag.text.strip() != "R$":
            return float(price_tag.text.split('R$')[-1].replace('.', '').replace(',', '.'))
        divs = price_tag.find_all('div')
        price_attrs = [d.attrs.get('class') for d in divs if 'class' in d.attrs and 'imgnum-monet' not in d.attrs.get('class')] # noqa
        price = ''
        for p in price_attrs:
            price += self.get_integer(p)
        try:
            return float(price)/100
        except ValueError:
            logger.exception(f'failed to parse price for {listing}')
            return 0.0

    def get_amount(self, listing: bs4.Tag) -> int:
        amount_tag = listing.select_one('div.quantity-with-image')
        divs = amount_tag.find_all('div')
        amount_divs = [d.attrs.get('class') for d in divs if 'class' in d.attrs and 'imgnum-unid' not in d.attrs.get('class')] # noqa
        amount = ''
        for a in amount_divs:
            amount += self.get_integer(a)
        try:
            return int(amount)
        except ValueError:
            logger.exception(f'failed to parse amount for {listing}')
            return 0

    def get_seller_str(self, listing: bs4.Tag) -> str:
        return listing.select_one('div.store-name').select_one('img').attrs['src']

    def get_condition_str(self, listing: bs4.Tag) -> str:
        return listing.select_one('div.quality').text

    def get_edition(self, listing: bs4.Tag) -> str:
        return listing.select_one('div.name-ed').text

    def get_foil(self, listing: bs4.Tag) -> bool:
        return listing.select_one('div.container-extras').select_one('div[title="Extra: Foil"]') is not None

    def get_language(self, listing: bs4.Tag) -> str:
        return listing.select_one('div.lang').select_one('img').attrs.get('title', '')

    def get_search_data(self) -> Card:
        if not self.prices:
            self.get_listings()
        return self.search_data


def debug_corr_count(integer_correspondence: dict):
    logger.debug(len(integer_correspondence))
    for num in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']:
        logger.debug(f"{num}: {sum([1 for v in integer_correspondence.values() if v == num])}")


def test():
    from pprint import pformat as pp
    import os
    import shutil
    import time
    start = time.time()
    if not os.path.exists('./imgs'):
        os.mkdir('./imgs')
    # s = Search('Guia Goblin')
    s = Search('Solitude')
    print(pp(s.get_listings()), file=open('guia_goblin.txt', 'w'))
    print(debug_corr_count(s.integer_correspondence))
    shutil.rmtree('./imgs')
    print(f'took {time.time()-start} seconds')


if __name__ == '__main__':
    test()
