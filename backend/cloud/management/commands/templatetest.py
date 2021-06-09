from django.core.management.base import BaseCommand, CommandError
import subprocess
import ipaddress
from django.conf import settings
import os
from subprocess import Popen, PIPE
import tempfile
from cloud import kuber


class Command(BaseCommand):
    help = 'Test CElery'

    def add_arguments(self, parser):
        parser.add_argument("--idstr")
        parser.add_argument("--network-policy", action='store_true')
        parser.add_argument("--namespace", action='store_true')

    def handle(self, *args, **options):
        if options.get('network_policy'):
            netpol_path = os.path.join(
                settings.BASE_DIR, "yamls", "creating-network-policy.yaml")

            with open(netpol_path, "rt") as fp:
                content = fp.read()
                content = content.replace(
                    "<namespace-id>", options.get("idstr"))
                print("Populated Yaml ====================================")
                print(content)

                outfile = os.path.join(
                    settings.BASE_DIR, "yamls", "create-network-policy.yaml")
                with open(outfile, "wt") as target:
                    target.write(content)

                with Popen(["/etc/kubernetes-cluster-config/calicoctl", "create", "-f", outfile], stdout=PIPE) as proc:
                    print(proc.stdout.read())

        if options.get('namespace'):
            path = os.path.join(
                settings.BASE_DIR, "yamls", "creating-namespace.yaml")

            with open(path, 'rt') as fin:
                yaml = fin.read().replace(
                    "<namespace-id>", options.get("idstr"))
                print(yaml)
                kuber.apply_template(yaml)
