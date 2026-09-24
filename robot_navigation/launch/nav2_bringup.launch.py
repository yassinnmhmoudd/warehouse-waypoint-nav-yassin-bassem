"""
Brings up the full Nav2 stack for the warehouse TurtleBot3 Burger.

Launches (each with its own params file, as required by the project spec):
  - map_server            (serves the saved warehouse map)
  - amcl                  (config/amcl.yaml)
  - planner_server        (config/planner_server.yaml)
  - controller_server     (config/controller_server.yaml)
  - behavior_server       (config/behavior_server.yaml)
  - bt_navigator          (config/bt_navigator.yaml)
  - lifecycle_manager     (activates the nodes above in order)

Usage:
    ros2 launch robot_navigation nav2_bringup.launch.py map:=/path/to/warehouse_map.yaml
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('robot_navigation')

    default_map_path = os.path.join(pkg_share, 'maps', 'warehouse_map.yaml')
    default_rviz_path = os.path.join(pkg_share, 'rviz', 'navigation.rviz')

    map_yaml = LaunchConfiguration('map')
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_rviz = LaunchConfiguration('use_rviz')
    autostart = LaunchConfiguration('autostart')

    declare_map_arg = DeclareLaunchArgument(
        'map', default_value=default_map_path,
        description='Full path to the saved warehouse map yaml file')

    declare_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time', default_value='True',
        description='Use simulation (Gazebo) clock')

    declare_rviz_arg = DeclareLaunchArgument(
        'use_rviz', default_value='True',
        description='Whether to start RViz with the saved config')

    declare_autostart_arg = DeclareLaunchArgument(
        'autostart', default_value='True',
        description='Automatically bring all nav2 lifecycle nodes to ACTIVE')

    lifecycle_nodes = [
        'map_server',
        'amcl',
        'planner_server',
        'controller_server',
        'behavior_server',
        'bt_navigator',
    ]

    map_server_node = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time, 'yaml_filename': map_yaml}],
    )

    amcl_node = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[os.path.join(pkg_share, 'config', 'amcl.yaml')],
    )

    planner_node = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[os.path.join(pkg_share, 'config', 'planner_server.yaml')],
    )

    controller_node = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=[os.path.join(pkg_share, 'config', 'controller_server.yaml')],
    )

    behavior_node = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        parameters=[os.path.join(pkg_share, 'config', 'behavior_server.yaml')],
    )

    bt_xml_path = os.path.join(
        get_package_share_directory('nav2_bt_navigator'),
        'behavior_trees',
        'navigate_to_pose_w_replanning_and_recovery.xml')

    bt_navigator_node = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=[
            os.path.join(pkg_share, 'config', 'bt_navigator.yaml'),
            {'default_nav_to_pose_bt_xml': bt_xml_path},
        ],
    )

    lifecycle_manager_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'autostart': autostart,
            'node_names': lifecycle_nodes,
        }],
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', default_rviz_path],
        output='screen',
        condition=IfCondition(use_rviz),
    )

    ld = LaunchDescription()
    ld.add_action(declare_map_arg)
    ld.add_action(declare_sim_time_arg)
    ld.add_action(declare_rviz_arg)
    ld.add_action(declare_autostart_arg)

    ld.add_action(map_server_node)
    ld.add_action(amcl_node)
    ld.add_action(planner_node)
    ld.add_action(controller_node)
    ld.add_action(behavior_node)
    ld.add_action(bt_navigator_node)
    ld.add_action(lifecycle_manager_node)
    ld.add_action(rviz_node)

    return ld