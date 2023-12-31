from spatial_spec.logic import Spatial
from spatial_spec.automaton_planning import AutomatonPlanner
from spatial_requests.command import Command, CommandType
from spatial_requests.guard_utility import reduce_set_of_guards, sog_fits_to_guard
from spatial_spec.geometry import Polygon, PolygonCollection, StaticObject

import copy
import os
import numpy as np
import networkx as nx
from lark import Token, Lark
from lark.reconstruct import Reconstructor
import matplotlib.pyplot as plt
from matplotlib import cm

class SpatialRequestPlanner:

    def __init__(self, spec, graspable_objects, bounds, samples):
        self.spatial = Spatial(quantitative=True)
        self.planner = AutomatonPlanner()
        self.bounds = bounds
        self.pruned_edges = {}

        grammar = os.path.dirname(__file__) + "/spatial.lark"
        parser = Lark.open(grammar, parser='lalr', maybe_placeholders=False)
        self.reconstructor = Reconstructor(parser)

        self.graspable_objects = {}
        for obj in graspable_objects:
            self.graspable_objects[obj.name] = obj

        spec_tree = self.spatial.parse(spec)
        self.planner.tree_to_dfa(spec_tree)
        self.orig_dfa = copy.deepcopy(self.planner.dfa)
        print("\ntemporal structure:", self.planner.temporal_formula)
        print("planner DFA nodes:", len(self.planner.dfa.nodes)," , edges:", len(self.planner.dfa.edges))

        # build workspace grid
        self.sample_points = self.sample_grid_mesh(bounds, samples)

        # object initialization - spatial variables
        for name, grasp_obj in self.graspable_objects.items():
            self.spatial.assign_variable(name, grasp_obj.get_static_shape())
        
        self.define_areas()

        # this dictionary contains a variable name to spatial tree mapping
        self.spatial_vars = self.planner.get_variable_to_tree_dict()
        
        # you have to define in which order you pass variable assignments to the planner
        self.trace_ap = list(self.spatial_vars.keys())

        # resets the automaton current state to the initial state (doesn't do anything here)
        self.planner.reset_state()

        # before you ask anything from the automaton, provide a initial observation of each spatial sub-formula
        self.planner.dfa_step(self.create_planner_obs(), self.trace_ap)

    def define_areas(self):
        # define phantom regions
        x_min = self.bounds[0]
        x_max = self.bounds[1]
        y_min = self.bounds[2]
        y_max = self.bounds[3]
        x_mid = x_min + (x_max - x_min) * 0.5
        y_mid = y_min + (y_max - y_min) * 0.5
        
        bottom_left_corner = Polygon(np.asarray([[x_min, y_mid],[x_min, y_max],[x_mid, y_max],[x_mid, y_mid]]))
        bottom_right_corner = Polygon(np.asarray([[x_mid, y_mid],[x_mid, y_max],[x_max, y_max],[x_max, y_mid]]))
        top_left_corner = Polygon(np.asarray([[x_min, y_min],[x_min, y_mid],[x_mid, y_mid],[x_mid, y_min]]))
        top_right_corner = Polygon(np.asarray([[x_mid, y_min],[x_mid, y_mid],[x_max, y_mid],[x_max, y_min]]))

        # top and bottom are swapped, but it worked that way, sorry future person...
        self.spatial.assign_variable("top_left_corner", StaticObject(PolygonCollection({top_left_corner})))
        self.spatial.assign_variable("top_right_corner", StaticObject(PolygonCollection({top_right_corner})))
        self.spatial.assign_variable("bottom_left_corner", StaticObject(PolygonCollection({bottom_left_corner})))
        self.spatial.assign_variable("bottom_right_corner", StaticObject(PolygonCollection({bottom_right_corner})))

    def create_planner_obs(self):
        # set objects in spatial
        self.spatial.reset_spatial_dict()
        for name, obj in self.graspable_objects.items():
            self.spatial.assign_variable(name, obj.get_static_shape())
        self.define_areas()

        obs = ''
        for var_ap in self.trace_ap:
            subtree = self.spatial_vars[var_ap]
            if self.spatial.interpret(subtree) > 0:
                obs += '1'
            else:
                obs += '0'
        return obs
    
    def sample_grid_mesh(self, bounds, samples):
        """Returns a grid mesh of evenly spaced values inside the previously computed bounds"""
        x_range = np.abs(bounds[1] - bounds[0])
        y_range = np.abs(bounds[3] - bounds[2])
        assert x_range > 0
        assert y_range > 0
        ratio = x_range / y_range
        x_steps = np.sqrt(samples * ratio)
        y_steps = samples / x_steps
        x_steps = int(x_steps)
        y_steps = int(y_steps)

        self.rx = np.linspace(bounds[0], bounds[1], num=x_steps)
        self.ry = np.linspace(bounds[2], bounds[3], num=y_steps)
        self.gx, self.gy = np.meshgrid(self.rx, self.ry)

        return np.c_[self.gx.ravel(), self.gy.ravel()]

    def get_relevant_objects(self, targets):
        """Returns the relevant object names from a set of target boolean configurations"""
        relv_objs = set()
        unmovable_objects = ["banana", "top_left_corner", "top_right_corner", "bottom_left_corner", "bottom_right_corner"]
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

        for pos in self.sample_points:
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

        return np.array([self.rx[id_y], self.ry[id_x]])
    
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
            proj_obj.shape.plot(ax, label=False, color=proj_obj.color)
        # plot target point
        plt.plot(target_point[0], target_point[1], "og")
        plt.autoscale()
        plt.colorbar(con)
        plt.show()

    def viz_objects(self):
        fig = plt.figure()
        ax = fig.add_subplot(111)
        # plot objects
        for proj_obj in self.graspable_objects.values():
            proj_obj.shape.plot(ax, label=False, color=proj_obj.color)

        plt.autoscale()
        plt.show()

    def find_smallest_request(self, node_cur):
        possible_nodes = {}

        # no previously pruned edges from this node
        if node_cur not in self.pruned_edges.keys():
            return None
        
        # check if the state behind a pruned edge has a path to an accepting state
        for candidate in self.pruned_edges[node_cur]:
            node_cand = candidate["node_to"]
            if node_cand in self.orig_dfa.graph["acc"]:
                possible_nodes[node_cand] = candidate["cost"]
                continue

            for node_acc in self.orig_dfa.graph["acc"]:
                if nx.has_path(self.orig_dfa, source=node_cur, target=node_acc):
                    # there is a path to an accepting state, so we can use this candidate
                    possible_nodes[node_cand] = candidate["cost"]

        # all pruned edges are infeasible
        if not possible_nodes:
            return None

        # find the smallest request
        return min(possible_nodes, key=possible_nodes.get)

    def generate_request_str(self, node_cur, node_to):
        # get target and constraint guards
        target_guards = self.orig_dfa.edges[node_cur, node_to]['guard']
        constraint_guards = []
        for succ in self.orig_dfa.successors(node_cur):
            if succ != node_to and succ != node_cur:
                constraint_guards.extend(self.orig_dfa.edges[node_cur, succ]['guard'])

        target_guards = reduce_set_of_guards(target_guards)
        constraint_guards = reduce_set_of_guards(constraint_guards)
        aps = self.orig_dfa.graph["ap"]

        # use spatial subtrees to create the string
        request_str = "Please help me achieve:\n"
        
        # target
        for tg in target_guards:
            for i in range(len(tg)):
                if tg[i] == 'X':
                    continue
                
                # check if constraints have the negation
                # TODO: WHEN IS THIS NOT SOUND?
                #redundant = False
                #for cg in constraint_guards:
                #    if (tg[i] == '0' and cg[i] == '1') or (tg[i] == '1' and cg[i] == '0'):
                #        redundant = True
                #        break

                #if redundant:
                #    continue

                subtree = self.spatial_vars[aps[i]]
                subtree_str = self.reconstructor.reconstruct(subtree)
                if tg[i] == '0':
                    #hacky hacky sorry
                    if subtree_str.startswith("(not"):
                        subtree_str = subtree_str[4:-1]
                    else:
                        subtree_str = 'not(' + subtree_str + ')'

                request_str += subtree_str + '\n'
            request_str += '\nOR\n'
        request_str = request_str[:-3]

        """
        # constraints
        if not constraint_guards:
            return request_str
            
        request_str += 'But avoid:\n'

        for cg in constraint_guards:
            for i in range(len(cg)):
                if cg[i] == 'X':
                    continue
                
                subtree = self.spatial_vars[aps[i]]
                subtree_str = self.reconstructor.reconstruct(subtree)
                if cg[i] == '0':
                    #hacky hacky sorry
                    if subtree_str.startswith("(not"):
                        subtree_str = subtree_str[4:-1]
                    else:
                        subtree_str = 'not(' + subtree_str + ')'

                request_str += subtree_str + '\n'
            request_str += 'OR\n'
        request_str = request_str[:-3]
        """
        return request_str

    def prune_edge(self, edge):
        node_cur = edge[0]
        node_to = edge[1]

        # obtain guards for the edge and guards for the self loop
        target_guards = self.orig_dfa.edges[node_cur, node_to]['guard']
        loop_guards = self.orig_dfa.edges[node_cur, node_cur]['guard'] # we assume this to always exist

        # determine request cost
        cost = len(target_guards[0]) # highest possible cost
        for t in target_guards:
            for l in loop_guards:
                assert len(t) == len(l)
                cand_cost = sum (t[i] != l[i] for i in range(len(t)))
                cost = min(cost, cand_cost)

        # insert pruned edge information
        if node_cur not in self.pruned_edges.keys():
            self.pruned_edges[node_cur] = []
        self.pruned_edges[node_cur].append({
            "node_to": node_to,
            "cost": cost
        })

        self.planner.dfa.remove_edge(node_cur, node_to)

    def currently_accepting(self):
        return self.planner.currently_accepting()

    def register_observation(self, object_list) -> None:
        # update objects
        for obj in object_list:
            self.graspable_objects[obj.name] = obj
        
        # register observation, we use the original dfa so it can use pruned edges
        node_cur = self.planner.current_state
        symbol = self.create_planner_obs()
        #self.viz_objects()

        symbol_ap = self.trace_ap
        for succ in self.orig_dfa.successors(node_cur):
            # directly applying the first edge that fits works because the dfa is deterministic!
            if sog_fits_to_guard(symbol, self.orig_dfa.edges[node_cur, succ]['guard'], self.trace_ap, self.orig_dfa.graph['ap']):
                self.planner.current_state = succ
                break

    def get_next_step(self) -> Command:
        print("Searching for target transition...")
        # loop until we have a target or no path to accepting states exist anymore (due to pruning infeasible edges)
        target_obj = None
        while True:
            target_set, constraint_set, edge = self.planner.plan_step()

            # we are currently accepting, so we don't need to do anything
            if self.planner.currently_accepting():
                print("Specification satisfied, no action necessary.")
                return Command(CommandType.NONE)

            # no path to accepting state exists, check for possible request
            if not target_set:
                node_current = self.planner.current_state
                node_request = self.find_smallest_request(node_current)
                if not node_request:
                    print("Specification impossible to satisfy anymore.")
                    return Command(CommandType.NONE)
                else:
                    print("Sending a request...")
                    request_str = self.generate_request_str(node_current, node_request)
                    return Command(CommandType.REQUEST, request_str=request_str)
            
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
                        #self.visualize_map(target_map, target_point, self.graspable_objects)
                        return Command(CommandType.EXECUTE, obj_name=obj_name, new_pos=target_point, edge=edge)
            
            # this edge is completely impossible by moving a single object, we prune the edge from the automaton 
            # (and remember it for future requests)
            if target_obj is None:
                print("Chosen edge turned out to be impossible. Pruning the edge...")
                self.prune_edge(edge)
        
    