from tastypie.resources import ModelResource
from dkp.models import Raid, Member, MemberDKP, Event, Pool


class RaidResource(ModelResource):
    class Meta:
        queryset = Raid.objects.all()
        allowed_methods = ['get']


class MemberResource(ModelResource):
    class Meta:
        queryset = Member.objects.all()
        allowed_methods = ['get']

class MemberDKPResource(ModelResource):
    class Meta:
        queryset = MemberDKP.objects.all()
        allowed_methods = ['get']

class EventResource(ModelResource):
    class Meta:
        queryset = Event.objects.all()
        allowed_methods = ['get']

class PoolResource(ModelResource):
    class Meta:
        queryset = Pool.objects.all()
        allowed_methods = ['get']

