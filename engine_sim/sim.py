import math

from .constants import *

"""
4 Stroke
Inline 4

All measurements in mm / radians / Kelvin
"""


class Cylinder:
    def __init__(self, radius: float, height: float, crank_radius: float, rod_length: float):
        self.radius = radius
        self.height = height

        self.crank_radius = crank_radius
        self.rod_length = rod_length

        self.displacement = math.pi * (radius ** 2) * self.stroke

        self.crank_rotation = 0.0
        self.crank_angular_velocity = 0.0

        self.temperature = 273 + 21  # kelvin
        self.__combusting = False
        self.mode = "N/A"

        self.contents = {
            "fuel": 0.0,  # kg
            "air": 0.5,  # kg
            "exhaust": 0.1  # kg
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
        return (self.temperature * boltzmann_constant * particle_count) / self.volume  # fixme - make volume based on gas amount, NOT actual volume of cylinder

    @property
    def rpm(self):
        return self.crank_angular_velocity * 60

    @property
    def stroke(self):
        return self.rod_length + self.crank_radius

    @property
    def crank_position(self):
        return self.crank_radius * math.sin(self.crank_rotation), self.crank_radius * math.cos(self.crank_rotation)

    @property
    def volume(self):
        # The pin is basically the head...
        return (self.height - self.pin_offset) * self.area

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
        exhaustA = self.cp_exhaust * self.contents["exhaust"]
        exhaustB = self.cp_exhaust * self.contents["air"]

        return (exhaustA + exhaustB) / (self.contents["exhaust"] + self.contents["air"])

    @property
    def crank_moment(self):
        return self.crank_radius * (self.piston_force * math.sin(self.crank_rotation))

    def __combust(self, deltaTime):
        fuel_quantity = min(fuel_burn_per_second * deltaTime, self.contents["fuel"])
        air_quantity = fuel_quantity * stoichiometric_air_fuel_ratio

        if air_quantity > self.contents["air"]:
            air_quantity = self.contents["air"]
            fuel_quantity = air_quantity / stoichiometric_air_fuel_ratio

        mass = fuel_quantity + air_quantity + self.contents["exhaust"]
        combustion_energy = fuel_quantity * fuel_energy_per_kg

        if combustion_energy == 0:
            self.__combusting = False

        self.temperature += combustion_energy / (mass * self.average_cp)

        self.contents["fuel"] -= fuel_quantity
        self.contents["air"] -= air_quantity
        self.contents["exhaust"] += (fuel_quantity + air_quantity)

    def inject(self, fuel: float, air: float):
        self.contents["fuel"] += fuel
        self.contents["air"] += air

    def exhaust(self):
        max_exhaust_mass = (atmospheric_pressure * self.volume) / (exhaust_R * self.temperature)
        self.contents["exhaust"] = min(max_exhaust_mass, self.contents["exhaust"])
        self.temperature = 273 + 200

    def simulate(self, deltaTime: float):
        if self.__combusting:
            self.__combust(deltaTime)

        start_volume = float(self.volume)
        self.__apply_angular_velocity(deltaTime)
        end_volume = float(self.volume)

        gamma = 1.4  # for air
        self.temperature *= (start_volume / end_volume) ** (gamma - 1)


class Engine:
    def __init__(self):
        self.cylinder_radius_mm = 100
        self.cylinder_height_mm = 80
        self.rod_length_mm = 60
        self.crank_radius_mm = 15
        self.crank_mass_kg = 2

        self.starter_torque = 0.0003  # Nm

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

    def __prepare_cylinders(self):
        shift = (2 * math.pi) / len(self.cylinders)

        for i, cylinder in enumerate(self.cylinders):
            cylinder.crank_rotation = shift * (i + 1)

        self.cylinder_stages = [index for index in self.fire_order]


    @property
    def moment_of_inertia(self):
        return self.crank_mass_kg * (self.crank_radius_mm / 1000) ** 2

    def run_starter(self, deltaTime: float):
        angular_acceleration = self.starter_torque / self.moment_of_inertia

        for cylinder in self.cylinders:
            cylinder.crank_angular_velocity += angular_acceleration * deltaTime

    def start(self):
        self.starter_timer = 2.0

    def do_computer(self, deltaTime: float):
        is_starting = self.starter_timer > 0

        if is_starting:
            self.run_starter(deltaTime)
            self.starter_timer -= deltaTime

        for idx, cylinder in enumerate(self.cylinders):
            stage = (self.fire_order[idx] + ((cylinder.crank_rotation % (4 * math.pi)) // math.pi)) % 4
            if self.cylinder_stages[idx] == stage and stage != 3.0:
                continue

            self.cylinder_stages[idx] = stage
            match stage:
                case 0.0:
                    cylinder.mode = "INJECT"
                    cylinder.inject(self.fuel_volume_per_cycle, self.fuel_volume_per_cycle * stoichiometric_air_fuel_ratio)
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
            crank_moment += moment if moment > 0 else moment * 0.5
            print(f"{cylinder.crank_moment}, ", end="")
        print("")

        angular_acceleration = crank_moment / self.moment_of_inertia


        for cylinder in self.cylinders:
            cylinder.crank_angular_velocity += angular_acceleration * deltaTime
