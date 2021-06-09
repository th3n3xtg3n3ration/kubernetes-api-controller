# Create your tasks here
from __future__ import absolute_import, unicode_literals
import logging
from django.core.exceptions import ObjectDoesNotExist
import requests
import json
import time
from .models import *
import ipaddress
from celery import shared_task
from datetime import datetime
import os
from django.conf import settings
from cloud import kuber
from django.utils import timezone
import uuid
from subprocess import Popen, PIPE
from yamls.myyaml import *
from kubernetes import client, config, utils
import itertools
import tempfile
from cloud import kuber
import pytz
import re


logger = logging.getLogger(__name__)

POLL_ITERATIONS = 32
tz = pytz.timezone("Europe/Istanbul")

SERVER_IN_PROGRESS = "Pending"
SERVER_IS_RUNNING = "Running"
SERVER_NOT_RUNNING = "Succeeded"


def get_ip():
    # """
    # docstring
    # """

    used_ip = UsedIp.objects.filter(used=False).first()
    if used_ip:
        used_ip.used = True
        used_ip.save()
        return used_ip.ip_address

    raise Exception("No available ip address from the pool!")


def do_cleanup(server_id):
    kuber.delete_pvc(server_id)
    kuber.delete_deployment(server_id)
    kuber.delete_ingress(server_id)
    kuber.delete_service(server_id)


@shared_task
def send_broken_subscription(subscription, service_type="IPG"):
    logger.debug("Sending Broken Subsription to Byp...")
    logger.debug("Ooops Seems Cloud Broken...")
    logger.debug(
        "Possible Problems: Physical disk space shortage, Cloud config file misconfiguration etc. ...")
    logger.debug("For detailed information, Please see Kubernetes cluster...")
    payload = {
        "subscription": subscription,
        "service": service_type
    }

    headers = {'Content-type': 'application/json'}
    url = 'https://byp.karel.cloud/byp/updateservicedetail/'
    r = requests.post(url, data=json.dumps(payload),
                      headers=headers, verify=False)
    logger.debug("Update service detail Response: Status:{}, Text:{}".format(
        r.status_code, r.text))

    Subscription.objects.filter(subscription=subscription).update(
        state="Error"
    )


@shared_task
def fix_broken_subsription():
    subscription_ids = []
    created_subscription_ids = list()
    updated_subscription_ids = list()
    versions = kuber.get_api_versions()

    try:
        logger.debug("@fix_broken_subsription")
        logger.debug("Fetching broken subscription from Byp...")
        headers = {'Content-type': 'application/json'}
        url = 'https://byp.karel.cloud/byp/getbrokensubscriptions/'
        response = requests.get(url, headers=headers, verify=False)
        if not response.status_code == 200:
            logger.error("Unable to fetch Broken Subscription List... Status Code {}".format(
                response.status_code))
            return

        subscriptions = response.json()
        if not subscriptions:
            return

        logger.debug("Found a total of {} Broken subscription".format(
            len(subscriptions)))

        for subscription in subscriptions:
            if not versions or not versions.versions:
                continue

            customer = subscription['customer']
            start_date = subscription['start_date']
            end_date = tz.localize(timezone.datetime.strptime(
                subscription['end_date'], "%Y-%m-%d"))  # str

            if timezone.now().astimezone(tz).date() >= end_date.date():
                logger.debug(
                    "Selected 'end_date' := {} for Subscription {} is too close or past the current date/time...".format(
                        end_date, subscription['subscription']))
                continue

            term_subscription = subscription['term_subscription']
            service_type = subscription['service_type']
            subscription_str = subscription['subscription']
            service_datas = subscription.get('service_data')

            if not service_datas:
                continue

            server_names = service_datas.get('servers')
            if not server_names:
                continue

            subscription_obj, created = Subscription.objects.get_or_create(
                customer=customer,
                subscription=subscription_str,
                defaults={
                    "start_date": start_date,
                    "end_date": end_date,
                    "term_subscription": term_subscription,
                    "service_type": service_type,
                    "state": "Initializing",
                    "server_name_prefix": str(
                        service_datas['server_name_prefix']),
                    "package": str(service_datas['package']),
                    "trunk_service_provider": str(
                        service_datas['trunk_service_provider']),
                    "extra_call_record_package": str(
                        service_datas['extra_call_record_package']),
                    "demo": str(service_datas['demo']),
                    "extra_duration_package": str(
                        service_datas['extra_duration_package']),
                    "exp20_dss_module_ip1141": str(
                        service_datas['exp20_dss_module_ip1141']),
                    "exp40_dss_module_ip136_ip138": str(
                        service_datas['exp40_dss_module_ip136_ip138']),
                    "ip1111_poe_no_adapter": str(
                        service_datas['ip1111_poe_no_adapter']),
                    "ip1131_poe_gigabit_no_adapter": str(
                        service_datas['ip1131_poe_gigabit_no_adapter']),
                    "ip1141_poe_no_adapter": str(
                        service_datas['ip1141_poe_no_adapter']),
                    "ip1141_ip131_ip132_adapter": str(
                        service_datas['ip1141_ip131_ip132_adapter']),
                    "ip1181_ip136_ip138_adapter": str(
                        service_datas['ip1181_ip136_ip138_adapter']),
                    "ip1211_w_adapter": str(
                        service_datas['ip1211_w_adapter']),
                    "ip1211_poe_no_adapter": str(
                        service_datas['ip1211_poe_no_adapter']),
                    "ip1211_ip1211p_ip1111_ip1131_adapter": str(
                        service_datas['ip1211_ip1211p_ip1111_ip1131_adapter']),
                    "ip131_poe_no_adapter": str(
                        service_datas['ip131_poe_no_adapter']),
                    "ip132_gigabit_no_adapter": str(
                        service_datas['ip132_gigabit_no_adapter']),
                    "ip136_poe_no_adapter": str(
                        service_datas['ip136_poe_no_adapter']),
                    "ip138_poe_no_adapter": str(
                        service_datas['ip138_poe_no_adapter']),
                    "karel_mobile": str(service_datas['karel_mobile']),
                    "vp128": str(service_datas['vp128']),
                    "yt510": str(service_datas['yt510']),
                    "yt520": str(service_datas['yt520']),
                    "yt530": str(service_datas['yt530']),
                    "expiration_processed": False
                }
            )

            if created:
                subscription_obj.idstr = uuid.uuid4().hex[:10]
                subscription_obj.save()

                created_subscription_ids.append(subscription_obj.id)
            else:
                updated_subscription_ids.append(subscription_obj.id)

            for server_name in server_names:
                srvtype, _ = ServerType.objects.get_or_create(
                    name=server_name)
                server_obj, _ = Server.objects.get_or_create(
                    subscription=subscription_obj,
                    server_type=srvtype,
                    defaults={
                        'action': 'Stop',
                        'idstr': uuid.uuid4().hex[:10],
                        "static_ip": get_ip()
                    }
                )

                if server_obj.server_type.name == "IpgServer":
                    ipg_server, server_created = IpgServer.objects.get_or_create(
                        server=server_obj, defaults={
                            "server_name": server_name,
                        })
                elif server_obj.server_type.name == "WebcmServer":
                    webcam_server, server_created = WebcmServer.objects.get_or_create(
                        server=server_obj, defaults={
                            "server_name": server_name
                        })

        handle_post_subscription(
            created_subscription_ids, updated_subscription_ids)

    except:
        pass


