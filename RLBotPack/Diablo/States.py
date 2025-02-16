from Utilities import *
import time
import math
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator

from rlutilities.linear_algebra import *
from rlutilities.mechanics import Aerial, AerialTurn, Dodge, Wavedash, Boostdash, Drive
from rlutilities.simulation import Game, Ball, Car


class baseState:
    def __init__(self, agent):
        self.agent = agent
        self.active = True

class State:
    RESET = 0
    WAIT = 1
    INITIALIZE = 2
    RUNNING = 3



class GetBoost(baseState):
    def update(self):
        return saferBoostGrabber(self.agent)


class airLaunch(baseState):
    def __init__(self,agent):
        baseState.__init__(self,agent)
        self.initiated = time.time()
        self.jumpTimer = time.time()
        self.firstJump = False
        self.secondJump = False
        self.firstJumpHold = 0.5
        self.secondJumpHold = 0.4
        self.active = True


    def update(self):
        stateController = SimpleControllerState()

        if not self.firstJump:
            self.firstJump = True
            stateController.jump = True
            self.jumpTimer = time.time()

        elif self.firstJump and not self.secondJump:
            if time.time() - self.jumpTimer < self.firstJumpHold:
                stateController.jump = True

            elif time.time() - self.jumpTimer > self.firstJumpHold and time.time() - self.jumpTimer < self.firstJumpHold +.05:
                stateController.boost = True
                stateController.jump = False

            else:
                self.secondJump = True
                stateController.boost = True
                self.jumpTimer = time.time()

        else:
            if time.time() - self.jumpTimer < self.secondJumpHold:
                stateController.jump = True
                stateController.boost = True

            else:
                self.active = False
                self.jump = False
                self.agent.activeState = AerialHandler(self.agent)

        if time.time() - self.jumpTimer > 0.15 and time.time() - self.jumpTimer < 0.35:
            stateController.pitch = 1
        return stateController


