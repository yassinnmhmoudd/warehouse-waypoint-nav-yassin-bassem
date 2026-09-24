# warehouse-waypoint-nav-[YOUR-NAME]

Autonomous TurtleBot3 Burger warehouse delivery robot — SLAM mapping, AMCL
localization, full Nav2 autonomous navigation stack, and a scripted waypoint
mission with live RViz markers.

> Replace `[YOUR-NAME]` everywhere (repo name, package.xml maintainers, this
> README) before you submit. Everywhere you see `<<FILL IN>>` you must
> measure a real value from your own map/run and drop it in.

---

## 1. Project Overview and Mission

This project builds a fully autonomous mobile-robot delivery system for a
simulated warehouse:

1. A TurtleBot3 Burger is spawned inside the ETGAH warehouse world (Gazebo Sim).
2. The warehouse is mapped once with **SLAM Toolbox**.
3. The saved map is reloaded and the robot is localized in it with **AMCL**.
4. The full **Nav2** stack (planner, controller, behavior server, BT navigator)
   is configured and verified with a manual 2D Goal Pose.
5. A custom ROS 2 node (`waypoint_mission_node`) then runs the required
   mission automatically:

   ```
   Charging Station (Home) -> Loading Station -> wait 30s
        -> Storage Area -> Shipping Station -> Charging Station (Home)
   ```

   Each leg only starts after the previous Nav2 goal has actually succeeded;
   if any goal fails, the mission stops immediately and logs which waypoint
   it failed at. All four named waypoints are drawn as RViz markers the whole
   time, with the current active goal shown in **green** and every other
   waypoint in **blue**.

---

## 2. Repository and Package Structure

```
warehouse-waypoint-nav-[YOUR-NAME]/
├── robot_navigation/            # ament_cmake package: Nav2 config + launch + map + rviz
│   ├── config/
│   │   ├── amcl.yaml
│   │   ├── planner_server.yaml
│   │   ├── controller_server.yaml
│   │   ├── behavior_server.yaml
│   │   └── bt_navigator.yaml
│   ├── launch/
│   │   ├── spawn_turtlebot3_warehouse.launch.py   # world + spawn TurtleBot3
│   │   └── nav2_bringup.launch.py                 # map_server + amcl + nav2 + rviz
│   ├── maps/                    # put warehouse_map.yaml + .pgm here after SLAM
│   ├── rviz/
│   │   └── navigation.rviz
│   ├── CMakeLists.txt
│   └── package.xml
├── warehouse_waypoints/         # ament_python package: the mission node
│   ├── resource/warehouse_waypoints
│   ├── warehouse_waypoints/
│   │   ├── __init__.py
│   │   └── nodes/
│   │       ├── __init__.py
│   │       └── waypoint_mission_node.py
│   ├── package.xml
│   ├── setup.cfg
│   └── setup.py
├── images/                      # screenshots referenced in section 14
└── README.md
```

`robot_navigation` holds everything Nav2 needs (params, launch, saved map,
RViz layout). `warehouse_waypoints` is a plain Python ROS 2 node package that
talks to Nav2's action server and publishes the waypoint markers — it has no
C++ build step, so it's `ament_python`.

---

## 3. Workspace Build Instructions

```bash
# 1. Clone the warehouse world (provided by the course)
mkdir -p ~/workspaces/turtlebot_ws/src
cd ~/workspaces/turtlebot_ws/src
git clone https://github.com/ETGAH/warehouse_world.git

# 2. Clone this repo alongside it
git clone https://github.com/<you>/warehouse-waypoint-nav-[YOUR-NAME].git

# 3. Build everything
cd ~/workspaces/turtlebot_ws
colcon build --symlink-install
source install/setup.bash
```

Add `source ~/workspaces/turtlebot_ws/install/setup.bash` to your `~/.bashrc`
so every new terminal has these packages on its path.

**Dependencies** (install via `rosdep` / apt if missing): `nav2_bringup`,
`nav2_map_server`, `nav2_amcl`, `nav2_planner`, `nav2_controller`,
`nav2_behaviors`, `nav2_bt_navigator`, `nav2_lifecycle_manager`,
`slam_toolbox`, `turtlebot3_description`, `ros_gz_sim`, `ros_gz_bridge`,
`rviz2`.

---

## 4. How to Launch TurtleBot3 Inside the Warehouse World

