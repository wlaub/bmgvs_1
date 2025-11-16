import math
import random
import time

import pygame

import pymunk as pm
import pymunk.util
from pymunk import Vec2d

from objects import Controller, Entity, COLLTYPE_DEFAULT
from entities import Ball, Wall

class Leg:
    def __init__(self, app, parent_body, pos, l, offset, m, r):
        self.app = app
        self.m = m
        self.r = r

        l*=r
        x,y = offset
        x*=r
        y*=r

        self.x = x
        self.y = y
        self.l = l
        self.parent_body = parent_body

#        self.foot_body = foot_body = pymunk.Body(self.m, float("inf"))
        self.foot_body = foot_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        foot_body.position = pos+Vec2d(x, l)
        self.foot_shape = foot_shape = pymunk.Poly.create_box(foot_body, (4*r,2*r))
        self.app.space.add(foot_body, foot_shape)

        self.knee_body = knee_body = pymunk.Body(1, math.inf)
        knee_body.position = pos+Vec2d(x,l/2)
        self.app.space.add(knee_body)

        self.c = pymunk.SlideJoint(self.parent_body, self.knee_body, (x,0), (0,0), l/2,l/2+1)
#        self.c = pymunk.SlideJoint(self.parent_body, self.foot_body, (x,0), (0,0), 0,l*2+1)
        self.app.space.add(self.c)
        self.c = pymunk.SlideJoint(self.foot_body, self.knee_body, (0,0), (0,0), l/2,l/2+1)
        self.app.space.add(self.c)
#        c = pymunk.DampedSpring(self.parent_body, self.foot_body, (x,0), (0,0), l, m*10000,100)
        c = pymunk.DampedSpring(self.parent_body, self.foot_body,
                                (0,-l), (0,0),
                                (l*l*4+x*x)**0.5,
                                m*10000,10000)
#        self.app.space.add(c)

        self.active = False
        self.active_position = Vec2d(*self.foot_body.position)
        self.offset = Vec2d(x,y)

    def update(self):
        if self.active:
            dt = time.time()-self.active_time
            t = dt*4

            if t >= 1:
                self.active = False
                t = 1

            self.foot_body.position = self.active_position+self.active_direction*t


    def activate(self, dx, dy):
        self.active = True
        self.active_position = self.foot_body.position
        self.active_direction = self.l*1.5*Vec2d(dx,dy)
        self.active_time = time.time()

    def deactivate(self, other):
        self.active = True
        self.active_position = self.foot_body.position
        self.active_direction = Vec2d(self.x*2.5,0)+(other.foot_body.position-self.foot_body.position)
        self.active_time = time.time()



class Player(Entity):
    def __init__(self, app, pos, m, r):
        r = 5
        self.app = app
        self.m = m
        self.r = r
        self.body = body = pm.Body(self.m, float("inf"))
        body.position = Vec2d(*pos)

        self.w =w= 10*r
        self.h =h= 30*r

        self.shape = pm.Poly(self.body, [
            (-w/2, -h+w),
            (-w/2, -h),
            (w/2, -h),
            (w/2, -h+w),
            ])

#        self.shape = shape = pm.Poly.create_box(body, (10*r,20*r))
#        self.shape.mass = m
        self.shape.collision_type = COLLTYPE_DEFAULT

        self.feets = []

        self.leg = leg = 20*r

        self.left_leg = Leg(self.app, self.body, pos, leg, (-w/2,0), m, 1)
        self.right_leg = Leg(self.app, self.body, pos, leg, (w/2,0), m, 1)

        self.center_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.set_center_position()
        self.app.space.add(self.center_body)

        c = pymunk.DampedSpring(self.center_body, self.body, (0,0), (0,0), 0, m*1000,1000000)
        self.app.space.add(c)



        self.legs = [self.left_leg, self.right_leg]
        self.active_leg_idx = 0
        self.active_leg = self.legs[self.active_leg_idx]
        self.active_leg.activate(0,0)
        self.walking = False

        self.angle = 0

        self.guns = []

