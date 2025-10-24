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

        self.displacement = math.pi * (radius ** 2) * self.stroke

        self.crank_rotation = 0.0
        self.crank_angular_velocity = 0.0

        self.temperature = ROOM_TEMP  # kelvin
        self.__combusting = False
        self.mode = "N/A"

        self.previous_volume = float(self.volume)

        self.contents = {
            "fuel": 0.0,  # kg
            "air": 0.0,  # kg
            "exhaust": 0.0  # kg
        }

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
    def rpm(self):
        return (self.crank_angular_velocity * 60.0) / (2.0 * math.pi)

    @property
    def stroke(self):
        return 2.0 * self.crank_radius

    @property
    def crank_position(self):
        return self.crank_radius * math.sin(self.crank_rotation), self.crank_radius * math.cos(self.crank_rotation)

    @property
    def volume(self):
        return self.min_volume + (self.piston_travel_from_TDC * self.area)

    @property
    def min_volume(self):
        return (self.height - (self.rod_length + self.crank_radius)) * self.area

    @property
    def area(self):
        return math.pi * (self.radius ** 2)

    @property
    def piston_force(self):
        """
            Pressure = Force / Area
            Force = Pressure * Area
        """
        return (self.pressure - atmospheric_pressure) * self.area

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

    @property
    def piston_travel_from_TDC(self):
        r = self.crank_radius
        l = self.rod_length
        theta = self.crank_rotation
        return r * math.cos(theta) + math.sqrt(max(0.0, l ** 2 - (r * math.sin(theta)) ** 2)) - l

    def __apply_angular_velocity(self, deltaTime):
        self.crank_rotation += self.crank_angular_velocity * deltaTime

        if self.crank_rotation > 4 * math.pi:
            self.crank_rotation -= 4 * math.pi

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

    @property
    def crank_moment(self):
        return self.crank_radius * (self.piston_force * math.sin(self.crank_rotation))

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
        combustion_energy = fuel_quantity * fuel_energy_per_kg

        if combustion_energy == 0:
            self.__combusting = False
            return

        if self.average_cp == 0:
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
        max_exhaust_mass = (atmospheric_pressure * self.volume) / (exhaust_R * self.temperature)

        if abs(max_exhaust_mass) > 10:
            print("[WARNING] Max Exhaust is high:", max_exhaust_mass, (exhaust_R, self.temperature))

        self.contents["exhaust"] -= max_exhaust_mass

        if self.contents["exhaust"] < 0:
            self.contents["exhaust"] = 0

        self.temperature = 273 + 100  # Idk how to do this

    def simulate(self, deltaTime: float):
        if self.__combusting:
            self.__combust(deltaTime)

        self.__apply_angular_velocity(deltaTime)
        end_volume = float(self.volume)

        gamma = 1.4  # for air


        ratio = self.previous_volume / end_volume
        if 1e-4 < ratio < 1e4:
            ratio = max(0.5, min(2.0, ratio))
            self.temperature *= ratio ** (gamma - 1)

        self.temperature -= (self.temperature - ROOM_TEMP) * 0.0001
        self.temperature = max(min(self.temperature, 4000), 250)

        self.previous_volume = end_volume


class Engine:
    def __init__(self):
        self.cylinder_radius_mm = 100
        self.cylinder_height_mm = 80
        self.rod_length_mm = 60
        self.crank_radius_mm = 15
        self.crank_mass_kg = 2

        self.starter_torque = 0.8  # Nm
        self.friction_coefficient = 0.8

        self.cylinders = [
            Cylinder(self.cylinder_radius_mm / 1000, self.cylinder_height_mm / 1000, self.crank_radius_mm / 1000,
                     self.rod_length_mm / 1000),
            Cylinder(self.cylinder_radius_mm / 1000, self.cylinder_height_mm / 1000, self.crank_radius_mm / 1000,
                     self.rod_length_mm / 1000),
            Cylinder(self.cylinder_radius_mm / 1000, self.cylinder_height_mm / 1000, self.crank_radius_mm / 1000,
                     self.rod_length_mm / 1000),
            Cylinder(self.cylinder_radius_mm / 1000, self.cylinder_height_mm / 1000, self.crank_radius_mm / 1000,
                     self.rod_length_mm / 1000),
        ]

        self.cylinder_stages = []  # Auto generated
        self.fire_order = [0, 2, 3, 1]

        self.__prepare_cylinders()

        assert len(self.cylinders) == len(self.fire_order), "Bad Engine Fire Order!"

        # Engine Computer
        self.last_fire = len(self.fire_order) - 1
        self.starter_timer = 0

        self.fuel_volume_per_cycle = 0.001
        self.idle_fuel_volume_per_cycle = 0.000001
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
        self.starter_timer = 10.0

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

        if crank_moment > 0.01:
            print("GOT CRANK MOVEMENT:", crank_moment)

        angular_acceleration = crank_moment / self.moment_of_inertia

        for cylinder in self.cylinders:
            cylinder.crank_angular_velocity += angular_acceleration * deltaTime
            cylinder.crank_angular_velocity *= self.friction_coefficient
