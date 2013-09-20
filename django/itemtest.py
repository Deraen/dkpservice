#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'testproject.settings'

from django.utils.timezone import get_default_timezone
from django.db import connections

from dkp.models import *
from dkp.items import itemid_from_name, iteminfo_from_id, item_search

# logger = logging.getLogger(__name__)

# print('Luodaan item pelkällä itemid')

# - Hakea nimi itemid perusteella
# testi1 = Item(pk=49481)
# testi1.save()

# print('Lisätään loot itemid:llä')

# - Onko Itemiä tuolla id:llä
# - Jos ei, luodaan ja etsitään nimi
# testi3 = Loot(item=16914, tier=Tier.objects.get(id=1), raid=Raid.objects.get(id=2191), memberdkp=MemberDKP.objects.get(tier=1, member=1), value=5)
# testi3.save()

# print itemid_from_name('Netherwind Crown')

# print iteminfo_from_id(49481)
# print iteminfo_from_id(78671)

# print itemid_search('Netherwind Crown')

print(item_search('Time Lord\'s'))

print(item_search('Leggings of the Forlorn Protector'))
