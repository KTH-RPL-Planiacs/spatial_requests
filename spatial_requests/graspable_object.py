from spatial_spec.geometry import Circle, Polygon, PolygonCollection, StaticObject
import numpy as np

class GraspableObject:

    def __init__(self, object_id, name, position, shape_info):
        self.id = object_id
        self.name = name
        self.pos = position
        self.shape_info = shape_info
        self.angle = 0

    def get_shape(self):
        if self.shape_info[0] == "circle":
            return Circle(self.pos, self.shape_info[1])
        if self.shape_info[0] == "rect":
            return Polygon(rectangle_around_center(self.pos[:2], self.shape_info[1][0], self.shape_info[1][1])).rotate(self.angle, use_radians=True)
        raise ValueError("Unexpected shape info in graspable object!")

    def get_static_shape(self):
        return StaticObject(PolygonCollection({self.get_shape()}))
    
def rectangle_around_center(center: np.ndarray, box_length1: float, box_length2: float) -> np.ndarray:
    return np.array(
        [center + [-box_length1 / 2, -box_length2 / 2],
         center + [box_length1 / 2, -box_length2 / 2],
         center + [box_length1 / 2, box_length2 / 2],
         center + [-box_length1 / 2, box_length2 / 2]])