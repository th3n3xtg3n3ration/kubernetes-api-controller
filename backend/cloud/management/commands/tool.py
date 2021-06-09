from django.core.management.base import BaseCommand, CommandError
from cloud.models import *
import ipaddress
from uuid import uuid4
import itertools


class Command(BaseCommand):
    help = 'Fix some'

    def add_arguments(self, parser):
        parser.add_argument("--clear-all", action='store_true')
        parser.add_argument("--gen-idstr")
        parser.add_argument("--gen-pool")
        parser.add_argument("--clear-pool", action='store_true')

    def handle(self, *args, **options):
        if options.get("clear_pool"):
            UsedIp.objects.all().delete()
            print("IP Pools deleted!")
        if options.get("gen_pool"):
            static_pool = options.get("gen_pool")
            for ip in ipaddress.ip_network(static_pool):
                ip_str = str(ip)
                if ip_str.endswith(".1"):
                    continue

                UsedIp.objects.get_or_create(
                    ip_address=ip_str, defaults={"used": False})

        if options.get('clear_all'):
            print("Deleting subscriptions and servers.")
            IpgServer.objects.all().delete()
            WebcmServer.objects.all().delete()
            Subscription.objects.all().delete()
        if options.get('gen_idstr'):
            if options.get('gen_idstr').lower() == 'sub':
                for s in Subscription.objects.all():
                    s.idstr = uuid4().hex[:10]
                    s.save()
            else:
                for s in Server.objects.all():
                    s.idstr = uuid4().hex[:10]
                    s.save()

        print("Done.")