#        self.guns.append(FaceGun(self.app, r))

    def set_center_position(self):
        left = self.left_leg.foot_body.position
        right = self.right_leg.foot_body.position

        dist = max(0,abs(left-right)-self.w)
        alpha = 1-min(1,dist/(self.leg*2))

        t = 5
        self.center_body.position = Vec2d(
#                ((left.x+right.x)/2+self.body.position.x)/2,
#                min(self.body.position.y-self.h/2, left.y-t, right.y-t)
                (left.x+right.x)/2, (left.y+right.y)/2-self.leg*alpha
                )

    def add_to_space(self, space):
        space.add(self.body, self.shape)
        for gun in self.guns:
            gun.add_to_space(space)

    def draw(self):


        for body, poly in [(self.body, self.shape)]:
            v = body.position #+ self.shape.offset.cpvrotate(self.body.rotation_vector)
            p = self.app.flipyv(v)

            ps = [p.rotated(body.angle) + body.position for p in poly.get_vertices()]
            ps.append(ps[0])
            ps = list(map(self.app.flipyv, ps))
            color = (128,128,128)
            pygame.draw.lines(self.app.screen, color, False, ps)
            pygame.draw.polygon(self.app.screen, color, ps)

        for gun in self.guns:
            gun.draw()


    def update(self):
        self.friction = 0

        speed = abs(self.body.velocity)
        if speed > 0:
            new_angle = math.atan2(self.body.velocity.y, self.body.velocity.x)
            self.angle = new_angle

        self.friction -=10

        for gun in self.guns:
            gun.update()

        controller = self.app.controller
        dx, dy = controller.get_left_stick()

        if controller.get_right_trigger():
            base_force = 6000
        else:
            base_force = 1500

        v = Vec2d(dx, dy)*base_force*self.m
#        self.left_leg.foot_body.apply_force_at_local_point(v)



        stick_active = (dx*dx+dy*dy) > 0.5
        if stick_active:
            self.active_leg.foot_body.position += Vec2d(dx,dy)*10
            if not self.active_leg.active:
                self.active_leg.activate(dx,dy)
                self.walking = True

        self.active_leg.update()

        if self.walking and not self.active_leg.active and not stick_active:
            self.walking = False
            if self.active_leg == self.left_leg:
                self.right_leg.deactivate(self.left_leg)
                self.active_leg = self.right_leg
            elif self.active_leg == self.right_leg:
                self.left_leg.deactivate(self.right_leg)
                self.active_leg = self.left_leg


        self.set_center_position()

        self.body.apply_force_at_local_point(self.friction*self.body.velocity*self.m)

#        self.mouse_body.position += Vec2d(dx,dy)


class FaceGun:
    def __init__(self, app, r):
        self.app = app
        self.last_hit = time.time()

        self.body = pm.Body(body_type = pm.Body.KINEMATIC)
        self.shape = pm.Poly(self.body, [
            (-r/2, r),
            (-r/2, r+r),
            (r/2, r+r),
            (r/2, r),
            ])
        self.shape.sensor=True
        self.shape.collision_type = COLLTYPE_DEFAULT

        self.hit_angle = 0

    def add_to_space(self, space):
        space.add(self.body, self.shape)

    def draw(self):
        if self.fire :
            body = self.body
            poly = self.shape
            ps = [p.rotated(body.angle) + body.position for p in poly.get_vertices()]
            ps.append(ps[0])
            ps = list(map(self.app.flipyv, ps))
            color = (0,128,0)
            pygame.draw.lines(self.app.screen, color, False, ps)
            pygame.draw.polygon(self.app.screen, color, ps)

    def update(self):
        controller = self.app.controller
        player = self.app.player

        now = time.time()

        dt = now-self.last_hit
        if now-self.last_hit > 2 and not controller.get_right_trigger():
            self.last_hit = now
            dt = 0
            self.hit_angle = player.angle

        self.fire = False
        self.body.position = player.body.position
        if dt < 1:
            t = math.sin(dt*math.pi)

            player.friction -= 25

            self.fire = True
            self.body.angle = self.hit_angle-t*3.14

            for ball in self.app.tracker[Ball]:
                try:
                    hit = self.shape.shapes_collide(ball.shape)
                    self.app.remove_entity(ball)
                except: pass
        else:
            self.body.angle = player.angle



