"""Autograder tests for Project 3: Ants vs. SomeBees"""

project_info = {
    'name': 'Project 3: Ants',
    'imports': [
        'from ants import *',
        'import ants',
        'import imp',
        # BEGIN SOLUTION NO PROMPT
        'import ants_sol',
        # END SOLUTION
    ],
    'remote': 'http://inst.eecs.berkeley.edu/~cs61a/sp14/proj/ants/',
    'version': '1.4',
    'hash_key': 'ayigduafmx4rzz004w7uv36q5hhdo08g8thjxkpqtuwh3u5lgka3c5rn1n9nj4n7v6fiaylvv1mkkkv5a1zxfcpp533jjy5g21mcnun0lihgatv1s1009ftikfow2puc'
}

no_lock = {
}

#########
# TESTS #
#########

preamble = """
        hive, layout = Hive(make_test_assault_plan()), test_layout
        colony = AntColony(None, hive, ant_types(), layout)
"""


tests = [
{
# Tests Food costs
    'name': ('Q2', 'q2', '2'),
    'points': 2,
    'suites': [
        [
            ['HarvesterAnt.food_cost', "2"],
            ['ThrowerAnt.food_cost', "4"],
        ],
        [
            ["""
             # Testing HarvesterAnt action
             colony.food = 4
             HarvesterAnt().action(colony)
             $ colony.food
             HarvesterAnt().action(colony)
             $ colony.food
             """,
             ['5', '6']]
        ],
    ]
},
{
# Tests Place exits and entrances
    'name': ('Q3', 'q3', '3'),
    'points': 1,
    'suites': [
        [
            ["""
             ### Simple test for Place
             exit = Place('Test Exit')
             $ exit.exit
             $ exit.entrance
             place = Place('Test Place', exit)
             $ place.exit
             $ exit.entrance
             """,
             [('None', 'exit', 'hive', 'colony.queen'),
              ('None', 'exit' 'hive', 'colony.queen'),
              ('exit', 'None', 'hive', 'colony.queen', 'place'),
              ('place', 'None', 'exit', 'hive', 'colony.queen')]],
            ["""
             ### Testing if entrances are properly initialized
             passed = True
             for entrance in colony.bee_entrances:
                 place = entrance
                 while place:
                     passed = passed and (place.entrance is not None)
                     place = place.exit

             $ passed
             """,
             'True', 'unlock'],
            ["""
             ### Testing if exits and entrances are different
             passed = True
             for place in colony.places.values():
                 passed = passed and \\
                          (place is not place.exit) and \\
                          (place is not place.entrance)
                 if place.exit and place.entrance:
                     passed = passed and (place.exit is not place.entrance)

             $ passed
             """,
             'True', 'unlock'],
        ],
    ]
},
{
# Tests Water
    'name': ('QA4', 'qA4', 'A4'),
    'points': 2,
    'preamble': {
        1: """
        old_add_insect = Place.add_insect
        def new_add_insect(self, insect):
            raise NotImplementedError()
        """,
    },
    'postamble': {
        1: """
        Place.add_insect = old_add_insect
        """,
    },
    'suites': [
        [
            ["""
             When should an insect be added to a Water Place?
             """,
             ('Always; after adding the insect, reduce its armor to 0 if it is not watersafe',
              'Only if the insect is watersafe; if it is not watersafe, reduce its armor to 0',
              'Only if the insect is watersafe; if it is not watersafe, remove the insect from the place',
              'Never; no insect can be placed in a Water Place'),
             'concept'],
            ["""
             What type of variable should "watersafe" be?
             """,
             ('class variable',
              'instance variable',
              'local variable',
              'global variable'),
             'concept'],
            ["""
             What method deals damage to an Insect and removes it from
             its Place? (You should use this method in your code.)
             """,
             ('reduce_armor, in the Insect class',
              'remove_insect, in the Place class',
              'sting, in the Bee class',
              'action, in the Insect class',
              'remove_ant, in the AntColony class'),
             'concept'],
            ["""
             ### Testing water deadliness
             test_ant = HarvesterAnt()
             test_water = Water('Water Test0')
             test_water.add_insect(test_ant)
             $ test_ant.armor
             $ test_water.ant is not test_ant
             """,
             ['0', 'True']],
            ["""
             ### Testing water with soggy (non-watersafe) bees
             test_ants = [Bee(1000000), HarvesterAnt(), Ant(), ThrowerAnt()]
             test_ants[0].watersafe = False # Make Bee non-watersafe
             test_water = Water('Water Test1')
             passed = True
             for test_ant in test_ants:
                 test_water.add_insect(test_ant)
                 passed = passed and \\
                          test_ant is not test_water.ant and \\
                          test_ant.armor == 0

             $ passed
             """,
             'True', 'unlock'],
            ["""
             ### Testing water with watersafe bees
             test_bee = Bee(1)
             test_water = Water('Water Test2')
             test_water.add_insect(test_bee)
             $ test_bee.armor
             $ test_bee in test_water.bees
             """,
             ['1', 'True'], 'unlock'],
        ],
        [
            ["""
             ### Testing water inheritance
             Place.add_insect = new_add_insect
             test_bee = Bee(1)
             test_water = Water('Water Test3')
             passed = False
             try:
                 test_water.add_insect(test_bee)
             except NotImplementedError:
                 passed = True

             $ passed   # Make sure to use inheritance!
             """,
             'True', 'unlock'],
            ["""
             ### Make sure to place the ant before watering it!

             Place.add_insect = new_add_insect
             test_ant = HarvesterAnt()
             test_water = Water('Water Test4')
             passed = False
             try:
                 test_water.add_insect(test_ant)
             except NotImplementedError:
                 passed = True

             $ passed   # Should be True
             """,
             'True', 'unlock'],
        ],
    ]
},
{
# Tests FireAnt
    'name': ('QA5', 'qA5', 'A5'),
    'points': 3,
    'suites': [
        [
            ["""
             ### Testing fire parameters
             fire = FireAnt()
             $ FireAnt.food_cost
             $ fire.armor
             """,
             ['4', '1']],
            ["""
             ### Testing fire damage
             place = Place('Fire Test1')
             bee = Bee(5)
             place.add_insect(bee)
             place.add_insect(FireAnt())
             bee.action(colony) # attack the FireAnt
             $ bee.armor
             """,
             '2'],
        ],
        [
            ["""
             ### Testing fire does damage to all Bees in its Place
             place = Place('Fire Test2')
             bee = Bee(3)
             place.add_insect(bee)
             place.add_insect(Bee(3))
             place.add_insect(FireAnt())
             bee.action(colony) # attack the FireAnt
             $ len(place.bees)  # How many bees are left?
             """,
             '0'],
            ["""
             ### Testing FireAnt dies
             place = Place('Fire Test3')
             bee = Bee(1)
             ant = FireAnt()
             place.add_insect(bee)
             place.add_insect(ant)
             bee.action(colony) # attack the FireAnt
             $ ant.armor
             """,
             '0'],
        ],
        [
            ["""
             ### Testing fire damage is instance attribute
             place = Place('Fire Test4')
             bee = Bee(900)
             buffAnt = ants.FireAnt()
             buffAnt.damage = 500   # Feel the burn!
             place.add_insect(bee)
             place.add_insect(buffAnt)
             bee.action(colony) # attack the FireAnt
             $ bee.armor    # is damage an instance attribute?
             """,
             '400'],
        ],
    ]
},
{
# Tests ThrowerAnt
    'name': ('QB4', 'qB4', 'B4'),
    'points': 2,
    'suites': [
        [
            ["""
             What function selects a random bee from a list of bees?
             """,
             ('random_or_none, defined in ant.py',
              'random.random(), defined in the "random" module',
              'getitem, defined in the "operators" module'),
             'concept'],
            ["""
             ### Testing nearest_bee
             thrower = ThrowerAnt()
             colony.places['tunnel_0_0'].add_insect(thrower)
             place = colony.places['tunnel_0_0']
             near_bee = Bee(2)
             far_bee = Bee(2)
             colony.places["tunnel_0_3"].add_insect(near_bee)
             colony.places["tunnel_0_6"].add_insect(far_bee)
             hive = colony.hive
             $ thrower.nearest_bee(hive) # near_bee or far_bee ?
             thrower.action(colony)      # Attack!
             $ near_bee.armor            # Should do 1 damage
             $ thrower.place             # Don't change self.place!
             """,
             [('near_bee', 'far_bee', 'None'),
              '1',
              ('place', 'hive', 'colony.queen', 'None')]],
            ["""
             ### Testing Nearest bee not in the hive
             thrower = ThrowerAnt()
             colony.places["tunnel_0_0"].add_insect(thrower)
             hive = colony.hive
             bee = Bee(2)
             hive.add_insect(bee)           # adding a bee to the hive
             $ thrower.nearest_bee(hive)    # bee or None ?
             """,
             ('None', 'bee', 'thrower', 'hive')],
        ],
        [
            ["""
             ### Test that ThrowerAnt attacks bees on its own square
             thrower = ThrowerAnt()
             colony.places['tunnel_0_0'].add_insect(thrower)
             near_bee = Bee(2)
             colony.places["tunnel_0_0"].add_insect(near_bee)
             $ thrower.nearest_bee(colony.hive)   # near_bee or None ?
             thrower.action(colony)     # Attack!
             $ near_bee.armor           # should do 1 damage
             """,
             [('near_bee', 'None', 'thrower', 'hive'), '1']],
            ["""
             ### Testing ThrowerAnt chooses a random target
             thrower = ThrowerAnt()
             colony.places["tunnel_0_0"].add_insect(thrower)
             bee1 = Bee(1001)
             bee2 = Bee(1001)
             colony.places["tunnel_0_3"].add_insect(bee1)
             colony.places["tunnel_0_3"].add_insect(bee2)
             # Throw 1000 times. The first bee should take ~1000*1/2 = ~500 damage,
             # and have ~501 remaining.
             for _ in range(1000):
                 thrower.action(colony)

             # Test if damage to bee1 is within 6 standard deviations (~95 damage)
             # If bees are chosen uniformly, this is true 99.9999998% of the time.
             def dmg_within_tolerance():
                 return abs(bee1.armor-501) < 95

             $ dmg_within_tolerance()
             """,
             'True', 'unlock'],
        ],
    ]
},
{
# Tests LongThrower and ShortThrower
    'name': ('QB5', 'qB5', 'B5'),
    'points': 3,
    'preamble': {
        0: """
        def new_action(self, colony):
            raise NotImplementedError()

        def new_throw_at(self, target):
            raise NotImplementedError()

        old_thrower_action = ThrowerAnt.action
        old_throw_at = ThrowerAnt.throw_at
        """,
    },
    'postamble': {
        0: """
        ThrowerAnt.action = old_thrower_action
        ThrowerAnt.throw_at = old_throw_at
        """,
    },
    'suites': [
        [
            ["""
             ### Testing Long/ShortThrower paramters
             short_t = ShortThrower()
             long_t = LongThrower()
             $ ShortThrower.food_cost
             $ LongThrower.food_cost
             $ short_t.armor
             $ long_t.armor
             """,
             ['3', '3', '1', '1']],
            ["""
             ### Testing LongThrower Inheritance from ThrowerAnt
             ThrowerAnt.action = new_action
             test_long = LongThrower()
             passed = 0
             try:
                 test_long.action(colony)
             except NotImplementedError:
                 passed += 1

             ThrowerAnt.action = old_thrower_action
             ThrowerAnt.throw_at = new_throw_at
             test_long = LongThrower()
             try:
                 test_long.throw_at(Bee(1))
             except NotImplementedError:
                 passed += 1

             ThrowerAnt.throw_at = old_throw_at
             $ passed
             """,
             '2', 'unlock'],
            ["""
             ### Testing ShortThrower Inheritance from ThrowerAnt
             ThrowerAnt.action = new_action
             test_short = ShortThrower()
             passed = 0
             try:
                 test_short.action(colony)
             except NotImplementedError:
                 passed += 1

             ThrowerAnt.action = old_thrower_action
             ThrowerAnt.throw_at = new_throw_at
             test_short = ShortThrower()
             try:
                 test_short.throw_at(Bee(1))
             except NotImplementedError:
                 passed += 1

             ThrowerAnt.throw_at = old_throw_at
             $ passed
             """,
             '2', 'unlock'],
        ],
        [
            ["""
             ### Test LongThrower Hit
             ant = LongThrower()
             in_range = Bee(2)
             colony.places['tunnel_0_0'].add_insect(ant)
             colony.places["tunnel_0_4"].add_insect(in_range)
             ant.action(colony)
             $ in_range.armor
             """,
             '1'],
            ["""
             ### Testing LongThrower miss
             ant = LongThrower()
             out_of_range = Bee(2)
             colony.places["tunnel_0_0"].add_insect(ant)
             colony.places["tunnel_0_3"].add_insect(out_of_range)
             ant.action(colony)
             $ out_of_range.armor
             """,
             '2'],
        ],
        [
            ["""
             ### Test ShortThrower hit
             ant = ShortThrower()
             in_range = Bee(2)
             colony.places['tunnel_0_0'].add_insect(ant)
             colony.places["tunnel_0_2"].add_insect(in_range)
             ant.action(colony)
             $ in_range.armor
             """,
             '1'],
            ["""
             ### Testing ShortThrower miss
             ant = ShortThrower()
             out_of_range = Bee(2)
             colony.places["tunnel_0_0"].add_insect(ant)
             colony.places["tunnel_0_3"].add_insect(out_of_range)
             ant.action(colony)
             $ out_of_range.armor
             """,
             '2'],
            ["""
             ### Testing if max_range is looked up in the instance
             ant = ShortThrower()
             ant.max_range = 10     # Buff the ant's range
             colony.places["tunnel_0_0"].add_insect(ant)
             bee = Bee(2)
             colony.places["tunnel_0_6"].add_insect(bee)
             ant.action(colony)
             $ bee.armor
             """,
             '1'],
        ],
    ]
},
{
# Tests WallAnt
    'name': ('QA6', 'qA6', 'A6'),
    'points': 1,
    'suites': [
        [
            ["""
             ### Testing WallAnt parameters
             wall = WallAnt()
             $ wall.armor
             $ WallAnt.food_cost
             """,
             ['4', '4']],
        ],
    ]
},
{
# Tests NinjaAnt
    'name': ('QA7', 'qA7', 'A7'),
    'points': 3,
    'suites': [
        [
            ["""
             ### Testing NinjaAnt parameters
             ninja = NinjaAnt()
             $ ninja.armor
             $ NinjaAnt.food_cost
             """,
             ['1', '6']],
            ["""
             ### Testing non-NinjaAnts do not block bees
             p0 = colony.places["tunnel_0_0"]
             p1 = colony.places["tunnel_0_1"]
             bee = Bee(2)
             p1.add_insect(bee)
             p1.add_insect(ThrowerAnt())
             bee.action(colony)  # attack ant, don't move past it
             $ bee.place
             """,
             ('p1', 'p0', 'None')],
        ],
        [
            ["""
             ### Testing NinjaAnts do block bees
             p0 = colony.places["tunnel_0_0"]
             p1 = colony.places["tunnel_0_1"]
             bee = Bee(2)
             p1.add_insect(bee)
             p1.add_insect(NinjaAnt())
             bee.action(colony)  # shouldn't attack ant, move past it
             $ bee.place
             """,
             ('p0', 'p1', 'None')],
            ["""
             ### Testing NinjaAnt strikes all bees in its place
             test_place = colony.places["tunnel_0_0"]
             for _ in range(3):
                 test_place.add_insect(Bee(1))

             ninja = NinjaAnt()
             test_place.add_insect(ninja)
             ninja.action(colony)   # should strike all bees in place
             $ len(test_place.bees)
             """,
             '0'],
        ],
        [
            ["""
             ### Testing damage is looked up on the instance
             place = colony.places["tunnel_0_0"]
             bee = Bee(900)
             place.add_insect(bee)
             buffNinja = NinjaAnt()
             buffNinja.damage = 500  # Sharpen the sword
             place.add_insect(buffNinja)
             buffNinja.action(colony)
             $ bee.armor
             """,
             '400'],
        ],
    ]
},
{
# Tests ScubaThrower
    'name': ('QB6', 'qB6', 'B6'),
    'points': 1,
    'preamble': {
        0: """
        def new_action(self, colony):
            raise NotImplementedError()

        def new_throw_at(self, target):
            raise NotImplementedError()

        old_thrower_action = ThrowerAnt.action
        old_throw_at = ThrowerAnt.throw_at
        """,
    },
    'postamble': {
        0: """
        ThrowerAnt.action = old_thrower_action
        ThrowerAnt.throw_at = old_throw_at
        """,
    },
    'suites': [
        [
            ["""
             ### Testing ScubaThrower parameters

             scuba = ScubaThrower()
             $ ScubaThrower.food_cost
             $ scuba.armor
             """,
             ['5', '1']],
            ["""
             ### Testing ScubaThrower Inheritance from ThrowerAnt

             ThrowerAnt.action = new_action
             test_scuba = ScubaThrower()
             passed = 0
             try:
                 test_scuba.action(colony)
             except NotImplementedError:
                 passed += 1

             ThrowerAnt.action = old_thrower_action
             ThrowerAnt.throw_at = new_throw_at
             test_scuba = ScubaThrower()
             try:
                 test_scuba.throw_at(Bee(1))
             except NotImplementedError:
                 passed += 1

             ThrowerAnt.throw_at = old_throw_at
             $ passed
             """,
             '2', 'unlock'],
            ["""
             ### Testing if ScubaThrower is watersafe
             water = Water('Water')
             ant = ScubaThrower()
             water.add_insect(ant)
             $ ant.place
             $ ant.armor
             """,
             ['water', '1']],
        ],
        [
            ["""
             ### Testing ScubaThrower on land
             place1 = colony.places["tunnel_0_0"]
             place2 = colony.places["tunnel_0_4"]
             ant = ScubaThrower()
             bee = Bee(3)
             place1.add_insect(ant)
             place2.add_insect(bee)
             ant.action(colony)
             $ bee.armor    # ScubaThrower can throw on land
             """,
             '2'],
            ["""
             ### Testing ScubaThrower in the water
             water = Water("water")
             water.entrance = colony.places["tunnel_0_1"]
             target = colony.places["tunnel_0_4"]
             ant = ScubaThrower()
             bee = Bee(3)
             water.add_insect(ant)
             target.add_insect(bee)
             ant.action(colony)
             $ bee.armor    # ScubaThrower can throw in water
             """,
             '2'],
        ],
    ]
},
{
# Tests HungryAnt
    'name': ('QB7', 'qB7', 'B7'),
    'points': 3,
    'suites': [
        [
            ["""
             ### Testing HungryAnt parameters
             hungry = HungryAnt()
             $ HungryAnt.food_cost
             $ hungry.armor
             """,
             ['4', '1']],
            ["""
             ### Testing HungryAnt eats and digests
             hungry = HungryAnt()
             super_bee, wimpy_bee = Bee(1000), Bee(1)
             place = colony.places["tunnel_0_0"]
             place.add_insect(hungry)
             place.add_insect(super_bee)
             hungry.action(colony)   # super_bee is no match for HungryAnt!
             $ super_bee.armor

             place.add_insect(wimpy_bee)
             for _ in range(3):
                 hungry.action(colony)  # digesting...not eating

             $ wimpy_bee.armor

             hungry.action(colony)      # back to eating!
             $ wimpy_bee.armor
             """,
             ['0', '1', '0']],
        ],
        [
            ["""
             ### Testing HungryAnt only waits when digesting
             hungry = HungryAnt()
             place = colony.places["tunnel_0_0"]
             place.add_insect(hungry)
             # Wait a few turns before adding Bee
             for _ in range(5):
                 hungry.action(colony)  # shouldn't be digesting

             bee = Bee(3)
             place.add_insect(bee)
             hungry.action(colony)  # Eating time!
             $ bee.armor
             """,
             '0'],
        ],
        [
            ["""
             ### Testing HungryAnt digest time looked up on instance
             very_hungry = HungryAnt()  # Add very hungry caterpi- um, ant
             very_hungry.time_to_digest = 0
             place = colony.places["tunnel_0_0"]
             place.add_insect(very_hungry)
             for _ in range(100):
                 place.add_insect(ants.Bee(3))

             for _ in range(100):
                 very_hungry.action(colony)   # Eat all the bees!

             $ len(place.bees)
             """,
             '0'],
        ],
    ]
},
{
# Tests BodyguardAnt
    'name': ('Q8', 'q8', '8'),
    'points': 5,
    'preamble': {
        'all': """
        place = Place("TestProblem8")
        bodyguard = BodyguardAnt()
        bodyguard2 = BodyguardAnt()
        test_ant = Ant()
        test_ant2 = Ant()
        harvester = HarvesterAnt()
        """,
    },
    'suites': [
        [
            ["""
             ### Testing BodyguardAnt parameters
             bodyguard = BodyguardAnt()
             $ BodyguardAnt.food_cost
             $ bodyguard.armor
             """,
             ['4', '2']],
            ["""
             ### Testing BodyguardAnt starts off empty
             $ bodyguard.ant
             bodyguard.action(colony)
             """,
             'None'],
            ["""
             ### Testing BodyguardAnt contain_ant
             bodyguard.contain_ant(test_ant)
             $ bodyguard.ant
             """,
             ('test_ant', 'bodyguard.ant', 'None')],
            ["""
             ### Testing BodyguardAnt is_container
             $ bodyguard.container
             """,
             'True'],
            ["""
             ### Testing normal Ant is_container is false
             $ test_ant.container
             """,
             'False'],
        ],
        [
            ["""
             ### Testing bodyguard.can_contain returns True on non-containers
             $ bodyguard.can_contain(test_ant)
             """,
             'True'],
            ["""
             ### Testing normal_ant.can_contain returns False
             $ test_ant.can_contain(test_ant2)
             """,
             'False'],
            ["""
             ### Testing bodyguard.can_contain returns False on otherbodyguards
             $ bodyguard.can_contain(bodyguard2)
             """,
             'False'],
            ["""
             ### Testing bodyguard.can_contain returns False once it is already containing
             bodyguard.contain_ant(test_ant)
             $ bodyguard.can_contain(test_ant2)
             """,
             'False'],
        ],
        [
            ["""
             ### Testing modified add_insect test 1
             place.add_insect(bodyguard)
             place.add_insect(test_ant)
             $ bodyguard.ant is test_ant
             $ place.ant is bodyguard
             """,
             ['True', 'True']],
            ["""
             ### Testing modified add_insect test 2
             place.add_insect(test_ant)
             place.add_insect(bodyguard)
             $ bodyguard.ant is test_ant
             $ place.ant is bodyguard
             """,
             ['True', 'True']],
            ["""
             ### Testing modified add_insect test 3
             place.add_insect(bodyguard)
             $ place is bodyguard.place
             passed = False
             try:
                 place.add_insect(bodyguard2)  # can't add bodyguard in another bodyguard
             except AssertionError:
                 passed = True

             $ passed
             """,
             ['True', 'True'], 'unlock'],
            ["""
             ### Testing modified add_insect test 4
             place.add_insect(bodyguard)
             place.add_insect(test_ant)
             passed = False
             try:
                 place.add_insect(test_ant2)  # can't add third ant
             except AssertionError:
                 passed = True

             $ passed
             """,
             'True', 'unlock'],
        ],
        [
            ["""
             ### Testing what happens if bodyguard ant perishes
             place.add_insect(bodyguard)
             place.add_insect(test_ant)
             bodyguard.reduce_armor(bodyguard.armor)
             $ place.ant is test_ant
             """,
             'True'],
            ["""
             ### Testing bodyguard performs contained ant's action
             food = colony.food
             bodyguard.contain_ant(harvester)
             bodyguard.action(colony)   # should do harvester's action
             $ colony.food
             """,
             ('food + 1', 'food', '0', '1')],
            ["""
             ### Testing bodyguard performs thrower's action
             ant = ThrowerAnt()
             bee = ants.Bee(2)
             colony.places["tunnel_0_0"].add_insect(bodyguard)
             colony.places["tunnel_0_0"].add_insect(ant)
             colony.places["tunnel_0_3"].add_insect(bee)
             bodyguard.action(colony)
             $ bee.armor
             """,
             '1'],
            ["""
             ### Testing removing a bodyguard doesn't remove contained ant
             place = colony.places['tunnel_0_0']
             bodyguard = BodyguardAnt()
             test_ant = Ant(1)
             place.add_insect(bodyguard)
             place.add_insect(test_ant)
             colony.remove_ant('tunnel_0_0')
             $ place.ant is test_ant
             """,
             'True'],
            ["""
             ### Testing bodyguarded ant does action of contained ant
             test_ant = Ant()
             def new_action( colony):
                 test_ant.armor += 9000
             test_ant.action = new_action

             place = colony.places['tunnel_0_0']
             bodyguard = BodyguardAnt()
             place.add_insect(test_ant)
             place.add_insect(bodyguard)
             place.ant.action(colony)
             $ place.ant.ant.armor
             """,
             '9001'],
        ],
        [
            ["""
             ### Testing if we can construct a container besides BodyGuard
             ant = ThrowerAnt()
             ant.container = True
             ant.ant = None
             $ ant.can_contain(ThrowerAnt())
             """,
             'True'],
            ["""
             ### Testing container doesn't contain other container
             bodyguard = BodyguardAnt()
             mod_guard = BodyguardAnt()
             mod_guard.container = False
             $ bodyguard.can_contain(mod_guard)
             """,
             'True'],
        ],
    ]
},
{
# Tests QueenAnt
    'name': ('Q9', 'q9', '9'),
    'points': 5,
    'preamble': {
        'all': """
        def queen_layout(queen, register_place, steps=5):
            "Create a two-tunnel layout with water in the middle of 5 steps."
            for tunnel in range(2):
                exit = queen
                for step in range(steps):
                    place = ants.Water if step == steps//2 else ants.Place
                    exit = place('tunnel_{0}_{1}'.format(tunnel, step), exit)
                    register_place(exit, step == steps-1)

        imp.reload(ants)
        hive = ants.Hive(ants.make_test_assault_plan())
        colony = ants.AntColony(None, hive, ants.ant_types(), queen_layout)
        queen = ants.QueenAnt()
        imposter = ants.QueenAnt()
        """,
    },
    'suites': [
        [
            ["""
             ### Testing queen place
             colony_queen = ants.Place('Original Queen Location of the Colony')
             ant_queen = ants.Place('Place given to the QueenAnt')
             queen_place = ants.QueenPlace(colony_queen, ant_queen)
             colony_queen.bees = [ants.Bee(1, colony_queen) for _ in range(3)]
             ant_queen.bees = [ants.Bee(2, colony_queen) for _ in range(4)]
             $ len(queen_place.bees)
             bee_armor = sum(bee.armor for bee in queen_place.bees)
             $ bee_armor
             """,
             ['7', '11']],
        ],
        [
            ["""
             ### Testing double damage
             back = ants.ThrowerAnt()
             thrower_damage = back.damage
             front = ants.FireAnt()
             fire_damage = front.damage
             side_back = ants.ThrowerAnt()
             side_front = ants.ThrowerAnt()
             armor, side_armor = 20, 10
             bee, side_bee = ants.Bee(armor), ants.Bee(side_armor)

             colony.places['tunnel_0_0'].add_insect(back)
             colony.places['tunnel_0_2'].add_insect(queen)
             colony.places['tunnel_0_4'].add_insect(bee)
             colony.places['tunnel_1_1'].add_insect(side_back)
             colony.places['tunnel_1_3'].add_insect(side_front)
             colony.places['tunnel_1_4'].add_insect(side_bee)

             # Simulate a battle in Tunnel 0 (contains Queen)
             back.action(colony)
             armor -= thrower_damage  # No doubling until queen's action
             $ bee.armor # if failed, damage doubled too early
             queen.action(colony)
             armor -= thrower_damage  # Queen should always deal normal damage
             $ bee.armor # if failed, Queen damage incorrect
             bee.action(colony)  # Bee moves forward
             colony.places['tunnel_0_3'].add_insect(front)  # Fire ant added
             back.action(colony)
             armor -= 2 * thrower_damage  # Damage doubled in back
             $ bee.armor  # if failed, back damage incorrect
             queen.action(colony)
             armor -= thrower_damage  # Queen should always deal normal damage
             $ bee.armor # If failed, Queen damage incorrect (2)
             back.action(colony)
             armor -= 2 * thrower_damage  # Thrower damage still doubled
             $ bee.armor # Back damage incorrect
             bee.action(colony)
             armor -= 2 * fire_damage  # Fire damage doubled
             $ bee.armor # if failed, Fire damage incorrect

             # Simulate a battle in Tunnel 1 (no Queen)
             $ side_bee.armor  # if failed, side bee took damage when it shouldn't have
             side_back.action(colony)
             side_armor -= thrower_damage  # Ant in another tunnel: normal damage
             $ side_bee.armor # If failed, side back damage is incorrect
             side_front.action(colony)
             side_armor -= thrower_damage  # Ant in another tunnel: normal damage
             $ side_bee.armor # If failed, side front damage is incorrect
             """,
             ['armor', 'armor', 'armor', 'armor', 'armor', 'armor',
              'side_armor', 'side_armor', 'side_armor']],
        ],
        [
            ["""
             ### Testing Game ends when Queen dies
             bee = ants.Bee(3)
             colony.places['tunnel_0_1'].add_insect(queen)
             colony.places['tunnel_0_2'].add_insect(bee)
             queen.action(colony)
             $ len(colony.queen.bees) <= 0 # If failed, Game ended before it should have
             bee.action(colony)
             $ len(colony.queen.bees) > 0 # Game should have ended
             """,
             ['True', 'True']],
            ["""
             ### Testing Imposter Queen
             ant = ants.ThrowerAnt()
             bee = ants.Bee(10)

             colony.places['tunnel_0_0'].add_insect(queen)
             colony.places['tunnel_0_1'].add_insect(imposter)
             colony.places['tunnel_0_3'].add_insect(ant)
             colony.places['tunnel_0_4'].add_insect(bee)

             imposter.action(colony)
             $ bee.armor   # Imposter should not damage bee
             $ ant.damage  # Imposter should double damage

             queen.action(colony)
             $ bee.armor   # Queen should damage bee
             $ ant.damage  # Queen should double damage
             ant.action(colony)
             $ bee.armor   # If failed, ThrowerAnt has incorrect damage

             $ queen.armor     # Long live the Queen
             $ imposter.armor  # Imposter should die
             """,
             ['10', '1', '9', '2', '7', '1', '0']],
        ],
        [
            ["""
             ### Testing bodyguard doubling
             bee = ants.Bee(3)
             guard = ants.BodyguardAnt()
             guard.damage, doubled = 5, 10
             colony.places['tunnel_0_1'].add_insect(queen)
             colony.places['tunnel_0_1'].add_insect(guard)
             colony.places['tunnel_0_2'].add_insect(bee)
             queen.action(colony)
             $ guard.damage # Bodyguard should be buffed

             queen.action(colony)
             $ bee.armor     # QueenAnt should not have been buffed
             $ guard.damage  # Bodyguard should not be buffed twice
             $ len(colony.queen.bees) <= 0 # Game should not have ended
             bee.action(colony)
             $ len(colony.queen.bees) > 0 # Game should have ended
             """,
             ['doubled', '1', 'doubled', 'True', 'True']],
            ["""
             ### Testing bodyguard contain doubling
             guard = ants.BodyguardAnt()
             guard.damage, doubled = 5, 10
             ant = ants.ThrowerAnt()
             ant_doubled = 2 * ant.damage
             colony.places['tunnel_0_1'].add_insect(queen)
             colony.places['tunnel_0_3'].add_insect(guard)
             colony.places['tunnel_0_3'].add_insect(ant)
             queen.action(colony)
             $ guard.damage # Bodyguard damage should have doubled
             $ ant.damage   # Contained ant should be buffed

             queen.action(colony)
             $ guard.damage # Bodyguard should not be buffed twice
             $ ant.damage   # contained ant should not be buffed twice
             """,
             ['doubled', 'ant_doubled', 'doubled', 'ant_doubled']],
        ],
        [
            ["""
             ### Testing Remove
             p0 = colony.places['tunnel_0_0']
             p1 = colony.places['tunnel_0_1']
             p0.add_insect(queen)
             p1.add_insect(imposter)
             p0.remove_insect(queen)
             p1.remove_insect(imposter)
             $ queen == p0.ant # Queen can't be removed
             $ p1.ant          # Imposter should have been removed
             queen.action(colony)
             """,
             ['True', 'None']],
            ["""
             ### Testing Die the old fashioned way
             bee = ants.Bee(3)
             # The bee has an uninterrupted path to the heart of the colony
             colony.places['tunnel_0_1'].add_insect(bee)
             colony.places['tunnel_0_2'].add_insect(queen)
             queen.action(colony)
             bee.action(colony)
             $ len(colony.queen.bees) <= 0 # Game should not be over
             queen.action(colony)
             bee.action(colony)
             $ len(colony.queen.bees) > 0 # Game should have ended
             """,
             ['True']*2],
            ["""
             ### Testing if queen will buff newly added ants
             colony.places['tunnel_0_0'].add_insect(ants.ThrowerAnt())
             colony.places['tunnel_0_2'].add_insect(queen)
             queen.action(colony)
             # Add ant and buff
             ant = ants.ThrowerAnt()
             colony.places['tunnel_0_1'].add_insect(ant)
             queen.action(colony)
             # Attack a bee
             bee = ants.Bee(3)
             colony.places['tunnel_0_4'].add_insect(bee)
             ant.action(colony)
             $ bee.armor # Queen should buff new ants
             """,
             '1'],
        ],
    ]
},
{
# Tests Extra Credit
    'name': ('EC', 'ec', 'extra'),
    'points': 2,
    'extra': True,
    'suites': [
        [
            ["""
             ### Testing status parameters
             slow = SlowThrower()
             stun = StunThrower()
             $ SlowThrower.food_cost
             $ StunThrower.food_cost
             $ slow.armor
             $ stun.armor
             """,
             ['4', '6', '1', '1']],
            ["""
             ### Testing Slow
             slow = SlowThrower()
             bee = Bee(3)
             colony.places["tunnel_0_0"].add_insect(slow)
             colony.places["tunnel_0_4"].add_insect(bee)
             slow.action(colony)
             colony.time = 1
             bee.action(colony)
             $ bee.place.name # SlowThrower should cause slowness on odd turns
             colony.time += 1
             bee.action(colony)
             $ bee.place.name # SlowThrower should cause slowness on odd turns
             for _ in range(3):
                 colony.time += 1
                 bee.action(colony)

             $ bee.place.name
             """,
             ["'tunnel_0_4'", "'tunnel_0_3'", "'tunnel_0_1'"]],
            ["""
             ### Testing Stun
             error_msg = "StunThrower doesn't stun for exactly one turn."
             stun = StunThrower()
             bee = Bee(3)
             colony.places["tunnel_0_0"].add_insect(stun)
             colony.places["tunnel_0_4"].add_insect(bee)
             stun.action(colony)
             bee.action(colony)
             $ bee.place.name # StunThrower should stun for exactly one turn
             bee.action(colony)
             $ bee.place.name # StunThrower should stun for exactly one turn
             """,
             ["'tunnel_0_4'", "'tunnel_0_3'"]],
        ],
        [
            ["""
             ### Testing if effects stack
             stun = StunThrower()
             bee = Bee(3)
             stun_place = colony.places["tunnel_0_0"]
             bee_place = colony.places["tunnel_0_4"]
             stun_place.add_insect(stun)
             bee_place.add_insect(bee)
             for _ in range(4): # stun bee four times
                 stun.action(colony)

             passed = True
             for _ in range(4):
                 bee.action(colony)
                 if bee.place.name != 'tunnel_0_4':
                     passed = False

             $ passed
             """,
             'True'],
            ["""
             ### Testing multiple stuns
             stun1 = StunThrower()
             stun2 = StunThrower()
             bee1 = Bee(3)
             bee2 = Bee(3)

             colony.places["tunnel_0_0"].add_insect(stun1)
             colony.places["tunnel_0_1"].add_insect(bee1)
             colony.places["tunnel_0_2"].add_insect(stun2)
             colony.places["tunnel_0_3"].add_insect(bee2)

             stun1.action(colony)
             stun2.action(colony)
             bee1.action(colony)
             bee2.action(colony)

             $ bee1.place.name
             $ bee2.place.name

             bee1.action(colony)
             bee2.action(colony)

             $ bee1.place.name
             $ bee2.place.name
             """,
             ["'tunnel_0_1'", "'tunnel_0_3'", "'tunnel_0_0'", "'tunnel_0_2'"]],
            ["""
             ### Testing long effect stack
             stun = StunThrower()
             slow = SlowThrower()
             bee = Bee(3)
             colony.places["tunnel_0_0"].add_insect(stun)
             colony.places["tunnel_0_1"].add_insect(slow)
             colony.places["tunnel_0_4"].add_insect(bee)
             for _ in range(3): # slow bee three times
                 slow.action(colony)

             stun.action(colony) # stun bee once

             colony.time = 0
             bee.action(colony) # stunned
             $ bee.place.name

             colony.time = 1
             bee.action(colony) # slowed thrice
             $ bee.place.name

             colony.time = 2
             bee.action(colony) # slowed thrice
             $ bee.place.name

             colony.time = 3
             bee.action(colony) # slowed thrice
             $ bee.place.name

             colony.time = 4
             bee.action(colony) # slowed twice
             $ bee.place.name

             colony.time = 5
             bee.action(colony) # slowed twice
             $ bee.place.name

             colony.time = 6
             bee.action(colony) # slowed once
             $ bee.place.name

             colony.time = 7
             bee.action(colony) # no effects
             $ slow.armor
             """,
             ["'tunnel_0_4'", "'tunnel_0_4'", "'tunnel_0_3'", "'tunnel_0_3'", "'tunnel_0_2'", "'tunnel_0_2'", "'tunnel_0_1'", '0']],
        ],
    ]
},

]

