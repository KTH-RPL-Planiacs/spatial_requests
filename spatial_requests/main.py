from spatial_requests.spatial_request_planner import SpatialRequestPlanner
from spatial_requests.projected_object import ProjectedObject
import numpy as np

def main():
    spec = "(F (blue leftof red))"

    graspable_objects = [
        ProjectedObject(obj_id=0,
                        name='blue',
                        proj_points=np.asarray([[0.0, -0.5], [0.3, 0.0], [-0.3, 0.0]])),
        ProjectedObject(obj_id=1,
                        name='red',
                        proj_points=np.asarray([[-1, -0.5], [-0.7, 0.0], [-1.3, 0.0]])),
    ]

    planner = SpatialRequestPlanner(spec, graspable_objects, min_x=-3, max_x=3, min_y=-3, max_y=3, step_size=0.05)
    planner.get_next_step()