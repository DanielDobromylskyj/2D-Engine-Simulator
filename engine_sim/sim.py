import math

from .constants import *

"""
4 Stroke
Inline 4

All measurements in mm / radians / Kelvin
"""

ROOM_TEMP = 273 + 21

class Cylinder:
    def __init__(self, radius: float, height: float, crank_radius: float, rod_length: float):
        self.radius = radius
        self.height = height

        self.crank_radius = crank_radius
        self.rod_length = rod_length

        self.crank_rotation = 0.0
        self.crank_angular_velocity = 0.0

        self.__combusting = False

        self.temperature = ROOM_TEMP  # kelvin
        self.mode = "None"

        self.contents = {
            "fuel": 0.0,  # kg
            "air": 0.0,  # kg
            "exhaust": 0.0  # kg
        }

        self.previous_volume = float(self.volume)

    @property
    def fuel_particles(self):
        return (self.contents["fuel"] / fuel_molar_mass) * avogadro_constant

    @property
    def air_particles(self):
        return (self.contents["air"] / air_molar_mass) * avogadro_constant

    @property
    def exhaust_particles(self):
        return (self.contents["exhaust"] / exhaust_molar_mass) * avogadro_constant

    @property
    def pressure(self):
        particle_count = self.fuel_particles + self.air_particles + self.exhaust_particles
        return (self.temperature * boltzmann_constant * particle_count) / self.volume

    @property
    def external_piston_pressure(self):
        return self.area * atmospheric_pressure

    @property
    def volume(self):
        """ The current volume of the cylinder, at its current crank angle """
        return self.area * (self.height - self.pin_offset)

    @property
    def volume_at_TDC(self):
        return self.area * (self.height - self.crank_radius + self.rod_length)

    @property
    def area(self):
        return math.pi * (self.radius ** 2)

    @property
    def rpm(self):
        return (self.crank_angular_velocity * 60.0) / (2.0 * math.pi)

    @property
    def piston_force(self):
        """ Negative numbers are it "pushing" down and positives are it being "pulled" back up"""
        return (self.pressure - self.external_piston_pressure) * self.area

    @property
    def crank_moment(self):
        theta = self.crank_rotation + (math.pi / 8.0)
        alpha = math.asin((self.crank_radius * math.sin(theta)) / self.rod_length)
        beta = 90 - theta - alpha

        print(self.piston_force)

        return self.crank_radius * (self.piston_force * math.cos(beta))

    @property
    def stroke(self):
        return 2.0 * self.crank_radius

    @property
    def crank_position(self):
        return self.crank_radius * math.sin(self.crank_rotation), self.crank_radius * math.cos(self.crank_rotation)

    @property
    def pin_offset(self):
        """
            l**2 = r**2 + x**2 - 2*r*x*cos(A)

            # To quadratic
            x**2 - 2*r*x*cos(A) + (r**2 - l**2) = 0

            # Solve quadratic
            x = r * cos(A) +/- sqrt( l**2 - (r**2 * sin(A)**2) )
        """

        a = self.crank_radius * math.cos(self.crank_rotation)
        b = math.sqrt((self.rod_length ** 2) - ((self.crank_radius ** 2) * (math.sin(self.crank_rotation) ** 2)))
        return a + b


    def spark(self):
        self.__combusting = True

    @property
    def cp_exhaust(self):
        # baseline ~1.08 kJ/kgK at 300K, slope 8e-5 per K
        return 1.08 + 8e-5 * (self.temperature - 300.0)

    @property
    def cp_air(self):
        """ Fucking guess-estimate my ass """
        return 1.005 + 0.0001 * (self.temperature - 300.0) / 100.0

    @property
    def average_cp(self):
        mass_ex = self.contents["exhaust"]
        mass_air = self.contents["air"]
        return (self.cp_exhaust * mass_ex + self.cp_air * mass_air) / (mass_ex + mass_air + 1e-9)

    def __combust(self, deltaTime):
        # Only burn when piston is moving down (after TDC)
        if math.cos(self.crank_rotation) < 0:
            return  # skip until it's actually pushing down

        fuel_quantity = min(fuel_burn_per_second * 0.1 * deltaTime, self.contents["fuel"])

        air_quantity = fuel_quantity * stoichiometric_air_fuel_ratio

        if air_quantity > self.contents["air"]:
            air_quantity = self.contents["air"]
            fuel_quantity = air_quantity / stoichiometric_air_fuel_ratio

        mass = fuel_quantity + air_quantity + self.contents["exhaust"]
        combustion_energy = fuel_quantity * fuel_energy_per_kg * 0.1

        if combustion_energy == 0:
            self.__combusting = False
            return


        self.temperature += combustion_energy / (mass * self.average_cp)

        self.contents["fuel"] -= fuel_quantity
        self.contents["air"] -= air_quantity

        self.contents["exhaust"] += (fuel_quantity + air_quantity)

    def inject(self, fuel: float, air: float):
        self.contents["fuel"] += fuel
        self.contents["air"] += air

    def exhaust(self):
        volume_change = self.previous_volume - self.volume

        max_exhaust_mass = (atmospheric_pressure * volume_change) / (exhaust_R * self.temperature)

        self.temperature *= 0.99

        for key in ["air", "exhaust"]:
            self.contents[key] -= max_exhaust_mass

            if self.contents[key] < 0:
                self.contents[key] = 0



    def __apply_angular_velocity(self, deltaTime):
        self.crank_rotation += self.crank_angular_velocity * deltaTime

        if self.crank_rotation > 4 * math.pi:
            self.crank_rotation -= 4 * math.pi


    def simulate(self, deltaTime: float):
        self.__apply_angular_velocity(deltaTime)

        if self.__combusting:
            self.__combust(deltaTime)

        new_volume = float(self.volume)

        gamma = 1.4  # for air

        ratio = self.previous_volume / new_volume
        if 1e-4 < ratio < 1e4:
            ratio = max(0.5, min(2.0, ratio))
            self.temperature *= ratio ** (gamma - 1)

        self.temperature -= (self.temperature - ROOM_TEMP) * 0.0001
        self.temperature = max(min(self.temperature, 4000), 250)
        self.previous_volume = new_volume



