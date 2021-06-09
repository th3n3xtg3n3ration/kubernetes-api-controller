from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import logging
from kubernetes import client, config, utils
import requests
from cloud.models import *
import yaml
from cloud import kuber, tasks
from pprint import pprint
import uuid

logger = logging.getLogger(__name__)


def stop_kuber_server(server_id, server_type):
    # Replace deployment
    image_name = "leonerath/website" if server_type == 'IpgServer' else "thenextgeneration/ipg-server:v2"
    payload = "{\r\n    \"apiVersion\": \"apps/v1\",\r\n    \"kind\": \"Deployment\",\r\n    \"metadata\": {\r\n        \"name\": \"karel-deployment-" + server_id + "\"\r\n    },\r\n    \"spec\": {\r\n        \"selector\": {\r\n            \"matchLabels\": {\r\n                \"app\": \"karel-deployment-" + server_id + "\"\r\n            }\r\n        },\r\n        \"replicas\": 0,\r\n        \"template\": {\r\n            \"metadata\": {\r\n                \"labels\": {\r\n                    \"app\": \"karel-deployment-" + server_id + \
        "\"\r\n                }\r\n            },\r\n            \"spec\": {\r\n                \"containers\": [\r\n                    {\r\n                        \"name\": \"karel-deployment-" + server_id + "\",\r\n                        \"image\": \"" + image_name + "\",\r\n                        \"imagePullPolicy\": \"Always\",\r\n                        \"ports\": [\r\n                            {\r\n                                \"containerPort\": 3000\r\n                            }\r\n                        ],\r\n                        \"resources\": {\r\n                            \"limits\": {\r\n                                \"memory\": \"600Mi\",\r\n                                \"cpu\": 1\r\n                            },\r\n                            \"requests\": {\r\n                                \"memory\": \"300Mi\", \"cpu\": \"500m\"\r\n                            }\r\n                        },\r\n                        \"volumeMounts\": [\r\n                            {\r\n                                \"name\": \"karel-master-data\",\r\n                                \"mountPath\": \"/data\"\r\n                            }\r\n                        ]\r\n                    }\r\n                ],\r\n                \"volumes\": [\r\n                    {\r\n                        \"name\": \"karel-master-data\",\r\n                        \"persistentVolumeClaim\": {\r\n                            \"claimName\": \"master-claim-" + server_id + "\"\r\n                        }\r\n                    }\r\n                ]\r\n            }\r\n        }\r\n    }\r\n}"
    headers = {'Content-type': 'application/json',
               'authorization': 'bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tMmM4dnMiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZGVmYXVsdCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6ImI2ZDMwOTdlLTk1MjYtNDQwZi05MTdkLTRkYmExMmYwM2JlNyIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZWZhdWx0OmRlZmF1bHQifQ.WuCzioQAqzUkeVH-NwjRPZk1usasVfCc3MS9W7sKVF7hYefmCM4PP1dGfIxeA9qVwDrg5Tmm9hzzqKTWym1sbUzlxvYUi0jac-cjWD9k8_g3IF7bW00b7w2jjJ3k5f0ogZyy4aGr0HLhJswencfElE-yOqTtB6AxWc-SReJ2Diq_M-LepUK5iEi9x7JXigBZ2JPa-PpYvDyG6167s9JJdklzHSNQIKV1i81qYyrkmSCqEbnerOU8EzaphCfibOsyyrJxqI_nbB-zoUscsbb8SPMnUozy6NonvOaO-8EZfQ_lyeLmB6KNMUwUFVLxHNUaFZs-R1LYztM8A5HVeD6dkw'}
    url = 'https://192.168.28.60:6443/apis/apps/v1/namespaces/kube-karel-cloud/deployments/karel-deployment-' + \
        str(server_id) + '/'
    r = requests.put(url, data=payload,
                     headers=headers, verify=False)
    if not r.status_code == 200:
        raise Exception(
            "stop_kuber_server() failed with status code: {}".format(r.status_code))


class Command(BaseCommand):
    help = 'Kubernetes API Test'

    def add_arguments(self, parser):
        parser.add_argument("--find-pod")
        parser.add_argument("--find-service")
        parser.add_argument("--rescale")
        parser.add_argument("--scale", type=int, default=0)
        parser.add_argument("--list-pods")
        parser.add_argument("--stop-pod")
        parser.add_argument("--find-deployment")
        parser.add_argument("--list-deployments")
        parser.add_argument("--get-version", action='store_true')
        parser.add_argument("--read-status")
        parser.add_argument("--applyf")
        parser.add_argument("--fix-broken", action='store_true')
        parser.add_argument("--send-broken")
        parser.add_argument("--update-info", action='store_true')

    def handle(self, *args, **options):
        if options['update_info']:
            for subscription_obj in Subscription.objects.all():
                tasks.upload_servers_info(subscription_obj)

        if options['send_broken']:
            tasks.send_broken_subscription(options['send_broken'])
        if options['fix_broken']:
            cnt = 0
            for sub in Subscription.objects.filter(idstr="0"):
                sub.idstr = uuid.uuid4().hex[:10]
                sub.save()
                cnt = cnt + 1
            tasks.fix_broken_subsription()
            print("Updated subscription idstr count := {}".format(cnt))
        if options['read_status']:
            sub_idstr, server_idstr = options['read_status'].split(",")
            status = kuber.read_pod_status(
                sub_idstr, server_idstr)
            pprint(status)

        if options['get_version']:
            version = kuber.get_api_versions()
            pprint(version)
            print("===============")
            print(version.versions)
        if options['find_pod']:
            idstr0, idstr2 = options['find_pod'].split(",")
            print("Looking for pod: {} {}")
            item = kuber.find_pod(idstr0, idstr2)
            print(item)
            print("Host IP: {}".format(item.status.host_ip))
            print("Pod IP: {}".format(item.status.pod_ip))
        if options['find_service']:
            idstr0, idstr2 = options['find_service'].split(",")
            print("Looking for service:")
            ret = kuber.find_service(idstr0, idstr2)
            print(ret)
        if options['list_pods']:
            idstr0 = options['list_pods']
            print(
                "Listing pods for namespace: n-{}".format(options['list_pods']))
            items = kuber.list_pods(idstr0)
            for item in items:
                # print(item)
                print("Host IP: {}".format(item.status.host_ip))
                print("Pod IP: {}".format(item.status.pod_ip))
                print("Pod Name: {}".format(item.metadata.name))
        if options['rescale']:
            idstr0, idstr1, server_type = options['rescale'].split(",")
            item = kuber.rescale_deployment(
                idstr0, idstr1, options.get('scale'), server_type)
        if options['list_deployments']:
            idstr0 = options['list_deployments']
            items = kuber.list_deployments(idstr0)
