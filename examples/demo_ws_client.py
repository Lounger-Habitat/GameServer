import asyncio
import json
import time
import argparse
from typing import Dict, List, Any, Callable, Optional

import websockets
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout


class WebSocketClient:
    """WebSocket client with event listener pattern similar to browser's addEventListener."""

    def __init__(self, server_url: str):
        self.server_url = server_url
        self.websocket = None
        self.connected = False
        self.event_handlers = {}
        self.own_info = {}
        self.heartbeat_task = None
        self.prompt_session = PromptSession()
        self.client_type = None

    async def connect(self, client_type: str, details: Dict[str, Any]):
        """Connect to the WebSocket server with client details."""
        # Build the URL based on client type
        if client_type == "env":
            url = f"{self.server_url}/env/{details.get('env_id', 1)}"
        elif client_type == "agent":
            url = f"{self.server_url}/agent/{details.get('env_id', 1)}/{details.get('agent_id', 1)}"
        elif client_type == "human":
            url = f"{self.server_url}/human/{details.get('env_id', 1)}/{details.get('human_id', 1)}"
        else:
            url = self.server_url

        self.own_info = details
        self.client_type = client_type

        try:
            self.websocket = await websockets.connect(url)
            self.connected = True
            print(f"Connected to {url} as {client_type}")

            # Start heartbeat task
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            # Trigger the 'connect' event
            # await self._trigger_event("connect", None)

            # Start listening for messages
            asyncio.create_task(self._message_loop())

            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def addListener(self, event_type: str, handler: Callable):
        """Add an event listener for a specific event type."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []

        self.event_handlers[event_type].append(handler)

    def removeListener(self, event_type: str, handler: Optional[Callable] = None):
        """Remove an event listener or all listeners of a specific type."""
        if handler is None:
            # Remove all handlers for this event type
            self.event_handlers[event_type] = []
        elif event_type in self.event_handlers:
            # Remove specific handler
            self.event_handlers[event_type] = [
                h for h in self.event_handlers[event_type] if h != handler
            ]

    async def send(
        self,
        msg_ins: str,
        data: Dict[str, Any],
        msg_to: Optional[str | Dict[str, Any]] = None,
    ):
        """Send a message to the WebSocket server."""
        if not self.connected or not self.websocket:
            print("Cannot send message: not connected")
            return False

        if msg_to is None:
            msg_to = {
                "role_type": "server"
            }  # Default to server if no recipient specified
        elif isinstance(msg_to, str):
            # Convert string to proper format
            msg_to = {"role_type": msg_to}

        envelope = {
            "ins": msg_ins,
            "msg_from": self.own_info,
            "msg_to": msg_to,
            "data": data,
            "timestamp": time.time(),
        }

        try:
            await self.websocket.send(json.dumps(envelope))
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False

    async def disconnect(self):
        """Close the WebSocket connection."""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()

        if self.websocket:
            await self.websocket.close()

        self.connected = False
        await self._trigger_event("close", {"reason": "Disconnect called"})

    async def _message_loop(self):
        """Listen for incoming messages in a loop."""
        try:
            while self.connected and self.websocket:
                message = await self.websocket.recv()

                try:
                    data = json.loads(message)
                    msg_ins = data.get("ins", "")

                    if msg_ins == "message":
                        # Trigger message event with original data
                        await self._trigger_event("message", data)

                    # Trigger specific event type if handlers exist
                    if msg_ins == "response":
                        await self._trigger_event("response", data)

                    if msg_ins == "error":
                        await self._trigger_event("error", data)

                except json.JSONDecodeError:
                    print(f"Invalid JSON received: {message}")

        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            await self._trigger_event("close", {"reason": "Connection closed"})
        except Exception as e:
            print(f"Error in message loop: {e}")
            self.connected = False
            await self._trigger_event("error", {"error": str(e)})

    async def _heartbeat_loop(self):
        """Send heartbeat messages periodically."""
        try:
            while self.connected and self.websocket:
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds

                if self.connected:
                    await self.send("heartbeat", {"timestamp": time.time()})
        except asyncio.CancelledError:
            # Task was cancelled, just exit
            return
        except Exception as e:
            print(f"Error in heartbeat loop: {e}")

    async def start_interactive_mode(self):
        """Start interactive command mode with prompt_toolkit."""
        print(f"\n{self.client_type.upper()} Client Interactive Mode")
        print("Available commands:")
        if self.client_type == "env":
            print("  status - Check connection status")
            print("  update [message] - Send update to all agents and humans")
            print("  direct [agent/human] [id] [message] - Send direct message")
            print("  quit - Exit the client")
        elif self.client_type == "agent":
            print("  status - Check connection status")
            print("  ping - Test connection to environment")
            print("  message [action] [params] - Send message to environment")
            print("  observe - Request environment observation")
            print("  quit - Exit the client")
        elif self.client_type == "human":
            print("  status - Check connection status")
            print("  say [message] - Say something")
            print("  message [name] - Perform an action")
            print("  quit - Exit the client")
        print("  help - Show this help message")

        try:
            while self.connected:
                with patch_stdout():
                    command = await self.prompt_session.prompt_async(
                        f"[{self.client_type.upper()}] > "
                    )

                if not await self._process_command(command.strip()):
                    break
        except KeyboardInterrupt:
            print("\nExiting...")
        except Exception as e:
            print(f"Error in interactive mode: {e}")

    async def _process_command(self, command: str) -> bool:
        """Process user commands and return False if should exit."""
        if not command:
            return True

        parts = command.split()
        cmd = parts[0].lower()

        if cmd == "quit" or cmd == "exit":
            await self.disconnect()
            return False

        if cmd == "help":
            await self.start_interactive_mode()
            return True

        if cmd == "status":
            await self.send("status", {})
            return True

        if cmd == "ping":
            await self.send("heartbeat", {"message": "Ping test"})
            return True

        if cmd == "message":
            if len(parts) < 4:
                print("Usage: message [who] [action] [params...]")
                return True
            msg_to = parts[1].lower()
            msg_to = msg_to.split("_")
            if msg_to[0] == "agent":
                msg_to = {
                    "role_type": "agent",
                    "env_id": self.own_info.get("env_id"),
                    "agent_id": int(msg_to[1]),
                }
            elif msg_to[0] == "human":
                msg_to = {
                    "role_type": "human",
                    "env_id": self.own_info.get("env_id"),
                    "human_id": int(msg_to[1]),
                }
            else:
                msg_to = {"role_type": "env", "env_id": self.own_info.get("env_id")}

            action_name = parts[2]
            params = parts[3:] if len(parts) > 3 else []
            await self.send(
                "message",
                {
                    "type": "action",
                    "id": "",
                    "action": action_name,
                    "parameters": params,
                },
                msg_to=msg_to,
            )
            return True

        # Client-specific commands
        if self.client_type == "env":
            return await self._process_env_command(parts)
        elif self.client_type == "agent":
            return await self._process_agent_command(parts)
        elif self.client_type == "human":
            return await self._process_human_command(parts)

        print(f"Unknown command: {cmd}")
        return True

    async def _process_env_command(self, parts: List[str]) -> bool:
        """Process environment-specific commands."""
        cmd = parts[0].lower()

        if cmd == "update":
            message = " ".join(parts[1:]) if len(parts) > 1 else "Environment updated"
            await self.send("broadcast", {"state": message})
        elif cmd == "direct" and len(parts) >= 3:
            target_type = parts[1]  # agent or human
            try:
                target_id = int(parts[2])
                message = " ".join(parts[3:]) if len(parts) > 3 else "Hello"
                msg_to = {
                    "role_type": target_type,
                    "env_id": self.own_info.get("env_id"),
                }
                if target_type == "agent":
                    msg_to["agent_id"] = target_id
                elif target_type == "human":
                    msg_to["human_id"] = target_id

                await self.send(
                    "message",
                    {"message": message},
                    msg_to=msg_to,
                )
            except ValueError:
                print("Invalid target ID")
        else:
            # Default broadcast message
            await self.send("broadcast", {"message": " ".join(parts)})

        return True

    async def _process_agent_command(self, parts: List[str]) -> bool:
        """Process agent-specific commands."""
        cmd = parts[0].lower()

        if cmd == "ping":
            await self.send(
                "ping",
                {"timestamp": time.time(), "message": "Ping from agent to environment"},
                msg_to={
                    "role_type": "env",
                    "env_id": self.own_info.get("env_id"),
                },
            )
        elif cmd == "message":
            action_name = parts[1] if len(parts) > 1 else "act"
            params = parts[2:] if len(parts) > 2 else []
            await self.send(
                "message",
                {"action": action_name, "parameters": params},
                msg_to={
                    "role_type": "env",
                    "env_id": self.own_info.get("env_id"),
                },
            )
        elif cmd == "observe":
            await self.send(
                "message",
                {"action": "observe", "target": "env"},
                msg_to={
                    "role_type": "env",
                    "env_id": self.own_info.get("env_id"),
                },
            )
        else:
            # Default action
            await self.send(
                "message",
                {"action": "custom", "message": " ".join(parts)},
                msg_to={
                    "role_type": "env",
                    "env_id": self.own_info.get("env_id"),
                },
            )

        return True

    async def _process_human_command(self, parts: List[str]) -> bool:
        """Process human-specific commands."""
        cmd = parts[0].lower()

        if cmd == "say":
            message = " ".join(parts[1:]) if len(parts) > 1 else ""
            await self.send(
                "human_action",
                {"action": "say", "message": message},
                msg_to={
                    "role_type": "env",
                    "env_id": self.own_info.get("env_id"),
                },
            )
        elif cmd == "action":
            action_name = parts[1] if len(parts) > 1 else "undefined"
            params = parts[2:] if len(parts) > 2 else []
            await self.send(
                "human_action",
                {"action": action_name, "parameters": params},
                msg_to={
                    "role_type": "env",
                    "env_id": self.own_info.get("env_id"),
                },
            )
        else:
            # Default say action
            await self.send(
                "human_action",
                {"action": "say", "message": " ".join(parts)},
                msg_to={
                    "role_type": "env",
                    "env_id": self.own_info.get("env_id"),
                },
            )

        return True

    async def _trigger_event(self, event_type: str, data: Any):
        """Trigger handlers for a specific event type."""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    print(f"Error in event handler for {event_type}: {e}")


async def hello(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Example function to handle 'hello' event.

    description: This function processes a hello message from the client.
    params:
        message (str): The hello message sent by the client.
    returns:
        dict: A response containing the status and a message.
    """
    params = data.get("parameters", {})
    await asyncio.sleep(1)  # Simulate some processing delay
    print(f"Received hello message: {params}")
    return {
        "type": "response",
        "id": "",
        "action": "hello_response",
        "parameters": f"Hello back! You said: {params}",
        "status": "success",
    }


