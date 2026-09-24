"""
Starts the ETGAH warehouse world (warehouse_world package, Gazebo Sim / gz-sim)
and spawns a TurtleBot3 into it at a configurable starting pose, reusing the
platform's own turtlebot3_gazebo launch files (robot_state_publisher + spawn +
ros_gz_bridge), so the topic bridging matches this platform exactly.

Requires the TURTLEBOT3_MODEL environment variable to be set, e.g.:
    export TURTLEBOT3_MODEL=burger

Usage:
    ros2 launch robot_navigation spawn_turtlebot3_warehouse.launch.py \
        x_pose:=0.0 y_pose:=0.0
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    x_pose = LaunchConfiguration('x_pose', default='0.0')
    y_pose = LaunchConfiguration('y_pose', default='0.0')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    warehouse_world_dir = get_package_share_directory('warehouse_world')
    turtlebot3_gazebo_dir = get_package_share_directory('turtlebot3_gazebo')

    # 1. Start the ETGAH warehouse world (world + its own gz<->ros bridge)
    warehouse_world_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(warehouse_world_dir, 'launch',
                         'warehouse_storage_launch.launch.py')
        )
    )

    # 2. robot_state_publisher (publishes /robot_description + /tf for the model)
    robot_state_publisher_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(turtlebot3_gazebo_dir, 'launch',
                         'robot_state_publisher.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
    )

    # 3. Spawn the TurtleBot3 + its matching ros_gz_bridge (scan/odom/cmd_vel/tf)
    spawn_turtlebot3_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(turtlebot3_gazebo_dir, 'launch',
                         'spawn_turtlebot3.launch.py')
        ),
        launch_arguments={'x_pose': x_pose, 'y_pose': y_pose}.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument('x_pose', default_value='0.0',
                               description='Starting X of the robot (Charging Station)'),
        DeclareLaunchArgument('y_pose', default_value='0.0',
                               description='Starting Y of the robot (Charging Station)'),
        DeclareLaunchArgument('use_sim_time', default_value='true'),

        warehouse_world_launch,
        robot_state_publisher_launch,
        spawn_turtlebot3_launch,
    ])