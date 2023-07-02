from spatial_requests.spatial_request_planner import SpatialRequestPlanner
from spatial_requests.graspable_object import GraspableObject
import numpy as np

def main():
    spec = "(F (blue leftof red))"

    graspable_objects = [
        GraspableObject(object_id=0,
                        name='blue',
                        position=np.array([1, 1]),
                        shape_info=['circle', 0.1]),
        GraspableObject(object_id=1,
                        name='red',
                        position=np.array([0, 0]),
                        shape_info=['rect', (0.1, 0.05)]),
    ]

    planner = SpatialRequestPlanner(spec, graspable_objects, min_x=-3, max_x=3, min_y=-3, max_y=3, step_size=0.05)
