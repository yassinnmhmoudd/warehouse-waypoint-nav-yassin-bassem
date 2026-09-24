#!/usr/bin/env python3
"""
waypoint_mission_node
======================

Runs the required warehouse mission:

    Charging Station (Home) -> Loading Station -> [wait 30s]
        -> Storage Area -> Shipping Station -> Charging Station (Home)

For every leg it:
  * sends the next pose to Nav2's NavigateToPose action and waits for the result
    before sending the next goal,
  * publishes a visualization_msgs/MarkerArray on /waypoint_markers showing all
    four named waypoints (sphere + text label), colouring the CURRENT active
    goal green and every other waypoint blue,
  * stops the whole mission and logs which waypoint failed if any goal is
    aborted, canceled, or rejected.

>>> IMPORTANT <<<
The x / y / yaw values in WAYPOINTS below are PLACEHOLDERS. Drive the robot
(or click "2D Pose Estimate" / "Publish Point") around your saved warehouse
map, read off the real coordinates of the Charging Station, Loading Station,
Storage Area and Shipping Station, and replace them before recording your
demo video.
"""
import math
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.duration import Duration

from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
from visualization_msgs.msg import Marker, MarkerArray


def yaw_to_quaternion(yaw: float):
    """Return (x, y, z, w) for a rotation of `yaw` radians about Z."""
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


# Ordered mission waypoints. "wait_seconds" is applied AFTER arriving there.
WAYPOINTS = [
    {"name": "Charging Station", "x": 0.0, "y": 0.0, "yaw": 0.0, "wait_seconds": 0.0},
    {"name": "Loading Station", "x": 2.0, "y": 1.5, "yaw": 0.0, "wait_seconds": 30.0},
    {"name": "Storage Area", "x": 4.5, "y": -1.0, "yaw": 1.57, "wait_seconds": 0.0},
    {"name": "Shipping Station", "x": 1.0, "y": -3.0, "yaw": 3.14, "wait_seconds": 0.0},
    {"name": "Charging Station", "x": 0.0, "y": 0.0, "yaw": 0.0, "wait_seconds": 0.0},
]

# Colors (RGBA)
COLOR_BLUE = (0.0, 0.4, 1.0, 1.0)
COLOR_GREEN = (0.0, 0.8, 0.0, 1.0)


class WaypointMissionNode(Node):

    def __init__(self):
        super().__init__('waypoint_mission_node')

        self._marker_pub = self.create_publisher(MarkerArray, '/waypoint_markers', 10)
        self._nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        # Unique named stations for the marker map (Home appears twice in the
        # route above -> start and end -- collapse to a single marker set).
        self._stations = {}
        for wp in WAYPOINTS:
            self._stations.setdefault(wp['name'], wp)

        self._active_name = None
        self.get_logger().info('Waypoint mission node ready. Waiting for Nav2 action server...')
        self._nav_client.wait_for_server()
        self.get_logger().info('Nav2 action server available. Starting mission.')

        self.publish_markers()
        self.run_mission()

    # ------------------------------------------------------------------ #
    # Markers
    # ------------------------------------------------------------------ #
    def publish_markers(self):
        """Publish (or republish) all named waypoint markers, coloring the
        currently active goal green and every other one blue."""
        array = MarkerArray()
        marker_id = 0
        for name, wp in self._stations.items():
            color = COLOR_GREEN if name == self._active_name else COLOR_BLUE

            sphere = Marker()
            sphere.header.frame_id = 'map'
            sphere.header.stamp = self.get_clock().now().to_msg()
            sphere.ns = 'waypoints'
            sphere.id = marker_id
            marker_id += 1
            sphere.type = Marker.SPHERE
            sphere.action = Marker.ADD
            sphere.pose.position.x = wp['x']
            sphere.pose.position.y = wp['y']
            sphere.pose.position.z = 0.15
            sphere.scale.x = sphere.scale.y = sphere.scale.z = 0.3
            sphere.color.r, sphere.color.g, sphere.color.b, sphere.color.a = color
            array.markers.append(sphere)

            label = Marker()
            label.header.frame_id = 'map'
            label.header.stamp = sphere.header.stamp
            label.ns = 'waypoint_labels'
            label.id = marker_id
            marker_id += 1
            label.type = Marker.TEXT_VIEW_FACING
            label.action = Marker.ADD
            label.pose.position.x = wp['x']
            label.pose.position.y = wp['y']
            label.pose.position.z = 0.55
            label.scale.z = 0.25
            label.color.r, label.color.g, label.color.b, label.color.a = (1.0, 1.0, 1.0, 1.0)
            label.text = name
            array.markers.append(label)

        self._marker_pub.publish(array)

    # ------------------------------------------------------------------ #
    # Nav2 goal helpers
    # ------------------------------------------------------------------ #
    def _make_pose(self, wp) -> PoseStamped:
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = wp['x']
        pose.pose.position.y = wp['y']
        qx, qy, qz, qw = yaw_to_quaternion(wp['yaw'])
        pose.pose.orientation.x = qx
        pose.pose.orientation.y = qy
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw
        return pose

    def send_goal_and_wait(self, wp) -> bool:
        """Send one NavigateToPose goal and block until it finishes.
        Returns True on success, False on failure (aborted/canceled/rejected)."""
        self._active_name = wp['name']
        self.publish_markers()

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = self._make_pose(wp)

        self.get_logger().info(f"Navigating to '{wp['name']}' "
                                f"(x={wp['x']}, y={wp['y']}, yaw={wp['yaw']})")

        send_goal_future = self._nav_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)
        goal_handle = send_goal_future.result()

        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().error(f"Goal to '{wp['name']}' was REJECTED by Nav2.")
            return False

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result()

        if result is None:
            self.get_logger().error(f"No result received for goal to '{wp['name']}'.")
            return False

        status = result.status
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(f"Reached '{wp['name']}' successfully.")
            return True
        else:
            status_name = {
                GoalStatus.STATUS_ABORTED: 'ABORTED',
                GoalStatus.STATUS_CANCELED: 'CANCELED',
                GoalStatus.STATUS_UNKNOWN: 'UNKNOWN',
            }.get(status, str(status))
            self.get_logger().error(
                f"Navigation to '{wp['name']}' FAILED with status {status_name}.")
            return False

    # ------------------------------------------------------------------ #
    # Mission
    # ------------------------------------------------------------------ #
    def run_mission(self):
        for wp in WAYPOINTS:
            success = self.send_goal_and_wait(wp)
            if not success:
                self.get_logger().error(
                    f"Mission STOPPED. Failed at waypoint: '{wp['name']}' "
                    f"(x={wp['x']}, y={wp['y']}, yaw={wp['yaw']}).")
                return

            wait_s = wp.get('wait_seconds', 0.0)
            if wait_s > 0:
                self.get_logger().info(f"Waiting {wait_s:.0f} seconds at '{wp['name']}'...")
                self._sleep_spinning(wait_s)

        self._active_name = None
        self.publish_markers()
        self.get_logger().info('Mission complete: robot is back at the Charging Station (Home).')

    def _sleep_spinning(self, seconds: float):
        """Sleep while still processing callbacks (so /waypoint_markers etc. stay alive)."""
        end_time = self.get_clock().now() + Duration(seconds=seconds)
        while rclpy.ok() and self.get_clock().now() < end_time:
            rclpy.spin_once(self, timeout_sec=0.5)


def main(args=None):
    rclpy.init(args=args)
    node = WaypointMissionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