async def echo(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Example function to handle 'echo' event.

    description: This function echoes back the received message.
    params:
        action (str): The action to perform.
        params (object): The parameters for the action.
    returns:
        dict: A response containing the status and the echoed data.
    """
    action = data.get("action", "echo")
    parameters = data.get("parameters", {})
    print(f"Received echo request: {action}, {parameters}")
    return {"status": "success", "data": {"action": action, "parameters": parameters}}


async def add(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Example function to handle 'add' event.

    description: This function adds two numbers and returns the result.
    params:
        a (int): The first number.
        b (int): The second number.
    returns:
        dict: A response containing the sum of the two numbers.
    """
    parameters = data.get("parameters", {})
    a = parameters[0]
    b = parameters[1] if len(parameters) > 1 else 0
    result = int(a) + int(b)
    print(f"Adding {a} + {b} = {result}")
    return {
        "type": "response",
        "id": "",
        "action": "add_response",
        "result": result,
        "status": "success",
    }


async def chat(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Example function to handle 'chat' event.

    description: This function simulates a chat response.
    params:
        message (str): The chat message sent by the client.
    returns:
        dict: A response containing the status and a chat reply.
    """
    parameters = data.get("parameters", "")
    from mlong import Model
    from mlong import user, system

    model = Model()
    res = model.chat(messages=[user(f"{parameters}")])

    print(f"Chat message received: {parameters}")
    print(f"Chatbot response: {res.message.content.text_content}")
    return {
        "type": "response",
        "id": "",
        "action": "chat_response",
        "result": f"{res.message.content.text_content}",
        "status": "success",
    }


API_FUNC = {
    "hello": hello,
    "echo": echo,
    "add": add,
    "chat": chat,
}


async def setup_default_handlers(client: WebSocketClient):
    """Set up default event handlers for the client."""

    async def on_connect(_):
        print(f"✓ {client.client_type.upper()} connected successfully!")

        # Send initialization message
        if client.client_type == "env":
            await client.send(
                "connected",
                {
                    "state": "Environment initialized",
                    "env_id": client.own_info.get("env_id"),
                },
            )
        elif client.client_type == "agent":
            await client.send(
                "connected",
                {
                    "action": "initialize",
                    "agent_id": client.own_info.get("agent_id"),
                },
            )
        elif client.client_type == "human":
            await client.send(
                "connected",
                {"action": "initialize", "message": "Human client initialized"},
            )

    async def on_message(data):
        """Handle incoming messages with nice formatting."""
        msg_ins = data.get("ins", "unknown")
        msg_from = data.get("msg_from", {})
        msg_to = data.get("msg_to", {})
        from_type = msg_from.get("role_type", "unknown")
        msg_data = data.get("data", {})

        print(
            f"\n📨 [{msg_ins.upper()}] from {from_type}: {json.dumps(msg_data, indent=2)}"
        )

        # Respond to specific messages
        handler = API_FUNC.get(msg_data.get("action", ""), None)
        if handler:
            response = await handler(msg_data)
            await client.send("response", response, msg_to=msg_from)
        else:
            print(f"⚠️  No handler for action: {msg_data.get('action', 'unknown')}")

    async def on_response(data):
        """Handle responses from the server."""
        msg_ins = data.get("ins", "unknown")
        msg_from = data.get("msg_from", {})
        msg_to = data.get("msg_to", {})
        from_type = msg_from.get("role_type", "unknown")
        msg_data = data.get("data", {})

        print(
            f"\n✅ Response [{msg_ins}] - Action: {msg_data.get('action', 'unknown')}, Status: {msg_data.get('status', 'unknown')}"
        )
        print(f"Data: {json.dumps(msg_data, ensure_ascii=False, indent=2)}")

    def on_close(data):
        print(f"\n❌ Connection closed: {data.get('reason', 'Unknown')}")

    def on_error(data):
        """Handle errors from the server."""
        print(f"\n⚠️ Error: {data}")

    client.addListener("connect", on_connect)
    client.addListener("message", on_message)
    client.addListener("response", on_response)
    client.addListener("close", on_close)
    client.addListener("error", on_error)


async def main():
    """Main function with argparse support."""
    parser = argparse.ArgumentParser(description="WebSocket client for game server")
    parser.add_argument(
        "--type",
        choices=["env", "agent", "human"],
        required=True,
        help="Type of client to connect as",
    )
    parser.add_argument(
        "--server",
        default="ws://localhost:8000/ws/metaverse",
        help="WebSocket server URL",
    )
    parser.add_argument("--env_id", type=int, default=1, help="Environment ID")
    parser.add_argument(
        "--agent_id", type=int, default=1, help="Agent ID (required for agent)"
    )
    parser.add_argument(
        "--human_id", type=int, default=1, help="Human ID (required for human)"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        default=True,
        help="Start in interactive mode",
    )

    args = parser.parse_args()

    # Validate required arguments
    if args.type == "agent" and args.agent_id is None:
        print("Error: --agent_id is required for agent client type")
        return

    if args.type == "human" and args.human_id is None:
        print("Error: --human_id is required for human client type")
        return

    # Create client
    client = WebSocketClient(args.server)

    # Set up connection details
    details = {"role_type": args.type, "env_id": args.env_id}
    if args.type == "agent":
        details["agent_id"] = args.agent_id
    elif args.type == "human":
        details["human_id"] = args.human_id

    # Set up default event handlers
    await setup_default_handlers(client)

    # Connect to server
    if await client.connect(args.type, details):
        if args.interactive:
            await client.start_interactive_mode()
        else:
            # Keep connection alive
            try:
                while client.connected:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nExiting...")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