def stop_servers_for_subscription(subscription_obj):
    logger.info("Stopping all servers for Subscription: {} of Customer: {}".format(
        subscription_obj.subscription, subscription_obj.customer))
    for server_obj in subscription_obj.server_set.all():
        try:
            stop_kuber_server(server_obj.idstr,
                              server_obj.server_type.name)
        except:
            pass


def server_active(idstr, server_type):
    logger.debug("@server_active({},{})".format(idstr, server_type))

    payload = {
        "state": 1,
        "server_id": "d-{}".format(idstr),
        "server_type": server_type
    }

    headers = {'Content-type': 'application/json'}
    url = 'https://byp.karel.cloud/byp/updateserverstate/'
    r = requests.post(url, data=json.dumps(payload),
                      headers=headers, verify=False)
    logger.debug(r.text)


def server_inactive(idstr, server_type):
    logger.debug("@server_inactive({},{})".format(idstr, server_type))

    payload = {
        "state": 2,
        "server_id": "d-{}".format(idstr),
        "server_type": server_type
    }
    headers = {'Content-type': 'application/json'}
    url = 'https://byp.karel.cloud/byp/updateserverstate/'
    r = requests.post(url, data=json.dumps(payload),
                      headers=headers, verify=False)
    logger.debug(r.text)


def server_starting(idstr, server_type):
    logger.debug("@server_starting({},{})".format(idstr, server_type))
    payload = {
        "state": 3,
        "server_id": "d-{}".format(idstr),
        "server_type": server_type
    }
    headers = {'Content-type': 'application/json'}
    url = 'https://byp.karel.cloud/byp/updateserverstate/'
    r = requests.post(url, data=json.dumps(payload),
                      headers=headers, verify=False)
    logger.debug(r.text)


def server_stopping(idstr, server_type):
    # payload = "{\r\n    \"state\": 4,\r\n    \"server_id\": \"" + \
    #     server_id + "\",\r\n    \"server_type\": \"" + server_type + "\"\r\n}"
    logger.debug("@server_stopping({},{})".format(idstr, server_type))
    payload = {
        "state": 4,
        "server_id": "d-{}".format(idstr),
        "server_type": server_type
    }

    headers = {'Content-type': 'application/json'}
    url = 'https://byp.karel.cloud/byp/updateserverstate/'
    r = requests.post(url, data=json.dumps(payload),
                      headers=headers, verify=False)
    logger.debug(r.text)


def get_addresses(subscription_object, server_object):
    """
    docstring
    """
    retry = 0
    item = dict()
    while True:
        time.sleep(2)
        retry = retry + 1
        if retry > 120:
            return item

        pod = kuber.find_pod(subscription_object.idstr, server_object.idstr)
        service = kuber.find_service(
            subscription_object.idstr, server_object.idstr)

        if not pod or not service:
            continue

        item = {
            "pod_ip": pod.status.pod_ip,
            "host_ip": pod.status.host_ip,
            "cluster_ip": service.spec.cluster_ip
        }

        if item.get('pod_ip') and item.get("cluster_ip"):
            return item


def upload_servers_info(subscription_object):
    """
    docstring
    """

    # payload["IpgServer"] = {
    #     "cpu": ipg.cpu,
    #     "ram": ipg.ram,
    #     "disc": ipg.disc,
    #     "widea_address": ipg.widea_address,
    #     "local_ip": "{}".format(clusterip),
    #     "internal_ip": "{}".format(pod_ip),
    #     "external_ip": "{}:{}".format(host_ip, port),
    #     "server_name": ipg.server_name,
    #     "state": ipg.state,
    #     "fqdn": ipg.fqdn
    # }
    service_payload = dict()
    for server_object in subscription_object.servers.all():
        if 'ipg' in server_object.server_type.name.lower():
            ipg = IpgServer.objects.get(server=server_object)
            if not ipg.internal_ip or not ipg.local_ip:
                break

            service_payload["IpgServer"] = {
                "cpu": ipg.cpu,
                "ram": ipg.ram,
                "disc": ipg.disc,
                "widea_address": ipg.widea_address,
                "local_ip": ipg.local_ip,
                "internal_ip": ipg.internal_ip,
                "external_ip": ipg.external_ip,
                "server_name": ipg.server_name,
                "state": ipg.state,
                "fqdn": ipg.fqdn,
                "server_id": "d-{}".format(ipg.server.idstr)
            }
        else:
            webcm = WebcmServer.objects.get(server=server_object)
            if not webcm.internal_ip or not webcm.local_ip:
                break

            service_payload["WebcmServer"] = {
                "address": webcm.address,
                "local_ip": webcm.local_ip,
                "internal_ip": webcm.internal_ip,
                "server_name": webcm.server_name,
                "state": webcm.state,
                "fqdn": webcm.fqdn,
                "server_id": "d-{}".format(webcm.server.idstr)
            }

        # payload["WebcmServer"] = {
        #     "address": webcm.address,
        #     "local_ip": "{}".format(clusterip),
        #     "internal_ip": "{}".format(pod_ip),
        #     "server_name": webcm.server_name,
        #     "state": webcm.state,
        #     "fqdn": webcm.fqdn
        # }

    payload = {
        "subscription": subscription_object.subscription,
        "service": "Ipg",
        "servers": service_payload
    }

    if len(payload["servers"]) < 2:
        return

    headers = {'Content-type': 'application/json'}
    url = 'https://byp.karel.cloud/byp/updateservicedetail/'
    r = requests.post(url,
                      data=json.dumps(payload),
                      headers=headers,
                      verify=False)
    if r.status_code == 200:
        logger.debug(
            "Yes! 'updateservicedetail' sent successfully. Byp returned '200'")
    else:
        logger.debug("Something went wrong while uploading server info.")
        logger.debug(r.text)