class AerialHandler():
    def __init__(self,agent):
        self.agent = agent
        self.active = False
        self.timer = time.time()
        self.setup()
        self.threshold = 300

    def setup(self):
        self.aerial = Aerial(self.agent.game.my_car)
        self.turn = AerialTurn(self.agent.game.my_car)
        myGoal = center = Vector([0, 5120 * sign(self.agent.team), 200])
        enemyGoal = center = Vector([0, 5120 * -sign(self.agent.team), 200])
        aboveThreshold = False

        if self.agent.me.boostLevel > 0:
            for i in range(0, self.agent.ballPred.num_slices):
                targetVec = Vector([self.agent.ballPred.slices[i].physics.location.x,
                                    self.agent.ballPred.slices[i].physics.location.y,
                                    self.agent.ballPred.slices[i].physics.location.z])

                if self.agent.ballPred.slices[i].physics.location.z >= 300:
                    if not aboveThreshold:
                        aboveThreshold =True
                    goalDist = distance2D(center, targetVec)
                    acceptable = False
                    if self.agent.team == 0:
                        if self.agent.me.location[1]  < targetVec[1]:
                            acceptable = True
                    else:
                        if self.agent.me.location[1]  > targetVec[1]:
                            acceptable = True

                    if acceptable:
                        zOffset = -10
                        if goalDist < 1500:
                            if targetVec[2] > 600:
                                zOffset = 70
                        shotAngle = correctAngle(math.degrees(angle2(targetVec, enemyGoal)) + 90 * -sign(self.agent.team))

                        if self.agent.team == 0:
                            if targetVec[1] >= 0:
                                if abs(targetVec[0]) > 893:
                                    if targetVec[0] > 0:
                                        closePost = Vector([893, 5120 * -sign(self.agent.team), 200])
                                    else:
                                        closePost = Vector([-893, 5120 * -sign(self.agent.team), 200])

                                    attackAngle  = correctAngle(math.degrees(angle2(targetVec, closePost)) + 90 * -sign(self.agent.team))

                                    targetLocal = toLocal(
                                        Vector([self.agent.ballPred.slices[i].physics.location.x,
                                                self.agent.ballPred.slices[i].physics.location.y,
                                                self.agent.ballPred.slices[i].physics.location.z]), self.agent.me)
                                    carToBallAngle = correctAngle(math.degrees(math.atan2(targetLocal[1],
                                                                                          targetLocal[0])))
                                    totalAngle = correctAngle(math.degrees(math.tan(attackAngle) + math.tan(carToBallAngle) / (1 - (math.tan(attackAngle) * math.tan(carToBallAngle)))))

                                    if abs(totalAngle) > 60:
                                        continue

                        elif self.agent.team == 1:
                            if targetVec[1] <= 0:
                                if abs(targetVec[0]) > 893:
                                    if targetVec[0] > 0:
                                        closePost = Vector([893, 5120 * -sign(self.agent.team), 200])
                                    else:
                                        closePost = Vector([-893, 5120 * -sign(self.agent.team), 200])

                                    attackAngle = correctAngle(
                                        math.degrees(angle2(targetVec, closePost)) + 90 * -sign(self.agent.team))

                                    targetLocal = toLocal(
                                        Vector([self.agent.ballPred.slices[i].physics.location.x,
                                                self.agent.ballPred.slices[i].physics.location.y,
                                                self.agent.ballPred.slices[i].physics.location.z]), self.agent.me)
                                    carToBallAngle = correctAngle(
                                        math.degrees(math.atan2(targetLocal[1], targetLocal[0])))

                                    totalAngle = correctAngle(carToBallAngle + attackAngle)

                                    if abs(totalAngle) > 60:
                                        continue


                        if abs(shotAngle) <=75:

                            xOffset = clamp(80,-80,(shotAngle*2)*-sign(self.agent.team))
                            self.aerial.target = vec3(self.agent.ballPred.slices[i].physics.location.x+xOffset,
                                                      self.agent.ballPred.slices[i].physics.location.y,
                                                      self.agent.ballPred.slices[i].physics.location.z+zOffset)

                            self.aerial.arrival_time = self.agent.ballPred.slices[i].game_seconds

                            simulation = self.aerial.simulate()
                            if norm(simulation.location - self.aerial.target) < 100:

                                self.target_ball = self.agent.ballPred.slices[i]
                                self.xOffset = xOffset
                                self.zOffset = zOffset
                                self.active = True
                                if self.agent.onSurface:
                                    if self.agent.ballPred.slices[i].physics.location.z >= 400:
                                        targetLocal = toLocal(Vector([self.agent.ballPred.slices[i].physics.location.x+xOffset,
                                                      self.agent.ballPred.slices[i].physics.location.y,
                                                      self.agent.ballPred.slices[i].physics.location.z+zOffset]), self.agent.me)

                                        carToBallAngle = correctAngle(math.degrees(math.atan2(targetLocal[1], targetLocal[0])))
                                        if abs(carToBallAngle) < 45:
                                            if distance2D(self.agent.me.location,targetLocal) > 1500:
                                                if self.agent.ballPred.slices[i].physics.location.z >= 900:
                                                    if not self.agent.onWall:
                                                        self.agent.activeState = airLaunch(self.agent)
                                                        self.active = False
                                                        return self.agent.activeState.update()
                                break

                else:
                    if aboveThreshold:
                        break

    def stillValid(self):
        for i in range(0, self.agent.ballPred.num_slices):
            if self.agent.ballPred.slices[i].physics.location.z >= 300:
                if abs(self.target_ball.game_seconds - self.agent.ballPred.slices[i].game_seconds) < self.agent.deltaTime*3:
                    difference = 0
                    difference+= abs((self.agent.ballPred.slices[i].physics.location.x+self.xOffset) - (self.target_ball.physics.location.x+self.zOffset))
                    difference += abs(self.agent.ballPred.slices[i].physics.location.y - self.target_ball.physics.location.y)
                    difference += abs((self.agent.ballPred.slices[i].physics.location.z+self.zOffset) - (self.target_ball.physics.location.z+self.zOffset))
                    if difference < 10:
                        self.aerial.target = vec3(self.agent.ballPred.slices[i].physics.location.x + self.xOffset,
                                                  self.agent.ballPred.slices[i].physics.location.y,
                                                  self.agent.ballPred.slices[i].physics.location.z + self.zOffset)

                        self.aerial.arrival_time = self.agent.ballPred.slices[i].game_seconds
                        self.target_ball = self.agent.ballPred.slices[i]

                        simulation = self.aerial.simulate()
                        return

        self.active = False
        self.setup()

    def update(self):
        if self.agent.me.boostLevel > 0:
            self.setup()
            self.aerial.step(self.agent.deltaTime)
            self.controls = self.aerial.controls
            self.controls.jump = True
            if self.aerial.finished:
                self.active = False
        else:
            self.active = False
        if time.time() - self.timer > 0.5:
            if self.agent.onSurface:
                self.active = False
        return self.controls