```bash
ros2 launch robot_navigation spawn_turtlebot3_warehouse.launch.py \
    x:=0.0 y:=0.0 yaw:=0.0
```

This starts the ETGAH warehouse world (via `warehouse_world`'s own
`warehouse_storage_launch.launch.py`), publishes the TurtleBot3 Burger's
`robot_description`, spawns it into the running Gazebo Sim world at the given
pose, and bridges `/cmd_vel`, `/odom`, `/scan`, and `/tf` between Gazebo and
ROS 2. `x`/`y`/`yaw` set the robot's starting pose — this is also the
Charging Station (Home) pose used later, so keep it consistent with what you
store in `waypoint_mission_node.py`.

Confirm the robot is alive:

```bash
ros2 topic echo /scan --once
ros2 topic echo /odom --once
ros2 run tf2_tools view_frames   # or: ros2 run tf2_ros tf2_echo odom base_footprint
```

---

## 5. How to Map the Warehouse Using SLAM Toolbox

```bash
ros2 launch slam_toolbox online_async_launch.py use_sim_time:=true
rviz2   # add Map (/map) and LaserScan (/scan) displays, Fixed Frame = map
```

Drive the robot with teleop so SLAM Toolbox can build the occupancy grid:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Teleoperate through **every accessible aisle**, all the way around the
Depot shelving, so there are no duplicated walls or large unexplored gaps,
and confirm the robot's pose visibly tracks along the map as you drive.

## 6. How to Save the Warehouse Map

```bash
ros2 run nav2_map_server map_saver_cli -f ~/workspaces/turtlebot_ws/src/warehouse-waypoint-nav-[YOUR-NAME]/robot_navigation/maps/warehouse_map
```

This writes both `warehouse_map.yaml` and `warehouse_map.pgm` into
`robot_navigation/maps/` — keep both files, they must ship together and both
are referenced in this repo. Reload the pair in RViz (Map display →
`/map`, or open the `.pgm` directly) to confirm it looks correct before
moving on.

---

## 7. How to Launch and Test AMCL Localization

```bash
ros2 launch robot_navigation nav2_bringup.launch.py \
    map:=$(pwd)/robot_navigation/maps/warehouse_map.yaml use_rviz:=false
```

(For now this just brings up `map_server` + `amcl`; the rest of the Nav2
servers listed in the same launch file will simply wait until you also need
them in step 8.) In RViz:

1. Add **Map** (`/map`), **LaserScan** (`/scan`), **PoseArray**
   (`/particlecloud`), **RobotModel**.
2. Click **2D Pose Estimate**, click on the map where the robot actually is,
   and drag to set its facing.
3. Confirm the laser scan lines up with the mapped walls.
4. Drive the robot a short distance and confirm the AMCL particle cloud
   converges around the true pose (localization recovery).

---

## 8. How to Launch the Complete Nav2 System

```bash
ros2 launch robot_navigation nav2_bringup.launch.py \
    map:=$(pwd)/robot_navigation/maps/warehouse_map.yaml use_rviz:=true
```

This brings up `map_server`, `amcl`, `planner_server`, `controller_server`,
`behavior_server`, and `bt_navigator`, activates them all through
`lifecycle_manager_navigation`, and opens RViz with `rviz/navigation.rviz`
(map, both costmaps, global/local plan, laser scan, particle cloud, and the
`/waypoint_markers` display already added).

```bash
ros2 topic echo /cmd_vel --once   # confirm geometry_msgs/msg/Twist
ros2 lifecycle list
```

Send one manual **2D Goal Pose** in RViz and confirm the global/local costmap,
a planned path, and actual robot motion all appear before automating anything.

---

## 9. Waypoint Names, Positions, and Orientations

Measured from `warehouse_map.yaml` (map frame, meters / radians):

| Waypoint          | x (m)         | y (m)         | yaw (rad)     |
|-------------------|---------------|---------------|---------------|
| Charging Station (Home) | `<<FILL IN>>` | `<<FILL IN>>` | `<<FILL IN>>` |
| Loading Station   | `<<FILL IN>>` | `<<FILL IN>>` | `<<FILL IN>>` |
| Storage Area      | `<<FILL IN>>` | `<<FILL IN>>` | `<<FILL IN>>` |
| Shipping Station  | `<<FILL IN>>` | `<<FILL IN>>` | `<<FILL IN>>` |

