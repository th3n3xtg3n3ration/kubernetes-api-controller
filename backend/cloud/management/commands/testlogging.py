from django.core.management.base import BaseCommand, CommandError
import logging

logger = logging.getLogger("cloud")


class Command(BaseCommand):
    help = 'Test Logging'

    def add_arguments(self, parser):
        parser.add_argument('message', type=str)
        parser.add_argument('--level', default='debug')

    def handle(self, *args, **options):
        if options['level'] == 'debug':
            logger.debug(options['message'])
            return
        if options['level'] == 'error':
            logger.error(options['message'])
            return

        logger.info(options['message'])