def update_server_info(subscription_object):
    """
    docstring
    """
    payload = dict()
    for server_object in subscription_object.servers.all():
        addresses = get_addresses(subscription_object, server_object)

        if 'ipg' in server_object.server_type.name.lower():
            ipg = IpgServer.objects.get(server=server_object)
            ipg.cpu = "1 vCore"
            ipg.ram = "512 MB"
            ipg.disc = "5 GB"
            ipg.internal_ip = addresses.get("pod_ip")
            ipg.local_ip = addresses.get("cluster_ip")
            ipg.external_ip = addresses.get("host_ip")
            ipg.widea_address = "https://d-{}.karel.cloud/widea".format(
                server_object.idstr)
            ipg.server_name = "karel-cloud-ipg-d-{}".format(
                server_object.idstr)
            ipg.state = 1
            ipg.fqdn = "d-{}.karel.cloud".format(server_object.idstr)
            ipg.save()

        if 'web' in server_object.server_type.name.lower():
            ipg = subscription_object.servers.filter(
                server_type__name='IpgServer').first()

            webcm = WebcmServer.objects.get(server=server_object)
            if ipg:
                webcm.address = "https://d-{}.karel.cloud/webcm".format(
                    ipg.idstr)
            else:
                webcm.address = "https://d-{}.karel.cloud/webcm".format(
                    server_object.idstr)
            webcm.local_ip = addresses.get("cluster_ip")
            webcm.internal_ip = addresses.get("pod_ip")
            webcm.server_name = "karel-cloud-webcm-d-{}".format(
                server_object.idstr)
            webcm.state = 1
            webcm.fqdn = "d-{}.karel.cloud".format(server_object.idstr)
            webcm.save()

    upload_servers_info(subscription_object)


#     if server_type_name == 'IpgServer':
#         try:
#             service_payload[server_type_name] = {
#                 "cpu": "1",
#                 "ram": "600Mi",
#                 "disc": "2Gi",
#                 "widea_address": "www.kareldeployment.com:32370/{}".format(server_id),
#                 "local_ip": "{}".format(clusterip),
#                 "internal_ip": "{}".format(pod_ip),
#                 "external_ip": "{}:{}".format(host_ip, port),
#                 "server_name": "karel-deployment-{}".format(server_id),
#                 "server_id": "{}".format(server_id),
#                 "state": "1",
#                 "fqdn": "www.kareldeployment.com:32370/{}".format(server_id),
#             }

#             default_values = {
#                 **service_payload[server_type_name],
#                 "state": 1
#             }
#             default_values.pop('server_id')

#             IpgServer.objects.update_or_create(
#                 server=server_object,
#                 defaults=default_values
#             )
#         except Exception as e:
#             logger.debug(e)

#     else:  # Webcm service
#         try:
#             service_payload[server_type_name] = {
#                 "address": "www.kareldeployment.com:32370/{}".format(server_id),
#                 "local_ip": "{}".format(clusterip),
#                 "internal_ip": "{}".format(pod_ip),
#                 "server_name": "karel-deployment-{}".format(server_id),
#                 "server_id": "{}".format(server_id),
#                 "state": "1",
#                 "fqdn": "www.kareldeployment.com:32370/{}".format(server_id),
#             }

#             default_values = {
#                 **service_payload[server_type_name],
#                 "state": 1
#             }

#             default_values.pop('server_id')

#             WebcmServer.objects.update_or_create(
#                 server=server_object,
#                 defaults=default_values
#             )
#         except Exception as e:
#             logger.debug(e)

# if not len(service_payload) == 2:  # IpgServer and WbcamServer
#     # Do not send to BYP
#     logger.error(
#         "Either IpgServer/WbcamServer or both has no IP. I am not submitting data to Byp!")
#     continue

# logger.debug(
#     "Yes! Both IpgServer and WbcamServer has IP. I am now submitting in to Byp!")
# payload = {
#     "subscription": server_object.subscription.subscription,
#     "service": "Ipg",
#     "servers": service_payload
# }

# # writejson2file(payload, "updateservicedetail-payload")

# headers = {'Content-type': 'application/json'}
# url = 'https://byp.karel.cloud/byp/updateservicedetail/'
# r = requests.post(url,
#                     data=json.dumps(payload),
#                     headers=headers,
#                     verify=False)
# if r.status_code == 200:
#     logger.debug(
#         "Yes! 'updateservicedetail' sent successfully. Byp returned '200'")
#     server_object.subscription.state = "Initialized"
#     server_object.subscription.save()
# else:
#     logger.debug(
#         "Byp did not return '200' for 'updateservicedetail' call")
#     server_object.subscription.state = "Not Initialized"
#     server_object.subscription.save()


@shared_task
def handle_post_subscription(created_subscription_ids, updated_subscription_ids):

    for subscription_id in itertools.chain(created_subscription_ids, updated_subscription_ids):
        subscription_object = Subscription.objects.get(pk=subscription_id)
        subscription_idstr = subscription_object.idstr

        print("Creating NAMESPACE idstr:{}.....".format(subscription_idstr))
        yaml = create_namespace(subscription_idstr)
        kuber.apply_template(yaml)
        print("End creatimg NAMESPACE=========================================>")

        print("Creating NETWORK POLICY idstr:{}.....".format(subscription_idstr))
        yaml = create_network_policy(subscription_idstr)
        kuber.apply_network_policy(yaml)
        print("End creatimg NETWORK POLICY=========================================>")

        for server_object in subscription_object.servers.all():
            # server_object.subscription = Subscription.objects.get(id=server_object.subscription)
            server_data = None
            server_type_name = server_object.server_type.name
            server_idstr = server_object.idstr
            if server_type_name == 'IpgServer':
                ipg_server = IpgServer.objects.get(server=server_object)
                server_data = ipg_server
                create_pvc = create_ipg_pvc
                create_deployment = create_ipg_deployment
                create_service = create_ipg_service
                create_ingress = create_ipg_ingress
            else:
                webcm_server = WebcmServer.objects.get(server=server_object)
                server_data = webcm_server
                create_pvc = create_webcam_pvc
                create_deployment = create_webcam_deployment
                create_service = create_webcam_service
                create_ingress = create_webcam_ingress

            print("Creating PVC idstr:{}.....".format(
                server_idstr))
            yaml = create_pvc(server_idstr, subscription_idstr)
            kuber.apply_template(yaml)
            print("End creatimg PVC=========================================>")

            print("Creating DEPLOYMENT idstr:{}.....".format(server_idstr))
            yaml = create_deployment(
                server_idstr, subscription_idstr, server_object.static_ip)
            kuber.apply_template(yaml)
            print("End creatimg DEPLOYMENT=========================================>")

            print("Creating SERVICE idstr:{}.....".format(server_idstr))
            yaml = create_service(server_idstr, subscription_idstr)
            kuber.apply_template(yaml)
            print("End creatimg SERVICE=========================================>")

            print("Creating INGRESS idstr:{}.....".format(
                server_idstr))
            yaml = create_ingress(server_idstr, subscription_idstr)
            kuber.apply_template(yaml)
            print("END CREATING INGRESS=========================================>")

        update_server_info(subscription_object)