class WaveDashing(baseState):
    def __init__(self,agent,targVec):
        baseState.__init__(self,agent)
        self.action = Wavedash(agent.game.my_car)
        self.action.direction = vec2(targVec[0],targVec[1])

    def update(self):
        self.action.step(self.agent.deltaTime)
        if self.action.finished:
            self.active = False
        return self.action.controls



# class JumpingState(baseState):
#     def __init__(self,agent, targetCode):
#         self.agent = agent
#         self.active = True
#         self.targetCode = targetCode
#         self.flip_obj = FlipStatus()
#
#     def update(self):
#         controller_state = SimpleControllerState()
#         jump = flipHandler(self.agent, self.flip_obj)
#         if jump:
#             if self.targetCode == 1:
#                 controller_state.pitch = -1
#                 controller_state.steer = 0
#                 controller_state.throttle = 1
#
#             elif self.targetCode == 0:
#                 ball_local = toLocal(self.agent.ball.location, self.agent.me)
#                 ball_angle = math.atan2(ball_local.data[1], ball_local.data[0])
#                 controller_state.jump = True
#                 controller_state.yaw = math.sin(ball_angle)
#                 pitch = -math.cos(ball_angle)
#                 controller_state.pitch = pitch
#                 if pitch > 0:
#                     controller_state.throttle = -1
#                 else:
#                     controller_state.throttle = 1
#
#             elif self.targetCode == 2:
#                 controller_state.pitch = 0
#                 controller_state.steer = 0
#                 controller_state.yaw = 0
#             elif self.targetCode == 3:
#                 controller_state.pitch = 1
#                 controller_state.steer = 0
#                 controller_state.throttle = -1
#
#             elif self.targetCode == -1:
#                 controller_state.pitch = 0
#                 controller_state.steer = 0
#                 controller_state.throttle = 0
#
#         controller_state.jump = jump
#         controller_state.boost = False
#         if self.flip_obj.flipDone:
#             self.active = False
#
#         return controller_state

class JumpingState(baseState):
    def __init__(self,agent, targetCode):
        self.agent = agent
        self.active = True
        self.targetCode = targetCode
        self.flip_obj = FlipStatus(agent.time)

    def update(self):
        controller_state = SimpleControllerState()
        jump = flipHandler(self.agent, self.flip_obj)
        if jump:
            if self.targetCode == 1:
                controller_state.pitch = -1
                controller_state.steer = 0
                controller_state.throttle = 1

            elif self.targetCode == 0:
                ball_local = toLocal(self.agent.ball.location, self.agent.me)
                ball_angle = math.atan2(ball_local.data[1], ball_local.data[0])
                controller_state.jump = True
                controller_state.yaw = math.sin(ball_angle)
                pitch = -math.cos(ball_angle)
                controller_state.pitch = pitch
                if pitch > 0:
                    controller_state.throttle = -1
                else:
                    controller_state.throttle = 1

            elif self.targetCode == 2:
                controller_state.pitch = 0
                controller_state.steer = 0
                controller_state.yaw = 0
            elif self.targetCode == 3:
                controller_state.pitch = 1
                controller_state.steer = 0
                controller_state.throttle = -1

            elif self.targetCode == -1:
                controller_state.pitch = 0
                controller_state.steer = 0
                controller_state.throttle = 0

        controller_state.jump = jump
        controller_state.boost = False
        if self.flip_obj.flipDone:
            self.active = False

        return controller_state


class gettingPhysical(baseState):
    def update(self):
        action = demoMagic(self.agent)
        if action != None:
            return action
        else:
            return saferBoostGrabber(self.agent)


class GroundShot(baseState):
    def __init__(self, agent):
        self.agent = agent
        self.active = True

    def update(self):
        return lineupShot(self.agent,3)

