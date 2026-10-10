"""Exercise the API server's Star Protocol routes without external services."""

from contextlib import contextmanager
import importlib
import json
import time
import unittest
from unittest.mock import patch
import uuid

import anyio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from star_protocol import COMPACT_PROTOCOL
from star_protocol.server import MessageRouter


hub = importlib.import_module("ws.hub")
hub_monitor = importlib.import_module("ws.hub_monitor")

LOOK = {
    "name": "LOOK",
    "description": "Observe the world",
    "parameters": {"type": "object", "additionalProperties": False},
}


def envelope(sender, recipient, kind, content, category="message"):
    return {
        "id": str(uuid.uuid4()),
        "timestamp": 1_780_000_000_000,
        "type": category,
        "sender": sender,
        "recipient": recipient,
        "payload": {"type": kind, "content": content},
    }


class StarProtocolRoutesTests(unittest.TestCase):
    def setUp(self):
        router = MessageRouter()
        for module in (hub, hub_monitor):
            replacement = patch.object(module, "message_router", router)
            replacement.start()
            self.addCleanup(replacement.stop)
        app = FastAPI()
        app.include_router(hub.router)
        app.include_router(hub_monitor.router)
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def receive(self, socket):
        # TestClient has no receive timeout; bound its in-memory ASGI stream so
        # a routing regression fails the test instead of hanging the suite.
        async def receive_with_timeout():
            with anyio.fail_after(2):
                return await socket._send_rx.receive()

        message = socket.portal.call(receive_with_timeout)
        self.assertEqual(message["type"], "websocket.send")
        return json.loads(message["text"])

    @contextmanager
    def connection(self, role, client_id):
        with self.client.websocket_connect(f"/ws/{role}/{client_id}") as socket:
            try:
                welcome = self.receive(socket)
                self.assertEqual(welcome["payload"]["content"]["event"], "connected")
                if role == "hub_monitor":
                    # The monitor also observes the Hub's unicast welcome to itself.
                    self.assertEqual(self.receive(socket), welcome)
                yield socket
            finally:
                socket.close()
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    clients = self.client.get("/api/monitor/clients").json()["clients"]
                    if not any(item["client_id"] == client_id for item in clients):
                        break
                else:
                    self.fail(f"Session {client_id} was not removed after close")

    def join(self, socket, environment, client_id="agent", env_id="env"):
        socket.send_json(envelope(client_id, "hub", "ctrl", {"op": "join", "env_id": env_id}, "system"))
        joined = self.receive(socket)["payload"]["content"]
        self.assertEqual((joined["event"], joined["env_id"]), ("joined", env_id))
        membership = self.receive(environment)["payload"]["content"]
        self.assertEqual(membership["event"], "client_joined")
        self.assertEqual(membership["msg"]["client_id"], client_id)

    def negotiate(self, agent, environment, client_id="agent"):
        discovery = envelope(client_id, "env", "discover", {"protocols": [COMPACT_PROTOCOL]})
        agent.send_json(discovery)
        self.assertEqual(self.receive(environment), discovery)
        for sender, recipient, source, destination, tools in (
            ("env", client_id, environment, agent, [LOOK]),
            (client_id, "env", agent, environment, []),
        ):
            specification = envelope(sender, recipient, "specification", {
                "protocol": COMPACT_PROTOCOL, "tools": tools, "events": [],
            })
            source.send_json(specification)
            self.assertEqual(self.receive(destination), specification)

    def assert_error(self, socket, code, original_id=None):
        error = self.receive(socket)
        self.assertEqual((error["type"], error["payload"]["type"]), ("system", "error"))
        content = error["payload"]["content"]
        self.assertEqual(content["code"], code)
        if original_id is not None:
            self.assertEqual(content["original_msg_id"], original_id)
        return content

    def test_negotiated_action_outcomes_ack_monitor_and_statistics(self):
        with self.connection("environment", "env") as environment, self.connection("agent", "agent") as agent:
            self.join(agent, environment)
            self.negotiate(agent, environment)
            with self.connection("hub_monitor", "observer") as monitor:
                action = envelope("agent", "env", "action", {"id": "look-1", "name": "LOOK", "params": {}})
                agent.send_json(action)
                self.assertEqual(self.receive(environment), action)
                self.assertEqual(self.receive(monitor), action)
                for status in ("running", "completed"):
                    outcome = envelope("env", "agent", "outcome", {
                        "id": f"look-1-{status}", "refs": ["look-1"],
                        "status": status, "data": {"text": status},
                    })
                    environment.send_json(outcome)
                    self.assertEqual(self.receive(agent), outcome)
                    self.assertEqual(self.receive(monitor), outcome)
                acknowledgement = envelope("agent", "env", "notify", {
                    "event": "ACK", "msg": {"envelope_id": outcome["id"]},
                }, "system")
                agent.send_json(acknowledgement)
                self.assertEqual(self.receive(environment), acknowledgement)
                self.assertEqual(self.receive(monitor), acknowledgement)

                stats_response = self.client.get("/api/monitor/stats")
                self.assertEqual(stats_response.status_code, 200)
                stats = stats_response.json()
                self.assertEqual((stats["total_clients"], stats["total_environments"]), (3, 1))
                self.assertEqual(stats["clients_by_role"], {
                    "agent": 1, "environment": 1, "human": 0, "monitor": 0, "hub_monitor": 1,
                })
                detail = self.client.get("/api/monitor/environments/env").json()
                self.assertEqual(detail["member_count"], 1)
                self.assertEqual(detail["members"][0]["client_id"], "agent")
                clients = self.client.get("/api/monitor/clients", params={"env_id": "env"}).json()
                self.assertEqual([item["client_id"] for item in clients["clients"]], ["agent"])

    def test_invalid_or_unnegotiated_messages_are_rejected_without_disconnect(self):
        with self.connection("environment", "env") as environment, self.connection("agent", "agent") as agent:
            self.join(agent, environment)
            action = envelope("agent", "env", "action", {"id": "look-1", "name": "LOOK", "params": {}})
            for missing in ("id", "timestamp"):
                with self.subTest(missing_wire_field=missing):
                    legacy = dict(action)
                    del legacy[missing]
                    agent.send_json(legacy)
                    self.assert_error(agent, 400)
            missing_id = envelope("agent", "env", "action", {"name": "LOOK", "params": {}})
            agent.send_json(missing_id)
            self.assert_error(agent, 400)
            agent.send_json(action)
            self.assertIn("negotiate", self.assert_error(agent, 400, action["id"])["msg"])
            forged = dict(action, sender="another-agent")
            agent.send_json(forged)
            self.assert_error(agent, 403, action["id"])

            # The same connection still works, and rejected traffic was never
            # queued for the Environment before the discovery handshake.
            self.negotiate(agent, environment)
            agent.send_json(action)
            self.assertEqual(self.receive(environment), action)
            legacy_outcome = envelope("env", "agent", "outcome", {"ref_id": "look-1", "success": True, "data": {}})
            environment.send_json(legacy_outcome)
            self.assert_error(environment, 400)

    def test_environment_broadcast_requires_every_member_contract_and_env_target(self):
        with self.connection("environment", "env") as environment, self.connection("agent", "agent") as agent, self.connection("human", "human") as human:
            self.join(agent, environment)
            self.join(human, environment, client_id="human")
            self.negotiate(agent, environment)
            event = envelope("env", "@env", "event", {
                "id": "world-1", "name": "world.changed", "data": {"text": "The world changed"},
                "refs": ["world-0"],
            }, "broadcast")
            environment.send_json(event)
            self.assert_error(environment, 400, event["id"])
            self.negotiate(human, environment, client_id="human")
            environment.send_json(event)
            self.assertEqual(self.receive(agent), event)
            self.assertEqual(self.receive(human), event)
            global_event = dict(event, recipient="@all")
            environment.send_json(global_event)
            self.assert_error(environment, 400, event["id"])

    def test_ack_rejects_logical_ids_and_nonmembers(self):
        with self.connection("environment", "env") as environment, self.connection("agent", "agent") as agent:
            acknowledgement = envelope("agent", "env", "notify", {
                "event": "ACK", "msg": {"envelope_id": str(uuid.uuid4())},
            }, "system")
            agent.send_json(acknowledgement)
            self.assert_error(agent, 403, acknowledgement["id"])
            self.join(agent, environment)
            invalid = envelope("agent", "env", "notify", {
                "event": "ACK", "msg": {"envelope_id": "logical-event-id"},
            }, "system")
            agent.send_json(invalid)
            self.assert_error(agent, 403, invalid["id"])
            # ACK does not require business capability negotiation; it preserves
            # the original physical Envelope ID and may safely be repeated.
            for _ in range(2):
                agent.send_json(acknowledgement)
                self.assertEqual(self.receive(environment), acknowledgement)


if __name__ == "__main__":
    unittest.main()
