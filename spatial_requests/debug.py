from spatial_requests.spatial_request_planner import SpatialRequestPlanner
from spatial_requests.projected_object import ProjectedObject
import numpy as np

def main():
    spec = "(F ((hammer leftof brick) & (hammer dist brick <= 10.0)))"
    spec += "& (G (!(hammer ovlp banana)))"
    spec += "& (G (!(hammer ovlp brick)))"
    spec += "& (G (!(brick ovlp banana)))"

    brick_points = [[[242, 192]], [[220, 302]], [[219, 303]], [[215, 304]], [[213, 304]], [[210, 303]], [[209, 302]], [[202, 293]], [[200, 290]], [[196, 283]], [[191, 273]], [[189, 268]], [[188, 265]], [[186, 257]], [[184, 246]], [[184, 219]], [[185, 212]], [[187, 205]], [[188, 202]], [[201, 182]], [[203, 179]], [[209, 177]], [[214, 177]], [[239, 180]], [[241, 183]], [[242, 187]]]
    brick_points_proc = np.squeeze(np.asarray(brick_points), axis=1)

    banana_points = [[[242, 192]], [[219, 298]], [[218, 302]], [[216, 303]], [[213, 303]], [[210, 301]], [[204, 294]], [[201, 290]], [[195, 281]], [[191, 272]], [[189, 267]], [[187, 258]], [[185, 247]], [[184, 236]], [[184, 228]], [[185, 216]], [[186, 211]], [[187, 208]], [[203, 180]], [[207, 178]], [[211, 177]], [[212, 177]], [[239, 181]], [[241, 185]], [[242, 190]]]
    banana_points_proc = np.squeeze(np.asarray(banana_points), axis=1)

    graspable_objects = [
        ProjectedObject(name='brick',
                        color='b',
                        proj_points=brick_points_proc),
        ProjectedObject(name='banana',
                        color='y',
                        proj_points=banana_points_proc),
    ]

    bounds = [190,465,130,430]
    planner = SpatialRequestPlanner(spec, graspable_objects, bounds, samples=500)
    command = planner.get_next_step()
