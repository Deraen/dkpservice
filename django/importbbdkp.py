#!/usr/bin/env python
# -*- coding: utf-8 -*-

from urllib.error import URLError
from datetime import datetime
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'testproject.settings'
import logging

from django.utils.timezone import get_default_timezone
from django.db import connections

from dkp.models import *
from dkp.items import iteminfo_from_id, item_search, SearchError

logger = logging.getLogger('dkp')

print('Clearing db')
Loot.objects.all().delete()
# Item.objects.all().delete()
Adjustment.objects.all().delete()
Raid.objects.all().delete()
Event.objects.all().delete()
MemberDKP.objects.all().delete()
Member.objects.all().delete()
Rank.objects.all().delete()


def dictfetchall(cursor):
    for row in cursor.fetchall():
        yield dict(zip([col[0] for col in cursor.description], row))

cursor = connections['old'].cursor()
prefix = 'bbeqdkp_'

print('\nEvents')

tiers = {
    13: Tier.objects.get(pk=1),
    11: Tier.objects.get(pk=2),
    6: Tier.objects.get(pk=3),
    14: Tier.objects.get(pk=4),
    12: Tier.objects.get(pk=5),
    10: Tier.objects.get(pk=6),
    9: Tier.objects.get(pk=7),
    15: Tier.objects.get(pk=8),
    18: Tier.objects.get(pk=9),
    19: Tier.objects.get(pk=10)
}

events = {}
cursor.execute('SELECT * FROM {}events'.format(prefix))
for event in dictfetchall(cursor):
    tier = tiers[event['event_dkpid']] if event['event_dkpid'] in tiers else None
    events[(tier, event['event_name'])] = Event.objects.create(name=event['event_name'], tier=tier)

print('\nRanks')
ranks = {}

cursor.execute('SELECT * FROM {}member_ranks'.format(prefix))
for rank in dictfetchall(cursor):
    ranks[rank['rank_id']] = Rank.objects.create(name=rank['rank_name'])

print('\nMembers')
members = {}
members_name = {}

fail = total = 0
cursor.execute('SELECT * FROM {}memberlist'.format(prefix))
for member in dictfetchall(cursor):
    total += 1
    new = Member.objects.create(
        name=member['member_name'],
        game_class=GameClass.objects.get(id=member['member_class_id']),
        game_race=GameRace.objects.get(id=member['member_race_id']),
        rank=ranks[member['member_rank_id']])
    members[member['member_id']] = new
    members_name[member['member_name']] = new

print('Failed: {}/{}\n'.format(fail, total))

print('MemberDKP')

# Memberdkp - tier-event relaation
memberdkps = {}
fail = total = 0
cursor.execute('SELECT * FROM {}memberdkp'.format(prefix))
for memberdkp in dictfetchall(cursor):
    total += 1
    try:
        tier = tiers[memberdkp['member_dkpid']]
        member = members[memberdkp['member_id']]
        memberdkps[(tier.id, member.id)] = MemberDKP.objects.create(tier=tier, member=member)
    except KeyError:
        fail += 1

print('Failed: {}/{}\n'.format(fail, total))

print('Raids')
raids = {}
raidstier = {}

fail = total = 0
cursor.execute('SELECT * FROM {}raids'.format(prefix))
for raid in dictfetchall(cursor):
    total += 1
    try:
        tier = tiers[raid['raid_dkpid']]
        event = events[(tier, raid['raid_name'])]
        new = Raid.objects.create(
            event=event,
            note=raid['raid_note'],
            value=raid['raid_value'],
            time=datetime.fromtimestamp(raid['raid_date'], get_default_timezone()))
        raids[raid['raid_id']] = new
        raidstier[raid['raid_id']] = tier
    except KeyError:
        fail += 1

print('Failed: {}/{}\n'.format(fail, total))

print('Adjustments')
fail = total = 0
cursor.execute('SELECT * FROM {}adjustments'.format(prefix))
for adjustment in dictfetchall(cursor):
    total += 1
    try:
        tier = tiers[adjustment['adjustment_dkpid']]
        Adjustment.objects.create(
            name=adjustment['adjustment_reason'],
            memberdkp=memberdkps[(tier.id, members[adjustment['member_id']].id)],
            time=datetime.fromtimestamp(adjustment['adjustment_date'], get_default_timezone()),
            value=adjustment['adjustment_value'])
    except KeyError:
        fail += 1

print('Failed: {}/{}\n'.format(fail, total))

print('Items')

unknown, _ = Item.objects.get_or_create(pk=0, name='Tuntematon item')