# @shared_task
# def handle_post_subscription(created_subscription_ids, updated_subscription_ids):
#     print("Subscription created!")
#     for subscription_id in created_subscription_ids:
#         service_payload = dict()

#         server_idstrs = Server.objects.filter(
#             subscription_id=subscription_id).values_list('idstr', flat=True)

#         for server_id in server_idstrs:
#             server_object = Server.objects.get(idstr=server_id)
#             # server_object.subscription = Subscription.objects.get(id=server_object.subscription)
#             server_type_name = server_object.server_type.name
#             server_data = None
#             if server_type_name == 'IpgServer':
#                 ipg_server = IpgServer.objects.get(server=server_object)
#                 server_data = ipg_server
#             else:
#                 webcm_server = WebcmServer.objects.get(server=server_object)
#                 server_data = webcm_server

#             pvc = kuber.find_pvc(server_id)
#             if not pvc:
#                 # Create PVC

#                 logger.debug("Creating New PVC...")
#                 payload = "\r\n\r\n{\"kind\": \"PersistentVolumeClaim\", \"apiVersion\": \"v1\", \"metadata\": {\"name\": \"master-claim-" + str(
#                     server_id) + "\", \"annotations\": {\"volume.beta.kubernetes.io/storage-class\": \"thin-disk\"}}, \"spec\": {\"accessModes\": [\"ReadWriteOnce\"], \"resources\": {\"requests\": {\"storage\": \"2Gi\"}}}}"
#                 headers = {'Content-type': 'application/json',
#                            'authorization': 'bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tMmM4dnMiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZGVmYXVsdCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6ImI2ZDMwOTdlLTk1MjYtNDQwZi05MTdkLTRkYmExMmYwM2JlNyIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZWZhdWx0OmRlZmF1bHQifQ.WuCzioQAqzUkeVH-NwjRPZk1usasVfCc3MS9W7sKVF7hYefmCM4PP1dGfIxeA9qVwDrg5Tmm9hzzqKTWym1sbUzlxvYUi0jac-cjWD9k8_g3IF7bW00b7w2jjJ3k5f0ogZyy4aGr0HLhJswencfElE-yOqTtB6AxWc-SReJ2Diq_M-LepUK5iEi9x7JXigBZ2JPa-PpYvDyG6167s9JJdklzHSNQIKV1i81qYyrkmSCqEbnerOU8EzaphCfibOsyyrJxqI_nbB-zoUscsbb8SPMnUozy6NonvOaO-8EZfQ_lyeLmB6KNMUwUFVLxHNUaFZs-R1LYztM8A5HVeD6dkw'}
#                 url = 'https://192.168.28.60:6443/api/v1/namespaces/kube-karel-cloud/persistentvolumeclaims'
#                 r = requests.post(url, data=payload,
#                                   headers=headers, verify=False)

#                 status_code = r.status_code
#                 reason = r.reason
#                 text = r.text
#                 if status_code != 201:
#                     logger.debug(
#                         "Unable to ceate PVC with reason '{}'. Updating service detail...".format(reason))
#                     do_cleanup(server_id)
#                     send_broken_subscription.apply_async(
#                         (server_object.subscription.subscription,))
#                     break
#             else:
#                 logger.debug("Persistent Volume Claim '{}' already exists!".format(
#                     pvc[0].metadata.name))

#             image_name = "leonerath/website" if server_object.server_type.name == 'IpgServer' else "thenextgeneration/ipg-server:v2"

#             deployment = kuber.find_deployment(server_id)

#             if not deployment:
#                 # Create Deployment
#                 logger.debug("Creating Deployment...")
#                 payload = "{\n\t\"apiVersion\": \"apps/v1\",\n\t\"kind\": \"Deployment\",\n\t\"metadata\": {\n\t\t\"name\": \"karel-deployment-" + str(
#                     server_id) + "\"\n\t},\n\t\"spec\": {\n\t\t\"selector\": {\n\t\t\t\"matchLabels\": {\n\t\t\t\t\"app\": \"karel-deployment-" + str(
#                     server_id) + "\"\n\t\t\t}\n\t\t},\n\t\t\"replicas\": 1,\n\t\t\"template\": {\n\t\t\t\"metadata\": {\n\t\t\t\t\"labels\": {\n\t\t\t\t\t\"app\": \"karel-deployment-" + str(
#                     server_id) + "\"\n\t\t\t\t}\n\t\t\t},\n\t\t\t\"spec\": {\n\t\t\t\t\"containers\": [\n\t\t\t\t\t{\n\t\t\t\t\t\t\"name\": \"karel-deployment-" + str(
#                     server_id) + "\",\n\t\t\t\t\t\t\"image\": \"" + image_name + "\",\n\t\t\t\t\t\t\"imagePullPolicy\": \"Always\",\n\t\t\t\t\t\t\"ports\": [\n\t\t\t\t\t\t\t{\n\t\t\t\t\t\t\t\t\"containerPort\": 3000\n\t\t\t\t\t\t\t}\n\t\t\t\t\t\t],\n\t\t\t\t\t\t\"resources\": {\n\t\t\t\t\t\t\t\"limits\": {\n\t\t\t\t\t\t\t\t\"memory\": \"600Mi\",\n\t\t\t\t\t\t\t\t\"cpu\": 1\n\t\t\t\t\t\t\t},\n\t\t\t\t\t\t\t\"requests\": {\n\t\t\t\t\t\t\t\t\"memory\": \"300Mi\",\n\t\t\t\t\t\t\t\t\"cpu\": \"500m\"\n\t\t\t\t\t\t\t}\n\t\t\t\t\t\t},\n\t\t\t\t\t\t\"volumeMounts\": [\n\t\t\t\t\t\t\t{\n\t\t\t\t\t\t\t\t\"name\": \"karel-master-" + str(
#                     server_id) + "\",\n\t\t\t\t\t\t\t\t\"mountPath\": \"/data\"\n\t\t\t\t\t\t\t}\n\t\t\t\t\t\t]\n\t\t\t\t\t}\n\t\t\t\t],\n\t\t\t\t\"volumes\": [\n\t\t\t\t\t{\n\t\t\t\t\t\t\"name\": \"karel-master-" + str(
#                     server_id) + "\",\n\t\t\t\t\t\t\"persistentVolumeClaim\": {\n\t\t\t\t\t\t\t\"claimName\": \"master-claim-" + str(
#                     server_id) + "\"\n\t\t\t\t\t\t}\n\t\t\t\t\t}\n\t\t\t\t]\n\t\t\t}\n\t\t}\n\t}\n}"
#                 headers = {'Content-type': 'application/json',
#                            'authorization': 'bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tMmM4dnMiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZGVmYXVsdCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6ImI2ZDMwOTdlLTk1MjYtNDQwZi05MTdkLTRkYmExMmYwM2JlNyIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZWZhdWx0OmRlZmF1bHQifQ.WuCzioQAqzUkeVH-NwjRPZk1usasVfCc3MS9W7sKVF7hYefmCM4PP1dGfIxeA9qVwDrg5Tmm9hzzqKTWym1sbUzlxvYUi0jac-cjWD9k8_g3IF7bW00b7w2jjJ3k5f0ogZyy4aGr0HLhJswencfElE-yOqTtB6AxWc-SReJ2Diq_M-LepUK5iEi9x7JXigBZ2JPa-PpYvDyG6167s9JJdklzHSNQIKV1i81qYyrkmSCqEbnerOU8EzaphCfibOsyyrJxqI_nbB-zoUscsbb8SPMnUozy6NonvOaO-8EZfQ_lyeLmB6KNMUwUFVLxHNUaFZs-R1LYztM8A5HVeD6dkw'}
#                 url = 'https://192.168.28.60:6443/apis/apps/v1/namespaces/kube-karel-cloud/deployments'
#                 r = requests.post(url, data=payload,
#                                   headers=headers, verify=False)
#                 status_code = r.status_code
#                 reason = r.reason
#                 text = r.text
#                 if r.status_code != 201:
#                     logger.debug(
#                         "Unable to create Deployment with Reason: {}".format(reason))
#                     do_cleanup(server_id)
#                     send_broken_subscription.apply_async(
#                         (server_object.subscription.subscription,))
#                     break
#             else:
#                 logger.debug("Deployment {} already exists!".format(
#                     deployment[0].metadata.name))

