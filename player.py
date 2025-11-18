import sys, os

import math
import random
import datetime
import time
import json

import pygame

import pymunk as pm
import pymunk.util
from enum import Enum

from pymunk import Vec2d

from objects import Controller, Entity, COLLTYPE_DEFAULT
from entities import Ball, Wall
from pickups import HealthPickup
from guns import Sord

class StepState(Enum):
    idle = 0
    shuffle = 420
    big_step = 67
    small_step = 720

class Leg(Entity):
    debug_draw = False

    step_speeds = {
        StepState.idle: 12,
        StepState.shuffle: 12,
        StepState.big_step: 4,
        StepState.small_step:7,
    }

    step_sizes = {
        StepState.big_step: 7,
        StepState.small_step: 1,
    }

    def __init__(self, app, parent, pos, l, offset):
        super().__init__(app, parent)
        parent_body = parent.body

        x,y = offset

        self.x = x
        self.y = y
        self.l = l
        self.parent_body = parent_body

        self.foot_body = foot_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        foot_body.position = pos+Vec2d(x, l)
        self.foot_shape = foot_shape = pymunk.Poly.create_box(foot_body, (4,2))
        self.app.space.add(foot_body, foot_shape)

        self.anchor = Vec2d(x,0)

        self.step_state = StepState.idle
        self.speed = 4

        self.step_start_position = Vec2d(*self.foot_body.position)
        self.offset = Vec2d(x,y)


    def draw(self):

        p0 = self.parent_body.position+self.anchor
        p1 = self.foot_body.position

        pygame.draw.line(self.app.screen, (0,0,0), p0, p1)

        if self.debug_draw:
            if self.app.player.active_leg == self:
                if self.app.player.left_leg == self:
                    pygame.draw.circle(self.app.screen, (0,0,128), p1, 2)
                else:
                    pygame.draw.circle(self.app.screen, (128,0,0), p1, 2)

    def update(self):
        if self.step_state != StepState.idle:
            dt = self.app.engine_time-self.step_start_time
            t = dt*self.speed

            if t >= 1:
                self.change_step_state(StepState.idle)
                t = 1

            self.foot_body.position = self.step_start_position+self.step_direction*t

            if self.debug_draw:
                pygame.draw.circle(self.app.screen, (0,128,0), self.step_start_position, 2)
                pygame.draw.circle(self.app.screen, (128,0,128), self.step_start_position+self.step_direction, 2)

    def change_step_state(self, state):
        if state is None: return
        self.speed = self.step_speeds[state]
        self.step_state = state

    def get_shuffle_pos(self, pos):
        dx = 2*(random.random()-0.5)
        rest = self.x*2.5
        dy = self.parent_body.position.y - self.app.player.center_body.position.y
        if dy > 0:
            rest = self.x*2.5*(1+dy/15)
        pos = Vec2d(rest+dx,0)+pos
        return pos

    def do_step(self, pos, state = None):
        """
        for shuffle state, pos should be other foot_body.position
        """
        if self.step_state != StepState.idle:
            print('no')
            return
        self.change_step_state(state)
        if self.step_state == StepState.shuffle:
            pos = self.get_shuffle_pos(pos)

        self.step_start_position = self.foot_body.position
        self.step_direction = (pos-self.foot_body.position)
        self.step_start_time = self.app.engine_time


