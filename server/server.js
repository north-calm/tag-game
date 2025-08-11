const WebSocket = require('ws')

const server = new WebSocket.Server({port: 8080});

allPlayers = {};


server.on('connection', (socket)=>{
    var playerId = Math.random().toString(36).substring(2, 15);
    allPlayers[playerId] = { id: playerId, x: 0, y: 0 };

    socket.on('message', (message)=>{
        recentMessage = JSON.parse(message);
        console.log(JSON.stringify(recentMessage))

        if(recentMessage.type == 'join_request'){
            allPlayers[playerId] = { id: playerId, x: 0, y: 0, socket: socket };
            socket.send(JSON.stringify({type: 'player_joined', data: { id: playerId }}));
        }

        if(recentMessage.type == "find_match"){
            // Find a match for the player
            const opponent = Object.values(allPlayers).find(player => player.id !== playerId);
            if (opponent) {
                allPlayers[playerId].opponent = opponent;
                socket.send(JSON.stringify({ type: 'match_found'  }));
                opponent.socket.send(JSON.stringify({ type: 'match_found' }));
            } else {
                socket.send(JSON.stringify({ type: 'waiting_for_opponent' }));
            }
        }

        if(recentMessage.type == "move"){
            console.log("Move event received", recentMessage.data);
            const { dx, dy } = recentMessage.data;
            if (allPlayers[playerId]) {
                allPlayers[playerId].x += dx;
                allPlayers[playerId].y = dy;
            }
            
            data = {
                players : {
                    [playerId]: {
                        pos: [allPlayers[playerId].x, allPlayers[playerId].y],
                        role: "catcher"
                    },
                    [allPlayers[playerId].opponent.id]: {
                        pos: [allPlayers[allPlayers[playerId].opponent.id].x, allPlayers[allPlayers[playerId].opponent.id].y],
                        role: "runner"
                    }
                }
            }

            socket.send(JSON.stringify({ type: 'state_update',  data: data }));

        }

    });

    socket.on('close', (event)=>{
        console.log('Client disconnected', event);
        delete allPlayers[playerId];
        server.clients.forEach(client => {
            if (client.readyState === WebSocket.OPEN) {
                client.send(JSON.stringify({...recentMessage, close: true}));
            }
        });
    });

    socket.on('error', (error)=>{
        console.error(`WebSocket error: ${error}`);
    });
})