#             service_name, cluster_ip, node_port = kuber.find_service(server_id)
#             if not cluster_ip:
#                 # Create Service
#                 logger.debug("Creating Service...")
#                 payload = "{\n\t\"apiVersion\": \"v1\",\n\t\"kind\": \"Service\",\n\t\"metadata\": {\n\t\t\"name\": \"karel-service-" + str(server_id) + "\",\n\t\t\"labels\": {\n\t\t\t\"app\": \"karel-deployment-" + str(
#                     server_id) + "\"\n\t\t}\n\t},\n\t\"spec\": {\n\t\t\"selector\": {\n\t\t\t\"app\": \"karel-deployment-" + str(server_id) + "\"\n\t\t},\n\t\t\"type\": \"NodePort\",\n\t\t\"ports\": [\n\t\t\t{\n\t\t\t\t\"port\": 3000,\n\t\t\t\t\"targetPort\": 3000,\n\t\t\t\t\"nodePort\": null\n\t\t\t}\n\t\t]\n\t}\n}"
#                 headers = {'Content-type': 'application/json',
#                            'authorization': 'bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tMmM4dnMiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZGVmYXVsdCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6ImI2ZDMwOTdlLTk1MjYtNDQwZi05MTdkLTRkYmExMmYwM2JlNyIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZWZhdWx0OmRlZmF1bHQifQ.WuCzioQAqzUkeVH-NwjRPZk1usasVfCc3MS9W7sKVF7hYefmCM4PP1dGfIxeA9qVwDrg5Tmm9hzzqKTWym1sbUzlxvYUi0jac-cjWD9k8_g3IF7bW00b7w2jjJ3k5f0ogZyy4aGr0HLhJswencfElE-yOqTtB6AxWc-SReJ2Diq_M-LepUK5iEi9x7JXigBZ2JPa-PpYvDyG6167s9JJdklzHSNQIKV1i81qYyrkmSCqEbnerOU8EzaphCfibOsyyrJxqI_nbB-zoUscsbb8SPMnUozy6NonvOaO-8EZfQ_lyeLmB6KNMUwUFVLxHNUaFZs-R1LYztM8A5HVeD6dkw'}
#                 url = 'https://192.168.28.60:6443/api/v1/namespaces/kube-karel-cloud/services'
#                 r = requests.post(url, data=payload,
#                                   headers=headers, verify=False)
#                 status_code = r.status_code
#                 reason = r.reason
#                 text = json.loads(r.text)
#                 port = text['spec']['ports'][0]['nodePort']
#                 clusterip = text['spec']['clusterIP']
#                 if r.status_code != 201:
#                     logger.debug(
#                         "Unable to create service with Reason: {}".format(reason))
#                     do_cleanup(server_id)
#                     send_broken_subscription.apply_async(
#                         (server_object.subscription.subscription,))
#                     break

#                 # Create Ingress
#                 logger.debug("Creating Ingress...")
#                 payload = "{\n\t\"apiVersion\": \"networking.k8s.io/v1beta1\",\n\t\"kind\": \"Ingress\",\n\t\"metadata\": {\n\t\t\"name\": \"karel-ingress-" + str(server_id) + "\",\n\t\t\"annotations\": {\n\t\t\t\"nginx.ingress.kubernetes.io/rewrite-target\": \"/\",\n\t\t\t\"kubernetes.io/ingress.class\": \"nginx\"\n\t\t}\n\t},\n\t\"spec\": {\n\t\t\"rules\": [\n\t\t\t{\n\t\t\t\t\"host\": \"www.kareldeployment.com\",\n\t\t\t\t\"http\": {\n\t\t\t\t\t\"paths\": [\n\t\t\t\t\t\t{\n\t\t\t\t\t\t\t\"path\": \"/" + str(
#                     server_id) + "\",\n\t\t\t\t\t\t\t\"backend\": {\n\t\t\t\t\t\t\t\t\"serviceName\": \"karel-service-" + str(server_id) + "\",\n\t\t\t\t\t\t\t\t\"servicePort\": 3000\n\t\t\t\t\t\t\t}\n\t\t\t\t\t\t}\n\t\t\t\t\t]\n\t\t\t\t}\n\t\t\t}\n\t\t]\n\t}\n}"

