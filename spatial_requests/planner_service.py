from spatial_requests.spatial_request_planner import SpatialRequestPlanner
from spatial_requests.projected_object import ProjectedObject
from spatial_requests.command import Command, CommandType

import time
import zmq
import json
import numpy as np

class PlannerService:

    def on_request(self, message):
        request = json.loads(message)
        response = {}
        assert "action" in request.keys()

        if request["action"] == "init":
            print("\nReceived init request.")
            response = self.on_init(request)
        elif request["action"] == "observation":
            print("\nReceived observation data.")
            response = self.on_observation(request)
        elif request["action"] == "plan_request":
            print("\nReceived planning request.")        
            response = self.on_plan(request)

        return json.dumps(response)
    
    def on_init(self, msg):
        #spec = "(F ((hammer leftof brick) & (hammer dist brick <= 10.0)))"
        #spec += "& (G (!(hammer ovlp banana)))"
        #spec += "& (G (!(hammer ovlp brick)))"
        #spec += "& (G (!(brick ovlp banana)))"

        spec = msg["specification"]

        ws = msg["workspace"]
        bounds = [ws[0][0], ws[1][0], ws[0][1], ws[1][1]]

        objects = [
            ProjectedObject(
                name='banana',
                color='y',
                proj_points=np.squeeze(np.asarray(msg["banana"]), axis=1)),
            ProjectedObject(
                name='brick',
                color='b',
                proj_points=np.squeeze(np.asarray(msg["brick"]), axis=1)),
            ProjectedObject(
                name='hammer',
                color='r',
                proj_points=np.squeeze(np.asarray(msg["hammer"]), axis=1)),
        ]
            
        self.planner = SpatialRequestPlanner(spec, objects, bounds, samples=500)
        return {"response": "ack"}

    def on_observation(self, msg):
        assert self.planner is not None, "Please send an init message first"
        objects = [
            ProjectedObject(
                name='banana',
                color='y',
                proj_points=np.squeeze(np.asarray(msg["banana"]), axis=1)),
            ProjectedObject(
                name='brick',
                color='b',
                proj_points=np.squeeze(np.asarray(msg["brick"]), axis=1)),
            ProjectedObject(
                name='hammer',
                color='r',
                proj_points=np.squeeze(np.asarray(msg["hammer"]), axis=1)),
        ]
        self.planner.register_observation(objects)
        return {
            "response": "ack",
            "spec_satisfied": self.planner.currently_accepting(),
            "info": "Object data received.",  
        }
    
    def on_plan(self, msg):
        assert self.planner is not None, "Please send an init message first"
        command = self.planner.get_next_step()

        if command.type == CommandType.NONE:
            return {
                "response": "none",
                "spec_satisfied": self.planner.currently_accepting(),
                "info": "Nothing to be done.",
            }
        elif command.type == CommandType.EXECUTE:
            return {
                "response": "execute",
                "spec_satisfied": self.planner.currently_accepting(),
                "info": "Move the specified object to new_pos.",
                "object_name": command.name,
                "new_pos": list(command.new_pos) 
            }
        elif command.type == CommandType.REQUEST:
            return {
                "response": "request",
                "spec_satisfied": self.planner.currently_accepting(),
                "info": "Display the request string for the user to see.",
                "request_str": command.request_str 
            }

        return {}


def main():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://0.0.0.0:5000")

    service = PlannerService()
    print("Socket created. Waiting for requests...")
 
    while True:
        #  Wait for next request from client
        message = socket.recv()

        # Generate response
        response = service.on_request(message)

        #  Send reply back to client
        socket.send(bytes(response, 'utf-8'))

