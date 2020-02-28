import sys
import os
from mpi4py import MPI
import numpy as np

sys.path.append("{}/../src".format(os.path.dirname(os.path.abspath(__file__))))

import unittest
from repast4py import core, space
from repast4py.space import BorderType, OccupancyType

# run with -n 9

# void create_test_comm(MPI_Comm* test_comm) {
#     MPI_Group world_group;
#     MPI_Comm_group(MPI_COMM_WORLD, &world_group);
#     const int exclude[1] = {8};
#     MPI_Group test_group;
#     MPI_Group_excl(world_group, 1, exclude, &test_group);
#     MPI_Comm_create_group(MPI_COMM_WORLD, test_group, 0, test_comm);
# }


def mp(x, y):
    return space.DiscretePoint(x, y)

def make_move(grid, agent, x, y, target, expected):
    grid.move(agent, space.DiscretePoint(x, y))
    expected[agent.uid] = (target, np.array([x, y, 0]))
    
class SharedGridTests(unittest.TestCase):

    long_message = True

    def test_ops(self):
        new_group = MPI.COMM_WORLD.Get_group().Incl([0, 1])
        comm = MPI.COMM_WORLD.Create_group(new_group)
    
        if comm != MPI.COMM_NULL:
            rank = comm.Get_rank()

            a1 = core.Agent(1, 0, rank)
            a2 = core.Agent(2, 0, rank)

            box = space.BoundingBox(xmin=0, xextent=20, ymin=0, yextent=40, zmin=0, zextent=0)
            grid = space.SharedGrid("shared_grid", bounds=box, borders=BorderType.Sticky, 
                occupancy=OccupancyType.Multiple, buffersize=2, comm=comm)

            grid.add(a1)
            grid.add(a2)

            if (rank == 0):
                pt = space.DiscretePoint(5, 20)
                grid.move(a1, pt)
                self.assertEqual(a1, grid.get_agent(pt))
                self.assertEqual(pt, grid.get_location(a1))

                agents = grid.get_agents(pt)
                expected = [a1]
                count  = 0
                for i, agent in enumerate(agents):
                    self.assertEqual(expected[i], agent)
                    count += 1
                self.assertEqual(1, count)

                grid.remove(a1)
                self.assertIsNone(grid.get_agent(pt))


            if (rank == 1):
                pt = space.DiscretePoint(12, 39)
                grid.move(a2, pt)
                self.assertEqual(a2, grid.get_agent(pt))
                self.assertEqual(pt, grid.get_location(a2))

                a3 = core.Agent(1, 0, rank)
                grid.add(a3)
                grid.move(a3, pt)

                agents = grid.get_agents(pt)
                expected = [a2, a3]
                count  = 0
                for i, agent in enumerate(agents):
                    self.assertEqual(expected[i], agent)
                    count += 1
                self.assertEqual(2, count)

    def test_oob(self):
        new_group = MPI.COMM_WORLD.Get_group().Incl([0, 1])
        comm = MPI.COMM_WORLD.Create_group(new_group)
        

        if comm != MPI.COMM_NULL:
            rank = comm.Get_rank()

            a1 = core.Agent(1, 0, rank)
            a2 = core.Agent(2, 0, rank)

            box = space.BoundingBox(xmin=0, xextent=20, ymin=0, yextent=40, zmin=0, zextent=0)
            grid = space.SharedGrid("shared_grid", bounds=box, borders=BorderType.Sticky, 
                occupancy=OccupancyType.Multiple, buffersize=2, comm=comm)

            grid.add(a1)
            grid.add(a2)

            if (rank == 0):
                pt = space.DiscretePoint(5, 20)
                grid.move(a1, pt)
                # move out of bounds
                pt = space.DiscretePoint(12, 22)
                grid.move(a1, pt)

                expected = {(1, 0, 0) : (1, np.array([12, 22, 0]))}
                for ob in grid._get_oob():
                    exp = expected.pop(ob[0])
                    self.assertEqual(exp[0], ob[1])
                    self.assertTrue(np.array_equal(exp[1], ob[2]))
                self.assertEqual(0, len(expected))


            if (rank == 1):
                a3 = core.Agent(1, 0, rank)
                grid.add(a3)

                pt = space.DiscretePoint(12, 39)
                grid.move(a2, pt)
                grid.move(a3, pt)

                grid.move(a2, space.DiscretePoint(0, 1))
                grid.move(a3, space.DiscretePoint(8, 200))
                
                expected = {(2, 0, 1) : (0, np.array([0, 1, 0])),
                    (1, 0, 1) : (0, np.array([8, 39, 0]))}
                for ob in grid._get_oob():
                    exp = expected.pop(ob[0])
                    self.assertEqual(exp[0], ob[1])
                    self.assertTrue(np.array_equal(exp[1], ob[2]))
                self.assertEqual(0, len(expected))

    def test_oob_3x3(self):
        comm = MPI.COMM_WORLD
        rank = comm.Get_rank()

        agents = [core.Agent(1, 0, rank), core.Agent(2, 0, rank), core.Agent(3, 0, rank),
            core.Agent(4, 0, rank), core.Agent(5, 0, rank), core.Agent(6, 0, rank),
            core.Agent(7, 0, rank), core.Agent(8, 0, rank)]

        box = space.BoundingBox(xmin=0, xextent=90, ymin=0, yextent=120, zmin=0, zextent=0)
        grid = space.SharedGrid("shared_grid", bounds=box, borders=BorderType.Sticky, 
            occupancy=OccupancyType.Multiple, buffersize=2, comm=comm)

        # print('{}: bounds: {}'.format(rank, grid.get_local_bounds()))
        for a in agents:
            grid.add(a)

        expected = {}
        if rank == 0:
            make_move(grid, agents[0], 32, 20, 3, expected)
            make_move(grid, agents[1], 35, 45, 4, expected)
            make_move(grid, agents[2], 15, 45, 1, expected)
            

        elif rank == 1:
            make_move(grid, agents[0], 15, 15, 0, expected)
            make_move(grid, agents[1], 35, 10, 3, expected)
            make_move(grid, agents[2], 45, 45, 4, expected)
            make_move(grid, agents[3], 35, 82, 5, expected)
            make_move(grid, agents[4], 15, 85, 2, expected)

        elif rank == 2:
            make_move(grid, agents[0], 15, 45, 1, expected)
            make_move(grid, agents[1], 35, 45, 4, expected)
            make_move(grid, agents[2], 35, 85, 5, expected)

        elif rank == 3:
            make_move(grid, agents[0], 15, 15, 0, expected)
            make_move(grid, agents[1], 15, 45, 1, expected)
            make_move(grid, agents[2], 45, 45, 4, expected)
            make_move(grid, agents[3], 65, 45, 7, expected)
            make_move(grid, agents[4], 65, 15, 6, expected)

        elif rank == 4:
            make_move(grid, agents[0], 15, 15, 0, expected)
            make_move(grid, agents[1], 15, 45, 1, expected)
            make_move(grid, agents[2], 15, 85, 2, expected)
            make_move(grid, agents[3], 35, 10, 3, expected)
            # make_move(grid, agents[4], 45, 45, 4, expected)
            make_move(grid, agents[5], 35, 85, 5, expected)
            make_move(grid, agents[7], 65, 15, 6, expected)
            make_move(grid, agents[6], 65, 45, 7, expected)
            make_move(grid, agents[4], 65, 85, 8, expected)
            

        elif rank == 5:
            make_move(grid, agents[1], 15, 45, 1, expected)
            make_move(grid, agents[4], 15, 85, 2, expected)
            make_move(grid, agents[2], 45, 45, 4, expected)
            make_move(grid, agents[3], 65, 45, 7, expected)
            make_move(grid, agents[7], 65, 85, 8, expected)

        elif rank == 6:
            make_move(grid, agents[3], 35, 10, 3, expected)
            make_move(grid, agents[4], 45, 45, 4, expected)
            make_move(grid, agents[6], 65, 45, 7, expected)
        
        elif rank == 7:
            make_move(grid, agents[3], 35, 10, 3, expected)
            make_move(grid, agents[4], 45, 45, 4, expected)
            make_move(grid, agents[5], 35, 85, 5, expected)
            make_move(grid, agents[7], 65, 15, 6, expected)
            make_move(grid, agents[1], 65, 85, 8, expected)

        elif rank == 8:
            make_move(grid, agents[4], 45, 45, 4, expected)
            make_move(grid, agents[5], 35, 85, 5, expected)
            make_move(grid, agents[6], 65, 45, 7, expected)

        for ob in grid._get_oob():
            exp = expected.pop(ob[0])
            self.assertEqual(exp[0], ob[1], rank)
            self.assertTrue(np.array_equal(exp[1], ob[2]), rank)
        self.assertEqual(0, len(expected), rank)


    def test_buffer_data(self):
        new_group = MPI.COMM_WORLD.Get_group().Incl([0, 1])
        comm = MPI.COMM_WORLD.Create_group(new_group)

        if comm != MPI.COMM_NULL:
            rank = comm.Get_rank()

            box = space.BoundingBox(xmin=0, xextent=20, ymin=0, yextent=40, zmin=0, zextent=0)
            grid = space.SharedGrid("shared_grid", bounds=box, borders=BorderType.Sticky, 
                occupancy=OccupancyType.Multiple, buffersize=2, comm=comm)

            if (rank == 0):
                a01 = core.Agent(1, 0, rank)
                a02 = core.Agent(2, 0, rank)
                a03 = core.Agent(3, 0, rank)
                grid.add(a01)
                grid.add(a02)
                grid.add(a03)

                pt = space.DiscretePoint(8, 20)
                grid.move(a01, pt)
                pt = space.DiscretePoint(9, 15)
                grid.move(a02, pt)
                pt = space.DiscretePoint(1, 15)
                grid.move(a03, pt)

                expected = (1, (8, 10, 0, 40, 0, 0))
                count = 0
                for bd in grid._get_buffer_data():
                    self.assertEqual(expected, bd)
                    count += 1
                self.assertEqual(1, count)


            if (rank == 1):
                a11 = core.Agent(1, 0, rank)
                a12 = core.Agent(2, 0, rank)
                a13 = core.Agent(3, 0, rank)

                grid.add(a11)
                grid.add(a12)
                grid.add(a13)

                pt = space.DiscretePoint(10, 20)
                grid.move(a11, pt)
                pt = space.DiscretePoint(11, 15)
                grid.move(a12, pt)
                pt = space.DiscretePoint(15, 15)
                grid.move(a13, pt)

                expected = (0, (10, 12, 0, 40, 0, 0))
                count = 0
                for bd in grid._get_buffer_data():
                    self.assertEqual(expected, bd)
                    count += 1
                self.assertEqual(1, count)
                    

