"""WebSocket API routes for real-time telemetry data streaming."""

import logging
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from ..services.websocket_bus import websocket_bus

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: int = Query(..., description="Session ID to connect to"),
) -> None:
    """WebSocket endpoint for real-time telemetry data streaming.
    
    Args:
        websocket: WebSocket connection.
        session_id: Session ID to stream data for.
        
    Raises:
        WebSocketDisconnect: When client disconnects.
    """
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for session {session_id}")
    
    try:
        # Connect to the WebSocket bus
        await websocket_bus.connect(websocket, session_id)
        
        # Send initial connection confirmation
        welcome_message = {
            "type": "connection",
            "session_id": session_id,
            "message": "Connected to telemetry data stream",
            "timestamp": "2025-09-25T22:00:00Z",  # Will be replaced with actual timestamp
        }
        await websocket.send_text(f'{{"type": "connection", "session_id": {session_id}, "message": "Connected to telemetry data stream"}}')
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client (ping/pong, etc.)
                data = await websocket.receive_text()
                logger.debug(f"Received message from session {session_id}: {data}")
                
                # Echo back any received messages (for ping/pong)
                await websocket.send_text(f'{{"type": "echo", "data": "{data}"}}')
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket client disconnected from session {session_id}")
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message for session {session_id}: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
    finally:
        # Disconnect from the WebSocket bus
        await websocket_bus.disconnect(websocket, session_id)


@router.get("/ws/test", response_class=HTMLResponse)
async def websocket_test_page() -> str:
    """Simple HTML test page for WebSocket connections.
    
    Returns:
        str: HTML page for testing WebSocket connections.
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .connected { background-color: #d4edda; color: #155724; }
            .disconnected { background-color: #f8d7da; color: #721c24; }
            .message { background-color: #f8f9fa; padding: 10px; margin: 5px 0; border-left: 3px solid #007bff; }
            .heartbeat { background-color: #fff3cd; color: #856404; }
            .telemetry { background-color: #d1ecf1; color: #0c5460; }
            button { padding: 10px 20px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; }
            .connect { background-color: #28a745; color: white; }
            .disconnect { background-color: #dc3545; color: white; }
            input { padding: 8px; margin: 5px; border: 1px solid #ccc; border-radius: 3px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>WebSocket Telemetry Test</h1>
            
            <div>
                <input type="number" id="sessionId" placeholder="Session ID" value="1">
                <button class="connect" onclick="connect()">Connect</button>
                <button class="disconnect" onclick="disconnect()">Disconnect</button>
            </div>
            
            <div id="status" class="status disconnected">Disconnected</div>
            
            <div>
                <h3>Messages:</h3>
                <div id="messages"></div>
            </div>
        </div>

        <script>
            let ws = null;
            let messageCount = 0;

            function connect() {
                const sessionId = document.getElementById('sessionId').value;
                if (!sessionId) {
                    alert('Please enter a session ID');
                    return;
                }

                const wsUrl = `ws://localhost:8000/api/v1/ws?session_id=${sessionId}`;
                ws = new WebSocket(wsUrl);

                ws.onopen = function(event) {
                    updateStatus('Connected', 'connected');
                    addMessage('WebSocket connection opened', 'connection');
                };

                ws.onmessage = function(event) {
                    try {
                        const data = JSON.parse(event.data);
                        addMessage(JSON.stringify(data, null, 2), data.type);
                    } catch (e) {
                        addMessage(event.data, 'raw');
                    }
                };

                ws.onclose = function(event) {
                    updateStatus('Disconnected', 'disconnected');
                    addMessage('WebSocket connection closed', 'disconnection');
                };

                ws.onerror = function(error) {
                    updateStatus('Error', 'disconnected');
                    addMessage('WebSocket error: ' + error, 'error');
                };
            }

            function disconnect() {
                if (ws) {
                    ws.close();
                    ws = null;
                }
            }

            function updateStatus(text, className) {
                const status = document.getElementById('status');
                status.textContent = text;
                status.className = 'status ' + className;
            }

            function addMessage(text, type) {
                const messages = document.getElementById('messages');
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message ' + type;
                messageDiv.innerHTML = `<strong>${++messageCount}:</strong> ${text}`;
                messages.appendChild(messageDiv);
                messages.scrollTop = messages.scrollHeight;
            }
        </script>
    </body>
    </html>
    """