class Dribble(baseState):
    def __init__(self, agent):
        self.agent = agent
        self.active = True

    def update(self):
        return lineupShot(self.agent,1)

class GroundDefend(baseState):
    def update(self):
        return defendGoal(self.agent)


class AerialDefend(baseState):
    pass




class Obstruct(baseState):
    def update(self):
        if not kickOffTest(self.agent):
            return turtleTime(self.agent)

        else:
            self.active = False
            self.agent.activeState = Kickoff(self.agent)
            return self.agent.activeState.update()

# class Kickoff(baseState):
#     def __init__(self,agent):
#         self.agent = agent
#         self.started = False
#         self.firstFlip = False
#         self.secondFlip = False
#         self.finalFlipDistance = 650
#         self.active = True
#         self.startTime = time.time()
#         self.flipState = None
#
#     def retire(self):
#         self.active = False
#         self.agent.activeState = None
#         self.flipState = None
#
#     def update(self):
#         spd = self.agent.getCurrentSpd()
#         if self.flipState != None:
#             if self.flipState.active:
#                 controller = self.flipState.update()
#                 if time.time() - self.flipState.flip_obj.flipStartedTimer <= 0.15:
#                     if spd < 2200:
#                         controller.boost = True
#                 return controller
#             if self.secondFlip:
#                 self.retire()
#
#         jumping = False
#         ballDistance = distance2D(self.agent.me.location, self.agent.ball.location)
#
#         if not self.started:
#             if not kickOffTest(self.agent):
#                 self.started = True
#                 self.startTime = time.time()
#
#         if self.started and time.time() - self.startTime > 2.5:
#             self.retire()
#
#         if not self.firstFlip:
#             if spd > 1100:
#                 self.flipState = JumpingState(self.agent,1)
#                 self.firstFlip = True
#                 return self.flipState.update()
#
#         if ballDistance > self.finalFlipDistance:
#             destination = self.agent.ball.location
#             if not self.firstFlip:
#                 destination.data[1] += (sign(self.agent.team)*200)
#             return greedyMover(self.agent, destination)
#
#         else:
#             self.flipState = JumpingState(self.agent,0)
#             self.secondFlip = True
#             return self.flipState.update()

class Kickoff(baseState):
    def __init__(self,agent):
        self.agent = agent
        self.started = False
        self.firstFlip = False
        self.secondFlip = False
        self.finalFlipDistance = 750
        self.active = True
        self.startTime = agent.time
        self.flipState = None

    def fakeKickOffChecker(self):
        closestToBall, bDist = findEnemyClosestToLocation(self.agent, self.agent.ball.location)
        myDist = findDistance(self.agent.me.location,self.agent.ball.location)

        if bDist:
            if bDist <= myDist*.75:
                return True
            else:
                return False
        return False

    def retire(self):
        self.active = False
        self.agent.activeState = None
        self.flipState = None

    def update(self):
        spd = self.agent.currentSpd
        if self.flipState != None:
            if self.flipState.active:
                controller = self.flipState.update()
                if self.agent.time - self.flipState.flip_obj.flipStartedTimer <= 0.15:
                    if spd < 2200:
                        controller.boost = True
                return controller
            if self.secondFlip:
                self.retire()

        jumping = False
        ballDistance = distance2D(self.agent.me.location, self.agent.ball.location)

        if not self.started:
            if not kickOffTest(self.agent):
                self.started = True
                self.startTime = self.agent.time

        if self.started and self.agent.time - self.startTime > 2.5:
            self.retire()

        if not self.firstFlip:
            if spd > 1100:
                self.flipState = JumpingState(self.agent,1)
                self.firstFlip = True
                return self.flipState.update()

        if ballDistance > self.finalFlipDistance:
            destination = self.agent.ball.location
            if not self.firstFlip:
                destination.data[1] += (sign(self.agent.team)*100)
            return greedyMover(self.agent, destination)

        else:
            self.flipState = JumpingState(self.agent,0)
            self.secondFlip = True
            return self.flipState.update()

