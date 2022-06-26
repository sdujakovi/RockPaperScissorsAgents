import random

from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State
from spade.message import Message

STATE_READY = "STATE_READY"
STATE_PLAYING = "STATE_PLAYING"
STATE_FINISHED = "STATE_FINISHED"

ROCK = "rock"
READY = "ready"
PAPER = "paper"
FINISH = "finish"
SCISSORS = "scissors"

WIN = "WIN!"
TIED = "TIED."
LOST = "LOST..."

playAgain = False


def getRandomMove():
    randomNumber = random.randint(0, 2)
    if randomNumber == 0:
        return ROCK
    elif randomNumber == 1:
        return PAPER
    elif randomNumber == 2:
        return SCISSORS


def getMatchWinner(remote, local):
    if remote == local:
        return TIED
    elif remote == ROCK and local == PAPER:
        return WIN
    elif remote == ROCK and local == SCISSORS:
        return LOST
    elif remote == PAPER and local == SCISSORS:
        return WIN
    elif remote == PAPER and local == ROCK:
        return LOST
    elif remote == SCISSORS and local == ROCK:
        return WIN
    elif remote == SCISSORS and local == PAPER:
        return LOST


class RockPaperScissorsRemoteBehaviour(FSMBehaviour):
    async def on_start(self):
        print("Starting...")

    async def on_end(self):
        print("Finishing...")
        await self.agent.stop()


class StateReady(State):
    async def run(self):
        print("My State: " + STATE_READY)
        myMessage = Message(to="stane@anoxinon.me")
        myMessage.body = READY
        receivedMessage = await self.receive(timeout=20)
        if receivedMessage.body == READY:
            print("Player State: " + STATE_READY)
            await self.send(myMessage)
            self.set_next_state(STATE_PLAYING)


class StatePlaying(State):
    def __init__(self):
        super().__init__()
        self.stat = None

    async def run(self):
        print("My State: " + STATE_PLAYING)
        myMessage = Message(to="stane@anoxinon.me")
        myMessage.body = getRandomMove()
        await self.send(myMessage)
        print("Waiting Player Move...")
        receivedMessage = await self.receive(timeout=20)
        self.stat = getMatchWinner(receivedMessage.body, myMessage.body)
        print(self.stat)
        self.set_next_state(STATE_FINISHED)


class StateFinished(State):
    async def run(self):
        print("My State: " + STATE_FINISHED)
        global playAgain
        receivedMessage = await self.receive(timeout=20)
        while True:
            if receivedMessage.body == READY:
                playAgain = True
                break
            elif receivedMessage.body == FINISH:
                playAgain = False
                break


class ServerAgent(Agent):
    async def setup(self):
        fsm = RockPaperScissorsRemoteBehaviour()
        fsm.add_state(name=STATE_READY, state=StateReady(), initial=True)
        fsm.add_state(name=STATE_PLAYING, state=StatePlaying())
        fsm.add_state(name=STATE_FINISHED, state=StateFinished())
        fsm.add_transition(source=STATE_READY, dest=STATE_PLAYING)
        fsm.add_transition(source=STATE_PLAYING, dest=STATE_FINISHED)
        self.add_behaviour(fsm)


if __name__ == "__main__":
    remoteAgent = ServerAgent("stane2@anoxinon.me", "stane123")
    future = remoteAgent.start()
    future.result()

    while True:
        if playAgain:
            future = remoteAgent.start()
            playAgain = False