class EAgent(core.Agent):

    def __init__(self, id, agent_type, rank, energy):
        super().__init__(id=id, type=agent_type, rank=rank)
        self.energy = energy
        self.restored = False

    def save(self):
        return (self.uid, self.energy)

    def restore(self, data):
        self.restored = True
        self.energy = data[1]


def create_agent(agent_data):
    # agent_data: [aid_tuple, energy]
    uid = agent_data[0]
    return EAgent(uid[0], uid[1], uid[2], agent_data[1])


class SharedContextTests(unittest.TestCase):

    long_message = True

    def test_add_remove(self):
        new_group = MPI.COMM_WORLD.Get_group().Incl([0, 1])
        comm = MPI.COMM_WORLD.Create_group(new_group)
        

        if comm != MPI.COMM_NULL:
            rank = comm.Get_rank()

            box = space.BoundingBox(xmin=0, xextent=20, ymin=0, yextent=40, zmin=0, zextent=0)
            grid = space.SharedGrid("shared_grid", bounds=box, borders=BorderType.Sticky, 
                occupancy=OccupancyType.Multiple, buffersize=2, comm=comm)

            context = core.SharedContext(comm)
            context.add_projection(grid)

            # test that adding to context 
            # adds to projection
            if rank == 0:
                a1 = core.Agent(1, 0, rank)
                context.add(a1)
                pt = space.DiscretePoint(0, 5)
                grid.move(a1, pt)
                self.assertEqual(a1, grid.get_agent(pt))
                self.assertEqual(pt, grid.get_location(a1))

                context.remove(a1)
                self.assertIsNone(grid.get_agent(pt))

            else:
                a2 = core.Agent(2, 0, rank)
                context.add(a2)
                pt = space.DiscretePoint(12, 30)
                grid.move(a2, pt)
                self.assertEqual(a2, grid.get_agent(pt))
                self.assertEqual(pt, grid.get_location(a2))
                count = 0
                for agent in context.agents():
                    count += 1
                    self.assertEqual(a2, agent)
                self.assertEqual(1, count)

    def test_synch(self):
        new_group = MPI.COMM_WORLD.Get_group().Incl([0, 1])
        comm = MPI.COMM_WORLD.Create_group(new_group)
        

        if comm != MPI.COMM_NULL:
            rank = comm.Get_rank()

            box = space.BoundingBox(xmin=0, xextent=20, ymin=0, yextent=40, zmin=0, zextent=0)
            grid = space.SharedGrid("shared_grid", bounds=box, borders=BorderType.Sticky, 
                occupancy=OccupancyType.Multiple, buffersize=2, comm=comm)

            context = core.SharedContext(comm)
            context.add_projection(grid)

            # test that adding to context 
            # adds to projection
            if rank == 0:
                a1 = EAgent(1, 0, rank, 12)
                context.add(a1)
                # oob
                pt = space.DiscretePoint(12, 5)
                grid.move(a1, pt)

            else:
                a2 = EAgent(2, 0, rank, 3)
                a3 = EAgent(3, 0, rank, 2)
                context.add(a2)
                context.add(a3)
                # oob
                pt = space.DiscretePoint(5, 30)
                grid.move(a2, pt)
                grid.move(a3, space.DiscretePoint(3, 20))

            context.synchronize(create_agent)

            if rank == 0:
                # should now have a2 and a3
                self.assertEqual(2, len(context._local_agents))
                # a2
                agent = context._local_agents[(2, 0, 1)]
                self.assertEqual((2, 0, 1), agent.uid)
                self.assertEqual(3, agent.energy)
                pt = space.DiscretePoint(5, 30)
                self.assertEqual(agent, grid.get_agent(pt))
                self.assertEqual(pt, grid.get_location(agent))

                # a3
                agent = context._local_agents[(3, 0, 1)]
                self.assertEqual((3, 0, 1), agent.uid)
                self.assertEqual(2, agent.energy)
                pt = space.DiscretePoint(3, 20)
                self.assertEqual(agent, grid.get_agent(pt))
                self.assertEqual(pt, grid.get_location(agent))

            else:
                # should now have a1
                self.assertEqual(1, len(context._local_agents))
                agent = context._local_agents[(1, 0, 0)]
                self.assertEqual((1, 0, 0), agent.uid)
                self.assertEqual(12, agent.energy)
                pt = space.DiscretePoint(12, 5)
                self.assertEqual(agent, grid.get_agent(pt))
                self.assertEqual(pt, grid.get_location(agent))

            if rank == 0:
                pt = space.DiscretePoint(5, 30)
                agent = grid.get_agent(pt)
                grid.move(agent, space.DiscretePoint(12, 38))
                agent.energy = -10
            
            context.synchronize(create_agent)

            if rank == 0:
                self.assertEqual(1, len(context._local_agents))
                # a3
                agent = context._local_agents[(3, 0, 1)]
                self.assertEqual((3, 0, 1), agent.uid)
                self.assertEqual(2, agent.energy)
                pt = space.DiscretePoint(3, 20)
                self.assertEqual(agent, grid.get_agent(pt))
                self.assertEqual(pt, grid.get_location(agent))

            if rank == 1:
                # a2 now back in 1
                self.assertEqual(2, len(context._local_agents))
                agent = context._local_agents[(2, 0, 1)]
                self.assertEqual((2, 0, 1), agent.uid)
                self.assertEqual(-10, agent.energy)
                pt = space.DiscretePoint(12, 38)
                self.assertEqual(agent, grid.get_agent(pt))
                self.assertEqual(pt, grid.get_location(agent))

                agent = context._local_agents[(1, 0, 0)]
                self.assertEqual((1, 0, 0), agent.uid)
                self.assertEqual(12, agent.energy)
                pt = space.DiscretePoint(12, 5)
                self.assertEqual(agent, grid.get_agent(pt))
                self.assertEqual(pt, grid.get_location(agent))



    def test_buffer(self):
        new_group = MPI.COMM_WORLD.Get_group().Incl([0, 1])
        comm = MPI.COMM_WORLD.Create_group(new_group)
        
        if comm != MPI.COMM_NULL:
            rank = comm.Get_rank()

            box = space.BoundingBox(xmin=0, xextent=20, ymin=0, yextent=40, zmin=0, zextent=0)
            grid = space.SharedGrid("shared_grid", bounds=box, borders=BorderType.Sticky, 
                occupancy=OccupancyType.Multiple, buffersize=2, comm=comm)

            context = core.SharedContext(comm)
            context.add_projection(grid)

            if rank == 0:
                a01 = EAgent(1, 0, rank, 1)
                a02 = EAgent(2, 0, rank, 2)
                a03 = EAgent(3, 0, rank, 3)
                context.add(a01)
                context.add(a02)
                context.add(a03)

                pt = space.DiscretePoint(8, 20)
                grid.move(a01, pt)
                pt = space.DiscretePoint(9, 15)
                grid.move(a02, pt)
                pt = space.DiscretePoint(9, 15)
                grid.move(a03, pt)

            if rank == 1:
                a11 = EAgent(1, 0, rank, 11)
                a12 = EAgent(2, 0, rank, 12)
                a13 = EAgent(3, 0, rank, 13)

                context.add(a11)
                context.add(a12)
                context.add(a13)

                pt = space.DiscretePoint(10, 20)
                grid.move(a11, pt)
                pt = space.DiscretePoint(11, 15)
                grid.move(a12, pt)
                pt = space.DiscretePoint(15, 15)
                grid.move(a13, pt)

            context.synchronize(create_agent)
            grid.synchronize_buffer(create_agent)

            if rank == 0:
                pt = space.DiscretePoint(10, 20)
                agent = grid.get_agent(pt)
                self.assertIsNotNone(agent)
                self.assertEqual((1, 0, 1), agent.uid)
                self.assertEqual(11, agent.energy)

                pt = space.DiscretePoint(11, 15)
                agent = grid.get_agent(pt)
                self.assertIsNotNone(agent)
                self.assertEqual((2, 0, 1), agent.uid)
                self.assertEqual(12, agent.energy)

                self.assertEqual(3, len(context._local_agents))

                # moves these agents out of the buffer zone
                pt = space.DiscretePoint(9, 15)
                for a in grid.get_agents(pt):
                    grid.move(a, space.DiscretePoint(5, 5))


            if rank == 1:
                pt = space.DiscretePoint(8, 20)
                agent = grid.get_agent(pt)
                self.assertIsNotNone(agent)
                self.assertEqual((1, 0, 0), agent.uid)
                self.assertEqual(1, agent.energy)

                pt = space.DiscretePoint(9, 15)
                expected = {(2,0,0) : 2, (3, 0, 0) : 3}
                for a in grid.get_agents(pt):
                    energy = expected.pop(a.uid) 
                    self.assertEqual(energy, a.energy)
                self.assertEqual(0, len(expected))

                self.assertEqual(3, len(context._local_agents))

            grid.synchronize_buffer(create_agent)

            if rank == 1:
                pt = space.DiscretePoint(8, 20)
                agent = grid.get_agent(pt)
                self.assertIsNotNone(agent)
                self.assertEqual((1, 0, 0), agent.uid)
                self.assertEqual(1, agent.energy)

                # nothing at 9, 15 now
                pt = space.DiscretePoint(9, 15)
                self.assertIsNone(grid.get_agent(pt))


    def test_buffer_3x3(self):
        comm = MPI.COMM_WORLD
        rank = comm.Get_rank()

        context = core.SharedContext(comm)

        agents = {}
        for a in [EAgent(1, 0, rank, 1), EAgent(2, 0, rank, 2), EAgent(3, 0, rank, 3),
            EAgent(4, 0, rank, 4), EAgent(5, 0, rank, 5), EAgent(6, 0, rank, 6),
            EAgent(7, 0, rank, 7), EAgent(8, 0, rank, 8)]:

            agents[a.uid] = a
            context.add(a)

        box = space.BoundingBox(xmin=0, xextent=90, ymin=0, yextent=120, zmin=0, zextent=0)
        grid = space.SharedGrid("shared_grid", bounds=box, borders=BorderType.Sticky, 
            occupancy=OccupancyType.Multiple, buffersize=1, comm=comm)
        context.add_projection(grid)

        data = {"0S" : ((1, 0, 0), mp(15, 39)), 
                "0SE" : ((2, 0, 0), mp(29, 39)), 
                "0E" : ((3, 0, 0), mp(29, 20)),

                "1N" : ((1, 0, 1), mp(15, 40)),
                "1S" : ((2, 0, 1), mp(15, 79)),
                "1NE" : ((3, 0, 1), mp(29, 40)),
                "1E" : ((4, 0, 1), mp(29, 45)),
                "1SE" : ((5, 0, 1), mp(29, 79)),

                '2N': ((1, 0, 2), mp(15, 80)),
                '2NE' :((2, 0, 2), mp(29, 80)),
                '2E' :((3, 0, 2), mp(29, 85)),

                '3W' : ((1, 0, 3), mp(30, 15)),
                '3SW' : ((2, 0, 3), mp(30, 39)),
                '3S' : ((3, 0, 3), mp(35, 39)),
                '3SE' : ((4, 0, 3), mp(59, 39)),
                '3E' : ((5, 0, 3), mp(59, 15)),

                '4NW' : ((1, 0, 4), mp(30, 40)),
                '4W' : ((2, 0, 4), mp(30, 45)),
                '4SW' : ((3, 0, 4), mp(30, 79)),
                '4S' : ((4, 0, 4), mp(35, 79)),
                '4SE' : ((5, 0, 4), mp(59, 79)),
                '4E' : ((6, 0, 4), mp(59, 45)),
                '4NE' : ((7, 0, 4), mp(59, 40)),
                '4N' : ((8, 0, 4), mp(35, 40)),

                '5NW' : ((1, 0, 5), mp(30, 80)),
                '5W' : ((3, 0, 5), mp(30, 85)),
                '5E' : ((4, 0, 5), mp(59, 85)),
                '5NE' : ((5, 0, 5), mp(59, 80)),
                '5N' : ((6, 0, 5), mp(35, 80)),

                '6W' : ((1, 0, 6), mp(60, 15)),
                '6SW' : ((2, 0, 6), mp(60, 39)),
                '6S' : ((3, 0, 6), mp(65, 39)),

                '7N' : ((1, 0, 7), mp(65, 40)),
                '7NW' : ((3, 0, 7), mp(60, 40)),
                '7W' : ((4, 0, 7), mp(60, 45)),
                '7SW' : ((5, 0, 7), mp(60, 79)),
                '7S' : ((6, 0, 7), mp(65, 79)),

                '8N' : ((1, 0, 8), mp(65, 80)),
                '8NW' : ((3, 0, 8), mp(60, 80)),
                '8W' : ((4, 0, 8), mp(60, 85))
        }

        for k, v in data.items():
            if k.startswith(str(rank)):
                grid.move(agents[v[0]], v[1])

        grid.synchronize_buffer(create_agent)

        exp = [
            ['1N', '3W', '4NW'],
            ['0S', '2N', '5NW', '4W', '3SW'],
            ['1S', '5W', '4SW'],
            ['0E', '1NE', '4N', '7NW', '6W'],
            ['0SE', '1E', '2NE', '5N', '8NW', '7W', '6SW', '3S'],
            ['1SE', '2E', '4S', '7SW', '8W'],
            ['3E', '4NE', '7N'],
            ['6S', '3SE', '4E', '5NE', '8N'],
            ['7S', '4SE', '5E']
        ]
        
        for e in exp[rank]:
            uid, pt = data[e]
            agent = grid.get_agent(pt)
            self.assertIsNotNone(agent, (e, rank))
            self.assertEqual(uid, agent.uid, (e, rank))
                
