import pygame
import threading
import json
import websocket
import random
import queue

# WebSocket server URL for multiplayer connection
SERVER_URL = "wss://tag-game-dsmf.onrender.com"

# Thread-safe queue for handling incoming messages from server
incoming_messages = queue.Queue()
ws = None  # Global WebSocket connection object

def on_message(wsapp, message):
    """
    Callback function triggered when receiving a message from the WebSocket server.
    Parses JSON message and adds it to the incoming message queue for processing.
    """
    msg = json.loads(message)
    incoming_messages.put(msg)

def on_open(wsapp):
    """
    Callback function triggered when WebSocket connection is established.
    Automatically sends a join request to the server upon connection.
    """
    print("Connected to server")
    wsapp.send(json.dumps({"type": "join_request"}))

def run_network():
    """
    Runs the WebSocket client in a separate thread to handle network communication.
    This allows the game to continue running while maintaining server connection.
    """
    global ws
    ws = websocket.WebSocketApp(
        SERVER_URL,
        on_message=on_message,
        on_open=on_open
    )
    ws.run_forever()

def send_message(msg_type, data=None):
    """
    Sends a message to the server via WebSocket connection.
    
    Args:
        msg_type (str): Type of message to send (e.g., "move", "find_match")
        data (dict): Optional data payload to include with the message
    """
    if ws:
        try:
            ws.send(json.dumps({"type": msg_type, "data": data or {}}))
        except websocket.WebSocketConnectionClosedException:
            print("WebSocket connection is closed.")

# Start network thread as daemon (will close when main program exits)
threading.Thread(target=run_network, daemon=True).start()

# Initialize Pygame
pygame.init()

# Screen dimensions and setup
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Multiplayer Tag Game")

# Color constants for game graphics
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)    # Color for runners
RED = (255, 0, 0)     # Color for catchers
BLACK = (0, 0, 0)
GRAY = (150, 150, 150)

# Game physics constants
PLAYER_RADIUS = 20
PLAYER_SPEED = 3

# Game state variables
game_state = "MENU"  # Current game state: MENU, LOBBY, or GAME
player_id = None     # Unique identifier assigned by server
players = {}         # Dictionary storing all player data from server
my_role = None       # Current player's role (catcher or runner)

# Initialize font for text rendering
font = pygame.font.Font(None, 50)
clock = pygame.time.Clock()

# Main game loop
running = True
while running:
    # Handle pygame events (window close, key presses, etc.)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # Handle ENTER key press in menu to start matchmaking
        if game_state == "MENU" and event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            print("Sending find_match request...")
            send_message("find_match")
            game_state = "LOBBY"

    # Handle player movement input during gameplay
    if game_state == "GAME" and my_role:
        keys = pygame.key.get_pressed()
        dx = dy = 0  # Movement deltas
        
        # Check arrow key inputs and set movement direction
        if keys[pygame.K_LEFT]:
            dx -= 1
        if keys[pygame.K_RIGHT]:
            dx += 1
        if keys[pygame.K_UP]:
            dy -= 1
        if keys[pygame.K_DOWN]:
            dy += 1

        # Send movement data to server if player is moving
        if dx or dy:
            send_message("move", {"dx": dx, "dy": dy})

    # Process all incoming messages from server
    while not incoming_messages.empty():
        msg = incoming_messages.get()
        print(f"DEBUG: Received from server -> {msg}") 

        msg_type = msg.get("type")
        data = msg.get("data")
        
        # Handle different message types from server
        if msg_type == "player_joined":
            # Server assigns unique player ID
            player_id = data.get("id")
            print(f"Assigned Player ID: {player_id}")

        elif msg_type == "match_found":
            # Match found, transition to game state
            print("Match found! Joining game...")
            game_state = "GAME"
            # Send initial position update to server
            send_message("move", {"dx": 0, "dy": 0})
            
        elif msg_type == "state_update":
            # Receive updated game state from server
            print(f"DEBUG: State update data -> {data}") 
            players = data.get("players", {})
            print(f"DEBUG: New players dictionary -> {players}") 
            
            # Update local player's role based on server data
            if player_id in players:
                my_role = players[player_id]["role"]
            
        elif msg_type == "game_over":
            # Handle game end, return to menu
            print(f"Game Over! Winner: {data.get('winner_role')}")
            game_state = "MENU"
            players = {}
            my_role = None

    # Clear screen with white background
    screen.fill(WHITE)

    # Render different screens based on current game state
    if game_state == "MENU":
        # Display main menu with instructions
        text_surface = font.render("Press ENTER to find a match", True, BLACK)
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        screen.blit(text_surface, text_rect)
        
    elif game_state == "LOBBY":
        # Display waiting message while matchmaking
        text_surface = font.render("Waiting for another player...", True, BLACK)
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        screen.blit(text_surface, text_rect)
    
    elif game_state == "GAME":
        # Render all players in the game
        for p_id, p_data in players.items():
            # Skip players with incomplete data
            if "pos" not in p_data or "role" not in p_data:
                continue

            pos = p_data["pos"]  # Player position [x, y]
            
            # Determine player color based on role
            role_string = p_data["role"][0].strip().lower()
            color = RED if role_string == "catcher" else BLUE
            
            # Highlight current player with gray border
            border_color = GRAY if p_id == player_id else BLACK
            
            # Draw player circle with border
            pygame.draw.circle(screen, border_color, pos, PLAYER_RADIUS + 2)
            pygame.draw.circle(screen, color, pos, PLAYER_RADIUS)
            
            # Draw role label below player
            role_text = font.render(role_string.capitalize(), True, BLACK)
            screen.blit(role_text, (pos[0] - role_text.get_width() // 2, pos[1] + PLAYER_RADIUS + 10))

    # Update display and maintain 60 FPS
    pygame.display.flip()
    clock.tick(60)

# Clean up pygame resources when exiting
pygame.quit()