#                 headers = {'Content-type': 'application/json',
#                            'authorization': 'bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tMmM4dnMiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZGVmYXVsdCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6ImI2ZDMwOTdlLTk1MjYtNDQwZi05MTdkLTRkYmExMmYwM2JlNyIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZWZhdWx0OmRlZmF1bHQifQ.WuCzioQAqzUkeVH-NwjRPZk1usasVfCc3MS9W7sKVF7hYefmCM4PP1dGfIxeA9qVwDrg5Tmm9hzzqKTWym1sbUzlxvYUi0jac-cjWD9k8_g3IF7bW00b7w2jjJ3k5f0ogZyy4aGr0HLhJswencfElE-yOqTtB6AxWc-SReJ2Diq_M-LepUK5iEi9x7JXigBZ2JPa-PpYvDyG6167s9JJdklzHSNQIKV1i81qYyrkmSCqEbnerOU8EzaphCfibOsyyrJxqI_nbB-zoUscsbb8SPMnUozy6NonvOaO-8EZfQ_lyeLmB6KNMUwUFVLxHNUaFZs-R1LYztM8A5HVeD6dkw'}
#                 url = 'https://192.168.28.60:6443/apis/networking.k8s.io/v1beta1/namespaces/kube-karel-cloud/ingresses'
#                 r = requests.post(url, data=payload,
#                                   headers=headers, verify=False)
#                 status_code = r.status_code
#                 reason = r.reason
#                 text = r.text
#                 if r.status_code != 201:
#                     logger.debug(
#                         "Unable to create Ingress with reason: {}".format(reason))
#                     do_cleanup(server_id)
#                     send_broken_subscription.apply_async(
#                         (server_object.subscription.subscription,))
#                     break
#             else:
#                 logger.debug("Service {} already exists!".format(service_name))

#             deployment = kuber.find_deployment(server_id)

#             if deployment[0].spec.replicas == 0:
#                 start_kuber_server(server_id, server_type_name)

#             logger.debug(
#                 "Looking up Cluster Ip from running Kubernetes Service...")
#             service_name, clusterip, port = kuber.find_service(server_id)
#             if not service_name:
#                 do_cleanup(server_id)
#                 send_broken_subscription.apply_async(
#                     (server_object.subscription.subscription,))
#                 break

#             logger.debug("Found service: {} with cluster_ip: {} and port: {}".format(
#                 service_name, clusterip, port))

#             pod_ip, host_ip, namespace, name, pod = kuber.find_pod(
#                 str(server_id))
#             retry = POLL_ITERATIONS
#             logger.debug("Waiting for Pod IP address...")
#             while retry > 0:
#                 logger.debug("Retrying {} more times".format(retry))
#                 retry = retry - 1
#                 if not pod_ip or not host_ip or not namespace or not name:
#                     pod_ip, host_ip, namespace, name, pod = kuber.find_pod(
#                         str(server_id))
#                     time.sleep(1)
#                     continue
#                 else:
#                     break

#             if not pod_ip or not host_ip:
#                 logger.debug(
#                     "Sorry, Missing Pod/Host Ip Address. Not adding server to Payload.")
#                 do_cleanup(server_id)
#                 send_broken_subscription.apply_async(
#                     (server_object.subscription.subscription,))
#                 break

#             logger.debug("Pod Ip: {}".format(pod_ip))
#             logger.debug("Host Ip: {}".format(host_ip))
#             logger.debug("namespace: {}".format(namespace))
#             logger.debug("name: {}".format(name))
#             logger.debug("retry: {}".format(retry))
#             logger.debug("server_id: {}".format(server_id))

#             logger.debug(
#                 "Yes! IP address successfully obtained for {}".format(server_type_name))
#             logger.debug("Adding payload info for {}".format(server_type_name))

#             if server_type_name == 'IpgServer':
#                 try:
#                     service_payload[server_type_name] = {
#                         "cpu": "1",
#                         "ram": "600Mi",
#                         "disc": "2Gi",
#                         "widea_address": "www.kareldeployment.com:32370/{}".format(server_id),
#                         "local_ip": "{}".format(clusterip),
#                         "internal_ip": "{}".format(pod_ip),
#                         "external_ip": "{}:{}".format(host_ip, port),
#                         "server_name": "karel-deployment-{}".format(server_id),
#                         "server_id": "{}".format(server_id),
#                         "state": "1",
#                         "fqdn": "www.kareldeployment.com:32370/{}".format(server_id),
#                     }

#                     default_values = {
#                         **service_payload[server_type_name],
#                         "state": 1
#                     }
#                     default_values.pop('server_id')

#                     IpgServer.objects.update_or_create(
#                         server=server_object,
#                         defaults=default_values
#                     )
#                 except Exception as e:
#                     logger.debug(e)

#             else:  # Webcm service
#                 try:
#                     service_payload[server_type_name] = {
#                         "address": "www.kareldeployment.com:32370/{}".format(server_id),
#                         "local_ip": "{}".format(clusterip),
#                         "internal_ip": "{}".format(pod_ip),
#                         "server_name": "karel-deployment-{}".format(server_id),
#                         "server_id": "{}".format(server_id),
#                         "state": "1",
#                         "fqdn": "www.kareldeployment.com:32370/{}".format(server_id),
#                     }

#                     default_values = {
#                         **service_payload[server_type_name],
#                         "state": 1
#                     }

#                     default_values.pop('server_id')

#                     WebcmServer.objects.update_or_create(
#                         server=server_object,
#                         defaults=default_values
#                     )
#                 except Exception as e:
#                     logger.debug(e)

#         if not len(service_payload) == 2:  # IpgServer and WbcamServer
#             # Do not send to BYP
#             logger.error(
#                 "Either IpgServer/WbcamServer or both has no IP. I am not submitting data to Byp!")
#             continue

#         logger.debug(
#             "Yes! Both IpgServer and WbcamServer has IP. I am now submitting in to Byp!")
#         payload = {
#             "subscription": server_object.subscription.subscription,
#             "service": "Ipg",
#             "servers": service_payload
#         }

#         # writejson2file(payload, "updateservicedetail-payload")

#         headers = {'Content-type': 'application/json'}
#         url = 'https://byp.karel.cloud/byp/updateservicedetail/'
#         r = requests.post(url,
#                           data=json.dumps(payload),
#                           headers=headers,
#                           verify=False)
#         if r.status_code == 200:
#             logger.debug(
#                 "Yes! 'updateservicedetail' sent successfully. Byp returned '200'")
#             server_object.subscription.state = "Initialized"
#             server_object.subscription.save()
#         else:
#             logger.debug(
#                 "Byp did not return '200' for 'updateservicedetail' call")
#             server_object.subscription.state = "Not Initialized"
#             server_object.subscription.save()


