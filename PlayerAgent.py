import cv2
import time
import asyncio
import mediapipe

from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State
from spade.message import Message

mediapipeHands = mediapipe.solutions.hands
drawingUtils = mediapipe.solutions.drawing_utils
drawingStyles = mediapipe.solutions.drawing_styles

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

localGesture = ""
localPoints = 0
remotePoints = 0
remoteGesture = ""
playAgain = False
showGesture = False


def getHandGestureBasedOnLandmark(handLandmarks):
    handCheck = handLandmarks.landmark
    if handCheck[4].y < handCheck[5].y:
        return READY
    elif all([handCheck[i].y < handCheck[i + 3].y for i in range(9, 20, 4)]):
        return ROCK
    elif handCheck[8].y < handCheck[7].y < handCheck[6].y < handCheck[5].y and handCheck[12].y < handCheck[11].y < \
            handCheck[10].y < handCheck[9].y and handCheck[
        16].y < handCheck[15].y < handCheck[14].y < handCheck[13].y:
        return PAPER
    elif handCheck[13].y < handCheck[16].y and handCheck[17].y < handCheck[20].y:
        return SCISSORS
    elif handCheck[4].y > handCheck[5].y:
        return FINISH
    else:
        return ""


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


class RockPaperScissorsLocalBehaviour(FSMBehaviour):
    async def on_start(self):
        print("Starting...")

    async def on_end(self):
        print("Finishing...")
        await self.agent.stop()


class ReadyState(State):
    async def run(self):
        print("My State: " + STATE_READY)
        myMessage = Message(to="stane2@anoxinon.me")
        myMessage.body = READY
        while True:
            await asyncio.sleep(3)
            if localGesture == READY:
                await self.send(myMessage)
                break
        receivedMessage = await self.receive(timeout=20)
        if receivedMessage.body == READY:
            print("Remote State: " + STATE_READY)
            self.set_next_state(STATE_PLAYING)


class PlayingState(State):
    def __init__(self):
        super().__init__()
        self.stat = None

    async def run(self):
        global localPoints
        global remotePoints
        global showGesture
        global remoteGesture
        global localGesture
        print("My State: " + STATE_PLAYING)
        print("Waiting Remote Move...")
        receivedMessage = await self.receive(timeout=20)
        myMessage = Message(to="stane2@anoxinon.me")
        showGesture = True
        await asyncio.sleep(3)
        remoteGesture = receivedMessage.body
        while True:
            await asyncio.sleep(1)
            if localGesture == ROCK:
                myMessage.body = ROCK
                break
            elif localGesture == PAPER:
                myMessage.body = PAPER
                break
            elif localGesture == SCISSORS:
                myMessage.body = SCISSORS
                break
            elif localGesture == FINISH:
                myMessage.body = FINISH
                break
        await self.send(myMessage)
        self.stat = getMatchWinner(receivedMessage.body, myMessage.body)
        print(self.stat)
        if self.stat == WIN:
            localPoints += 1
        elif self.stat == TIED:
            localPoints += 1
            remotePoints += 1
        else:
            remotePoints += 1

        remoteGesture = ""
        localGesture = ""
        self.set_next_state(STATE_FINISHED)


class FinishState(State):
    async def run(self):
        print("My State: " + STATE_FINISHED)
        global playAgain
        myMessage = Message(to="stane2@anoxinon.me")
        await asyncio.sleep(3)
        while True:
            await asyncio.sleep(1)
            if localGesture == READY:
                playAgain = True
                myMessage.body = READY
                break
            elif localGesture == FINISH:
                playAgain = False
                myMessage.body = FINISH
                break
        await self.send(myMessage)


class PlayerAgent(Agent):
    async def setup(self):
        rockPaperScissorsLocalBehaviour = RockPaperScissorsLocalBehaviour()
        rockPaperScissorsLocalBehaviour.add_state(name=STATE_READY, state=ReadyState(), initial=True)
        rockPaperScissorsLocalBehaviour.add_state(name=STATE_PLAYING, state=PlayingState())
        rockPaperScissorsLocalBehaviour.add_state(name=STATE_FINISHED, state=FinishState())
        rockPaperScissorsLocalBehaviour.add_transition(source=STATE_READY, dest=STATE_PLAYING)
        rockPaperScissorsLocalBehaviour.add_transition(source=STATE_PLAYING, dest=STATE_FINISHED)
        rockPaperScissorsLocalBehaviour.add_transition(source=STATE_FINISHED, dest=STATE_READY)
        self.add_behaviour(rockPaperScissorsLocalBehaviour)


if __name__ == "__main__":

    playerAgent = PlayerAgent("stane@anoxinon.me", "stane123")
    future = playerAgent.start()
    future.result()

    vid = cv2.VideoCapture(0)

    with mediapipeHands.Hands(
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
    ) as hands:
        while True:
            if playAgain:
                future = playerAgent.start()
                playAgain = False
            ret, frame = vid.read()
            if not ret or frame is None: break
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(frame)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            if results.multi_hand_landmarks:
                hand = results.multi_hand_landmarks[0]
                drawingUtils.draw_landmarks(
                    frame,
                    hand,
                    mediapipeHands.HAND_CONNECTIONS,
                    drawingStyles.get_default_hand_landmarks_style(),
                    drawingStyles.get_default_hand_connections_style()
                )

            frame = cv2.flip(frame, 1)

            hls = results.multi_hand_landmarks
            if hls and len(hls) == 1:
                localGesture = getHandGestureBasedOnLandmark(hls[0])
            else:
                localGesture == ""

            if localGesture != "":
                cv2.putText(frame, localGesture, (50, 250), cv2.FONT_HERSHEY_PLAIN, 2, (255, 153, 51), 2, cv2.LINE_AA)

            if remoteGesture != "":
                cv2.putText(frame, remoteGesture, (500, 250), cv2.FONT_HERSHEY_PLAIN, 2, (255, 153, 51), 2, cv2.LINE_AA)

            matchPoints = f"{localPoints} : {remotePoints}"
            cv2.putText(frame, matchPoints, (290, 50), cv2.FONT_HERSHEY_PLAIN, 2, (255, 153, 51), 2, cv2.LINE_AA)

            cv2.imshow('frame', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'): break

    vid.release()
    cv2.destroyAllWindows()

    while playerAgent.is_alive():
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            playerAgent.stop()
            break
    print("Agent finished")
