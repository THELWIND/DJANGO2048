import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room
from .logic import Game2048Logic
from django.contrib.auth.models import User

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f'game_{self.room_code}'
        self.user = self.scope['user']

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Assign Player if needed and get role
        role_data = await self.assign_player_and_get_state()
        
        # If room is full and user is not a player, reject (or spec - optional)
        # For now, we just send the state.
        
        await self.send(text_data=json.dumps({
            'type': 'init',
            'role': role_data['role'],
            'p1_name': role_data['p1_name'],
            'p2_name': role_data['p2_name'],
            'board_p1': role_data['board_p1'],
            'board_p2': role_data['board_p2'],
            'score_p1': role_data['score_p1'],
            'score_p2': role_data['score_p2'],
            'winner': role_data['winner']
        }))
        
        # Broadcast player join to update names
        await self.channel_layer.group_send(
             self.room_group_name,
             {
                 'type': 'player_joined',
                 'p1_name': role_data['p1_name'],
                 'p2_name': role_data['p2_name']
             }
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        direction = text_data_json.get('direction')

        if direction:
            update_data = await self.process_move(direction)
            
            if update_data:
                # Send message to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'game_update',
                        'data': update_data
                    }
                )

    async def game_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'update',
            'data': event['data']
        }))

    async def player_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'player_joined',
            'p1_name': event['p1_name'],
            'p2_name': event['p2_name']
        }))

    @database_sync_to_async
    def assign_player_and_get_state(self):
        room = Room.objects.get(room_code=self.room_code)
        
        role = 'spectator'
        if room.player1 == self.user:
            role = 'p1'
        elif room.player2 == self.user:
            role = 'p2'
        elif room.player1 is None:
            room.player1 = self.user
            # Init P1 Board
            game = Game2048Logic(size=4)
            room.board_p1 = game.matrix
            room.score_p1 = 0
            room.save()
            role = 'p1'
        elif room.player2 is None:
            room.player2 = self.user
             # Init P2 Board
            game = Game2048Logic(size=4)
            room.board_p2 = game.matrix
            room.score_p2 = 0
            room.save()
            role = 'p2'
        
        return {
            'role': role,
            'p1_name': room.player1.username if room.player1 else "Waiting...",
            'p2_name': room.player2.username if room.player2 else "Waiting...",
            'board_p1': room.board_p1,
            'board_p2': room.board_p2,
            'score_p1': room.score_p1,
            'score_p2': room.score_p2,
            'winner': room.winner
        }

    @database_sync_to_async
    def process_move(self, direction):
        room = Room.objects.get(room_code=self.room_code)
        
        # Require 2 players to start
        if not room.player1 or not room.player2:
            return None
        
        if room.is_over:
            return None

        role = 'spectator'
        if room.player1 == self.user: role = 'p1'
        elif room.player2 == self.user: role = 'p2'
        
        if role == 'spectator':
            return None

        # Load Logic
        game = Game2048Logic(size=4)
        
        if role == 'p1':
            game.matrix = room.board_p1
            game.score = room.score_p1
        else:
            game.matrix = room.board_p2
            game.score = room.score_p2
            
        state = game.move(direction)
        
        # Save State
        if role == 'p1':
            room.board_p1 = state['grid']
            room.score_p1 = state['score']
        else:
            room.board_p2 = state['grid']
            room.score_p2 = state['score']

        # Check Win/Loss Conditions
        # 1. Check 2048 Win (Immediate Win)
        has_2048 = any(2048 in row for row in state['grid'])
        if has_2048:
            room.winner = role
            room.is_over = True
        
        # 2. Check Stuck/Loss (Immediate Loss -> Opponent Wins)
        elif state['status'] == 'lost':
            # Current player lost, so opponent wins
            opponent = 'p2' if role == 'p1' else 'p1'
            room.winner = opponent
            room.is_over = True
        
        room.save()

        return {
            'role': role, # Who moved
            'board': state['grid'],
            'score': state['score'],
            'winner': room.winner
        }