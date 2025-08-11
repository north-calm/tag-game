import pygame
import threading
import json
import asyncio
import websockets
import queue

SERVER_URL = "ws://localhost:8080"

incoming_messages = queue.Queue()
ws = None

# ---- Networking ----
async def run_network():
    global ws
    async with websockets.connect(SERVER_URL) as websocket:
        ws = websocket
        print("Connected to server")
        await ws.send(json.dumps({"type": "join_request"}))

        async for message in ws:
            msg = json.loads(message)
            incoming_messages.put(msg)

async def send_message(msg_type, data=None):
    if ws:
        try:
            await ws.send(json.dumps({"type": msg_type, "data": data or {}}))
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection is closed.")

def start_network_loop():
    asyncio.run(run_network())

# Start networking in a background thread
threading.Thread(target=start_network_loop, daemon=True).start()

# ---- Game ----
pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Multiplayer Tag Game")

WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
BLACK = (0, 0, 0)
GRAY = (150, 150, 150)

PLAYER_RADIUS = 20

game_state = "MENU"
player_id = None
players = {}
my_role = None

font = pygame.font.Font(None, 50)
clock = pygame.time.Clock()

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        if game_state == "MENU" and event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            print("Sending find_match request...")
            asyncio.run(send_message("find_match"))
            game_state = "LOBBY"

    if game_state == "GAME" and my_role:
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_LEFT]: dx -= 1
        if keys[pygame.K_RIGHT]: dx += 1
        if keys[pygame.K_UP]: dy -= 1
        if keys[pygame.K_DOWN]: dy += 1

        if dx or dy:
            asyncio.run(send_message("move", {"dx": dx, "dy": dy}))

    while not incoming_messages.empty():
        msg = incoming_messages.get()
        msg_type = msg.get("type")
        data = msg.get("data")
        
        if msg_type == "player_joined":
            player_id = data.get("id")
            print(f"Assigned Player ID: {player_id}")

        elif msg_type == "match_found":
            print("Match found! Joining game...")
            game_state = "GAME"
            
        elif msg_type == "state_update":
            players = data.get("players", {})
            if player_id in players:
                my_role = players[player_id]["role"]
            
        elif msg_type == "game_over":
            print(f"Game Over! Winner: {data.get('winner_role')}")
            game_state = "MENU"
            players = {}
            my_role = None

    screen.fill(WHITE)

    if game_state == "MENU":
        text_surface = font.render("Press ENTER to find a match", True, BLACK)
        screen.blit(text_surface, text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
        
    elif game_state == "LOBBY":
        text_surface = font.render("Waiting for another player...", True, BLACK)
        screen.blit(text_surface, text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))

    elif game_state == "GAME":
        for p_id, p_data in players.items():
            pos = p_data["pos"]
            role = p_data["role"]
            color = RED if role == "catcher" else BLUE
            
            pygame.draw.circle(screen, BLACK, pos, PLAYER_RADIUS + 2)
            pygame.draw.circle(screen, color, pos, PLAYER_RADIUS)
            role_text = font.render(role.capitalize(), True, BLACK)
            screen.blit(role_text, (pos[0] - role_text.get_width() // 2, pos[1] + PLAYER_RADIUS + 10))
            if p_id == player_id:
                pygame.draw.circle(screen, GRAY, pos, PLAYER_RADIUS, 3)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
