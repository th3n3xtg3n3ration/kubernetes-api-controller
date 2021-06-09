from django.core.mail import send_mail
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from datetime import datetime, timedelta, date
import random
from datetime import datetime
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny


@api_view(["POST", "GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def testapiview(request):
    return Response({"message": "hey"})