class aerialRecovery(baseState):
    def update(self):
        if self.agent.onSurface or self.agent.me.location[2] < 100:
            self.active = False
        controller_state = SimpleControllerState()

        if self.agent.me.rotation[2] > 0:
            controller_state.roll = -1

        elif self.agent.me.rotation[2] < 0:
            controller_state.roll = 1

        if self.agent.me.rotation[0] > self.agent.velAngle:
            controller_state.yaw = -1

        elif self.agent.me.rotation[0] < self.agent.velAngle:
            controller_state.yaw = 1

        if self.active:
            controller_state.throttle = 1
        else:
            controller_state.throttle = 0

        return controller_state



class halfFlip(baseState):
    def __init__(self,agent):
        self.agent = agent
        self.active = True
        self.firstJump= False
        self.secondJump = False
        self.jumpStart = 0
        self.timeCreated = time.time()


    def update(self):
        controller_state = SimpleControllerState()
        if not self.firstJump:
            controller_state.throttle = -1
            controller_state.jump = True
            controller_state.pitch = 1
            self.firstJump = True
            self.jumpStart = time.time()
            return controller_state

        elif self.firstJump and not self.secondJump:
            jumpTimer = time.time() - self.jumpStart
            controller_state.throttle = -1
            controller_state.pitch = 1
            controller_state.jump = False
            if jumpTimer < 0.12:
                controller_state.jump = True
            if jumpTimer > 0.15:
                controller_state.jump = True
                self.jumpStart = time.time()
                self.secondJump = True
            return controller_state

        elif self.firstJump and self.secondJump:
            timer = time.time() - self.jumpStart
            if timer < 0.15:
                controller_state.throttle = -1
                controller_state.pitch = 1

            else:
                controller_state.pitch = -1
                controller_state.throttle = 1
                controller_state.roll = 1

            if timer > .8:
                controller_state.roll = 0
            if timer > 1.15:
                self.active = False
            return controller_state

        else:
            print("halfFlip else conditional called in update. This should not be happening")



class Chase(baseState):
    def __init__(self, agent):
        self.agent = agent
        self.active = True

    def update(self):
        if not kickOffTest(self.agent):
            return efficientMover(self.agent,self.agent.ball,self.agent.maxSpd)
        else:
            self.active = False
            self.agent.activeState = Kickoff(self.agent)
            return self.agent.activeState.update()

class backMan(baseState):
    def update(self):
        return backmanDefense(self.agent)


class secondMan(baseState):
    def update(self):
        return secondManSupport(self.agent)




def alteredStateManager(agent):
    agentType = type(agent.activeState)
    if agentType == JumpingState:
        if agent.activeState.active != False:
            return
    if agentType != gettingPhysical:
        agent.activeState = gettingPhysical(agent)

def halfFlipStateManager(agent):
    if agent.activeState.active == False:
        agent.activeState = halfFlip(agent)

    else:
        if type(agent.activeState) != halfFlip:
            agent.activeState = halfFlip(agent)




class emergencyDefend(baseState):
    def update(self):
        penetrationPosition = convertStructLocationToVector(self.agent.goalPred)
        penetrationPosition.data[1] = 5350 * sign(self.agent.team)
        if self.agent.goalPred.game_seconds - self.agent.gameInfo.seconds_elapsed > .1:
            if distance2D(self.agent.me.location,penetrationPosition) > 100:
                return testMover(self.agent,penetrationPosition,2300)
        else:
            if penetrationPosition[2] > 300:
                self.activeState = JumpingState(self.agent,-1)
                return self.activeState.update()

            else:
                self.activeState = JumpingState(self.agent,0)
                return self.activeState.update()

def parseCarInfo(carList, index, _max = False):
    val = 0
    best = None
    for each in carList:
        if _max:
            if each[index] > val:
                best = each
                val = each[index]
        else:
            if each[index] < val:
                best = each
                val = each[index]

    return best

