import os
from urlparse import urlparse

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.core.mail import send_mass_mail
from twilio.rest import TwilioRestClient
from twilio.rest.resources import Connection
from twilio.rest.resources.connection import PROXY_TYPE_HTTP

proxy_url = os.environ.get("http_proxy")
host, port = urlparse(proxy_url).netloc.split(":")
Connection.set_proxy_info(host, int(port), proxy_type=PROXY_TYPE_HTTP)

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from watergunwars.models import UserForm, UserProfileForm, UpdateUserForm
from watergunwars.models import UserProfile, War, WarForm

from datetime import datetime, date, time, timedelta
from django.utils import timezone

def index(request):
    if War.objects.filter(current_war=True).exists():
        war = War.objects.get(current_war=True)
    else:
        war = None
    return render(request, 'watergunwars/index.html', {'war':war})

@login_required
def user_killed(request):
    request.user.profile.user_killed()
    return HttpResponseRedirect(reverse('index'))

@login_required
def killed_target(request):
    request.user.profile.killed_target()
    return HttpResponseRedirect(reverse('index'))

@login_required
def killed_attacker(request):
    request.user.profile.killed_attacker()
    return HttpResponseRedirect(reverse('index'))

@login_required
def new_war(request):
    if UserProfile.active_agents.count() < 2:
        return HttpResponse('Cannot start a war with less than two players.')

    # deactivate any prexisting wars
    for war in War.objects.all():
        war.active = False
        war.current_war = False
        war.save()

    if request.method == 'POST':
        war_form = WarForm(data=request.POST)
        if war_form.is_valid():
            war = war_form.save()
            war.num_agents = UserProfile.active_agents.count()
            war.num_alive = war.num_agents
            war.num_dead = 0

            # reset player status
            for agent in UserProfile.active_agents.all():
                agent.status_dead = False
                agent.status_dead_confirmed = False
                agent.killed_by_target = False
                agent.date_of_death = None
                agent.kill_count = 0
                agent.save()

            # create a list of all players ordered randomly
            random_list = list(UserProfile.active_agents.all().order_by('?'))
            num_agents = len(random_list)
            # for each player assign next player in list as target
            for x in range(0, num_agents-1):
                agent = random_list[x]
                target = random_list[x+1]
                agent.target = target
                agent.date_target_assigned = timezone.make_aware(datetime.combine(date.today(), time.max))
                agent.date_target_due = agent.date_target_assigned + timedelta(weeks=1)
                agent.save()
            # for last player assign first player of list as target
            first = random_list[0]
            last = random_list[num_agents-1]
            last.target = first
            last.date_target_assigned = timezone.make_aware(datetime.combine(date.today(), time.max))
            last.date_target_due = agent.date_target_assigned + timedelta(weeks=1)
            last.save()

            war.save()

            client = TwilioRestClient(war.twilio_account_sid, war.twilio_auth_token)

            message_list = []

            for agent in UserProfile.active_agents.all():
                if agent.phone_num:
                    client.messages.create(
                    to= agent.phone_num,
                  	from_= war.twilio_phone_num,
                  	body= "---- Water Gun Wars ---- Let the games begin! You have until 11:59 pm on %s to eliminate your target: %s. Rules are on the website. Stay safe, have fun, and good luck!" % (agent.date_target_due.date(), agent.target),
                    )
                if agent.user.email:
                    message = (
                    'Water Gun Wars',
                    'Let the games begin! You have until 11:59 pm on %s to eliminate your target: %s. Rules are on the website. Stay safe, have fun, and good luck!' % (agent.date_target_due.date(), agent.target),
                    'chswgw@gmail.com',
                    [agent.user.email],
                    )
                    message_list.append(message)

            send_mass_mail(message_list, fail_silently=True)

            return HttpResponseRedirect(reverse('index'))
        else:
            print war_form.errors
    else:
        war_form = WarForm()
    return render(request, 'watergunwars/new_war.html',
            {'war_form': war_form})

@login_required
def end_war(request):
    if War.objects.filter(current_war=True).exists():
        war = War.objects.get(current_war=True)
        war.current_war = False
        war.end_date = date.today()
        war.save()
        if war.active:
            war.description = 'War was cancelled.'
            war.active = False
            war.save()

            client = TwilioRestClient(war.twilio_account_sid, war.twilio_auth_token)

            message_list = []

            for agent in UserProfile.active_agents.all():
                if agent.phone_num:
                    client.messages.create(
                    to= agent.phone_num,
                    from_= war.twilio_phone_num,
                    body= "---- Water Gun Wars ---- The war has been cancelled.",
                    )
                if agent.user.email:
                    message = (
                    'Water Gun Wars',
                    'The war has been cancelled.',
                    'chswgw@gmail.com',
                    [agent.user.email]
                    )
                    message_list.append(message)

            send_mass_mail(message_list, fail_silently=True)

            # deactivate all players
            for agent in UserProfile.active_agents.all():
                agent.active = False
                agent.save()

    return HttpResponseRedirect(reverse('index'))

@login_required
def temp(request):
    for agent in UserProfile.active_agents.all():
        if not agent.dead:
            original_date = timezone.localtime(agent.date_target_assigned).date()
            agent.date_target_assigned = timezone.make_aware(datetime.combine(original_date, time.max))
            agent.date_target_due = agent.date_target_assigned + timedelta(weeks=1)
            agent.save()
    return HttpResponseRedirect(reverse('index'))

def register(request):
    registered = False

    if request.method == 'POST':

        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            user.set_password(user.password)
            user.save()

            profile = profile_form.save(commit=False)
            profile.user = user
            if War.objects.filter(current_war=True).exists():
                profile.active = False
            profile.save()

            registered = True

        else:
            print user_form.errors, profile_form.errors

    else:
        user_form = UserForm()
        profile_form = UserProfileForm()

    return render(request, 'watergunwars/register.html',
            {'user_form': user_form, 'profile_form': profile_form, 'registered': registered})

@login_required
def update_user(request):
    updated = False

    if request.method == 'POST':

        form = UpdateUserForm(data=request.POST)

        if form.is_valid():
            user = request.user
            user.email = form.cleaned_data['email']
            user.profile.phone_num = form.cleaned_data['phone_num']
            user.save()
            user.profile.save()

            updated = True

        else:
            print form.errors

    else:
        user = request.user
        form = UpdateUserForm(initial={'phone_num': user.profile.phone_num, 'email': user.email})

    return render(request, 'watergunwars/update_user.html', {'form': form, 'updated': updated})

def user_login(request):
    username = request.POST.get('username')
    password = request.POST.get('password')

    user = authenticate(username=username, password=password)

    if user:
        login(request, user)

    return HttpResponseRedirect(reverse('index'))

@login_required
def user_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('index'))
