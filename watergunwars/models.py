import os
from urlparse import urlparse

from django.core.mail import send_mail, send_mass_mail
from twilio.rest import TwilioRestClient
from twilio.rest.resources import Connection
from twilio.rest.resources.connection import PROXY_TYPE_HTTP

proxy_url = os.environ.get("http_proxy")
host, port = urlparse(proxy_url).netloc.split(":")
Connection.set_proxy_info(host, int(port), proxy_type=PROXY_TYPE_HTTP)

from django.contrib.auth.models import User
from django.db import models
from django import forms
from django.forms import ModelForm
from django.contrib.admin.widgets import AdminDateWidget

from django.core.validators import RegexValidator

from datetime import datetime, date, time, timedelta
from django.utils import timezone

class ActiveUserManager(models.Manager):
    def get_queryset(self):
        return super(ActiveUserManager, self).get_queryset().filter(active=True)

class InactiveUserManager(models.Manager):
    def get_queryset(self):
        return super(InactiveUserManager, self).get_queryset().filter(active=False)

class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile', help_text="The User (object) that this UserProfile (object) is linked to. The username (codename) is shown.")
    phone_regex = RegexValidator(regex=r'^\d{10}$', message="Must be 10 digits long")
    phone_num = models.CharField('Phone Number', blank=True, max_length=10, validators=[phone_regex])

    active = models.BooleanField('Active', default=True, help_text="Default setting is true. Set to false to remove someone from participating in the war. Do not modify if war is in progress.")
    status_dead = models.BooleanField('Marked Dead', default=False, help_text="Automatically set to true when another player submits the elimination of this person.")
    status_dead_confirmed = models.BooleanField('Confirmed Dead', default=False, help_text="Automatically set to true when this person submits the elimination of himself.")
    date_of_death = models.DateTimeField('Date of Death', blank=True, null=True, help_text="Automatically set to the date and time that 'Dead' and 'Confirmed Dead' were both set to true.")

    killed_by_target = models.BooleanField('Killed by Target', default=False, help_text="Automatically set to true when this person's target submits the elimination of this person.")

    target = models.OneToOneField('self', related_name='attacker', blank=True, null=True, help_text="The UserProfile (object) that this person is assigned to eliminate.")
    date_target_assigned = models.DateTimeField('Date Target Assigned', blank=True, null=True, help_text="Default setting for time is 11:59 pm.")
    date_target_due = models.DateTimeField('Date Target Due', blank=True, null=True, help_text="Default setting is 'Date Target Assigned' + 1 week. Time setting has no effect as the website only checks for (and eliminates) late players every day at midnight.")

    kill_count = models.IntegerField('Kill Count', default=0, blank=True, help_text="Number of eliminations this person has earned (including those in self-defense)")

    agents = models.Manager()
    active_agents = ActiveUserManager()
    inactive_agents = InactiveUserManager()

    class Meta:
        get_latest_by = 'date_of_death'
        unique_together = ('user', 'phone_num')
        ordering = ['active', '-date_target_due', '-date_of_death']

    def __unicode__(self):
        return self.user.get_full_name()

    @property
    def dead(self):
        return self.status_dead and self.status_dead_confirmed

    def send_message_to_killed_target(self):
        war = War.objects.get(active=True)
        client = TwilioRestClient(war.twilio_account_sid, war.twilio_auth_token)

        if self.target.phone_num:
            client.messages.create(
            to= self.target.phone_num,
              from_= war.twilio_phone_num,
              body= "---- Water Gun Wars ---- Pending your confirmation: %s has submitted your elimination." % self,
            )
        if self.target.user.email:
            send_mail(
            'Water Gun Wars',
            'Pending your confirmation: %s has submitted your elimination.' % self,
            'chswgw@gmail.com',
            [self.target.user.email],
            fail_silently=True
            )

    def send_message_to_killed_attacker(self):
        war = War.objects.get(active=True)
        client = TwilioRestClient(war.twilio_account_sid, war.twilio_auth_token)

        if self.attacker.phone_num:
            client.messages.create(
            to= self.attacker.phone_num,
              from_= war.twilio_phone_num,
              body= "---- Water Gun Wars ---- Pending your confirmation: %s has submitted your elimination." % self,
            )
        if self.attacker.user.email:
            send_mail(
            'Water Gun Wars',
            'Pending your confirmation: %s has submitted your elimination.' % self,
            'chswgw@gmail.com',
            [self.attacker.user.email],
            fail_silently=True
            )

    def elimination_message(self):
        war = War.objects.get(active=True)
        client = TwilioRestClient(war.twilio_account_sid, war.twilio_auth_token)

        if self.phone_num:
            client.messages.create(
            to= self.phone_num,
          	from_= war.twilio_phone_num,
          	body= "---- Water Gun Wars ---- Elimination confirmed: %s (Agent %s)." % (self, self.user),
            )
        if self.user.email:
            send_mail(
            'Water Gun Wars',
            'Elimination confirmed: %s (Agent %s).' % (self, self.user),
            'chswgw@gmail.com',
            [self.user.email],
            fail_silently=True
            )

    def killed_target(self):
        self.target.status_dead = True
        self.target.save()

        if self.target.dead:
            self.kill_count += 1
            self.save()
            self.target.eliminate()
        else:
            self.send_message_to_killed_target()

    def killed_attacker(self):
        self.attacker.status_dead = True
        self.attacker.killed_by_target = True
        self.attacker.save()

        if self.attacker.dead:
            self.kill_count += 1
            self.save()
            self.attacker.eliminate()
        else:
            self.send_message_to_killed_attacker()

    def user_killed(self):
        self.status_dead_confirmed = True
        self.save()

        if self.dead:
            if self.killed_by_target:
                self.target.kill_count += 1
                self.target.save()
            else:
                self.attacker.kill_count += 1
                self.attacker.save()
            self.eliminate()

    def eliminate(self):
        if (self.target is not None):
            attacker = self.attacker
            target = self.target

            attacker.target = target
            attacker.date_target_assigned = timezone.make_aware(datetime.combine(date.today(), time.max))
            attacker.date_target_due = attacker.date_target_assigned + timedelta(weeks=1)

            self.target = None
            self.date_target_assigned = None
            self.date_target_due = None
            self.date_of_death = timezone.now()
            self.save()

            attacker.save()

            war = War.objects.get(active=True)
            war.num_dead = UserProfile.active_agents.filter(target=None).count()
            war.num_alive = UserProfile.active_agents.exclude(target=None).count()
            war.save()

            client = TwilioRestClient(war.twilio_account_sid, war.twilio_auth_token)

            if attacker.target == attacker:
                war = War.objects.get(active=True)
                war.end_date = date.today()

                war.first_place = attacker
                war.second_place = UserProfile.agents.latest('date_of_death')
                war.third_place = UserProfile.agents.exclude(date_of_death = war.second_place.date_of_death).latest('date_of_death')

                most_kills = UserProfile.active_agents.latest('kill_count').kill_count
                war.most_kills = UserProfile.active_agents.filter(kill_count=most_kills)

                war.active = False
                war.save()

                message_list = []

                for agent in UserProfile.active_agents.all():
                    if agent.phone_num:
                        client.messages.create(
                        to= agent.phone_num,
                      	from_= war.twilio_phone_num,
                      	body= "---- Water Gun Wars ---- The war is over! First place is awarded to... %s (Agent %s)! More info on website." % (war.first_place, war.first_place.user),
                        )
                    if agent.user.email:
                        message = (
                        'Water Gun Wars',
                        'The war is over! First place is awarded to... %s (Agent %s)! More info on website.' % (war.first_place, war.first_place.user),
                        'chswgw@gmail.com',
                        [agent.user.email],
                        )
                        message_list.append(message)

                send_mass_mail(message_list, fail_silently=True)

            else:
                if self.killed_by_target:
                    if attacker.target.phone_num:
                        client.messages.create(
                        to= attacker.target.phone_num,
                      	from_= war.twilio_phone_num,
                      	body= "---- Water Gun Wars ---- Elimination confirmed: %s (Agent %s)." % (self, self.user),
                        )
                    if attacker.target.user.email:
                        send_mail(
                        'Water Gun Wars',
                        'Elimination confirmed: %s (Agent %s).' % (self, self.user),
                        'chswgw@gmail.com',
                        [attacker.target.user.email],
                        fail_silently=True
                        )
                    if attacker.phone_num:
                        client.messages.create(
                        to= attacker.phone_num,
                      	from_= war.twilio_phone_num,
                      	body= "---- Water Gun Wars ---- Your target was eliminated: %s (Agent %s). You have until 11:59 pm on %s to eliminate your new target: %s." % (self, self.user, attacker.date_target_due.date(), attacker.target),
                        )
                    if attacker.user.email:
                        send_mail(
                        'Water Gun Wars',
                        'Your target was eliminated: %s (Agent %s). You have until 11:59 pm on %s to eliminate your new target: %s.' % (self, self.user, attacker.date_target_due.date(), attacker.target),
                        'chswgw@gmail.com',
                        [attacker.user.email],
                        fail_silently=True
                        )
                else:
                    if attacker.phone_num:
                        client.messages.create(
                        to= attacker.phone_num,
                      	from_= war.twilio_phone_num,
                      	body= "---- Water Gun Wars ---- Elimination confirmed: %s (Agent %s). You have until 11:59 pm on %s to eliminate your new target: %s." % (self, self.user, attacker.date_target_due.date(), attacker.target),
                        )
                    if attacker.user.email:
                        send_mail(
                        'Water Gun Wars',
                        'Elimination confirmed: %s (Agent %s). You have until 11:59 pm on %s to eliminate your new target: %s.' % (self, self.user, attacker.date_target_due.date(), attacker.target),
                        'chswgw@gmail.com',
                        [attacker.user.email],
                        fail_silently=True
                        )
                self.elimination_message()
            return True
        else:
            return False

    def eliminate_basic(self):
        if (self.target is not None):
            attacker = self.attacker
            target = self.target

            attacker.target = target
            attacker.date_target_assigned = timezone.make_aware(datetime.combine(date.today(), time.max))
            attacker.date_target_due = attacker.date_target_assigned + timedelta(weeks=1)

            self.target = None
            self.date_target_assigned = None
            self.date_target_due = None
            self.status_dead = True;
            self.status_dead_confirmed = True;
            self.date_of_death = timezone.now()
            self.save()

            attacker.save()

            self.elimination_message()
            return True
        else:
            return False