def writejson2file(jason, tag):
    with open("debug/debug-{}{}.log".format(tag, int(datetime.now().timestamp())), "wt") as fp:
        fp.write(json.dumps(jason, indent=1))


def wait_for_pod_start(server_id):
    time.sleep(4)
    server_object = Server.objects.get(idstr=server_id)
    ref = timezone.now()
    pod = kuber.find_pod(server_object.subscription.idstr, server_object.idstr)

    while not pod:
        # logger.debug("Pod {} phase := {}".format(server_id, pod.status.phase))
        pod = kuber.find_pod(
            server_object.subscription.idstr, server_object.idstr)
        time.sleep(2)
        if (timezone.now() - timezone.timedelta(minutes=5)) > ref:
            logger.debug(
                "Server {} is not running for too long".format(server_id))
            raise Exception("pod did not start!")


def wait_for_pod_stop(server_id):
    time.sleep(4)
    server_object = Server.objects.get(idstr=server_id)
    ref = timezone.now()
    pod = kuber.find_pod(server_object.subscription.idstr, server_object.idstr)

    while pod:
        # logger.debug("Pod {} phase := {}".format(server_id, pod.status.phase))
        pod = kuber.find_pod(
            server_object.subscription.idstr, server_object.idstr)
        time.sleep(2)
        if (timezone.now() - timezone.timedelta(minutes=5)) > ref:
            logger.debug(
                "Server {} is not stopping for too long".format(server_id))
            raise Exception("pod did not stop!")


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

    wait_for_pod_stop(server_id)


def start_kuber_server(server_id, server_type):
    # Request Start server to Cluster
    image_name = "leonerath/website" if server_type == 'IpgServer' else "thenextgeneration/ipg-server:v2"

    payload = "{\r\n    \"apiVersion\": \"apps/v1\",\r\n    \"kind\": \"Deployment\",\r\n    \"metadata\": {\r\n        \"name\": \"karel-deployment-" + server_id + "\"\r\n    },\r\n    \"spec\": {\r\n        \"selector\": {\r\n            \"matchLabels\": {\r\n                \"app\": \"karel-deployment-" + server_id + "\"\r\n            }\r\n        },\r\n        \"replicas\": 1,\r\n        \"template\": {\r\n            \"metadata\": {\r\n                \"labels\": {\r\n                    \"app\": \"karel-deployment-" + server_id + \
        "\"\r\n                }\r\n            },\r\n            \"spec\": {\r\n                \"containers\": [\r\n                    {\r\n                        \"name\": \"karel-deployment-" + server_id + "\",\r\n                        \"image\": \"" + image_name + "\",\r\n                        \"imagePullPolicy\": \"Always\",\r\n                        \"ports\": [\r\n                            {\r\n                                \"containerPort\": 3000\r\n                            }\r\n                        ],\r\n                        \"resources\": {\r\n                            \"limits\": {\"memory\": \"600Mi\",\r\n                                        \"cpu\": 1\r\n                                        },\r\n                            \"requests\": {\r\n                                \"memory\": \"300Mi\",\r\n                                \"cpu\": \"500m\"\r\n                            }\r\n                        },\r\n                        \"volumeMounts\": [\r\n                            {\r\n                                \"name\": \"karel-master-data\",\r\n                                \"mountPath\": \"/data\"\r\n                            }\r\n                        ]\r\n                    }\r\n                ],\r\n                \"volumes\": [\r\n                    {\r\n                        \"name\": \"karel-master-data\",\r\n                        \"persistentVolumeClaim\": {\r\n                            \"claimName\": \"master-claim-" + server_id + "\"\r\n                        }\r\n                    }\r\n                ]\r\n            }\r\n        }\r\n    }\r\n}"
    headers = {'Content-type': 'application/json',
               'authorization': 'bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tMmM4dnMiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZGVmYXVsdCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6ImI2ZDMwOTdlLTk1MjYtNDQwZi05MTdkLTRkYmExMmYwM2JlNyIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZWZhdWx0OmRlZmF1bHQifQ.WuCzioQAqzUkeVH-NwjRPZk1usasVfCc3MS9W7sKVF7hYefmCM4PP1dGfIxeA9qVwDrg5Tmm9hzzqKTWym1sbUzlxvYUi0jac-cjWD9k8_g3IF7bW00b7w2jjJ3k5f0ogZyy4aGr0HLhJswencfElE-yOqTtB6AxWc-SReJ2Diq_M-LepUK5iEi9x7JXigBZ2JPa-PpYvDyG6167s9JJdklzHSNQIKV1i81qYyrkmSCqEbnerOU8EzaphCfibOsyyrJxqI_nbB-zoUscsbb8SPMnUozy6NonvOaO-8EZfQ_lyeLmB6KNMUwUFVLxHNUaFZs-R1LYztM8A5HVeD6dkw'}
    url = 'https://192.168.28.60:6443/apis/apps/v1/namespaces/kube-karel-cloud/deployments/karel-deployment-' + \
        str(server_id) + '/'
    r = requests.put(url, data=payload,
                     headers=headers, verify=False)

    if not r.status_code == 200:
        raise Exception(
            "start_kuber_server() failed with status code: {}".format(r.status_code))

    wait_for_pod_start(server_id)


def update_server_internal_status(server_id, status):
    Server.objects.filter(idstr=server_id).update(
        status=status
    )


def validate_action_for(server_object, action, server_type_prefix):
    """
    docstring
    """
    dep = kuber.find_deployment(
        server_object.subscription.idstr, server_object.idstr)
    if not dep:
        raise Exception("Cannot apply action <{}>'. Deployment <{}> not found".format(
            action, "{}-d-{}".format(server_type_prefix, server_object.idstr)))
    if dep.spec.replicas == 1 and action in ['start']:
        raise Exception(
            "Cannot <{}> server. Its already running.".format(action))
    if dep.spec.replicas == 0 and action in ['stop', 'restart']:
        raise Exception(
            "Cannot <{}> server. Its not running.".format(action))

    logger.debug("Yes! we can apply action <{}> to {}-d-{}".format(action,
                                                                   server_type_prefix, server_object.idstr))


