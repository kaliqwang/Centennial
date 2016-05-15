from django.contrib import admin
from watergunwars.models import UserProfile, War
from django.utils.translation import ugettext_lazy as _

admin.site.site_header = 'Water Gun Wars Admin'
admin.site.site_title = 'Water Gun Wars Admin'
admin.site.index_title = 'Home'

class ActiveListFilter(admin.SimpleListFilter):
    title = 'Participating'
    parameter_name = 'inactive'

    def lookups(self, request, model_admin):
         return (
            ('True', _('Not')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'True':
            return queryset.filter(active=False)
        else:
            return queryset.filter(active=True)
        return queryset


class UserProfileAdmin(admin.ModelAdmin):
    def username(self, obj):
        return obj.user.username
    username.admin_order_field = 'user__username'
    username.short_description = "codename"

    def email(self, obj):
        return obj.user.email
    email.admin_order_field = 'user__email'
    email.short_description = "email"

    def name(self, obj):
        return obj.user.get_full_name()
    name.admin_order_field = 'user__last_name'
    name.short_description = "name"

    def is_active(self, obj):
        return obj.active
    is_active.boolean = True
    is_active.admin_order_field = 'active'
    is_active.short_description = "Is Active"

    def is_alive(self, obj):
        return (not obj.dead)
    is_alive.boolean = True
    is_alive.admin_order_field = 'status_dead_confirmed'
    is_alive.short_description = "Is Alive"

    readonly_fields = ('username', 'email', 'phone_num', 'is_active', 'is_alive')

    fieldsets = (
        ('User Info', {'fields': ('username', 'phone_num', 'email', 'is_active', 'is_alive')}),
        ('Objective', {'fields': ('target', 'date_target_assigned', 'date_target_due', 'kill_count')}),
        ('Status', {'fields': ('status_dead', 'status_dead_confirmed', 'killed_by_target', 'date_of_death')}),
    )

    list_display = ('name', 'username', 'is_active', 'is_alive', 'date_of_death', 'target', 'date_target_due', 'kill_count', 'phone_num')
    list_display_links = ('name',)
    list_filter = (ActiveListFilter,)

    list_per_page = 200

    actions = ['activate_selected', 'inactivate_selected', 'eliminate_selected']

    def activate_selected(self, request, queryset):
        count = queryset.update(active=True)
        if count == 1:
            message_bit = "1 agent was"
        else:
            message_bit = "%s agents were" % count
        self.message_user(request, "%s successfully activated." % message_bit)
    activate_selected.short_description = "Activate selected players"

    def inactivate_selected(self, request, queryset):
        count = queryset.update(active=False)
        if count == 1:
            message_bit = "1 agent was"
        else:
            message_bit = "%s agents were" % count
        self.message_user(request, "%s successfully inactivated." % message_bit)
    inactivate_selected.short_description = "Inactivate selected players"

    def eliminate_selected(self, request, queryset):
        count = 0
        for agent in queryset:
            if (agent.eliminate_basic()):
                count += 1
        if count == 1:
            message_bit = "1 agent was"
        else:
            message_bit = "%s agents were" % count
        self.message_user(request, "%s successfully eliminated." % message_bit)
        war = War.objects.get(active=True)
        war.num_dead = UserProfile.active_agents.filter(target=None).count()
        war.num_alive = UserProfile.active_agents.exclude(target=None).count()
        war.save()
    eliminate_selected.short_description = "Eliminate selected players"

    # def get_changelist_form(self, request, **kwargs):
    #     return CustomUserProfileAdminForm

    # list_editable = ('date_target_due',)

class WarAdmin(admin.ModelAdmin):
    readonly_fields = ('start_date',)
    fieldsets = (
        (None, {'fields': ('active', 'current_war', 'start_date', 'end_date', 'description')}),
        ('Players', {'fields': ('num_agents', 'num_alive', 'num_dead')}),
        ('Winners', {'fields': ('first_place', 'second_place', 'third_place', 'most_kills')}),
        ('Twilio', {'fields': ('twilio_phone_num', 'twilio_account_sid', 'twilio_auth_token')}),
    )

    list_display = ('start_date', 'end_date', 'current_war', 'active', 'first_place', 'second_place', 'third_place')
    list_filter = ['start_date', 'end_date', 'active']

    filter_horizontal = ('most_kills',)

admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(War, WarAdmin)
