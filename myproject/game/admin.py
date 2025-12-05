from django.contrib import admin
from .models import GameRecord, Room

class GameRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'mode', 'score', 'start_time', 'end_time', 'duration_display', 'is_finished')
    list_filter = ('mode', 'is_finished', 'start_time')
    search_fields = ('user__username',)

    def duration_display(self, obj):
        return obj.duration()
    duration_display.short_description = "Thời gian chơi"

admin.site.register(GameRecord, GameRecordAdmin)

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_code', 'player1', 'player2', 'score_p1', 'score_p2', 'winner', 'is_over', 'created_at')
    list_filter = ('is_over', 'created_at')
    search_fields = ('room_code', 'player1__username', 'player2__username')
    readonly_fields = ('created_at',)