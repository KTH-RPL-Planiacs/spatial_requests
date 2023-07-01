from spatial_requests.spatial_request_planner import SpatialRequestPlanner

def main():
    spec = "(F (blue leftof red))"
    planner = SpatialRequestPlanner(spec)
    print("success")
