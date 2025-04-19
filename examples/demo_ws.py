from rich.console import Console
from rich.prompt import Prompt
from rich.json import JSON
import asyncio
import websockets
import json

console = Console()


async def connect_to_websocket():
    uri = Prompt.ask(
        "[bold green]Enter WebSocket URL", default="ws://localhost:8000/ws"
    )
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjeCJ9.Gb_y2viQzURkq9cTmP9bdE6I_c1RZZcKLrnZgluLZP0"
    uri = f"{uri}?token={token}"
    console.print(f"[bold blue]Connecting to WebSocket:[/bold blue] {uri}")
    async with websockets.connect(uri) as websocket:
        # 发送其他消息或处理逻辑
        await websocket.send("Hello, WebSocket!")
        console.print(f"[bold blue]Sent:[/bold blue] Hello, WebSocket!")

        # 接收服务器响应
        response = await websocket.recv()
        console.print(f"[bold green]Received:[/bold green] {response}")

        # 持续监听和发送消息
        while True:
            try:
                # 提示用户输入消息
                user_input = Prompt.ask(
                    "[bold yellow]Enter message to send (or 'exit' to quit)"
                )
                if user_input.lower() == "exit":
                    console.print("[bold red]Exiting WebSocket client...[/bold red]")
                    break

                # 发送用户输入的消息
                await websocket.send(user_input)
                console.print(f"[bold blue]Sent:[/bold blue] {user_input}")

                # 接收服务器响应
                response = await websocket.recv()
                console.print(f"[bold green]Received:[/bold green] {response}")
            except websockets.exceptions.ConnectionClosed:
                console.print("[bold red]Connection closed[/bold red]")
                break


# 运行 WebSocket 客户端
asyncio.run(connect_to_websocket())
