const WebSocket = require('ws')

const server = new WebSocket.Server({port: 8080});

allPlayers = {};

server.on('connection', (socket)=>{
    var playerId = Math.random().toString(36).substring(2, 15);
    allPlayers[playerId] = { id: playerId, x: Math.random() * 800, y: Math.random() * 600, socket: socket };

    socket.on('message', (message)=>{
        recentMessage = JSON.parse(message);
        // console.log(JSON.stringify(recentMessage))

        if(recentMessage.type == 'join_request'){
            // allPlayers[playerId] = { id: playerId, x: 0, y: 0, socket: socket };
            socket.send(JSON.stringify({type: 'player_joined', data: { id: playerId }}));
        }

        if(recentMessage.type == "find_match"){
            // Find a match for the player
            allPlayers[playerId].isReady = true;
            const opponent = Object.values(allPlayers).find(player => player.id !== playerId && !player.inAMatch && player.socket.readyState === WebSocket.OPEN && player.isReady);
            if (opponent) {
                var role = Math.random() < 0.5 ? 'catcher' : 'runner';
                allPlayers[playerId].opponent = opponent;
                allPlayers[playerId].inAMatch = true;
                allPlayers[playerId].role = role;
                opponent.opponent = allPlayers[playerId];
                opponent.inAMatch = true;
                opponent.role = role === 'catcher' ? 'runner' : 'catcher';
                socket.send(JSON.stringify({ type: 'match_found', data: {role: role, oppId: opponent.id, pos: [allPlayers[playerId].x, allPlayers[playerId].y], oppPos: [opponent.x, opponent.y]} }));
                opponent.socket.send(JSON.stringify({ type: 'match_found', data: {role: opponent.role, oppId: playerId, pos: [opponent.x, opponent.y], oppPos: [allPlayers[playerId].x, allPlayers[playerId].y]} }));

                setTimeout(() => {
                    if(!allPlayers[playerId] || !allPlayers[opponent.id] || !allPlayers[playerId].inAMatch || !allPlayers[opponent.id].inAMatch) return;
                    allPlayers[playerId].isReady = false;
                    opponent.isReady = false;
                    allPlayers[playerId].inAMatch = false;
                    opponent.inAMatch = false;

                    var isPlayerWinner = (allPlayers[playerId].role === 'runner');
                    socket.send(JSON.stringify({ type: 'game_over', data: {winner: isPlayerWinner ? playerId : opponent.id} }));
                    opponent.socket.send(JSON.stringify({ type: 'game_over', data: {winner: isPlayerWinner ? playerId : opponent.id} }));

                }, 20000);
            } else {
                socket.send(JSON.stringify({ type: 'waiting_for_opponent' }));
            }
        }

        if(recentMessage.type == "move"){
            if(!allPlayers[playerId].inAMatch) return;
            // console.log("Move event received", recentMessage.data);
            const { dx, dy } = recentMessage.data;
            if (allPlayers[playerId]) {
                allPlayers[playerId].x += dx;
                allPlayers[playerId].y += dy;
            }

            const opponent = allPlayers[playerId].opponent;
            const player = allPlayers[playerId];

            if(player.x < 0) player.x = 0;
            if(player.y < 0) player.y = 0;

            
            if(player.x + 50 > opponent.x && player.x < opponent.x + 50 && player.y + 50 > opponent.y && player.y < opponent.y + 50){
                var isPlayerWinner = (allPlayers[playerId].role === 'catcher');
                var data = {winner: isPlayerWinner ? playerId : opponent.id};
                socket.send(JSON.stringify({ type: 'game_over',  data: data }));
                opponent.socket.send(JSON.stringify({ type: 'game_over', data: data }));
                player.inAMatch = false;
                opponent.inAMatch = false;
                player.isReady = false;
                opponent.isReady = false;
                return;
            }

            data = {
                players : {
                    [playerId]: {
                        pos: [player.x, player.y],
                        role: [player.role]
                    },
                    [opponent.id]: {
                        pos: [opponent.x, opponent.y],
                        role: [opponent.role]
                    }
                }
            }

            socket.send(JSON.stringify({ type: 'state_update',  data: data }));
            opponent.socket.send(JSON.stringify({ type: 'state_update', data: data }));

        }

    });

    socket.on('close', (event)=>{
        console.log('Client disconnected', event);

        if(allPlayers[playerId].inAMatch){
            allPlayers[playerId].opponent.socket.send(JSON.stringify({ type: 'game_over', data: {} }));
            allPlayers[playerId].opponent.inAMatch = false;
        }

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