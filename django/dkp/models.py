# -*- coding: utf-8 -*-
import string
import logging


from django.db import models
from django.db.models import Sum, Count, Avg

from dkp.utils import raid_period, calculate_percent, cached_method, cached_property, QuerySetManager


DATE_FORMAT = '%d.%m.%y'
TIME_FORMAT = '%H:%M'

logger = logging.getLogger('dkp')


class Config(models.Model):
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name


class Pool(models.Model):
    name = models.CharField(max_length=100, unique=True)
    sort = models.IntegerField()

    def __unicode__(self):
        return self.name


class Tier(models.Model):
    name = models.CharField(max_length=100)
    pool = models.ForeignKey(Pool)
    sort = models.IntegerField()

    class Meta:
        """
        Samannimisiä tier vain eri pooleissa.
        Ei samaa järjestys numeroa pool sisällä monelle tier.
        """
        unique_together = (('pool', 'name'), ('pool', 'sort'),)

    def __unicode__(self):
        return u'{}: {}'.format(self.pool.name, self.name)

    @cached_method('Tier_{id}_sum_{period}')
    def sum(self, period=30):
        base = Raid.objects.filter(event__tier=self.id)
        if period > 0:
            base = base.filter(time__gte=raid_period(period))
        return base.aggregate(Sum('value'))['value__sum'] or 0

    @cached_method('Tier_{id}_count_{period}')
    def count(self, period=30):
        base = Raid.objects.filter(event__tier=self.id)
        if period > 0:
            base = base.filter(time__gte=raid_period(period))
        return base.count()


class Event(models.Model):
    name = models.CharField(max_length=100)
    tier = models.ForeignKey(Tier)
    attendance = models.BooleanField(default=True)

    class Meta:
        """
        Ei samannimisiä event tier sisällä
        """
        unique_together = ('tier', 'name')

    def __unicode__(self):
        return u'{}'.format(self.name)

    @models.permalink
    def get_absolute_url(self):
        return ('view_event', (), {'tier': self.tier.id, 'eventid': self.id})


