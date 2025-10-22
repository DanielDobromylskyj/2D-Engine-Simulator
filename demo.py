from engine_sim import sim
from engine_sim import view_single

import pygame

pygame.init()

engine = sim.Engine()
engine.start()
cylinder = engine.cylinders[0]

screen = pygame.display.set_mode((600, 800))
view = view_single.View(screen, cylinder, debug=True)
clock = pygame.time.Clock()

clock.tick(60)
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    deltaTime = clock.get_time() / 1000
    engine.simulate(deltaTime)

    view.draw()
    pygame.display.flip()

    clock.tick(60)

