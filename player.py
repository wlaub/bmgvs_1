import math
import random
import time

import pygame

import pymunk as pm
import pymunk.util
from pymunk import Vec2d

from objects import Controller, Entity, COLLTYPE_DEFAULT
from entities import Ball, Wall

class Player(Entity):
    def __init__(self, app, pos, m, r):
        self.app = app
        self.m = m
        self.r = r
        self.moment = pm.moment_for_circle(m, 0, r)
        self.body = body = pm.Body(m, self.moment)
        body.position = Vec2d(*pos)

        self.shape = shape = pm.Circle(body, r)
        shape.collision_type = COLLTYPE_DEFAULT






        self.angle = 0

        self.guns = []

        self.guns.append(FaceGun(self.app, r))

    def add_to_space(self, space):
        space.add(self.body, self.shape)
        for gun in self.guns:
            gun.add_to_space(space)

    def draw(self):
        v = self.body.position + self.shape.offset.cpvrotate(self.body.rotation_vector)
        p = self.app.flipyv(v)

        pygame.draw.circle(self.app.screen, pygame.Color("green"), p, int(self.r), 2)

        end = self.body.position + Vec2d(self.r*math.cos(self.angle), self.r*math.sin(self.angle))
        pygame.draw.line(self.app.screen, (0,255,0), p, self.app.flipyv(end), 1)

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

        v = Vec2d(dx, -dy)*base_force*self.m
        self.body.apply_force_at_local_point(v)
        self.body.apply_force_at_local_point(self.friction*self.body.velocity*self.m)



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



