import socket
import time
from enum import IntEnum
from typing import Tuple, Optional

from mcstatus import MinecraftServer
from mcstatus.pinger import PingResponse


# I can't prove that the server is starting until it actually answers any calls.
# I therefore assume it to be until I get an answer or the timeout hits
class State(IntEnum):
    UNKOWN = 0
    OFFLINE = 1
    ASSUMED_STARTING = 2
    PROVED_STARTING = 3
    ONLINE = 4


class MCServerObserver:
    _cache_time__s = 10

    def __init__(self, local_address: str):
        """address from minecraft client as HOST:PORT"""
        self._last_reply = None
        self._last_fetched = 0
        self._server = MinecraftServer.lookup(local_address)

        self._assumed_starting_until = 0

    def assume_starting(self, seconds: int):
        """Server won't respond after starting until the service is able to answer"""
        self._assumed_starting_until = time.time() + seconds

    def _fetch_state(self) -> PingResponse:
        now = time.time()
        if (now - self._last_fetched) < self._cache_time__s and self._last_reply is not None:
            # print("using cached value")
            return self._last_reply

        # print(f"Fetching status for {LOCAL_ADDRESS}")
        last_state = self._server.status()
        last_fetched = time.time()
        return last_state

    def is_online(self):
        # could also use server.ping()
        return self.get_state()[0] == State.ONLINE

    def get_state(self) -> Tuple[State, Optional[PingResponse]]:
        """always works for newer servers, but won't expose everything"""

        try:
            state = self._fetch_state()
            return State.ONLINE, state
        except ConnectionRefusedError:
            # nothing there (yet?)
            if self._assumed_starting_until > time.time(): return State.ASSUMED_STARTING, None
            return State.OFFLINE, None
        except BrokenPipeError:
            # there, but unable to handle request
            return State.PROVED_STARTING, None

    def get_state_str(self) -> str:
        """always works for newer servers, but won't expose everything"""

        state, response = self.get_state()
        if state == State.ONLINE:
            return self._response_to_str(response)
        elif state == State.ASSUMED_STARTING:
            return "assumed to be starting"
        elif state == State.PROVED_STARTING:
            return "starting"
        elif state == State.OFFLINE:
            # nothing there
            return "offline"
        else:
            return "unknown"

    @staticmethod
    def _response_to_str(status: PingResponse) -> str:
        s_players = f"{status.players.online}/{status.players.max}"
        return f"online with {s_players} players ({status.latency:.0f}ms)"

    def get_players(self):
        """needs enable-query=true in server.properties and open and forwarded UDP port for full list"""

        state, response = self.get_state()

        if state != State.ONLINE:
            return "unknown, server not online"

        try:
            all_players = self._server.query().players.names
            # out = ""
            # for player in all_players:
            #    out += player
            return all_players
        except socket.timeout:
            print("query failed, query not enabled or UDP port not open?")
            some_players = response.players.sample
            return some_players + "..?"
