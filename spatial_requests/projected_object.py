from spatial_spec.geometry import Polygon, PolygonCollection, StaticObject
import numpy as np
import copy

class ProjectedObject:

    def __init__(self, name, proj_points, color='r'):
        self.name = name
        self.color = color
        self.proj_points = proj_points
        self.shape = Polygon(self.proj_points, convex_hull=True)
    
    def update_points(self, new_points):
        self.proj_points = new_points
        self.shape = Polygon(self.proj_points, convex_hull=True)

    def get_static_shape(self):
        return StaticObject(PolygonCollection({self.shape}))

    def get_displaced_static_shape(self, d):
        copied_shape = copy.deepcopy(self.shape)
        copied_shape.translate(d)
        return StaticObject(PolygonCollection({copied_shape}))