@shared_task
def cloud_post_control_server(server_ids, action, server_type):
    logger.debug("Here @ cloud_post_control_server()")
    for server_id in server_ids:
        _, idstr = server_id.split("-")
        server_object = Server.objects.get(idstr=idstr)
        try:
            logger.debug("Server Id: {}, Server Type: {}, idstr: {}".format(
                server_id, server_type, idstr))
            Server.objects.filter(pk=server_object.pk).update(
                operation='command')
            server_type_prefix = "ipg" if 'ipg' in server_object.server_type.name.lower() else "webcm"
            validate_action_for(server_object, action, server_type_prefix)
            if action == 'stop':
                try:
                    logger.debug("'stop' command called")
                    server_stopping(idstr, server_object.server_type.name)
                    kuber.rescale_deployment(
                        server_object.subscription.idstr, server_object.idstr, 0, server_type_prefix)
                    wait_for_pod_stop(idstr)
                    server_inactive(idstr, server_object.server_type.name)
                except Exception as e:
                    logger.debug("Error @ stop command")
                    logger.debug(e)
            elif action == 'start':
                try:
                    logger.debug("'start' command called")
                    server_starting(idstr, server_object.server_type.name)
                    kuber.rescale_deployment(
                        server_object.subscription.idstr, server_object.idstr, 1, server_type_prefix)
                    wait_for_pod_start(idstr)
                    server_active(idstr, server_object.server_type.name)
                except Exception as e:
                    logger.debug("Error @ start command")
                    logger.debug(str(e))
            elif action == 'restart':
                try:
                    logger.debug("'restart' command called!")
                    server_stopping(idstr, server_object.server_type.name)
                    kuber.rescale_deployment(
                        server_object.subscription.idstr, server_object.idstr, 0, server_type_prefix)
                    wait_for_pod_stop(server_object.idstr)
                except Exception as e:
                    logger.debug(
                        "Error @ restart command (stopping phase)")
                    logger.debug(str(e))
                    # Reset to original state if error
                try:
                    server_starting(idstr, server_object.server_type.name)
                    kuber.rescale_deployment(
                        server_object.subscription.idstr, server_object.idstr, 1, server_type_prefix)
                    wait_for_pod_start(idstr)
                    server_active(idstr, server_object.server_type.name)
                except Exception as e:
                    logger.debug(
                        "Error @ restart command (starting phase)")
                    logger.debug(str(e))
        except Exception as e:
            logger.error(e)
        finally:
            Server.objects.filter(pk=server_object.pk).update(
                operation='none')


@ shared_task
def cloud_initialized():
    logger.debug("tasks::cloud_initialized() called!")
    payload = "{\n        \"subscription\": \"" + str(needed_id) + "\",\n        \"service\": \"Ipg\",\n        \"servers\": {\n                \"IpgServer\": {\n                        \"cpu\": \"1\",\n                        \"ram\": \"600Mi\",\n                        \"disc\": \"2Gi\",\n                        \"widea_address\": \"www.kareldeployment.com:32370/" + str(gloval_IpgServer_server_id) + "\",\n                        \"local_ip\": \"" + str(global_clusterip) + "\",\n                        \"internal_ip\": \"" + str(global_ip_address) + ":" + str(global_port) + "\",\n                        \"external_ip\": \"" + str(global_ip_address) + ":" + str(global_port) + "\",\n                        \"server_name\": \"karel-deployment-" + str(gloval_IpgServer_server_id) + "\",\n                        \"server_id\": \"" + str(
        gloval_IpgServer_server_id) + "\",\n                        \"state\": \"1\",\n                        \"fqdn\": \"www.kareldeployment.com:32370/" + str(gloval_IpgServer_server_id) + "\"\n                },\n                \"WebcmServer\": {\n                        \"address\": \"www.kareldeployment.com:32370/" + str(global_WebcmServer_server_id) + "\",\n                        \"local_ip\": \"" + str(global_clusterip) + "\",\n                        \"internal_ip\": \"" + str(global_ip_address) + ":" + str(global_port) + "\",\n                        \"server_name\": \"karel-deployment-" + str(global_WebcmServer_server_id) + "\",\n                        \"server_id\": \"" + str(global_WebcmServer_server_id) + "\",\n                        \"state\": \"1\",\n                        \"fqdn\": \"www.kareldeployment.com:32370/" + str(global_WebcmServer_server_id) + "\"\n                }\n        }\n}"
    headers = {'Content-type': 'application/json'}
    url = 'https://byp.karel.cloud/byp/updateservicedetail/'
    r = requests.post(url, data=payload, headers=headers, verify=False)


@ shared_task
def cloud_check_server_availability():
    try:
        for server_obj in Server.objects.filter(oncommand=False).exclude(subscription__state='Initializing'):
            pod_ip, host_ip, namespace, pod_name, pod = kuber.find_pod(
                server_obj.idstr)

            # If pod not exists (not running) or pod is one of the failed states but status is Active
            if (not pod or pod.status.phase in ["Failed", "Unknown", "Succeeded"]) and server_obj.status == "Active":
                logger.debug(
                    "Pod {} is now inactive.".format(server_obj.idstr))
                Server.objects.filter(
                    idstr=server_obj.idstr).update(status='Inactive')
                server_inactive(server_obj.idstr, server_obj.server_type.name)

            # If pod exists (running) but status is Inactive
            if pod and server_obj.status == "Inactive":
                logger.debug(
                    "Pod {} is Running.".format(server_obj.idstr))
                Server.objects.filter(
                    idstr=server_obj.idstr).update(status='Active')
                server_active(server_obj.idstr, server_obj.server_type.name)

    except Exception as e:
        logger.debug("Failure @ cloud_check_server_availability()")
        logger.debug("Reason: {}".format(str(e)))


@ shared_task
def check_expiry():
    expired_subs = Subscription.objects.filter(
        end_date__lt=timezone.now(),
        expiration_processed=False
    )

    for sub in expired_subs:
        Subscription.objects.filter(pk=sub.pk).update(
            expiration_processed=True
        )

        logger.debug("Subscription '{}' has expired!".format(sub.subscription))
        for server in sub.server_set.all():
            try:
                stop_kuber_server(server.idstr, server.server_type.name)
                server_inactive(server.idstr, server.server_type.name)
                update_server_internal_status(server.idstr, "Inactive")
            except Exception as e:
                logger.error(e)


@shared_task
def test_celery(pause):
    print("you sent: ")
    print(" ".join([str(p) for p in pause]))
    print("Hellow from Celery!! Im running in background.!")
    print("Pausing {} seconds".format(pause[0]))
    time.sleep(pause)
    print("Done.!")


@shared_task
def update_ip_pool(static_pool, host):
    """
    docstring
    """
    print("@update_ip_pool")
    ip_pattern = re.compile(r'\d+\.\d+\.\d+\.\d')
    match = ip_pattern.search(host)
    aa,bb = static_pool.split('/')

    for ip in ipaddress.ip_network(static_pool):
        ip_str = str(ip)
        if ip_str.endswith(".1") or ip_str==aa:
            continue
        if match and match.group(0)==ip_str:
            continue

        UsedIp.objects.get_or_create(
            ip_address=ip_str, defaults={"used": False})
