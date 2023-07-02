from spatial_spec.logic import Spatial
from spatial_spec.automaton_planning import AutomatonPlanner
from enum import Enum
import numpy as np
from lark import Token
import matplotlib.pyplot as plt
from matplotlib import cm

class CommandType(Enum):
    EXECUTE = 1
    REQUEST = 2
    NONE = 3

class Command:

    def __init__(self, type, obj_name=None, new_pos=None, request_str=None):
        self.type = type
        self.name = obj_name
        self.new_pos = new_pos
        self.request_str = request_str


class SpatialRequestPlanner:

    def __init__(self, spec, graspable_objects, min_x, max_x, min_y, max_y, step_size):
        self.spatial = Spatial(quantitative=True)
        self.planner = AutomatonPlanner()
        self.pruned_edges = []

        self.graspable_objects = {}
        for obj in graspable_objects:
            self.graspable_objects[obj.name] = obj

        spec_tree = self.spatial.parse(spec)
        self.planner.tree_to_dfa(spec_tree)
        print("\ntemporal structure:", self.planner.temporal_formula)
        print("planner DFA nodes:", len(self.planner.dfa.nodes)," , edges:", len(self.planner.dfa.edges))

        # build workspace grid
        self.rx, self.ry = np.arange(min_x, max_x, step_size), np.arange(min_y, max_y, step_size)
        self.gx, self.gy = np.meshgrid(self.rx, self.ry)

        # object initialization - spatial variables
        for name, grasp_obj in self.graspable_objects.items():
            self.spatial.assign_variable(name, grasp_obj.get_static_shape())

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
    
    def get_relevant_objects(self, targets):
        """Returns the relevant object names from a set of target boolean configurations"""
        relv_objs = set()
        unmovable_objects = [] #TODO: add those somehow
        dfa_ap = self.planner.get_dfa_ap()

        for trgt in targets:
            for i, bit in enumerate(trgt):
                # skip don't care bits
                if bit == 'X':
                    continue
                # otherwise, it's relevant, so we get the subtree
                subtree = self.spatial_vars[dfa_ap[i]]
                # get all leaves that correspond to a variable
                for token in subtree.scan_values(lambda x: isinstance(x, Token)):
                    if token.type == 'NAME' and token.value not in unmovable_objects:
                        relv_objs.add(token.value)

        return relv_objs
    
    def composite_constraint_map(self, object_to_move, constraints):
        """Combines constraints maps into a single map by logical disjunction"""
        result = []
        for constraint in constraints:
            constraint_map = self.gradient_map_from_guard(object_to_move, guard=constraint)

            # merge constraint map into composite constraint map
            # since we don't want to satisfy any constraint, we simply remember the maximum (logical disjunction)
            if len(result) > 0:
                result = np.maximum(constraint_map, result)
            else:
                result = constraint_map

        return result
    
    def gradient_map_from_guard(self, object_to_move, guard):
        """Computes a gradient map of a transition guard by logical conjunction of individual maps"""
        result = []
        dfa_ap = self.planner.get_dfa_ap()

        for i, guard_val in enumerate(guard):
            # skip don't care variables
            if guard_val == 'X':
                continue

            # evaluate for that object
            tree = self.spatial_vars[dfa_ap[i]]
            gradient_values = self.gradient_map(object_to_move, tree)

            # if the guard has the variable as negative, flip the gradient map
            if guard_val == '0':
                gradient_values = [-1 * x for x in gradient_values]

            # merge results into the constraint_map (by logical conjunction)
            if len(result) > 0:
                result = np.minimum(result, gradient_values)
            else:
                result = gradient_values

        return result

    def gradient_map(self, object_to_move, spatial_tree):
        """Computes a uniformly sampled map of the satisfaction value of a single spatial subformula considering the changing position of a single object."""
        centroid = object_to_move.shape.center
        grad_values = []

        for pos in self._sample_points:
            d = pos - centroid
            virtual_shape = object_to_move.get_displaced_static_shape(d)
            self.spatial.reset_spatial_dict()
            self.spatial.assign_variable(object_to_move.name, virtual_shape)
            grad_values.append(self.spatial.interpret(spatial_tree))

        # reset the object position
        self.spatial.reset_spatial_dict()
        self.spatial.assign_variable(object_to_move.name, object_to_move.get_static_shape())
        return grad_values
    
    def find_best_point(self, map_2d, threshold):
        """Find the highest value point in a sampled map respecting the constraints"""
        boolean_table = map_2d > threshold

        # forbid all positions that are constrained
        for i in range(map_2d.shape[0]):
            for j in range(map_2d.shape[1]):
                if np.isnan(map_2d[i][j]):
                    boolean_table[i, j] = False

        # copy the gradient, mask the values
        masked_map_2d = np.array(map_2d, copy=True)
        for i in range(masked_map_2d.shape[0]):
            for j in range(masked_map_2d.shape[1]):
                if not boolean_table[i, j]:
                    masked_map_2d[i, j] = np.nan

        if not np.any(masked_map_2d > 0):
            return None

        result = np.where(masked_map_2d == np.nanmax(masked_map_2d))
        # zip the 2 arrays to get the exact coordinates
        list_of_coordinates = list(zip(result[0], result[1]))
        pos = int(len(list_of_coordinates) / 2)
        id_x = list_of_coordinates[pos][0]
        id_y = list_of_coordinates[pos][1]

        return np.array([self._rx[id_y], self._ry[id_x]])
    
    def visualize_map(self, target_map, target_point, proj_objs):
        """Plots gradient values"""
        fig = plt.figure()
        ax = fig.add_subplot(111)
        values_2d = np.array(target_map).reshape(self.gx.shape)
        granularity = 0.05
        con = ax.contourf(self.gx, self.gy, values_2d,
                          levels=np.arange(np.nanmin(values_2d) - granularity, np.nanmax(values_2d) + granularity, granularity),
                          cmap=cm.coolwarm,
                          alpha=0.3,
                          antialiased=False)
        # plot objects
        for proj_obj in proj_objs.values():
            proj_obj.shape.plot(ax, label=False, color='r')
        # plot target point
        plt.plot(target_point[0], target_point[1], "og")
        plt.autoscale()
        plt.colorbar(con)
        plt.show()

    def register_observation(self, object_list) -> None:
        # update objects
        for obj in object_list:
            id = obj["id"]
            new_points = obj["new_points"]
            self.graspable_objects[id].update_points(new_points)
        
        # register observation
        self.planner.dfa_step(self.create_planner_obs(), self.trace_ap)   

    def get_next_step(self) -> Command:
        print("Searching for target transition...")
        # loop until we have a target or no path to accepting states exist anymore (due to pruning infeasible edges)
        target_obj = None
        while True:
            target_set, constraint_set, edge = self.planner.plan_step()
            print("Considering", target_set, "with constraints", constraint_set, "...")

            # we are currently accepting, so we don't need to do anything
            if self.planner.currently_accepting():
                print("Specification satisfied, no action necessary.")
                return Command(CommandType.NONE)

            # no path to accepting state exists, check for possible request
            if not target_set:
                # TODO: check for requests
                print("Specification impossible to satisfy.")
                return Command(CommandType.NONE)
            
            # try all objects relevant to the current targets
            for obj_name in self.get_relevant_objects(target_set):
                print("Considering ", obj_name, "...")
                relevant_obj = self.graspable_objects[obj_name]
                composite_constraint_map = self.composite_constraint_map(relevant_obj, constraint_set)

                # try out all target options
                for target in target_set:
                    target_map = self.gradient_map_from_guard(relevant_obj, guard=target)

                    # remove the composite constraint from the map
                    if constraint_set:
                        assert len(target_map) == len(composite_constraint_map)
                        for v in range(len(target_map)):
                            if composite_constraint_map[v] > 0:
                                target_map[v] = np.nan
                    
                    # find the best point for the object
                    target_point = self.find_best_point(np.array(target_map).reshape(self.gx.shape), threshold=0)

                    # if we found a point, good!
                    if target_point is not None:
                        print("Found a point for ",obj_name, "!")
                        self.visualize_map(target_map, target_point, self.graspable_objects)
                        return Command(CommandType.EXECUTE, obj_name=obj_name, new_pos=target_point)
            
            # this edge is completely impossible by moving a single object, we prune the edge from the automaton 
            # (and remember it for future requests)
            if target_obj is None:
                print("Chosen edge turned out to be impossible. Pruning the edge...")
                self.pruned_edges.append(edge)
                self.planner.dfa.remove_edge(edge[0], edge[1])
        
    