class War(models.Model):
    active = models.BooleanField(default=True)
    current_war = models.BooleanField(default=True)
    start_date = models.DateField(auto_now_add=True, null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    num_agents = models.IntegerField(default=0, null=True, blank=True)
    num_alive = models.IntegerField(default=0, null=True, blank=True)
    num_dead = models.IntegerField(default=0, null=True, blank=True)

    first_place = models.ForeignKey(UserProfile, related_name='war_first_place', null=True, blank=True)
    second_place = models.ForeignKey(UserProfile, related_name='war_second_place', null=True, blank=True)
    third_place = models.ForeignKey(UserProfile, related_name='war_third_place', null=True, blank=True)
    most_kills = models.ManyToManyField(UserProfile, related_name='war_most_kills', blank=True)

    phone_regex = RegexValidator(regex=r'^\d{10}$', message="Must be 10 digits long")
    twilio_phone_num = models.CharField('Twilio Phone Number', max_length=10, validators=[phone_regex])
    twilio_account_sid = models.CharField('Twilio Account SID', max_length=34, validators=[RegexValidator(regex='^.{34}$', message='Must be 34 characters long')])
    twilio_auth_token = models.CharField('Twilio Authorization Token', max_length=32, validators=[RegexValidator(regex='^.{32}$', message='Must be 32 characters long')])

    def __unicode__(self):
        return unicode(self.start_date)

    @property
    def length(self):
        if self.end_date is None:
            return (date.today() - self.start_date).days
        return (self.end_date - self.start_date).days

class UserForm(ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'password', 'email')
        help_texts = {
            'username': '(codename)',
            'email': 'For email notifications (optional)'
        }

class UserProfileForm(ModelForm):
    class Meta:
        model = UserProfile
        fields = ('phone_num',)
        help_texts = {
            'phone_num': 'For text notifications (recommended)'
        }

class UpdateUserForm(forms.Form):
    phone_regex = RegexValidator(regex=r'^\d{10}$', message="Must be 10 digits long")
    phone_num = forms.CharField(label='Phone Number', required=False, validators=[phone_regex], help_text="For text notifications (recommended)")
    email = forms.EmailField(required=False, help_text="For email notifications (optional)")

class WarForm(ModelForm):
    class Meta:
        model = War
        fields = ('twilio_phone_num', 'twilio_account_sid', 'twilio_auth_token')

class CustomUserProfileAdminForm(ModelForm):
    class Meta:
        model = UserProfile
        fields = ('date_target_due',)
        widgets = {
            'date_target_due': AdminDateWidget
        }