These live in `WAYPOINTS` at the top of
`warehouse_waypoints/warehouse_waypoints/nodes/waypoint_mission_node.py` —
the values checked in there are **placeholders**; update them to your real
measured coordinates (click **Publish Point** in RViz on each station,
read `x, y` from the topic, and read `yaw` off the robot's heading you want
it to end each leg facing).

---

## 10. Mission Route

```
Charging Station (Home)
        │  navigate
        ▼
Loading Station  ──── wait exactly 30 seconds ────┐
        │                                          │
        ▼ navigate                                 │
Storage Area                                        │
        │ navigate                                  │
        ▼                                            │
Shipping Station                                     │
        │ navigate                                   │
        ▼                                            │
Charging Station (Home)  ◄──────────────────────────┘
```

Each leg waits for the previous `NavigateToPose` result before the next goal
is sent (see `send_goal_and_wait()` in `waypoint_mission_node.py`); if any
leg is aborted, canceled, or rejected, the mission stops immediately and logs
the exact waypoint (name + pose) where it failed instead of continuing.

---

## 11. RViz Waypoint-Marker Behavior

`waypoint_mission_node` publishes a `visualization_msgs/msg/MarkerArray` on
**`/waypoint_markers`**: one sphere + one text label per named station, all
in the `map` frame. Whenever the active Nav2 goal changes, the whole array is
republished with updated colors:

* 🔵 **Blue** — inactive waypoint (`RGBA 0.0, 0.4, 1.0, 1.0`)
* 🟢 **Green** — the current active navigation goal (`RGBA 0.0, 0.8, 0.0, 1.0`)

Only one marker is green at any time; add `MarkerArray → /waypoint_markers`
in RViz to see it live.

---

## 12. Required Terminal Output

Capture (and paste into your submission / keep visible in the demo video):

* `spawn_turtlebot3_warehouse.launch.py` console log showing the world and
  bridge starting cleanly, with no repeated errors.
* SLAM Toolbox log while teleoperating (map updates, no TF errors).
* `map_saver_cli` output confirming `warehouse_map.yaml` / `.pgm` were written.
* `nav2_bringup.launch.py` output showing every lifecycle node transition to
  `active` (`ros2 lifecycle list` for `map_server`, `amcl`, `planner_server`,
  `controller_server`, `behavior_server`, `bt_navigator` all reporting `active`).
* `waypoint_mission_node` console log for a full run: one "Navigating to …"
  / "Reached … successfully." pair per leg, the "Waiting 30 seconds at
  'Loading Station'..." line, and the final "Mission complete" line.

---

## 13. Problems Encountered and Their Solutions

| Problem | Solution |
|---|---|
| `<<FILL IN — e.g. AMCL never converges near shelving>>` | `<<FILL IN — e.g. increased max_particles / retuned alpha params in amcl.yaml>>` |
| `<<FILL IN — e.g. robot clips shelf corners in the local costmap>>` | `<<FILL IN — e.g. increased robot_radius / inflation_radius in planner_server.yaml & controller_server.yaml>>` |
| `<<FILL IN — e.g. TurtleBot3-gz topic names didn't match the bridge config>>` | `<<FILL IN — e.g. adjusted arguments in spawn_turtlebot3_warehouse.launch.py's ros_gz_bridge node>>` |

Replace this table with the *actual* issues you hit while running this on
your machine — this section is graded on honesty, not on having zero problems.

---

## 14. Screenshots

Place these in `images/` and reference them here:

* `images/mapping.png` — SLAM Toolbox mid-map, teleoperating through an aisle.
* `images/localization.png` — AMCL particle cloud converged on the real pose.
* `images/nav2_costmaps.png` — global + local costmap and a planned path from
  a manual 2D Goal Pose.
* `images/waypoints_all.png` — all four named waypoint markers visible.
* `images/waypoint_active_green.png` — the active goal in green, others blue.
* `images/waypoint_topic.png` — `ros2 topic echo /waypoint_markers --once` (or
  RViz's Displays panel showing the `/waypoint_markers` topic subscribed).

---

## 15. Demonstration Video

`<<FILL IN — link to your complete narrated demo video>>`

The video must show, in order: warehouse setup (world + TurtleBot3 spawn),
SLAM Toolbox mapping, AMCL localization + recovery, Nav2 bring-up with a
manual 2D Goal Pose, the full autonomous mission end-to-end (including the
30-second wait at the Loading Station), and the waypoint markers updating
live throughout.