def teamStateManager(agent):
    if len(agent.allies) < 1:
        soloStateManager(agent)
        return

    agentType = type(agent.activeState)
    if agentType != Kickoff:
        if not kickOffTest(agent):
            myGoalLoc = Vector([0, 5150 * sign(agent.team), 200])

            ballDistanceFromGoal = distance2D(myGoalLoc, agent.ball)

            carDistancesFromGoal = []
            cardistancesFromBall = []
            carInfo = []
            for c in agent.allies:
                cdfg = distance2D(myGoalLoc, c.location)
                cdfb = distance2D(agent.ball.location, c.location)
                carDistancesFromGoal.append(cdfg)
                cardistancesFromBall.append(cdfb)
                carInfo.append([cdfg, cdfb, c])

            carDistanceFromGoal = distance2D(myGoalLoc, agent.me)
            carDistanceFromBall = distance2D(agent.me.location,agent.ball.location)
            _test = None


            timeTillBallReady = 9999
            agent.ballDelay = 6
            # if agent.contested:
            #     ballStruct = findSuitableBallPosition2(agent, 300, agent.getCurrentSpd(), agent.me.location)
            # else:
            #     ballStruct = findSuitableBallPosition2(agent, 120, agent.getCurrentSpd(), agent.me.location)

            # if agent.contested:
            #     ballStruct = findSuitableBallPosition(agent, 300, agent.getCurrentSpd(), agent.me.location)
            # else:
            #     ballStruct = findSuitableBallPosition(agent, 120, agent.currentSpd, agent.me.location)

            ballStruct = findSuitableBallPosition(agent, 120, agent.currentSpd, agent.me.location)
            agent.selectedBallPred = ballStruct
            goalward = ballHeadedTowardsMyGoal(agent)

            if ballStruct != None:
                if ballStruct == agent.ballPred.slices[0]:
                    timeTillBallReady = 0
                else:
                    timeTillBallReady = ballStruct.game_seconds - agent.gameInfo.seconds_elapsed
            else:
                timeTillBallReady = 0
            agent.ballDelay = timeTillBallReady

            if agentType == JumpingState:
                if agent.activeState.active != False:
                    return
            if agentType == airLaunch:
                if agent.activeState.active != False:
                    return

            if agentType == halfFlip:
                if agent.activeState.active != False:
                    return
            if agentType == WaveDashing:
                if agent.activeState.active != False:
                    return

            if agentType == aerialRecovery:
                if agent.activeState.active != False:
                    _test = AerialHandler(agent)
                    if _test.active:
                        if _test.target_ball.game_seconds - agent.gameInfo.seconds_elapsed < timeTillBallReady:
                            agent.activeState = _test
                    return

            if agentType == AerialHandler:
                if agent.activeState.active != False:
                    return


            if _test == None:
                _test = AerialHandler(agent)

            if _test.active:
                if _test.target_ball.game_seconds - agent.gameInfo.seconds_elapsed < timeTillBallReady :
                    agent.activeState = _test
                    return

            if not agent.onSurface:
                if agent.me.location[2] > 150:
                    if agentType != aerialRecovery:
                        agent.activeState = aerialRecovery(agent)
                        return

            if agent.goalPred != None:
                if agentType != emergencyDefend:
                    agent.activeState = emergencyDefend(agent)
                return





            if len(agent.allies) == 1:
                if carDistanceFromBall< cardistancesFromBall[0]:
                    if carDistanceFromGoal < ballDistanceFromGoal:
                        if not goalward:
                            if agentType != Dribble:
                                agent.activeState = Dribble(agent)
                            return
                        else:
                            if agentType != GroundDefend:
                                agent.activeState = GroundDefend(agent)
                            return
                    else:
                        if ballDistanceFromGoal <= 3500:
                            if agent.activeState != backMan:
                                agent.activeState = backMan(agent)
                            return
                        else:
                            agent.activeState = secondMan(agent)

                else:
                    if ballDistanceFromGoal >=3500:
                        if agentType != secondMan:
                            agent.activeState = secondMan(agent)
                        return
                    else:
                        if agentType != backMan:
                            agent.activeState = backMan(agent)
                        return

            else:
                if carDistanceFromBall < min(cardistancesFromBall):
                    if carDistanceFromGoal < ballDistanceFromGoal:
                        if agentType != Dribble:
                            agent.activeState = Dribble(agent)
                        return
                    else:
                        if agent.activeState != backMan:
                            agent.activeState = backMan(agent)
                        return

                elif carDistanceFromBall < max(cardistancesFromBall):
                    mostForward = parseCarInfo(carInfo, 0, _max=True)
                    moveForward = False
                    if agent.team == 0:
                        if mostForward[2].location[1] - 50 > agent.ball.location[1]:
                            moveForward = True
                    else:
                        if mostForward[2].location[1] - 50 < agent.ball.location[1]:
                            moveForward = True

                    if moveForward:
                        if agentType != Dribble:
                            agent.activeState = Dribble(agent)
                        return
                    else:
                        if agentType != secondMan:
                            agent.activeState = secondMan(agent)
                        return

                else:
                    if agent.activeState != backMan:
                        agent.activeState = backMan(agent)
                    return

        else:
            agent.activeState = Kickoff(agent)