itemfixes = {
    'Book Of Binding Will': 'Book of Binding Will',
    'Stormwake, the Tempest Reach': 'Stormwake, the Tempest\'s Reach',
    'wind stalker leggings': 'Wind Stalker Leggings',
    'Shoulder of the Forlorn Vanquisher': 'Shoulders of the Forlorn Vanquisher',
    'Helm of Forlorn Protector': 'Helm of the Forlorn Protector',
    'Legging of the Forlorn Conqueror': 'Leggings of the Forlorn Conqueror',
    'Greathelm of the Veracious Maw': 'Greathelm of the Voracious Maw',
    'Treads of The Penitent Man': 'Treads of the Penitent Man',
    'Sulfuras, The Extinguished Hand': 'Sulfuras, the Extinguished Hand',
    'shard of torment': 'Shard of Torment',
    'The hungerer': 'The Hungerer',
    'Finger of Incineration': 'Fingers of Incineration',
    'Flickerin Cowl': 'Flickering Cowl',
    'Breastplate of the incendiary soul': 'Breastplate of the Incendiary Soul',
    'crystallized firestone': 'Crystallized Firestone',
    'Bell of Enreging Resonance': 'Bell of Enraging Resonance',
    'Mantle of Roaming Flames': 'Mantle of Roaring Flames',
    'Iso Miekka!': 'Reclaimed Ashkandi, Greatsword of the Brotherhood',
    'Chimaron Armguards': 'Chimaeron Armguards',
    'Molten Tantrum boots': 'Molten Tantrum Boots',
    'Floworm Choker': 'Flowform Choker',
    '78170': 'Shoulders of the Corrupted Vanquisher',
    '94795': 'Spinescale Seal',
    '86135': 'Starcrusher Gauntlets',
}

randomitems = [
    'Permafrost Signet',
    'Gale Rouser Belt',
    'Planetary Band',
    'Thunder Wall Belt',
    'Mistral Circle',
    'Star Chaser Belt',
    'Flickering Handguards',
    'Flickering Cowl',
    'Flickering Shoulderpads',
    'Flickering Wristbands',
    'Flickerin Cowl',
    'Flickering Shoulders',
    'Tempest Keeper Belt',
    'Planetary Drape',
]

# 0 normal, 1 heroic, 2 raidfinder
itemsources = {
    'Nightmare Rider\'s Boots': 1,
    'Belt of the Fallen Brood': 1,
    'Crown of the Twilight Queen': 1,
    'Bracers of the Mat\'redor': 1,
    'Twilight Scale Leggings': 1,
    'Bindings of Bleak Betrayal': 1,
    'Bracers of the Dark Mother': 1,
    'Living Ember': 0,
    'Leggings of the Fiery Protector': 1,
    'Leggings of the Fiery Vanquisher': 1,
    'Leggings of the Fiery Conqueror': 1,
    'Caelestrasz\'s Will': 1,
    'Shard of Woe': 1,
    'Chest of the Fiery Conqueror': 1,
    'Chest of the Fiery Protector': 1,
    'Gauntlets of the Fiery Conqueror': 1,
    'Shoulders of the Fiery Protector': 1,
    'Helm of the Fiery Vanquisher': 0,
    'Crown of the Fiery Vanquisher': 1,
    'Chest of the Fiery Vanquisher': 1,
    'Gauntlets of the Fiery Vanquisher': 1,
    'Shoulders of the Fiery Conqueror': 1,
    'Gauntlets of the Fiery Protector': 1,
    'Smoldering Egg of Millagazor': 0,
    'Shoulders of the Fiery Vanquisher': 1,
    'Crown of the Fiery Conqueror': 1,
    'War-Torn Crushers': 1,
    'Dragonwrath, Tarecgosa\'s Rest': 0,
    'Crown of the Fiery Protector': 1,
    'Helm of the Fiery Conqueror': 0,
    'Spine of the Thousand Cuts': 0,
    'Essence of Destruction': 0,
    'Life-Binder\'s Handmaiden': 0,
    'Ruinblaster Shotgun': 0,
    'Nightblind Cinch': 0,
    'Reins of the Blazing Drake': 0,
    'Golad, Twilight of Aspects': 0,
    'Tiriosh, Nightmare of Ages': 0,
}


