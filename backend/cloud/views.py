from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import BasicAuthentication
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.utils import json
import requests
import time
import uuid
import random
import socket
import struct
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from logging import getLogger
from cloud.tasks import handle_post_subscription, cloud_post_control_server, \
    cloud_initialized, send_broken_subscription
from .serializers import SubscriptionCreateSerializer, ServerStatusSerializer, ChangeServerSerializer, \
    UpdateServiceSerializer, GetbrokenSubscriptionsSerializer
from .models import *
from common.serializers import serialize_subscription, server_active, server_inactive, server_starting, server_stopping
from django.conf import settings
import os
import logging
import pytz
from django.utils import timezone
import ipaddress
from cloud import kuber

gloval_IpgServer_server_id = global_clusterip = global_ip_address = global_port = global_WebcmServer_server_id = needed_id = 0
logger = getLogger(__name__)

# FORMAT = '%(asctime)-15s  %(message)s'
# LOG_FILENAME = os.path.join(settings.BASE_DIR, 'debug', 'debug.log')
# logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG, format=FORMAT)


tz = pytz.timezone("Europe/Istanbul")


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


def write2file(fname, content):
    with open(os.path.join(settings.BASE_DIR, 'debug', fname), 'wt') as fp:
        fp.write(content)


class SubscriptionCreateView(GenericAPIView):
    serializer_class = SubscriptionCreateSerializer

    def post(self, request):
        logger.debug("SubscriptionCreateView:post() called!")
        try:
            versions = kuber.get_api_versions()
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            subscriptions = serializer.data.get('subscriptions')

            if not subscriptions:
                return Response(
                    {
                        "result": False,
                        "Message": "Empty subscription"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not versions or not versions.versions:
                # tasks.fix
                send_broken_subscription.apply_async(
                    (subscriptions[0]['subscription'], "IPG"), countdown=4)
                return Response(
                    {
                        "result": True,
                        "Message": "Service Created successfully and Server Created Request sent to BYP"
                    },
                    status=status.HTTP_200_OK
                )

            created_subscription_ids = list()
            updated_subscription_ids = list()

            for subscription in subscriptions:
                customer = subscription['customer']
                start_date = subscription['start_date']
                end_date = tz.localize(timezone.datetime.strptime(
                    subscription['end_date'], "%Y-%m-%d"))  # str

                if timezone.now().astimezone(tz).date() >= end_date.date():
                    logger.error(
                        "Selected 'end_date' := {} for Subscription {} is too close or past the current date/time...".format(
                            end_date, subscription['subscription']))
                    send_broken_subscription.apply_async(
                        (subscription,), countdown=1)

                    logger.error("'End Date' already passed.")
                    return Response(
                        {
                            "result": False,
                            "Message": "'End Date' already passed."
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                term_subscription = subscription['term_subscription']
                service_type = subscription['service_type']
                subscription_str = subscription['subscription']
                service_datas = subscription.get('service_data')

                if not service_datas:
                    logger.error("No 'service_datas' found")
                    return Response(
                        {
                            "result": False,
                            "Message": "No 'service_datas' found"
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                server_names = service_datas.get('servers')
                if not server_names:
                    logger.error("No 'servers' found")
                    return Response(
                        {
                            "result": False,
                            "Message": "No 'servers' found"
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

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

            handle_post_subscription.apply_async(
                (created_subscription_ids, updated_subscription_ids), countdown=3)

            logger.debug(
                "Service Created successfully and Server Created Request sent to BYP")

            return Response(
                {
                    "result": True,
                    "Message": "Service Created successfully and Server Created Request sent to BYP"
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {
                    "result": False,
                    "Message": "Failed to create subscription! with error '{}'".format(str(e))
                },
                status=status.HTTP_400_BAD_REQUEST
            )


# class SubscriptionCreateView(GenericAPIView):
#     serializer_class = SubscriptionCreateSerializer

#     def post(self, request):
#         logger.debug("SubscriptionCreateView:post() called!")
#         try:
#             serializer = self.get_serializer(data=request.data)
#             serializer.is_valid(raise_exception=True)

#             subscriptions = serializer.data.get('subscriptions')
#             subscription_ids = []
#             if not subscriptions:
#                 return Response(
#                     {
#                         "result": False,
#                         "Message": "Empty subscription"
#                     },
#                     status=status.HTTP_400_BAD_REQUEST
#                 )

#             for subscription in subscriptions:
#                 customer = subscription['customer']
#                 start_date = subscription['start_date']
#                 end_date = tz.localize(timezone.datetime.strptime(
#                     subscription['end_date'], "%Y-%m-%d"))  # str

#                 if timezone.now().astimezone(tz).date() >= end_date.date():
#                     logger.debug(
#                         "Selected 'end_date' := {} for Subscription {} is too close or past the current date/time...".format(
#                             end_date, subscription['subscription']))
#                     send_broken_subscription.apply_async(
#                         (subscription,), countdown=1)

#                     return Response(
#                         {
#                             "result": False,
#                             "Message": "'End Date' already passed."
#                         },
#                         status=status.HTTP_400_BAD_REQUEST
#                     )

#                 term_subscription = subscription['term_subscription']
#                 service_type = subscription['service_type']
#                 subscription_str = subscription['subscription']
#                 service_datas = subscription.get('service_data')

#                 if not service_datas:
#                     continue

#                 subscription_a, created = Subscription.objects.update_or_create(
#                     customer=customer,
#                     subscription=subscription_str,
#                     defaults={
#                         "start_date": start_date,
#                         "end_date": end_date,
#                         "term_subscription": term_subscription,
#                         "service_type": service_type,
#                         "state": "Initializing",
#                         "server_name_prefix": str(
#                             service_datas['server_name_prefix']),
#                         "package": str(service_datas['package']),
#                         "trunk_service_provider": str(
#                             service_datas['trunk_service_provider']),
#                         "extra_call_record_package": str(
#                             service_datas['extra_call_record_package']),
#                         "demo": str(service_datas['demo']),
#                         "extra_duration_package": str(
#                             service_datas['extra_duration_package']),
#                         "exp20_dss_module_ip1141": str(
#                             service_datas['exp20_dss_module_ip1141']),
#                         "exp40_dss_module_ip136_ip138": str(
#                             service_datas['exp40_dss_module_ip136_ip138']),
#                         "ip1111_poe_no_adapter": str(
#                             service_datas['ip1111_poe_no_adapter']),
#                         "ip1131_poe_gigabit_no_adapter": str(
#                             service_datas['ip1131_poe_gigabit_no_adapter']),
#                         "ip1141_poe_no_adapter": str(
#                             service_datas['ip1141_poe_no_adapter']),
#                         "ip1141_ip131_ip132_adapter": str(
#                             service_datas['ip1141_ip131_ip132_adapter']),
#                         "ip1181_ip136_ip138_adapter": str(
#                             service_datas['ip1181_ip136_ip138_adapter']),
#                         "ip1211_w_adapter": str(
#                             service_datas['ip1211_w_adapter']),
#                         "ip1211_poe_no_adapter": str(
#                             service_datas['ip1211_poe_no_adapter']),
#                         "ip1211_ip1211p_ip1111_ip1131_adapter": str(
#                             service_datas['ip1211_ip1211p_ip1111_ip1131_adapter']),
#                         "ip131_poe_no_adapter": str(
#                             service_datas['ip131_poe_no_adapter']),
#                         "ip132_gigabit_no_adapter": str(
#                             service_datas['ip132_gigabit_no_adapter']),
#                         "ip136_poe_no_adapter": str(
#                             service_datas['ip136_poe_no_adapter']),
#                         "ip138_poe_no_adapter": str(
#                             service_datas['ip138_poe_no_adapter']),
#                         "karel_mobile": str(service_datas['karel_mobile']),
#                         "vp128": str(service_datas['vp128']),
#                         "yt510": str(service_datas['yt510']),
#                         "yt520": str(service_datas['yt520']),
#                         "yt530": str(service_datas['yt530']),
#                         "expiration_processed": False
#                     }
#                 )

#                 subscription_ids.append(subscription_a.id)

#                 server_names = service_datas.get('servers')

#                 if not server_names:
#                     continue

#                 for server_name in server_names:
#                     srvtype, _ = ServerType.objects.get_or_create(
#                         name=server_name)
#                     server_obj, _ = Server.objects.get_or_create(
#                         subscription=subscription_a,
#                         server_type=srvtype,
#                         defaults={
#                             'action': 'Stop',
#                             'idstr': 'd-' + uuid.uuid4().hex[:8]
#                         }
#                     )

#                     if server_obj.server_type.name == "IpgServer":
#                         ipg_server, server_created = IpgServer.objects.get_or_create(
#                             server_name=server_name, server=server_obj)
#                     elif server_obj.server_type.name == "WebcmServer":
#                         webcam_server, server_created = WebcmServer.objects.get_or_create(
#                             server_name=server_name, server=server_obj)

#             cloud_post_subscription_create.apply_async(
#                 (subscription_ids,), countdown=3)

#             return Response(
#                 {
#                     "result": True,
#                     "Message": "Service Created successfully and Server Created Request sent to BYP"
#                 },
#                 status=status.HTTP_200_OK
#             )

#         except Exception as e:
#             logger.error(e)
#             raise e


class SubscriptionDeleteView(GenericAPIView):

    def delete(self, request, pk):
        is_subscription = Subscription.objects.filter(subscription=pk).exists()
        if is_subscription:
            Subscription.objects.filter(subscription=pk).delete()
            return Response(
                {
                    "result": True,
                    "errorMsg": "Removed successfully."
                },
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {
                    "result": False,
                    "errorMsg": "Invalid subscription."
                },
                status=status.HTTP_200_OK
            )


class SubscriptionDetailView(GenericAPIView):

    def get(self, request, pk):
        try:
            logger.debug("SubscriptionDetailView::get() was called!")
            subscription = Subscription.objects.get(id=pk)
            return Response(
                {
                    "result": True,
                    "subscription": {
                        **serialize_subscription(subscription)
                    }

                },
                status=status.HTTP_200_OK
            )
        except ObjectDoesNotExist:
            return Response(
                {
                    "result": False,
                    "errorMsg": "Invalid subscription."
                },
                status=status.HTTP_200_OK
            )


class ControlServerView(GenericAPIView):
    serializer_class = ServerStatusSerializer

    def post(self, request):
        try:
            logger.debug("@ControlServerView::post()")
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            server_ids = serializer.data.get('server_ids')
            action = serializer.data.get('action')
            server_type = serializer.data.get('server_type')

            cloud_post_control_server.apply_async(
                (server_ids, action, server_type), countdown=3)

            return Response(
                {
                    "result": True,
                    "subscriptions": {
                        "msg": "server status changed successfully."
                    }
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(e)


class UpdateServiceDetail(GenericAPIView):
    serializer_class = UpdateServiceSerializer

    def post(self, request):

        logger.debug("UpdateServiceDetail::post() was called!")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subscription = serializer.validated_data['subscription']
        print(subscription.id)
        subscription_list = []

        servers = request.data.get('servers')
        ipgserver_input = servers['IpgServer']
        ipgserver_object_id = Server.objects.filter(
            subscription=subscription).values_list('id', flat=True)[0]
        ipgserver = IpgServer.objects.get(server=ipgserver_object_id)
        ipgserver.cpu = ipgserver_input['cpu']
        ipgserver.ram = ipgserver_input['ram']
        ipgserver.disc = ipgserver_input['disc']
        ipgserver.widea_address = ipgserver_input['widea_address']
        ipgserver.local_ip = ipgserver_input['local_ip']
        ipgserver.internal_ip = ipgserver_input['internal_ip']
        ipgserver.external_ip = ipgserver_input['external_ip']
        ipgserver.server_name = ipgserver_input['server_name']
        ipgserver.state = ipgserver_input['state']
        ipgserver.fqdn = ipgserver_input['fqdn']
        ipgserver.save()

        webcmServer_input = servers['WebcmServer']
        webcmserver_object_id = Server.objects.filter(
            subscription=subscription).values_list('id', flat=True)[1]
        webcmserver = WebcmServer.objects.get(server=webcmserver_object_id)
        webcmserver.address = webcmServer_input['address']
        webcmserver.local_ip = webcmServer_input['local_ip']
        webcmserver.internal_ip = webcmServer_input['internal_ip']
        webcmserver.server_name = webcmServer_input['server_name']
        webcmserver.state = webcmServer_input['state']
        webcmserver.fqdn = webcmServer_input['fqdn']
        webcmserver.save()

        return Response(
            {
                "result": True,
                "subscription": subscription.subscription,
                "service": "Ipg",
                "servers": {
                    "IpgServer": {
                        "cpu": ipgserver.cpu,
                        "ram": ipgserver.ram,
                        "disc": ipgserver.disc,
                        "widea_address": ipgserver.widea_address,
                        "local_ip": ipgserver.local_ip,
                        "internal_ip": ipgserver.internal_ip,
                        "external_ip": ipgserver.external_ip,
                        "server_name": ipgserver.server_name,
                        "server_id": ipgserver.server.id,
                        "state": ipgserver.state,
                        "fqdn": ipgserver.fqdn,
                    },
                    "WebcmServer": {
                        "address": webcmserver.address,
                        "local_ip": webcmserver.local_ip,
                        "internal_ip": webcmserver.internal_ip,
                        "server_name": webcmserver.server_name,
                        "server_id": webcmserver.server.id,
                        "state": webcmserver.state,
                        "fqdn": webcmserver.fqdn,
                    }
                }

            },
            status=status.HTTP_200_OK
        )


class ChangeServerView(GenericAPIView):
    serializer_class = ChangeServerSerializer

    def post(self, request):
        logger.debug("@ChangeServerView::post()")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        server = serializer.validated_data['server']
        server.status = serializer.data.get('status')
        server.server_type = serializer.validated_data['server_type']
        server.save()

        return Response(
            {
                "result": True,
                "subscriptions": {
                    "status": server.status,
                    "server_id": server.id,
                    "server_type": server.server_type.name,
                }
            },
            status=status.HTTP_200_OK
        )


class GetBrokenSubscriptionsView(GenericAPIView):
    serializer_class = GetbrokenSubscriptionsSerializer

    def post(self, request):
        logger.debug("@GetBrokenSubscriptionsView::post()")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subscriptions = serializer.data.get('subscriptions')
        subscription_list = []
        if subscriptions:
            for subscription in subscriptions:
                subscription_a = Subscription(
                    customer=subscription['customer'],
                    start_date=subscription['start_date'],
                    end_date=subscription['end_date'],
                    term_subscription=subscription['term_subscription'],
                    service_type=subscription['service_type'],
                    subscription=subscription['subscription'],
                    server_name_prefix=subscription['server_name_prefix'],
                    package=subscription['package'],
                    trunk_service_provider=subscription['trunk_service_provider'],
                    extra_call_record_package=subscription['extra_call_record_package'],
                    demo=subscription['demo'],
                    extra_duration_package=subscription['extra_duration_package'],
                    state="Initializing"
                )
                subscription_a.save()
                servers = subscription['servers']

                if servers:
                    for server in servers:
                        server = Server(
                            server_type=ServerType.objects.get(name=server),
                            action='stop',
                            subscription=subscription_a
                        )
                        server.save()
                        if server.server_type.name == "IpgServer":
                            ipg = IpgServer()
                            ipg.server = server
                            ipg.save()
                        elif server.server_type.name == "WebcmServer":
                            webcm = WebcmServer()
                            webcm.server = server
                            webcm.save()
                        Servers.append(server.server_type.name)
                subscription_list.append({
                    **serialize_subscription(subscription_a),
                    "servers": Servers
                })

        return Response(
            {
                "result": True,
                "subscriptions": subscription_list

            },
            status=status.HTTP_200_OK
        )


class EverySoOften(GenericAPIView):

    def post(self, request):
        logger.debug("EverySoOften::post() was called!")
        # cloud_every_so_often()
        return Response({})

        # while True:
        #     servers = Server.objects.filter(status='Active')
        #     for server in servers:
        #         server_id = server.idstr
        #         server_type = server.server_type.name
        #         # Check server state
        #         headers = {'Content-type': 'application/json',
        #                    'authorization': 'bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tMmM4dnMiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZGVmYXVsdCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6ImI2ZDMwOTdlLTk1MjYtNDQwZi05MTdkLTRkYmExMmYwM2JlNyIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZWZhdWx0OmRlZmF1bHQifQ.WuCzioQAqzUkeVH-NwjRPZk1usasVfCc3MS9W7sKVF7hYefmCM4PP1dGfIxeA9qVwDrg5Tmm9hzzqKTWym1sbUzlxvYUi0jac-cjWD9k8_g3IF7bW00b7w2jjJ3k5f0ogZyy4aGr0HLhJswencfElE-yOqTtB6AxWc-SReJ2Diq_M-LepUK5iEi9x7JXigBZ2JPa-PpYvDyG6167s9JJdklzHSNQIKV1i81qYyrkmSCqEbnerOU8EzaphCfibOsyyrJxqI_nbB-zoUscsbb8SPMnUozy6NonvOaO-8EZfQ_lyeLmB6KNMUwUFVLxHNUaFZs-R1LYztM8A5HVeD6dkw'}
        #         url = 'https://192.168.28.60:6443/apis/apps/v1/namespaces/kube-karel-cloud/deployments/karel-deployment-' + \
        #             str(server_id) + '/'
        #         r = requests.get(url, headers=headers, verify=False)
        #         text = json.loads(r.text)
        #         status_code = r.status_code

        #         if status_code == 200:
        #             # parse response from cluster
        #             try:
        #                 active = text['status']['availableReplicas']
        #                 if active == 1:
        #                     server_active(server_id, server_type)
        #             except:
        #                 inactive = text['status']['unavailableReplicas']
        #                 replicas = text['spec']['replicas']
        #                 if replicas == 0 or inactive == 1:
        #                     server_inactive(server_id, server_type)
        #         else:
        #             # inactive to byp
        #             server_inactive(server_id, server_type)

        #     try:
        #         servers = Server.onjects.filter(status='Inactive')
        #         for server in servers:
        #             server_id = server.idstr
        #             server_type = server.server_type.name
        #             # Check server state
        #             headers = {'Content-type': 'application/json',
        #                        'authorization': 'bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tMmM4dnMiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZGVmYXVsdCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6ImI2ZDMwOTdlLTk1MjYtNDQwZi05MTdkLTRkYmExMmYwM2JlNyIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZWZhdWx0OmRlZmF1bHQifQ.WuCzioQAqzUkeVH-NwjRPZk1usasVfCc3MS9W7sKVF7hYefmCM4PP1dGfIxeA9qVwDrg5Tmm9hzzqKTWym1sbUzlxvYUi0jac-cjWD9k8_g3IF7bW00b7w2jjJ3k5f0ogZyy4aGr0HLhJswencfElE-yOqTtB6AxWc-SReJ2Diq_M-LepUK5iEi9x7JXigBZ2JPa-PpYvDyG6167s9JJdklzHSNQIKV1i81qYyrkmSCqEbnerOU8EzaphCfibOsyyrJxqI_nbB-zoUscsbb8SPMnUozy6NonvOaO-8EZfQ_lyeLmB6KNMUwUFVLxHNUaFZs-R1LYztM8A5HVeD6dkw'}
        #             url = 'https://192.168.28.60:6443/apis/apps/v1/namespaces/kube-karel-cloud/deployments/karel-deployment-' + \
        #                 str(server_id) + '/'
        #             r = requests.get(url, headers=headers, verify=False)
        #             text = json.loads(r.text)
        #             status_code = r.status_code

        #             if status_code == 200:
        #                 # parse response from cluster
        #                 try:
        #                     active = text['status']['availableReplicas']
        #                     if active == 1:
        #                         server_active(server_id, server_type)
        #                 except:
        #                     inactive = text['status']['unavailableReplicas']
        #                     replicas = text['spec']['replicas']
        #                     if replicas == 0 or inactive == 1:
        #                         server_inactive(server_id, server_type)
        #             else:
        #                 # inactive to byp
        #                 server_inactive(server_id, server_type)
        #         time.sleep(2)
        #     except ObjectDoesNotExist:
        #         pass
        # return True


# @api_view(['post'])
# @authentication_classes([BasicAuthentication])
# def initialized(request):
#     logging.debug("Initialized::post() called!")
#     cloud_initialized()
#     return Response()

class Initialized(GenericAPIView):

    def post(self, request):
        logger.debug("Initialized::post() called!")
        cloud_initialized.delay()
        return Response({})
        # return Response({"message": "No longer need to call this Enpoint as it will now run repeatedly in the background."})
        # while True:
        #     payload = "{\n        \"subscription\": \"" + str(needed_id) + "\",\n        \"service\": \"Ipg\",\n        \"servers\": {\n                \"IpgServer\": {\n                        \"cpu\": \"1\",\n                        \"ram\": \"600Mi\",\n                        \"disc\": \"2Gi\",\n                        \"widea_address\": \"www.kareldeployment.com:32370/" + str(gloval_IpgServer_server_id) + "\",\n                        \"local_ip\": \"" + str(global_clusterip) + "\",\n                        \"internal_ip\": \"" + str(global_ip_address) + ":" + str(global_port) + "\",\n                        \"external_ip\": \"" + str(global_ip_address) + ":" + str(global_port) + "\",\n                        \"server_name\": \"karel-deployment-" + str(gloval_IpgServer_server_id) + "\",\n                        \"server_id\": \"" + str(
        #         gloval_IpgServer_server_id) + "\",\n                        \"state\": \"1\",\n                        \"fqdn\": \"www.kareldeployment.com:32370/" + str(gloval_IpgServer_server_id) + "\"\n                },\n                \"WebcmServer\": {\n                        \"address\": \"www.kareldeployment.com:32370/" + str(global_WebcmServer_server_id) + "\",\n                        \"local_ip\": \"" + str(global_clusterip) + "\",\n                        \"internal_ip\": \"" + str(global_ip_address) + ":" + str(global_port) + "\",\n                        \"server_name\": \"karel-deployment-" + str(global_WebcmServer_server_id) + "\",\n                        \"server_id\": \"" + str(global_WebcmServer_server_id) + "\",\n                        \"state\": \"1\",\n                        \"fqdn\": \"www.kareldeployment.com:32370/" + str(global_WebcmServer_server_id) + "\"\n                }\n        }\n}"
        #     headers = {'Content-type': 'application/json'}
        #     url = 'https://byp.karel.cloud/byp/updateservicedetail/'
        #     r = requests.post(url, data=payload, headers=headers, verify=False)
        #     time.sleep(1)
        # return True


@ csrf_exempt
def tasks(request):
    if request.method == 'POST':
        return _post_tasks(request)
    else:
        return JsonResponse({}, status=405)


def _post_tasks(request):
    # message = request.POST['message']
    # logging.debug('calling demo_task. message={0}'.format(message))
    # demo_task(repeat=300)
    return JsonResponse({}, status=302)
