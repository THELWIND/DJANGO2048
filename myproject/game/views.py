from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from .models import GameRecord
from .logic import Game2048Logic
from .logic_6x6 import Game2048Logic6x6
from .ai_solver import Game2048AI
from .forms import CustomUserCreationForm  # Import Form mới
import json

from django.contrib.auth import views as auth_views
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm
import threading
import logging

logger = logging.getLogger(__name__)

# --- AUTH VIEWS ---
class CustomPasswordResetView(auth_views.PasswordResetView):
    template_name = 'password_reset_form.html'
    form_class = PasswordResetForm

    def form_valid(self, form):
        # Lấy email từ form
        email = form.cleaned_data.get('email')
        
        # Kiểm tra xem user có tồn tại không (để Debug)
        if User.objects.filter(email=email).exists():
            print(f"DEBUG: [Main Thread] Tìm thấy User '{email}'. Bắt đầu luồng gửi mail...")
        else:
            print(f"DEBUG: [Main Thread] Cảnh báo - Không tìm thấy User '{email}'.")

        # Chuẩn bị các tham số cần thiết để gửi mail
        # Lưu ý: Chúng ta không thể truyền 'request' vào thread vì nó có thể bị đóng
        # Nhưng PasswordResetForm cần request để tạo link https://...
        # Nên ta phải tạo context đầy đủ ở đây.
        
        opts = {
            'use_https': self.request.is_secure(),
            'token_generator': self.token_generator,
            'from_email': self.from_email,
            'email_template_name': self.email_template_name,
            'subject_template_name': self.subject_template_name,
            'request': self.request,
            'html_email_template_name': self.html_email_template_name,
            'extra_email_context': self.extra_email_context,
        }

        # Hàm chạy trong Thread riêng
        def send_email_background():
            try:
                print(f"DEBUG: [Background Thread] Đang kết nối SMTP để gửi tới {email}...")
                form.save(**opts)
                print(f"DEBUG: [Background Thread] >>> GỬI THÀNH CÔNG tới {email} <<<")
            except Exception as e:
                # In lỗi chi tiết ra Log của Render
                print(f"ERROR: [Background Thread] LỖI GỬI MAIL: {e}")

        # Khởi chạy Thread
        t = threading.Thread(target=send_email_background)
        t.setDaemon(True) # Thread sẽ tự tắt khi server tắt
        t.start()

        # Trả về trang thành công ngay lập tức (Không chờ mail)
        return super(auth_views.PasswordResetView, self).form_valid(form)

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST) # Sử dụng Custom Form
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = CustomUserCreationForm() # Sử dụng Custom Form
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('index')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

# --- GAME VIEWS ---
@login_required(login_url='login')
def index(request):
    """
    Main Menu View
    """
    return render(request, 'index.html', {
        'best_score': get_best_score(request.user)
    })

@login_required(login_url='login')
def single_player_view(request):
    game = Game2048Logic(size=4)
    request.session['single_matrix'] = game.matrix
    request.session['single_score'] = 0
    request.session['single_game_id'] = None
    
    return render(request, 'single_player.html', {
        'grid': game.matrix,
        'score': 0
    })

@login_required(login_url='login')
def hard_mode_view(request):
    game = Game2048Logic6x6(size=6)
    request.session['single_6x6_matrix'] = game.matrix
    request.session['single_6x6_score'] = 0
    request.session['single_6x6_game_id'] = None
    
    state = game.get_game_state() # Get display state

    return render(request, 'hard_mode.html', {
        'grid_6x6': state['grid'],
        'score': 0
    })

@login_required(login_url='login')
def local_pvp_view(request):
    game_p1 = Game2048Logic(size=4)
    game_p2 = Game2048Logic(size=4)
    
    request.session['p1_matrix'] = game_p1.matrix
    request.session['p1_score'] = 0
    request.session['p2_matrix'] = game_p2.matrix
    request.session['p2_score'] = 0
    request.session['versus_game_id'] = None

    return render(request, 'local_pvp.html', {
        'p1_grid': game_p1.matrix,
        'p2_grid': game_p2.matrix
    })

@login_required(login_url='login')
def ai_game_view(request):
    game_user = Game2048Logic(size=4)
    game_agent = Game2048Logic(size=4)
    
    request.session['user_ai_matrix'] = game_user.matrix
    request.session['user_ai_score'] = 0
    request.session['agent_ai_matrix'] = game_agent.matrix
    request.session['agent_ai_score'] = 0
    request.session['ai_game_id'] = None

    return render(request, 'ai_game.html', {
        'user_ai_grid': game_user.matrix,
        'agent_ai_grid': game_agent.matrix
    })

def get_best_score(user):
    # Return best score for Easy mode by default
    best = GameRecord.objects.filter(user=user, mode='EASY').order_by('-score').first()
    return best.score if best else 0