class Engine:
    def __init__(self):
        self.cylinder_radius_mm = 100
        self.cylinder_height_mm = 80
        self.rod_length_mm = 60
        self.crank_radius_mm = 15
        self.crank_mass_kg = 30

        self.starter_torque = 200  # Nm
        self.friction_coefficient = 0.8

        self.cylinders = [
            Cylinder(self.cylinder_radius_mm / 1000, self.cylinder_height_mm / 1000, self.crank_radius_mm / 1000,
                     self.rod_length_mm / 1000)
        ]

        self.cylinder_stages = []  # Auto generated
        self.fire_order = [0]

        self.__prepare_cylinders()

        assert len(self.cylinders) == len(self.fire_order), "Bad Engine Fire Order!"

        # Engine Computer
        self.last_fire = len(self.fire_order) - 1
        self.starter_timer = 0

        self.fuel_volume_per_cycle = 0.001
        self.idle_fuel_volume_per_cycle = 0.0001
        self.idle_rpm = 1000
        self.throttle = 0

    def __prepare_cylinders(self):
        shift = (4 * math.pi) / len(self.cylinders)
        for i, cylinder in enumerate(self.cylinders):
            cylinder.crank_rotation = i * shift + (math.pi / 8)  # add slight offset

        self.cylinder_stages = [index for index in self.fire_order]

    @property
    def rpm(self):
        return sum([c.rpm for c in self.cylinders]) / len(self.cylinders)

    @property
    def moment_of_inertia(self):
        return self.crank_mass_kg * (self.crank_radius_mm / 1000) ** 2

    def run_starter(self, deltaTime: float):
        angular_acceleration = self.starter_torque / self.moment_of_inertia

        for cylinder in self.cylinders:
            cylinder.crank_angular_velocity += angular_acceleration * deltaTime

    def start(self):
        self.starter_timer = 5.0

    def do_computer(self, deltaTime: float):
        is_starting = self.starter_timer > 0

        if is_starting:
            self.run_starter(deltaTime)
            self.starter_timer -= deltaTime

        fuel_volume = self.fuel_volume_per_cycle * self.throttle
        if self.rpm < self.idle_rpm:
            fuel_volume = self.idle_fuel_volume_per_cycle

        for idx, cylinder in enumerate(self.cylinders):
            stage = (self.fire_order[idx] + ((cylinder.crank_rotation % (4 * math.pi)) // math.pi)) % 4
            if self.cylinder_stages[idx] == stage and stage != 3.0:
                continue

            self.cylinder_stages[idx] = stage
            match stage:
                case 0.0:
                    cylinder.mode = "INJECT"
                    cylinder.inject(fuel_volume, fuel_volume * stoichiometric_air_fuel_ratio)
                    break
                case 1.0:
                    cylinder.mode = "COMPRESS"
                    break

                case 2.0:
                    cylinder.mode = "COMBUST"
                    cylinder.spark()
                    break

                case 3.0:
                    cylinder.mode = "EXHAUST"
                    cylinder.exhaust()
                    break


    def simulate(self, deltaTime: float):
        self.do_computer(deltaTime)

        crank_moment = 0
        for cylinder in self.cylinders:
            cylinder.simulate(deltaTime)
            moment = cylinder.crank_moment
            crank_moment += moment


        angular_acceleration = crank_moment / self.moment_of_inertia

        for cylinder in self.cylinders:
            cylinder.crank_angular_velocity += angular_acceleration * deltaTime
            cylinder.crank_angular_velocity *= self.friction_coefficient
