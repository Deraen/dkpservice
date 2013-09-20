from django.conf.urls import patterns, include, url
from tastypie.api import Api
from dkp.resources import RaidResource, MemberResource, MemberDKPResource, EventResource, PoolResource

v1_api = Api(api_name='v1')
v1_api.register(RaidResource())
v1_api.register(MemberResource())
v1_api.register(MemberDKPResource())
v1_api.register(EventResource())
v1_api.register(PoolResource())

urlpatterns = patterns('',
        (r'^api/', include(v1_api.urls)),
)

