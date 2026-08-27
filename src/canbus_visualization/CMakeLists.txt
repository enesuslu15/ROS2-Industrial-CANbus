cmake_minimum_required(VERSION 3.8)
project(canbus_visualization)

find_package(ament_cmake REQUIRED)

# Install directories
install(DIRECTORY
  launch
  rviz
  urdf
  DESTINATION share/${PROJECT_NAME}
)

ament_package()