def launchStateManager(agent):
    if agent.activeState:
        if agent.activeState.active:
            return
        else:
            if type(agent.activeState) == airLaunch:
                agent.activeState = aerialRecovery(agent)

            else:
                if agent.onSurface:
                    if agent.getCurrentSpd() < 50:
                        agent.activeState = airLaunch(agent)

    else:
        agent.activeState = airLaunch(agent)



def soloStateManager(agent):
    agentType = type(agent.activeState)

    if agentType != Kickoff:
        if not kickOffTest(agent):
            myGoalLoc = center = Vector([0, 5150 * sign(agent.team), 200])

            ballDistanceFromGoal = distance2D(myGoalLoc, agent.ball)
            carDistanceFromGoal = distance2D(myGoalLoc, agent.me)

            timeTillBallReady = 9999
            agent.ballDelay = 6
            # if agent.contested:
            #     ballStruct = findSuitableBallPosition2(agent, 220, agent.getCurrentSpd(), agent.me.location)
            # else:
            #     ballStruct = findSuitableBallPosition2(agent, 120, agent.getCurrentSpd(), agent.me.location)


            ballStruct = findSuitableBallPosition(agent, 120, agent.currentSpd, agent.me.location)

            agent.selectedBallPred = ballStruct
            goalward = ballHeadedTowardsMyGoal(agent)
            agent.openGoal = openNet = openGoalOpportunity(agent)

            if ballStruct != None:
                if ballStruct == agent.ballPred.slices[0]:
                    timeTillBallReady = 0
                else:
                    timeTillBallReady = ballStruct.game_seconds - agent.gameInfo.seconds_elapsed
            else:
                timeTillBallReady = 0
            agent.ballDelay = timeTillBallReady

            if agent.ball.location[2] <= 120:
                agent.ballGrounded = True
            else:
                agent.ballGrounded = False

            if agentType == JumpingState:
                if agent.activeState.active != False:
                    return
            if agentType == airLaunch:
                if agent.activeState.active != False:
                    return

            if agentType == halfFlip:
                if agent.activeState.active != False:
                    return
            if agentType == WaveDashing:
                if agent.activeState.active != False:
                    return

            if agentType == aerialRecovery:
                if agent.activeState.active != False:
                    return

            if agentType == AerialHandler:
                if agent.activeState.active != False:
                    return

            _test = AerialHandler(agent)
            if _test.active:
                if _test.target_ball.game_seconds - agent.gameInfo.seconds_elapsed < timeTillBallReady:
                    agent.activeState = _test
                    return

            if not agent.onSurface:
                if agent.me.location[2] > 150:
                    if agentType != aerialRecovery:
                        agent.activeState = aerialRecovery(agent)
                        return

            if agent.goalPred != None:
                if agentType != emergencyDefend:
                    agent.activeState = emergencyDefend(agent)
                return

            if ballDistanceFromGoal < 2500:
                if agentType != GroundDefend:
                    agent.activeState = GroundDefend(agent)


            elif carDistanceFromGoal > ballDistanceFromGoal + 50:
                if agentType != GroundDefend:
                    agent.activeState = GroundDefend(agent)

            elif goalward:
                if agentType != GroundDefend:
                    agent.activeState = GroundDefend(agent)


            else:
                if openNet:
                    if agentType != Dribble:
                        agent.activeState = Dribble(agent)
                    return

                elif challengeDecider(agent):
                    if agentType != Dribble:
                        agent.activeState = Dribble(agent)
                    return


                elif agent.me.boostLevel >= 25:
                    if agentType != Dribble:
                        agent.activeState = Dribble(agent)

                else:
                    if agentType != Dribble:
                        agent.activeState = Dribble(agent)

        else:
            agent.activeState = Kickoff(agent)