fail = total = 0
cursor.execute('SELECT * FROM {}items'.format(prefix))
for item in dictfetchall(cursor):
    buyers = item['item_buyer'].split(',')  # Voi olla useampi ostaja tuol
    tier = tiers[item['item_dkpid']]

    for buyer in buyers:
        total += 1
        name = buyer.replace(' ', '')
        try:
            disenchanted = False
            deleted = False
            if name == 'disenchanted':
                disenchanted = True
            else:
                member_name = members_name[name]
                memberdkp = memberdkps[(tier.id, members_name[name].id)]
            raid = raids[item['raid_id']]

            heroic = raid.name().endswith('(H)')

            # 0: Jos ei id ja ei nimieä niin ei voida tehdä mitään
            # 1: Jos id määritelty: -haetaan item tietokannasta
            #                       -jos item ei tietokannassa, haetaan tuon id item wowheadista tietokantaan
            # 2: Jos nimi määritelty: -haetaan tietokannasta nimellä + heroic
            #                         -haetaan wowheadistä nimen perusteella kaikki tietokantaan ja valitaan nimellä + heroic

            item_ = unknown

            for random_prefix in randomitems:
                if item['item_name'].startswith(random_prefix):
                    item['item_name'] = random_prefix

            if item['item_name'] in itemfixes:
                item['item_name'] = itemfixes[item['item_name']]

            if item['item_name'] in itemsources:
                heroic = itemsources[item['item_name']] == 1

            if item['item_gameid']:
                try:
                    item_ = Item.objects.get(pk=item['item_gameid'])
                except Item.DoesNotExist:
                    logger.info('Itemiä {} ei ollut tietokannassa'.format(item['item_gameid']))

                    try:
                        info = iteminfo_from_id(item['item_gameid'])
                    except SearchError as e:
                        logger.error(e)
                        logger.error('Id:lle {} ei löytynyt tietoja, lisätään tuntemattomana.'.format(item['item_gameid']))
                        info = {
                            'name': 'Tuntematon item ID:llä',
                            'quality': 0,
                            'icon': 'inv_misc_food_54',
                            'source': 0,
                        }

                    info['id'] = item['item_gameid']
                    item_ = Item.objects.create(**info)

            elif item['item_name']:
                try:
                    item_ = Item.objects.filter(name=item['item_name'], source=1 if heroic else 0)[0]
                except IndexError:
                    logger.info('Itemiä {}-{} ei ollut tietokannassa'.format(item['item_name'], 'heroic' if heroic else 'normal'))

                    try:
                        for found in item_search(item['item_name']):
                            logger.info('Tallennetaan item {}-{}'.format(found['name'], SOURCE_CHOICES[found['source']]))
                            new = Item(**found)
                            new.save()
                    except SearchError as e:
                        logger.error('Virhe hakiessa item {} : {}'.format(item['item_name'], e))
                    else:
                        try:
                            item_ = Item.objects.filter(name=item['item_name'], source=1 if heroic else 0)[0]
                        except IndexError:
                            try:
                                item_ = Item.objects.filter(name=item['item_name'])[0]
                            except IndexError:
                                logger.error('Itemiä {} ei löytynyt tietokannasta, edes wowhead haun jälkeen.'.format(item['item_name']))

            # Tarkistetaan vielä onko item järkevästä lähteestä - Heroic event -> Heroic item
            # if heroic != (item_.source == 1):
            #     logger.info('Itemin {} lähde: {}, raid {}'.format(item_.name, item_.source, raid.event.name))

            if disenchanted:
                Loot.objects.create(
                    raid=raid,
                    status=1,
                    item=item_,
                    value=0)
            else:
                Loot.objects.create(
                    raid=raid,
                    memberdkp=memberdkp,
                    item=item_,
                    value=item['item_value'])
        except KeyError:
            fail += 1

print('Failed: {}/{}\n'.format(fail, total))

print('Attendance')
fail_member = total_member = fail_raid = total_raid = 0
cursor.execute('SELECT * FROM {}raid_attendees ORDER BY raid_id'.format(prefix))

raid_id = -1
to_add = []
raid = None
tier = -1

for attendance in dictfetchall(cursor):
    if attendance['raid_id'] != raid_id:
        if raid:
            raid.attendees.add(*to_add)

        raid_id = attendance['raid_id']
        try:
            tier = raidstier[attendance['raid_id']]
            raid = raids[raid_id]
        except KeyError:
            fail_raid += 1
            raid = None

        to_add = []
        total_raid += 1

    try:
        to_add.append(memberdkps[(tier.id, members[attendance['member_id']].id)])
    except KeyError:
        fail_member += 1

    total_member += 1

# Vika raid
if raid:
    raid.attendees.add(*to_add)
    total_raid += 1

print('Failed: {}/{}. Missing raid: {}/{}\n'.format(fail_member, total_member, fail_raid, total_raid))

# fail = total = 0
# cursor.execute('SELECT * FROM {}raid_attendees ORDER BY raid_id'.format(prefix))
# for attendance in dictfetchall(cursor):
#     total += 1
#     try:
#         raid = raids[attendance['raid_id']]
#         tier = raidstier[attendance['raid_id']]
#         memberdkp = memberdkps[(tier.id, members[attendance['member_id']].id)]
#         raid.attendees.add(memberdkp)
#     except KeyError:
#         fail += 1

# print('Failed: {}/{}\n'.format(fail, total))

MemberDKP.objects.update_dkp()
