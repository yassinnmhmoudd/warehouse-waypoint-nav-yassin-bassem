from setuptools import find_packages, setup

package_name = 'warehouse_waypoints'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='YOUR-NAME',
    maintainer_email='you@example.com',
    description='Autonomous warehouse waypoint mission: RViz markers + Nav2 goal sequencing.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'waypoint_mission_node = warehouse_waypoints.nodes.waypoint_mission_node:main',
        ],
    },
)
