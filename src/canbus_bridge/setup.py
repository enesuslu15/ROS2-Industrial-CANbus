from setuptools import setup
import os
from glob import glob

package_name = 'canbus_bridge'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools', 'python-can'],
    zip_safe=True,
    maintainer='Enes Uslu',
    maintainer_email='enesuslu15@gmail.com',
    description='ROS2 bridge for Industrial CANbus UDP Multicast data',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'can_to_ros_node = canbus_bridge.can_to_ros_node:main'
        ],
    },
)