@login_required
def move_api(request):
    """
    API nhận lệnh di chuyển.
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        direction = data.get('direction')
        player = data.get('player', 'single') 
        
        # Defaults
        size = 4
        LogicClass = Game2048Logic
        game_mode = 'EASY'

        if player == 'single_6x6':
            size = 6
            LogicClass = Game2048Logic6x6
            matrix_key = 'single_6x6_matrix'
            score_key = 'single_6x6_score'
            game_id_key = 'single_6x6_game_id'
            game_mode = 'HARD_6X6'
        elif player == 'p1':
            matrix_key = 'p1_matrix'
            score_key = 'p1_score'
            game_id_key = 'versus_game_id'
            game_mode = '2PLAYER'
        elif player == 'p2':
            matrix_key = 'p2_matrix'
            score_key = 'p2_score'
            game_id_key = 'versus_game_id'
            game_mode = '2PLAYER'
        elif player == 'user_ai':
            matrix_key = 'user_ai_matrix'
            score_key = 'user_ai_score'
            game_id_key = 'ai_game_id'
            game_mode = 'VERSUS_AI'
        else: # single
            matrix_key = 'single_matrix'
            score_key = 'single_score'
            game_id_key = 'single_game_id'
            game_mode = 'EASY'

        matrix = request.session.get(matrix_key)
        score = request.session.get(score_key, 0)
        
        if not matrix:
            return JsonResponse({'error': 'Game not initialized'}, status=400)

        # Initialize Logic
        game = LogicClass(size=size)
        game.matrix = matrix
        game.score = score
        
        # Execute Move
        state = game.move(direction)
        
        # Check WIN condition (Standard 2048)
        if size == 4:
            has_2048 = any(2048 in row for row in state['grid'])
            if has_2048:
                state['status'] = 'won'
        # For 6x6, status is already set by game.move() including bomb logic

        # Save State
        # IMPORTANT: For 6x6, state['grid'] is for DISPLAY (has relative time).
        # We need to save game.matrix (absolute timestamps) to session.
        if player == 'single_6x6':
            request.session[matrix_key] = game.matrix
        else:
            request.session[matrix_key] = state['grid']
            
        request.session[score_key] = state['score']
        
        # --- DB LOGIC ---
        game_id = request.session.get(game_id_key)
        if not game_id:
            record = GameRecord.objects.create(user=request.user, mode=game_mode, score=0)
            request.session[game_id_key] = record.id
            game_id = record.id
        
        if game_id:
            record = GameRecord.objects.get(id=game_id)
            
            # Save score for standard modes
            if player in ['single', 'user_ai', 'single_6x6']:
                record.score = state['score']
            
            # Versus Logic
            is_versus = player in ['p1', 'p2', 'user_ai']
            if is_versus:
                if state['status'] == 'won':
                    record.score = state['score']
                    record.is_finished = True
                    record.end_time = timezone.now()
                elif state['status'] == 'lost':
                     # Logic for opponent winning (Simplified: User loses)
                    if player == 'user_ai':
                        opponent_score = request.session.get('agent_ai_score', 0)
                        record.score = opponent_score
                    else:
                        opponent = 'p2' if player == 'p1' else 'p1'
                        opponent_score = request.session.get(f'{opponent}_score', 0)
                        record.score = opponent_score
                    record.is_finished = True
                    record.end_time = timezone.now()

            # Finish Logic for Single
            if player in ['single', 'single_6x6'] and state['status'] in ['lost', 'won']:
                record.end_time = timezone.now()
                record.is_finished = True
            
            record.save()

        return JsonResponse(state)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def ai_move_api(request):
    # Existing AI logic remains same (Size=4)
    matrix = request.session.get('agent_ai_matrix')
    score = request.session.get('agent_ai_score', 0)
    
    if not matrix: return JsonResponse({'error': 'Game not initialized'}, status=400)

    game = Game2048Logic(size=4)
    game.matrix = matrix
    game.score = score
    
    ai_solver = Game2048AI(Game2048Logic)
    best_move = ai_solver.get_best_move(matrix)
    state = game.move(best_move)
    
    if any(2048 in row for row in state['grid']): state['status'] = 'won'
    
    request.session['agent_ai_matrix'] = state['grid']
    request.session['agent_ai_score'] = state['score']

    game_id = request.session.get('ai_game_id')
    if game_id:
        record = GameRecord.objects.get(id=game_id)
        if state['status'] == 'won':
            record.score = state['score']
            record.is_finished = True
            record.end_time = timezone.now()
            record.save()
        elif state['status'] == 'lost':
            user_score = request.session.get('user_ai_score', 0)
            record.score = user_score
            record.is_finished = True
            record.end_time = timezone.now()
            record.save()

    return JsonResponse(state)

# --- ONLINE CO-OP VIEWS ---
import uuid
from .models import Room

@login_required
def create_room(request):
    room_code = str(uuid.uuid4())[:8]
    # Create room, assign P1
    game = Game2048Logic(size=4)
    Room.objects.create(
        room_code=room_code, 
        player1=request.user,
        board_p1=game.matrix
    )
    return redirect('room', room_code=room_code)

@login_required
def join_room(request):
    if request.method == 'POST':
        room_code = request.POST.get('room_code')
        room = Room.objects.filter(room_code=room_code).first()
        if room:
            # If P2 is empty and user is not P1
            if room.player2 is None and room.player1 != request.user:
                game = Game2048Logic(size=4)
                room.player2 = request.user
                room.board_p2 = game.matrix
                room.save()
            return redirect('room', room_code=room_code)
    return redirect('index')

@login_required
def room(request, room_code):
    room = get_object_or_404(Room, room_code=room_code)
    return render(request, 'room.html', {'room_code': room_code})
