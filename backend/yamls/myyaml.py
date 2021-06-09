from argparse import ArgumentParser
import re
import os
from django.conf import settings


def display_placeholders(filename):
    """
    docstring
    """
    pass


def create_ipg_deployment(deployment_id, namespace_id, static_ip):
    """
    docstring
    """
    yaml_path = os.path.join(settings.BASE_DIR, "yamls",
                             "creating-deployment-for-ipg-server.yaml")

    with open(yaml_path, 'rt') as fp:
        content = fp.read()
        return content.replace("<namespace-id>", namespace_id).replace(
            "<deployment-id>", deployment_id).replace("<static-ip-address>", static_ip)


def create_ipg_ingress(deployment_id, namespace_id):
    """
    docstring
    """
    yaml_path = os.path.join(settings.BASE_DIR, "yamls",
                             "creating-ingress-for-ipg-server.yaml")

    with open(yaml_path, 'rt') as fp:
        content = fp.read()
        return content.replace("<namespace-id>", namespace_id).replace(
            "<deployment-id>", deployment_id)


def create_namespace(namespace_id):
    """
    docstring
    """
    yaml_path = os.path.join(settings.BASE_DIR, "yamls",
                             "creating-namespace.yaml")

    with open(yaml_path, 'rt') as fp:
        content = fp.read()
        return content.replace("<namespace-id>", namespace_id)


def create_network_policy(namespace_id):
    """
    docstring
    """
    yaml_path = os.path.join(settings.BASE_DIR, "yamls",
                             "creating-network-policy.yaml")

    with open(yaml_path, 'rt') as fp:
        content = fp.read()
        return content.replace("<namespace-id>", namespace_id)


def create_ipg_pvc(deployment_id, namespace_id):
    """
    docstring
    """
    yaml_path = os.path.join(settings.BASE_DIR, "yamls",
                             "creating-pvc-for-ipg-server.yaml")

    with open(yaml_path, 'rt') as fp:
        content = fp.read()
        return content.replace("<namespace-id>", namespace_id).replace(
            "<deployment-id>", deployment_id)


def create_ipg_service(deployment_id, namespace_id):
    """
    docstring
    """
    yaml_path = os.path.join(settings.BASE_DIR, "yamls",
                             "creating-service-for-ipg-server.yaml")

    with open(yaml_path, 'rt') as fp:
        content = fp.read()
        return content.replace("<namespace-id>", namespace_id).replace(
            "<deployment-id>", deployment_id)

# ===========================================================================================


def create_webcam_service(deployment_id, namespace_id):
    """
    docstring
    """
    yaml_path = os.path.join(settings.BASE_DIR, "yamls",
                             "creating-service-for-webcm-server.yaml")

    with open(yaml_path, 'rt') as fp:
        content = fp.read()
        return content.replace("<namespace-id>", namespace_id).replace(
            "<deployment-id>", deployment_id)


def create_webcam_pvc(deployment_id, namespace_id):
    """
    docstring
    """
    yaml_path = os.path.join(settings.BASE_DIR, "yamls",
                             "creating-pvc-for-webcm-server.yaml")

    with open(yaml_path, 'rt') as fp:
        content = fp.read()
        return content.replace("<namespace-id>", namespace_id).replace(
            "<deployment-id>", deployment_id)


def create_webcam_deployment(deployment_id, namespace_id, static_ip):
    """
    docstring
    """
    yaml_path = os.path.join(settings.BASE_DIR, "yamls",
                             "creating-deployment-for-webcm-server.yaml")

    with open(yaml_path, 'rt') as fp:
        content = fp.read()
        return content.replace("<namespace-id>", namespace_id).replace(
            "<deployment-id>", deployment_id).replace("<static-ip-address>", static_ip)


def create_webcam_ingress(deployment_id, namespace_id):
    """
    docstring
    """
    yaml_path = os.path.join(settings.BASE_DIR, "yamls",
                             "creating-ingress-for-webcm-server.yaml")

    with open(yaml_path, 'rt') as fp:
        content = fp.read()
        return content.replace("<namespace-id>", namespace_id).replace(
            "<deployment-id>", deployment_id)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--dvariables")

    args = parser.parse_args()

    if args.dvariables:
        with open(args.dvariables, 'rt') as fp:
            rgx = re.compile(r'<.+?>')
            matches = rgx.findall(fp.read())
            for match in set(matches):
                print(match)
