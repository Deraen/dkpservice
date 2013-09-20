# -*- coding: utf-8 -*-
from urllib.request import urlopen
from urllib.parse import urlencode
from xml.etree import ElementTree
import json
import re
import logging

from django.core.cache import cache
from dkp.models import *
from dkp.utils import cache_set

#from battlenet import Connection, APIError, EUROPE

logger = logging.getLogger('dkp')


class SearchError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def itemid_from_name(name):
    """
    Haetaan nimen perusteella ekana tietokannasta.
    Sitten wowheadista (battlenet api ei tarjoa tähän hakua).
    Cachetetaan wowhead haut.
    """
    try:
        return Item.objects.get(name=name).id
    except:
        key = 'Itemid_{}'.format(hash(name))
        val = cache.get(key)
        if val is None:
            url = "http://www.wowhead.com/" + urlencode({'item': name}) + "&xml"
            try:
                doc = urlopen(url)
            except URLError:
                raise SearchError('Virhe ladattessa url {}'.format(url))
            else:
                xml = ElementTree.parse(doc)

                # XXX: Jotain poikkeuksia tms varmaan voi tapahtua?
                # try:
                return cache_set(key, int(xml.getroot().find('item').get('id')))
                # except:
                #     print url
                #     raise SearchError('Virhe käsitellessä XML item {}'.format(name))

        return val


def iteminfo_from_id(id):
    """
    Haetaan id perusteella wowhaedistä
    """
    url = "http://www.wowhead.com/" + urlencode({'item': id}) + "&xml"
    try:
        doc = urlopen(url)
    except URLError:
        raise SearchError('Virhe ladattessa url {}'.format(url))

    xml = ElementTree.parse(doc)

    itemElement = xml.find('item')
    if itemElement is None:
        if xml.find('error') is not None:
            print(url)
            raise SearchError('Wowhead error: {}'.format(xml.find('error').text))
        else:
            raise SearchError('Virhe parsiessa XML')

    name = itemElement.find('name').text
    quality = itemElement.find('quality').get('id')
    icon = itemElement.find('icon').text
    json_data = json.loads('{%s}' % itemElement.find('json').text)
    source = 0  # Normal
    if 'heroic' in json_data:
        source = 1  # Heroic
    elif 'raidfinder' in json_data:
        source = 2  # Raidfinder

    return {
        'name': name,
        'quality': quality,
        'icon': icon,
        'source': source,
    }

    # Battlenet versio. Sieltä ei saa tietoon onko heroic tms.
    # try:
    #     item = connection.get_item(EUROPE, id)
    # except APIError as e:
    #     logger.error(e)
    #     raise ItemDoesNotExist

    # logger.info('API kertoi id:lle {} nimeksi {}'.format(id, item['name']))
    # print item
    # print 'Heroic' if 'heroic' in item else 'Ei oo heroic'
    # return {
    #     'name': item['name'],
    #     'quality': item['quality'],
    #     'heroic': False,
    #     'icon': item['icon'],
    # }


def item_search(name):
    """
    Haetaan nimen perusteella itemien tiedot wowhaedistä.
    Koska hakusivulta vaikea parsia osaa tiedoista, haetaan id perusteella xml,
    käyttäen aikaisempaa iteminfo_from_id-funktiota.
    """
    url = 'http://www.wowhead.com/search?' + urlencode({'q': name})
    try:
        doc = urlopen(url)
    except:
        raise SearchError('Virhe ladattessa url {}'.format(url))

    doc = doc.read().decode('utf8')
    page_re = re.compile("PageTemplate.set\({pageName: '(\w*)', activeTab: \d}\)")
    page_search = page_re.search(doc)
    if page_search:
        page = page_search.group(1)
    else:
        raise SearchError("Error parsing search results.")

    if page == "search":
        json_re = re.compile("new Listview\({template: 'item', id: '\w*',.*data: (\[.*\])")
        match = json_re.search(doc)

        if match:
            data = match.group(1)
            data = data.replace(',frombeta:\'1\'', ',\"frombeta\":1')

            try:
                data_dict = json.loads(data)
            except ValueError as e:
                print('Etsitty nimellä', name)
                print(data)
                raise SearchError('Error parsing search results: {}'.format(e))
            else:
                r = []
                for item in data_dict:
                    try:
                        info = iteminfo_from_id(item['id'])
                    except SearchError as e:
                        logger.error(e)
                    else:
                        info['id'] = item['id']
                        r.append(info)

                return r
        else:
            raise SearchError("No items found.")

        raise SearchError("FUU1")

    elif page == "item":
        id = itemid_from_name(name)
        info = iteminfo_from_id(id)
        info['id'] = id
        return [info]

    raise SearchError("Search returned strange page? {}".format(page))
