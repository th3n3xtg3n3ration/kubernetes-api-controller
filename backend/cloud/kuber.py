import tempfile
from django.conf import settings
import logging
from kubernetes import client, config, utils
import kubernetes
import re
from cloud.models import *
from subprocess import Popen, PIPE
import os

logger = logging.getLogger(__name__)
# aToken = settings.KUBERNETES_API_TOKEN
# # Create a configuration object
# aConfiguration = client.Configuration()
# # Specify the endpoint of your Kube cluster
# aConfiguration.host = settings.KUBERNETES_REMOTE_HOST

# # Security part.
# # In this simple example we are not going to verify the SSL certificate of
# # the remote cluster (for simplicity reason)
# aConfiguration.verify_ssl = False
# # Nevertheless if you want to do it you can with these 2 parameters
# # configuration.verify_ssl=True
# # ssl_ca_cert is the filepath to the file that contains the certificate.
# # configuration.ssl_ca_cert="certificate"

# aConfiguration.api_key = {"authorization": "Bearer " + aToken}

# # Configs can be set in Configuration class directly or using helper utility
# # config.load_kube_config()

# aApiClient = client.ApiClient(aConfiguration)
# # Do calls
# v1 = client.CoreV1Api(aApiClient)
# api_instance = client.AppsV1Api(aApiClient)
# extapi = client.ExtensionsV1beta1Api(aApiClient)


def get_kuber_client():
    """
    docstring
    """
    cluster = Cluster.objects.first()
    if not cluster:
        logger.error("Cluster info not found")
        return

    aToken = cluster.token
    # Create a configuration object
    aConfiguration = client.Configuration()
    # Specify the endpoint of your Kube cluster
    aConfiguration.host = cluster.host

    # Security part.
    # In this simple example we are not going to verify the SSL certificate of
    # the remote cluster (for simplicity reason)
    aConfiguration.verify_ssl = False
    # Nevertheless if you want to do it you can with these 2 parameters
    # configuration.verify_ssl=True
    # ssl_ca_cert is the filepath to the file that contains the certificate.
    # configuration.ssl_ca_cert="certificate"

    aConfiguration.api_key = {"authorization": "Bearer " + aToken}

    # Configs can be set in Configuration class directly or using helper utility
    # config.load_kube_config()

    aApiClient = client.ApiClient(aConfiguration)
    return aApiClient


def apply_network_policy(yaml):
    """
    docstring
    """
    outfile = os.path.join(
        settings.BASE_DIR, "yamls", "create-network-policy.yaml")
    with open(outfile, "wt") as target:
        target.write(yaml)
        target.flush()

    with Popen(["/etc/kubernetes-cluster-config/calicoctl", "create", "-f", outfile], stdout=PIPE) as proc:
        response = proc.stdout.read().decode("utf-8")
        if 'fail' in response.lower():
            print(
                "=======================NETWORK POLICT YAML BODY==========================")
            print(yaml)
            print(
                "==================== END NETWORK POLICT YAML BODY========================")
        print(response)


def apply_template(yaml):
    """
    docstring
    """

    fd, path = tempfile.mkstemp()
    with open(fd, 'w') as f:
        f.write(yaml)
        f.flush()

        try:
            kuber = get_kuber_client()
            utils.create_from_yaml(kuber, path, True)
            print("Template Applied!")
        except Exception as e:
            logger.error(e)


def find_pvc(service_id):
    kclient = get_kuber_client()
    v1 = client.CoreV1Api(kclient)
    ret = v1.list_namespaced_persistent_volume_claim(
        'kube-karel-cloud', field_selector='metadata.name=master-claim-{}'.format(service_id))
    if ret and ret.items:
        return list(ret.items)


def list_deployments(idstr):
    """
    docstring
    """
    kclient = get_kuber_client()
    api_instance = client.AppsV1Api(kclient)

    ret = api_instance.list_namespaced_deployment(
        'n-{}'.format(idstr))
    return ret.items


def find_deployment(subscriptions_idstr, server_idstr):
    kclient = get_kuber_client()
    api_instance = client.AppsV1Api(kclient)

    namespace = "n-{}".format(subscriptions_idstr)

    ret = api_instance.list_namespaced_deployment(namespace)
    for item in ret.items:
        if server_idstr in item.metadata.name:
            return item


