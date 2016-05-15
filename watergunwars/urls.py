from django.conf.urls import url

from watergunwars import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    # ex: /user_killed/
    url(r'^user_killed/$', views.user_killed, name='user_killed'),
    # ex: /killed_target/
    url(r'^killed_target/$', views.killed_target, name='killed_target'),
    # ex: /killed_attacker/
    url(r'^killed_attacker/$', views.killed_attacker, name='killed_attacker'),
    # ex: /new_war/
    url(r'^new_war/$', views.new_war, name='new_war'),
    # ex: /end_war/
    url(r'^end_war/$', views.end_war, name='end_war'),
    # ex: /register/
    url(r'^register/$', views.register, name='register'),
    # ex: /update_user
    url(r'^update_user/$', views.update_user, name='update_user'),
    # ex: /login/
    url(r'^login/$', views.user_login, name='login'),
    # ex: /logout/
    url(r'^logout/$', views.user_logout, name='logout'),

    # ex: /temp/
    url(r'^temp/$', views.temp, name='temp'),
]