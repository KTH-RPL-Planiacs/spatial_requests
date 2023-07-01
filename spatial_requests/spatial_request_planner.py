from spatial_spec.logic import Spatial
from spatial_spec.automaton_planning import AutomatonPlanner

class SpatialRequestPlanner:

    def __init__(self, spec):
        self.spatial = Spatial(quantitative=True)
        self.planner = AutomatonPlanner()

        spec_tree = self.spatial.parse(spec)
        self.planner.tree_to_dfa(spec_tree)
        print("\ntemporal structure:", self.planner.temporal_formula)
        print("planner DFA nodes:", len(self.planner.dfa.nodes)," , edges:", len(self.planner.dfa.edges))

    def observation(object_list):
        pass

    def next_step():
        pass