def delete_pvc(server_id):
    kclient = get_kuber_client()
    v1 = client.CoreV1Api(kclient)
    try:
        logger.debug("Deleting PVC master-claim-{}".format(server_id))
        v1.delete_namespaced_persistent_volume_claim(
            'master-claim-{}'.format(server_id), 'kube-karel-cloud')
    except Exception as e:
        logger.error(e)


def delete_service(server_id):
    kclient = get_kuber_client()
    v1 = client.CoreV1Api(kclient)
    try:
        logger.debug("Deleting Service karel-service-{}".format(server_id))
        v1.delete_namespaced_service(
            'karel-service-{}'.format(server_id), 'kube-karel-cloud')
    except Exception as e:
        logger.error(e)


def delete_ingress(server_id):
    kclient = get_kuber_client()
    ext_api = client.ExtensionsV1beta1Api(kclient)
    try:
        logger.debug("Deleting Ingress karel-ingress-{}".format(server_id))
        ext_api.delete_namespaced_ingress(
            'karel-ingress-{}'.format(server_id), 'kube-karel-cloud')
    except Exception as e:
        logger.error(e)


def delete_deployment(server_id):
    kclient = get_kuber_client()
    api_instance = client.AppsV1Api(kclient)

    try:
        logger.debug(
            "Deleting Deployment karel-deployment-{}".format(server_id))
        api_instance.delete_namespaced_deployment(
            'karel-deployment-{}'.format(server_id), 'kube-karel-cloud')
    except Exception as e:
        logger.error(e)


def list_pods(subscription_idstr):
    kclient = get_kuber_client()
    v1 = client.CoreV1Api(kclient)
    # karel-deployment-d-9427e340-5fcd949c44-p2w7r
    ret = v1.list_namespaced_pod(
        'n-{}'.format(subscription_idstr), watch=False)

    return ret.items


def find_service(subscription_idstr, server_idstr):
    kclient = get_kuber_client()
    v1 = client.CoreV1Api(kclient)
    ret = v1.list_namespaced_service(
        'n-{}'.format(subscription_idstr), watch=False)
    for i in ret.items:
        if server_idstr in i.metadata.name:
            #port = text['spec']['ports'][0]['nodePort']
            return i


def find_pod(subscription_idstr, server_idstr):
    kclient = get_kuber_client()
    v1 = client.CoreV1Api(kclient)
    # karel-deployment-d-9427e340-5fcd949c44-p2w7r
    ret = v1.list_namespaced_pod(
        'n-{}'.format(subscription_idstr), watch=False)

    for item in ret.items:
        if server_idstr in item.metadata.name:
            return item


def rescale_deployment(subscription_idstr, server_idstr, scale, server_type='ipg'):
    """
    docstring
    """
    logger.debug(
        "@rescale_deployment({},{},{})".format(subscription_idstr, server_idstr, scale))
    kclient = get_kuber_client()
    v1 = client.AppsV1Api(kclient)

    deployment_name = "{}-d-{}".format(server_type, server_idstr)
    namespace_name = "n-{}".format(subscription_idstr)
    logger.debug("deployment name: {}, namespace: {}".format(
        deployment_name, namespace_name))

    try:
        body = {
            "spec": {
                "replicas": scale
            }
        }
        logger.debug("Rescaling...")
        v1.patch_namespaced_deployment_scale(
            name=deployment_name, namespace=namespace_name, body=body)
    except Exception as e:
        logger.error(e)


def get_api_versions():
    """
    docstring
    """
    try:
        kclient = get_kuber_client()
        api_instance = client.CoreApi(kclient)
        return api_instance.get_api_versions()
    except:
        pass


def read_pod_status(sub_idstr, server_idstr):
    """
    docstring
    """
    pod = find_pod(sub_idstr, server_idstr)
    if not pod:
        return

    namespace = 'n-{}'.format(sub_idstr)
    kclient = get_kuber_client()
    api_instance = client.CoreV1Api(kclient)
    status = api_instance.read_namespaced_pod_status(
        pod.metadata.name, namespace)
    return status
