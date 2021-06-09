from django.core.management.base import BaseCommand, CommandError
from cloud.tasks import test_celery


class Command(BaseCommand):
    help = 'Test CElery'

    def add_arguments(self, parser):
        parser.add_argument('pause', type=int)

    def handle(self, *args, **options):
        pause = options['pause']
        test_celery.delay([pause, pause, pause, pause])
