from django.core.management.base import BaseCommand
from watergunwars.models import UserProfile
from datetime import datetime, date, time
from django.utils import timezone

class Command(BaseCommand):
    help = 'Eliminates agents who have passed their target due date'

    def handle(self, *args, **options):
        # dt_now = timezone.make_aware(datetime.combine(date.today(), time.min))
        # if UserProfile.active_agents.count() > 2:
        #     for agent in UserProfile.active_agents.exclude(date_target_due=None).filter(date_target_due__lte = dt_now):
        #         agent.status_dead = True
        #         agent.status_dead_confirmed = True
        #         agent.save()
        #         agent.eliminate_basic()
        return