class GameRace(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __unicode__(self):
        return self.name


class GameClass(models.Model):
    name = models.CharField(max_length=100, unique=True)
    css = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

    def save(self):
        self.css = string.lower(self.name).replace(' ', '')
        super(GameClass, self).save()


class Rank(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __unicode__(self):
        return self.name


class Member(models.Model):
    name = models.CharField(max_length=100, unique=True)
    note = models.TextField(blank=True)
    game_race = models.ForeignKey(GameRace)
    game_class = models.ForeignKey(GameClass)
    rank = models.ForeignKey(Rank)

    def __unicode__(self):
        return self.name


class MemberDKP(models.Model):
    """
    XXX: pre_delete: poista attendancet, itemit, adjustmentit.
    virhe jos näiten poistamisen jälkeen valuet != 0?
    """
    member = models.ForeignKey(Member)
    tier = models.ForeignKey(Tier)

    def clean_tier(self):
        """
        MemberDKP tieriä ei voida muuttaa. Hajoittaisin raid attendancet yms.
        """
        return self.instance.tier

    class Meta:
        """
        Memberillä korkeintaan yksi MemberDKP per tier
        """
        unique_together = ('member', 'tier')

    # Päivittyvät automaattisesti
    value_earned = models.IntegerField(default=0)
    value_spent = models.IntegerField(default=0)
    value_adjustment = models.IntegerField(default=0)
    value_lastraid = models.DateTimeField(null=True, auto_now_add=False)

    objects = QuerySetManager()

    class QuerySet(models.query.QuerySet):
        def active_members(self):
            return self.exclude(member__rank__name='Out')

        def tier(self, tier):
            return self.filter(tier=tier)

        def game_class(self, var):
            return self.filter(member__game_class=var)

        def standings(self):

            self = self.extra(
                select={'sum30': """
                SELECT COALESCE(SUM(dkp_raid.value), 0) AS sum30
                FROM dkp_raid, dkp_raid_attendees
                WHERE dkp_raid.id = dkp_raid_attendees.raid_id
                  AND dkp_raid_attendees.memberdkp_id = dkp_memberdkp.id
                  AND dkp_raid.time >= %s"""},
                select_params=(raid_period(30).isoformat(), ))

            return self

        def update_dkp(self, tier=-1):
            if tier >= 0:
                self = self.filter(tier=tier)

            for memberdkp in self:
                memberdkp.update_earned()
                memberdkp.update_spent()
                memberdkp.update_adjustment()
                memberdkp.update_lastraid()

    def __unicode__(self):
        return u'{}'.format(self.name)

    @models.permalink
    def get_absolute_url(self):
        return ('view_member', (), {'tier': self.tier.id, 'memberid': self.member.id})

    @property
    def name(self):
        """Admin näkymää varten"""
        return self.member.name

    @property
    def calculate_earned(self):
        return self.raid_set.aggregate(Sum('value'))['value__sum'] or 0

    def update_earned(self):
        self.value_earned = self.calculate_earned
        self.save()

    def correct_earned(self):
        return self.value_earned == self.calculate_earned

    @property
    def calculate_spent(self):
        return self.loot_set.aggregate(Sum('value'))['value__sum'] or 0

    def update_spent(self):
        self.value_spent = self.calculate_spent
        self.save()

    def correct_spent(self):
        return self.value_spent == self.calculate_spent

    @property
    def calculate_adjustment(self):
        return self.adjustment_set.aggregate(Sum('value'))['value__sum'] or 0

    def update_adjustment(self):
        self.value_adjustment = self.calculate_adjustment
        self.save()

    @property
    def correct_adjustment(self):
        return self.value_adjustment == self.calculate_adjustment

    def update_lastraid(self):
        try:
            self.value_lastraid = self.raid_set.latest('time').time
        except:
            self.value_lastraid = None
        self.save()

    @property
    def current(self):
        return self.value_earned - self.value_spent + self.value_adjustment

    @cached_method('MemberDKP_{id}_sum_{period}')
    def sum(self, period=-1):
        r = self.raid_set
        if period > 0:
            r = r.filter(time__gte=raid_period(period))
        return r.aggregate(Sum('value'))['value__sum'] or 0

    @cached_method('MemberDKP_{id}_count_{period}')
    def count(self, period=-1):
        r = self.raid_set
        if period > 0:
            r = r.filter(time__gte=raid_period(period))
        return r.count()

    def sumPercent(self, period=-1):
        return calculate_percent(self.sum(period=period), self.tier.sum(period=period))

    def countPercent(self, period=-1):
        return calculate_percent(self.count(period=period), self.tier.count(period=period))

    @cached_property
    def percent30(self):
        try:
            # Standingsejä näytettäessä hyödynnetään arvoa subquerystä
            return calculate_percent(self.sum30, self.tier.sum(period=30))
        except:
            # Muuten joka memberdkplle suoritetaan uusi query
            return self.sumPercent(period=30)

    @property
    def good_activity(self):
        return self.percent30 >= 0.6

    @property
    def multiplier(self):
        return self.percent30 if self.good_activity else 0

    @property
    def activity(self):
        return int(100 * self.percent30)

    @property
    def usable(self):
        return int(self.multiplier * self.current)


class Raid(models.Model):
    event = models.ForeignKey(Event)
    time = models.DateTimeField()
    date = models.DateField()
    note = models.TextField(blank=True)
    value = models.IntegerField()
    attendees = models.ManyToManyField(MemberDKP)

    objects = QuerySetManager()

    class QuerySet(models.query.QuerySet):
        def with_attendees_counts(self):
            return self.annotate(attendees_count_a=Count('attendees'))

        @property
        def average_value(self):
            return int(self.aggregate(Avg('value'))['value__avg']) or 0

        @property
        def average_attendees(self):
            return int(self.aggregate(Avg('attendees_count_a'))['attendees_count_a__avg']) or 0

    def __unicode__(self):
        return u'{}: {}'.format(self.event.name, self.time.strftime(DATE_FORMAT + ' ' + TIME_FORMAT))

    @models.permalink
    def get_absolute_url(self):
        return ('view_raid', (), {'tier': self.event.tier.id, 'raidid': self.id})

    def tier(self):
        return self.event.tier.name

    def name(self):
        return self.event.name

    def save(self, **kwargs):
        self.date = self.time
        super(Raid, self).save(**kwargs)

    @property
    def attendees_count(self):
        try:
            return self.attendees_count_a
        except:
            return MemberDKP.objects.filter(raid=self.id).count()


QUALITY_CHOICES = ((0, 'Poor'), (1, 'Common'), (2, 'Uncommon'), (3, 'Rare'), (4, 'Epic'), (5, 'Legendary'), (6, 'Artifact'), (7, 'Heirloom'),)
SOURCE_CHOICES = ((0, 'Normal'), (1, 'Heroic'), (2, 'Raidfinder'),)


class Item(models.Model):
    """
    Pk toimii samalla itemid.
    """
    name = models.CharField(max_length=100)
    quality = models.SmallIntegerField(default=0, choices=QUALITY_CHOICES)
    icon = models.CharField(max_length=100, null=True)
    source = models.SmallIntegerField(default=0, choices=SOURCE_CHOICES)

    objects = QuerySetManager()

    class QuerySet(models.query.QuerySet):
        def with_drop_counts(self):
            return self.annotate(drop_count=Count('loot'))

        def with_average_loot_values(self):
            return self.annotate(avg_value=Avg('loot__value'))

        @property
        def average_value(self):
            """
            Laskee itemien average valuen keskiarvon.
            Eli vaatii with_average_loot_value käyttöä
            """
            return int(self.aggregate(Avg('avg_value'))['avg_value__avg']) or 0

    def __unicode__(self):
        return u'{}'.format(self.name)


LOOT_CHOICES = ((0, 'Looted'), (1, 'Disenchanted'))


class Loot(models.Model):
    raid = models.ForeignKey(Raid)
    memberdkp = models.ForeignKey(MemberDKP, null=True, blank=True)
    status = models.SmallIntegerField(default=0, choices=LOOT_CHOICES)
    item = models.ForeignKey(Item)
    value = models.IntegerField()

    objects = QuerySetManager()

    class QuerySet(models.query.QuerySet):
        @property
        def average_value(self):
            return int(self.aggregate(Avg('value'))['value__avg']) or 0

    def __unicode__(self):
        return u'{}'.format(self.item.name)

    @models.permalink
    def get_absolute_url(self):
        return ('view_item', (), {'tier': self.raid.event.tier.id, 'itemid': self.item.id})

    @property
    def name(self):
        return self.item.name


class Adjustment(models.Model):
    name = models.CharField(max_length=200)
    memberdkp = models.ForeignKey(MemberDKP)
    time = models.DateTimeField()
    value = models.IntegerField()

    def __unicode__(self):
        return self.name
