from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class GameRecord(models.Model):
    MODE_CHOICES = [
        ('EASY', 'Single Player (Easy)'),
        ('HARD_6X6', 'Single Player (Hard 6x6)'),
        ('2PLAYER', '2 Players (Versus)'),
        ('VERSUS_AI', 'Versus AI (Machine)'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='EASY')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_finished = models.BooleanField(default=False)

    def duration(self):
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return timezone.now() - self.start_time
        return None

    def __str__(self):
        return f"{self.user.username} - {self.mode} - {self.score}"

class Room(models.Model):
    room_code = models.CharField(max_length=10, unique=True)
    
    player1 = models.ForeignKey(User, related_name='rooms_as_p1', on_delete=models.SET_NULL, null=True, blank=True)
    player2 = models.ForeignKey(User, related_name='rooms_as_p2', on_delete=models.SET_NULL, null=True, blank=True)
    
    board_p1 = models.JSONField(default=dict)
    board_p2 = models.JSONField(default=dict)
    
    score_p1 = models.IntegerField(default=0)
    score_p2 = models.IntegerField(default=0)
    
    winner = models.CharField(max_length=150, null=True, blank=True)
    is_over = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.room_code
