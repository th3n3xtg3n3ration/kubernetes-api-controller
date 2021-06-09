from django.db.models.signals import post_save
from django.dispatch import receiver
from cloud.models import *
import ipaddress
from cloud.tasks import update_ip_pool


@receiver(post_save, sender=Cluster)
def ip_pool_changed(sender, instance, created, **kwargs):
    print("@ip_pool_changed")
    update_ip_pool.apply_async(args=[instance.static_pool,instance.host], countdown=2)
