from spatial_requests.spatial_request_planner import SpatialRequestPlanner
from spatial_requests.projected_object import ProjectedObject
import numpy as np

def main():
    spec = "(F ((blue leftof red) & (blue dist red <= 2.0)))"
    spec += "& (G (!(blue ovlp red)))"

    graspable_objects = [
        ProjectedObject(name='blue',
                        color='b',
                        proj_points=np.asarray([[0.0, -0.5], [0.3, 0.0], [-0.3, 0.0]])),
        ProjectedObject(name='red',
                        color='r',
                        proj_points=np.asarray([[-1, -0.5], [-1.5, -0.8], [-0.7, 0.0], [-1.3, 0.0]])),
    ]

    bounds = [-3,3,-3,3]
    planner = SpatialRequestPlanner(spec, graspable_objects, bounds, samples=500)
    command = planner.get_next_step()
    planner.prune_edge(command.edge)
    command = planner.get_next_step()
    print(command.request_str)