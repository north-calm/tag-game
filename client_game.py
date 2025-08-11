import pygame
import threading
import json
import websocket
import random
import queue # Using queue for thread-safe message handling

# Server URL
SERVER_URL = "ws://localhost:8080"

# Using a thread-safe queue for incoming messages
incoming_messages = queue.Queue()
ws = None

# ---- Networking ----
def on_message(wsapp, message):
    msg = json.loads(message)
    incoming_messages.put(msg)

def on_open(wsapp):
    print("Connected to server")
    wsapp.send(json.dumps({"type": "join_request"}))

def run_network():
    global ws
    ws = websocket.WebSocketApp(
        SERVER_URL,
        on_message=on_message,
        on_open=on_open
    )
    ws.run_forever()

def send_message(msg_type, data=None):
    if ws:
        try:
            ws.send(json.dumps({"type": msg_type, "data": data or {}}))
        except websocket.WebSocketConnectionClosedException:
            print("WebSocket connection is closed.")

# Start networking in a background thread
threading.Thread(target=run_network, daemon=True).start()

# ---- Game ----
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Multiplayer Tag Game")

# Colors
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
BLACK = (0, 0, 0)
GRAY = (150, 150, 150)

# Player properties
PLAYER_RADIUS = 20
PLAYER_SPEED = 3

# Game state variables
game_state = "MENU" # MENU, LOBBY, GAME
player_id = None
players = {} # Dictionary to store all player data {id: {"pos": [x, y], "role": "catcher/runner"}}
my_role = None

font = pygame.font.Font(None, 50)
clock = pygame.time.Clock()

running = True
while running:
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # Menu logic
        if game_state == "MENU" and event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            print("Sending find_match request...")
            send_message("find_match")
            game_state = "LOBBY"

    # Player movement and sending updates
    if game_state == "GAME" and my_role:
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_LEFT]:
            dx -= 1
        if keys[pygame.K_RIGHT]:
            dx += 1
        if keys[pygame.K_UP]:
            dy -= 1
        if keys[pygame.K_DOWN]:
            dy += 1

        if dx or dy:
            send_message("move", {"dx": dx, "dy": dy})

    # Process incoming messages from the server
    while not incoming_messages.empty():
        msg = incoming_messages.get()
        msg_type = msg.get("type")
        data = msg.get("data")
        
        if msg_type == "player_joined":
            # unique ID from the server
            player_id = data.get("id")
            print(f"Assigned Player ID: {player_id}")

        elif msg_type == "match_found":
            print("Match found! Joining game...")
            game_state = "GAME"
            
        elif msg_type == "state_update":
            # Server sends the entire game state
            players = data.get("players", {})
            
            # Find my role based on my ID
            if player_id in players:
                my_role = players[player_id]["role"]
            
        elif msg_type == "game_over":
            print(f"Game Over! Winner: {data.get('winner_role')}")
            game_state = "MENU"
            players = {}
            my_role = None
            
    # ---- Drawing ----
    screen.fill(WHITE)

    if game_state == "MENU":
        text_surface = font.render("Press ENTER to find a match", True, BLACK)
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        screen.blit(text_surface, text_rect)
        
    elif game_state == "LOBBY":
        text_surface = font.render("Waiting for another player...", True, BLACK)
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        screen.blit(text_surface, text_rect)

    elif game_state == "GAME":
        # Draw all players based on the latest state from the server
        for p_id, p_data in players.items():
            pos = p_data["pos"]
            role = p_data["role"]
            color = RED if role == "catcher" else BLUE
            
            # Draw player circle
            pygame.draw.circle(screen, BLACK, pos, PLAYER_RADIUS + 2)
            pygame.draw.circle(screen, color, pos, PLAYER_RADIUS)
            
            # Draw role text
            role_text = font.render(role.capitalize(), True, BLACK)
            screen.blit(role_text, (pos[0] - role_text.get_width() // 2, pos[1] + PLAYER_RADIUS + 10))
            
            # Highlight my player
            if p_id == player_id:
                pygame.draw.circle(screen, GRAY, pos, PLAYER_RADIUS, 3)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()