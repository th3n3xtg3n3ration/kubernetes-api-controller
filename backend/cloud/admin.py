from django.contrib import admin
from cloud.models import *
# admin.site.register(Subscription)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('customer', 'subscription', 'start_date', 'end_date', 'idstr',
                    'server_name_prefix', 'package', 'service_type')
    search_fields = ('customer', 'server_name_prefix', 'idstr', 'subscription')
    list_filter = ('package',)


@admin.register(ServerType)
class ServerTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    def get_customer(self, obj):
        return obj.subscription.customer
    get_customer.short_description = "Customer"

    def subscription(self, obj):
        """
        docstring
        """
        return obj.subscription.subscription

    list_display = ('action', 'server_type', 'subscription',
                    'get_customer', 'status', 'idstr', 'operation')
    search_fields = ('idstr', 'subscription__customer',
                     'subscription__subscription')


@admin.register(IpgServer)
class IpgServerAdmin(admin.ModelAdmin):
    list_display = ('cpu', 'ram', 'disc', 'widea_address', 'server_id',
                    'local_ip', 'internal_ip', 'external_ip', 'server_name', 'server', 'state', 'fqdn')


@admin.register(WebcmServer)
class WebcmServerAdmin(admin.ModelAdmin):
    list_display = ('address', 'local_ip', 'internal_ip', 'server_id',
                    'server_name', 'server', 'state', 'fqdn')


@admin.register(Cluster)
class ClusterAdmin(admin.ModelAdmin):
    def token_part(self, obj):
        """
        docstring
        """
        return f"{obj.token[:100]}......more"

    list_display = ('host', 'token_part', 'static_pool', 'active')


@admin.register(UsedIp)
class UsedIpAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'ip_address', 'used')
