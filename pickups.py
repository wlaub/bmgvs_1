import math
import random
import time

import pygame

import pymunk as pm
import pymunk.util
from pymunk import Vec2d

from registry import register, entity_registry

from objects import Controller, Entity, COLLTYPE_DEFAULT, Pickup

@register
class SordPickup(Pickup):

    def __init__(self, app, pos):
        super(Pickup, self).__init__(app)
        self.body = body = pm.Body(body_type = pymunk.Body.STATIC)
        body.position = Vec2d(*pos)

        self.w = w = 3+2
        self.h = h = 7+2
        self.shape = shape = pm.Poly.create_box(body, (self.w, self.h))
        shape.sensor = True
        shape.collision_type = COLLTYPE_DEFAULT
        self.player_on = False

    def draw(self):
        p = self.app.jj(self.body.position)
        color = (0,0,255)

        vertices = []
        for v in self.shape.get_vertices():
            p = self.app.jj(v.rotated(self.body.angle)+self.body.position+Vec2d(-2,3)) #TODO fix this
            vertices.append(p)
        pygame.draw.polygon(self.app.screen, color, vertices, 1)


    def on_player(self, player):
        #TODO make this collide with the player's hand instead of head
        #TODO formalize player_on for pickups
        self.player_on = True
        if self.app.controller.equip():
            sord = self.app.create_entity('Sord', player)
            player.equip('front_hand', sord)
            self.app.start_game()
            super().on_player(player)


@register
class HealthPickup(Pickup):

    def __init__(self, app, pos):
        super().__init__(app, pos, 4)

    def on_player(self, player):
        extra = max(0,player.health-3)
        player.health += 1/(1+extra)
        super().on_player(player)

@register
class LengthPickup(Pickup):

    def __init__(self, app, pos):
        super().__init__(app, pos, 4)

    def on_player(self, player):
        for sord in self.app.tracker['Sord']:
            sord.offset += Vec2d(1,0)
        super().on_player(player)

@register
class LoreOrePickup(Pickup):

    def __init__(self, app, pos):
        super().__init__(app, pos, 2)

    def on_player(self, player):
        self.app.lore_score += 1
        super().on_player(player)

@register
class BeanPickup(Pickup):

    def __init__(self, app, pos):
        super().__init__(app, pos, 2)

    def on_player(self, player):
        self.app.beans += 1
        super().on_player(player)

@register
class CoffeePotPickup(Pickup):

    def __init__(self, app, pos):
        super().__init__(app, pos, 16)

    def on_player(self, player):
        if self.app.beans > 0:
            self.app.beans -= 1
            player.boost_speed(amt=10, dur=10)
            super().on_player(player)


