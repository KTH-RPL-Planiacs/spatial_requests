from spatial_spec.logic import Spatial
from spatial_spec.automaton_planning import AutomatonPlanner
from enum import Enum
import numpy as np

class CommandType(Enum):
    EXECUTE = 1
    REQUEST = 2
    IMPOSSIBLE = 3

class Command:

    def __init__(self, type, obj_id=None, new_pos=None, request_str=None):
        self.type = type
        self.obj_id = obj_id
        self.new_pos = new_pos
        self.request_str = request_str


class SpatialRequestPlanner:

    def __init__(self, spec, graspable_objects, min_x, max_x, min_y, max_y, step_size):
        self.spatial = Spatial(quantitative=True)
        self.planner = AutomatonPlanner()
        self.pruned_edges = []

        self.graspable_objects = {}
        for obj in graspable_objects:
            self.graspable_objects[obj.id] = obj

        spec_tree = self.spatial.parse(spec)
        self.planner.tree_to_dfa(spec_tree)
        print("\ntemporal structure:", self.planner.temporal_formula)
        print("planner DFA nodes:", len(self.planner.dfa.nodes)," , edges:", len(self.planner.dfa.edges))

        # build workspace grid
        self.rx, self.ry = np.arange(min_x, max_x, step_size), np.arange(min_y, max_y, step_size)
        self.gx, self.gy = np.meshgrid(self.rx, self.ry)

        # object initialization - spatial variables
        for grasp_obj in self.graspable_objects:
            self.spatial.assign_variable(grasp_obj.name, grasp_obj.get_static_shape())

        # this dictionary contains a variable name to spatial tree mapping
        self.spatial_vars = self.planner.get_variable_to_tree_dict()
        
        # you have to define in which order you pass variable assignments to the planner
        self.trace_ap = list(self.spatial_vars.keys())

        # resets the automaton current state to the initial state (doesn't do anything here)
        self.planner.reset_state()

        # before you ask anything from the automaton, provide a initial observation of each spatial sub-formula
        self.planner.dfa_step(self.create_planner_obs(), self.trace_ap)

    def create_planner_obs(self):
        obs = ''
        for var_ap in self.trace_ap:
            subtree = self.spatial_vars[var_ap]
            if self.spatial.interpret(subtree) > 0:
                obs += '1'
            else:
                obs += '0'
        return obs

    def register_observation(self, object_list) -> None:
        # update objects
        for obj in object_list:
            id = obj["id"]
            new_points = obj["new_points"]
            self.graspable_objects[id].update_points(new_points)
        
        # register observation
        self.planner.dfa_step(self.create_planner_obs(), self.trace_ap)
        



    def get_next_step(self) -> Command:
        target_set, constraint_set, edge = self.planner.plan_step()
        print("Considering", target_set, "with constraints", constraint_set, "...")

        if 1 == 0:
            obj_id = 0
            new_pos = (0,0)
            return Command(CommandType.EXECUTE, obj_id=obj_id, new_pos=new_pos)
        else:
            request_str = "Hi"
            return Command(CommandType.REQUEST, request_str=request_str)