class Exoskeleton(Entity):
    def __init__(self, app, parent, pos, hips, leg_length = 3):
        super().__init__(app, parent)

        self.left_leg = self.parent.left_leg
        self.right_leg = self.parent.right_leg

        self.walking = False

        self.app.add_entity(self)

    def add_to_space(self, space):
        pass
    def remove_from_space(self, space):
        pass

    def update(self):
        fast_walk = self.parent.fast_walk
        stick_active = self.parent.stick_active
        aim = self.parent.aim
        dx, dy = aim

        if stick_active and self.parent.active_leg.step_state == StepState.idle:
            #start the next stick-driven step
            #select the new active leg
            left = self.left_leg.foot_body.position
            right = self.right_leg.foot_body.position

            if left.dot(aim) < right.dot(aim):
                self.parent.active_leg = self.left_leg
                other_leg = self.right_leg
            else:
                self.parent.active_leg = self.right_leg
                other_leg = self.left_leg

            """
            select the position on a radius around the other foot that
            maximizes the motion of their center of mass in the direction
            of the stick
            """
            pos = self.parent.active_leg.foot_body.position
            other_pos = other_leg.foot_body.position
            dr = abs(aim)
            dr2 = dr*dr
            x1,y1 = pos
            x0,y0 = other_pos

            if not fast_walk:
                step_type = StepState.small_step
            else:
                step_type = StepState.big_step
            R = self.parent.active_leg.l*Leg.step_sizes[step_type]

            c1 = dr2*x0
            c2 = abs(dx*R*dr)


            sgn = -1 if dy < 0 else 1

            cx1 = (c1-c2)/dr2
            cx2 = (c1+c2)/dr2
            cy1 = y0 + sgn*math.sqrt(R*R+2*x0*cx1 -x0*x0 - cx1*cx1)
            cy2 = y0 + sgn*math.sqrt(R*R+2*x0*cx2 -x0*x0 - cx2*cx2)

            if self.parent.debug_draw:
                pygame.draw.circle(self.app.screen, (255,0,0), other_pos, R, 1)

            p0 = Vec2d(cx1, cy1)
            p1 = Vec2d(cx2, cy2)

            #TODO there has got to be a better way to pick the branch
            #pick the one that goes the furthest in the aim direction?
            if (p0-pos).dot(aim) > (p1-pos).dot(aim):
                self.parent.active_leg.do_step(p0, step_type)
            else:
                self.parent.active_leg.do_step(p1, step_type)


            self.walking = True

    def post_update(self):

        fast_walk = self.parent.fast_walk
        stick_active = self.parent.stick_active
        aim = self.parent.aim
        dx, dy = aim

        #stop walking after last step
        if self.walking and self.parent.active_leg.step_state == StepState.idle and not stick_active:
            self.walking = False




