# ROS2 Industrial CANbus

This repository converts the [Industrial-CANbus-Data-Analyzer](https://github.com/enesuslu15/Industrial-CANbus-Data-Analyzer) into a ROS2 ecosystem. 

It provides:
- Custom ROS2 messages for Motor Telemetry and Anomaly Alerts (`canbus_msgs`)
- A Python bridge node that listens to the raw UDP CAN frames and publishes them to ROS2 topics (`canbus_bridge`)
- RViz2 and Gazebo visualization tools (`canbus_visualization`)

## Workspace Structure
- `src/canbus_msgs`: C++ message definitions
- `src/canbus_bridge`: Python ROS2 node
- `src/canbus_visualization`: URDF, RViz2 configs, and Launch files

## Build Instructions (Windows Native ROS2)

1. Open your ROS2 Native Windows command prompt.
2. Navigate to this workspace directory.
3. Build the packages:
```cmd
colcon build --merge-install
```
4. Source the setup file:
```cmd
call install\setup.bat
```

## Running the Project

First, ensure your CAN simulator (Node A) from the original project is running and publishing UDP multicast data.

Then, launch the entire ROS2 bridge and visualization environment:
```cmd
ros2 launch canbus_visualization visualize.launch.py
```

### Inspecting Topics
You can inspect the live decoded CAN data on the ROS2 network:
```cmd
ros2 topic echo /motor/telemetry
ros2 topic echo /motor/anomaly
```