class Player(Entity):
    debug_draw = False
    def __init__(self, app, pos):
        super().__init__(app)
        self.health = 3
        self.grace_time = 1
        self.app = app
        self.m = m = 10000
        self.body = body = pm.Body(self.m, float("inf"))
        body.position = Vec2d(*pos)

        self.fast_walk = False
        self.stick_active = False
        self.aim = Vec2d(0,0)

        self.w =w= 10
        self.h =h= 17
        self.hips = 1
        self.leg = leg = 3

        self.front_hand_position = Vec2d(4,-5)
        self.back_hand_position = Vec2d(-2,-4)
        self.back_elbow_position = Vec2d(-2,-5)

        #stuff
        self.bean_hot_counter = 0
        self.bean_hot_potency = 1
        self.walk_rate = 1

        #physics
        self.shape = pm.Poly(self.body, [
            (-w/2, -h+w),
            (-w/2, -h),
            (w/2, -h),
            (w/2, -h+w),
            ])
        self.shape.collision_type = COLLTYPE_DEFAULT

        #layugs
        self.left_leg = Leg(self.app, self, pos, self.leg, (-self.hips,0))
        self.right_leg = Leg(self.app, self, pos, self.leg, (self.hips,0))

        self.legs = [self.left_leg, self.right_leg]
        self.active_leg_idx = 0
        self.active_leg = self.legs[self.active_leg_idx]


        #feets
        self.feets = []
        feets = Exoskeleton(self.app, self, pos, self.hips)
        self.feets.append(feets)

        #body control
        self.center_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.set_center_position()
        self.app.space.add(self.center_body)

        c = pymunk.DampedSpring(self.center_body, self.body, (0,0), (0,0), 0, m*1000,1000000)
        self.app.space.add(c)

        self.guns = []
        self.guns.append(Sord(self.app, self))

    def boost_speed(self, amt, dur):
        if self.bean_hot_counter > self.app.engine_time:
            return
        self.bean_hot_potency = amt
        self.bean_hot_counter = self.app.engine_time+dur

    def set_center_position(self):
        left = self.left_leg.foot_body.position
        right = self.right_leg.foot_body.position

        #the body center should go down when the feet are far apart
        dist = max(0,abs(left-right)-self.w)
        alpha = 1-min(1,dist/(self.leg*2))

        self.center_body.position = Vec2d(
                (left.x+right.x)/2, (left.y+right.y)/2-self.leg*alpha
                )

    def add_to_space(self, space):
        space.add(self.body, self.shape)

    def on_remove(self):
        for gun in self.guns:
            self.app.remove_entity(gun)
        for feet in self.feets:
            self.app.remove_entity(feet)
        self.app.player = None
        self.write_session_stats()

    def write_session_stats(self):
        now = datetime.datetime.now()
        filename=now.strftime('%Y%m%d_%H%M%S.json')
        stats = {
            'now': now.isoformat(),
            'then': self.app.startup_time.isoformat(),
            'title': self.app.title,
            'seed': self.app.seed,
            'health': self.health,
            'time_of_death': self.app.engine_time,
            'lore_score': self.app.lore_score,
            'beans': self.app.beans,
           }
        print(f'{stats["lore_score"]} {stats["title"]} {stats["seed"]}')
        print(json.dumps(stats, indent=2))
        with open(os.path.join('stats/', filename) ,'w') as fp:
            json.dump(stats, fp)


    def draw(self):
        body = self.body
        poly = self.shape
        p = body.position #+ self.shape.offset.cpvrotate(self.body.rotation_vector)

        #head
        color = (240,192,160)
        if ( self.app.engine_time-self.last_hit >= self.grace_time-0.1 or
             int(7*(self.app.engine_time-self.last_hit)/self.grace_time) % 2 == 0
            ):
            pygame.draw.rect(self.app.screen, color,
                pygame.Rect(p+Vec2d(-self.w/2, -self.h), (self.w, self.w))
                )
        pygame.draw.rect(self.app.screen, (0,0,0),
            pygame.Rect(p+Vec2d(-self.w/2-1, -self.h-1), (self.w+2, self.w+2)),
            1
            )
        #hair
        pygame.draw.rect(self.app.screen, (128,128,128),
            pygame.Rect(p+Vec2d(-self.w/2, -self.h), (5, self.health))
            )
        #eye
        pygame.draw.rect(self.app.screen, (0,0,128),
            pygame.Rect(p+Vec2d(4, -self.h+2), (2, 2))
            )
        #body
        pygame.draw.line(self.app.screen, (0,0,0), p, p+Vec2d(0,-6))
        pygame.draw.line(self.app.screen, (0,0,0), p-Vec2d(-1,0), p-Vec2d(1,0))
        #arms
        pygame.draw.line(self.app.screen, (0,0,0),
                p+self.back_elbow_position,
                p+self.front_hand_position,
                )
        pygame.draw.line(self.app.screen, (0,0,0),
                p+self.back_elbow_position,
                p+self.back_hand_position,
                )

        #layugs
        for leg in self.legs:
            leg.draw()


        for gun in self.guns:
            gun.draw()

    def get_hit(self, dmg):
        self._basic_hit_spell(dmg)

    def update(self):
        self.friction =-10

        #guns
        for gun in self.guns:
            gun.update()

        #boosts
        dt = self.bean_hot_counter - self.app.engine_time
        if dt > 0:
            self.walk_speed = self.bean_hot_potency
        else:
            self.walk_speed = 1

        #controls
        speed = abs(self.body.velocity)

        controller = self.app.controller

        self.fast_walk = fast_walk = controller.get_right_trigger()
        dx, dy = controller.get_left_stick()
        self.stick_active = stick_active = (dx*dx+dy*dy) > 0.5
        self.aim = aim = Vec2d(dx,dy)

        for feet in self.feets:
            feet.update()

        #update legs
        self.active_leg.update()

        idle = True
        for feet in self.feets:
            feet.post_update()
            if feet.walking:
                idle = False

        #if no feets active, shuffle in place
        if idle and not stick_active and self.active_leg.step_state == StepState.idle:
            if self.active_leg == self.left_leg:
                self.right_leg.do_step(self.left_leg.foot_body.position, StepState.shuffle)
                self.active_leg = self.right_leg
            elif self.active_leg == self.right_leg:
                self.left_leg.do_step(self.right_leg.foot_body.position, StepState.shuffle)
                self.active_leg = self.left_leg

        #finally update the center based on where the feets are
        self.set_center_position()

        #apply friction if slow walk
        if not fast_walk:
            self.body.apply_force_at_local_point(self.friction*self.body.velocity*self.m)



