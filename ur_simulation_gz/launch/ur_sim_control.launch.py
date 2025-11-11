# Copyright (c) 2021 Stogl Robotics Consulting UG (haftungsbeschränkt)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
#    * Neither the name of the {copyright_holder} nor the names of its
#      contributors may be used to endorse or promote products derived from
#      this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Author: Denis Stogl

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    RegisterEventHandler,
    TimerAction,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
    IfElseSubstitution,
    TextSubstitution,
)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue, ParameterFile
from launch_ros.substitutions import FindPackageShare

from os.path import exists

def launch_setup(context, *args, **kwargs):
    # Initialize Arguments
    ur_type = LaunchConfiguration("ur_type")
    safety_limits = LaunchConfiguration("safety_limits")
    safety_pos_margin = LaunchConfiguration("safety_pos_margin")
    safety_k_position = LaunchConfiguration("safety_k_position")
    # General arguments
    controllers_file = LaunchConfiguration("controllers_file")
    tf_prefix = LaunchConfiguration("tf_prefix")
    activate_joint_controller = LaunchConfiguration("activate_joint_controller")
    initial_joint_controller = LaunchConfiguration("initial_joint_controller")
    description_file = LaunchConfiguration("description_file")
    launch_rviz = LaunchConfiguration("launch_rviz")
    rviz_config_file = LaunchConfiguration("rviz_config_file")
    gazebo_gui = LaunchConfiguration("gazebo_gui")
    world_file = LaunchConfiguration("world_file")
    # MIA Hand launch Arguments
    serial_port = LaunchConfiguration('serial_port').perform(context)
    #rviz2_gui = LaunchConfiguration('rviz2_gui')
    laterality = LaunchConfiguration('laterality').perform(context)
    prefix = LaunchConfiguration('prefix').perform(context)
    robot_ns = LaunchConfiguration('robot_ns').perform(context)
    use_mock_hardware = LaunchConfiguration('use_mock_hardware').perform(context)

    # --- MIA Hand ---
    # Joint limits configuration (P)
    joint_limits_config_file_path = PathJoinSubstitution([
        FindPackageShare('mia_hand_description'), 'calibration',
        'joint_limits.yaml']).perform(context)

    if exists(joint_limits_config_file_path):
        joint_limits_config_file = 'joint_limits.yaml'
    else:
        joint_limits_config_file = 'joint_limits_default.yaml'

    # Transmission configuration (P)
    transmissions_config_file_path = PathJoinSubstitution([
        FindPackageShare('mia_hand_description'), 'calibration',
        'transmission_config.yaml']).perform(context)

    if exists(transmissions_config_file_path):
        transmissions_config_file = 'transmission_config.yaml'
    else:
        transmissions_config_file = 'transmission_config_default.yaml'


    # UR5 Robot description
    robot_description_content = Command([
            PathJoinSubstitution([FindExecutable(name="xacro")])," ",
            description_file," ",
            "safety_limits:=",safety_limits," ",
            "safety_pos_margin:=",safety_pos_margin," ",
            "safety_k_position:=",safety_k_position," ",
            "name:=","ur5e"," ",
            "ur_type:=", ur_type," ",
            "tf_prefix:=",tf_prefix," ",
            "simulation_controllers:=",controllers_file," ",
            "serial_port:=",serial_port," ",
            "laterality:=",laterality," ",
            "prefix:=",prefix," ",
            "joint_limits_config_file:=",joint_limits_config_file," ",
            "use_mock_hardware:=",use_mock_hardware,
        ]
    )
    robot_description = {"robot_description": robot_description_content}

    # ur_controllers = PathJoinSubstitution([
    #     FindPackageShare('ur_simulation_gz'),
    #     'config',
    #     'ur_controllers.yaml'
    # ])

    # ros2_control_node = Node(
    #     package = 'controller_manager',
    #     executable = 'ros2_control_node',
    #     parameters =[
    #         ParameterFile(ur_controllers, allow_substs=True),
    #     ],
    #     output = 'both',
    # )

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[robot_description, {'use_sim_time': True}],
        output = 'both',
    )


    # RViz

    #rviz2_config_file = PathJoinSubstitution([
    #   FindPackageShare('mia_hand_description'), 'rviz', 'mia_hand_config.rviz'
    #])

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config_file],
        condition=IfCondition(launch_rviz),
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "-c", "/controller_manager"],
    )

    # joint_state_broadcaster_spawner = Node(
    #     package="controller_manager",
    #     executable="spawner",
    #     arguments=["joint_state_broadcaster"],
    # )


    rviz2_joint_state_publisher = Node(
        condition = IfCondition(launch_rviz),
        name = 'rviz2_joint_state_publisher',
        package = 'mia_hand_description',
        executable = 'rviz2_joint_state_publisher_node',
        parameters = [
            robot_description,
            PathJoinSubstitution([
              FindPackageShare('mia_hand_description'),
              'calibration',
              TextSubstitution(text = transmissions_config_file)
            ])
        ]
    )


    # There may be other controllers of the joints, but this is the initially-started one
    initial_joint_controller_spawner_started = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[initial_joint_controller, "-c", "/controller_manager"],
        condition=IfCondition(activate_joint_controller),
    )
    initial_joint_controller_spawner_stopped = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[initial_joint_controller, "-c", "/controller_manager", "--stopped"],
        condition=UnlessCondition(activate_joint_controller),
    )

    velocity_controllers_spawner = Node(
        name = 'velocity_controllers_spawner',
        package = 'controller_manager',
        executable = 'spawner',
        arguments = [
            'thumb_joint_velocity_controller',
            'index_joint_velocity_controller',
            'mrl_joint_velocity_controller',
            '--inactive',
            '-c', '/controller_manager'
        ]
    )

    position_controllers_spawner = Node(
        name = 'position_controllers_spawner',
        package = 'controller_manager',
        executable = 'spawner',
        arguments = [
            'thumb_joint_position_controller',
            'index_joint_position_controller',
            'mrl_joint_position_controller',
            '-c', '/controller_manager'
        ]
    )

    joint_trajectory_controller_spawner = Node(
        name = 'joint_trajectory_controller_spawner',
        package = 'controller_manager',
        executable = 'spawner',
        arguments = [
            'joint_trajectory_controller',
            '--inactive',
            '-c', '/controller_manager'
        ]
    )

    trajectory_controller_spawner = Node(
        name = 'trajectory_controller_spawner',
        package = 'controller_manager',
        executable = 'spawner',
        arguments = [
            'joint_trajectory_controller',
            '--inactive',
            '-c', '/controller_manager'
        ]
    )

    # delay_velocity_controllers_spawner_after_joint_state_broadcaster_spawner = RegisterEventHandler(
    #     event_handler = OnProcessExit(
    #         target_action = joint_state_broadcaster_spawner,
    #         on_exit = [velocity_controllers_spawner]
    #     )
    # )

    # delay_position_controllers_spawner_after_joint_state_broadcaster_spawner = RegisterEventHandler(
    #     event_handler = OnProcessExit(
    #         target_action = joint_state_broadcaster_spawner,
    #         on_exit = [position_controllers_spawner]
    #     )
    # )

    # delay_trajectory_controller_spawner_after_joint_state_broadcaster_spawner = RegisterEventHandler(
    #     event_handler = OnProcessExit(
    #         target_action = joint_state_broadcaster_spawner,
    #         on_exit = [trajectory_controller_spawner]
    #     )
    # )

    # delay_rviz_joint_state_publisher_after_joint_state_broadcaster_spawner = RegisterEventHandler(
    #     event_handler = OnProcessExit(
    #         target_action = joint_state_broadcaster_spawner,
    #         on_exit = [rviz2_joint_state_publisher]
    #     )
    # )


    # delay_rviz_after_joint_state_broadcaster_spawner = RegisterEventHandler(
    #     event_handler=OnProcessExit(
    #         target_action=joint_state_broadcaster_spawner,
    #         on_exit=[rviz_node],
    #     ),
    #     condition=IfCondition(launch_rviz),
    # )

    # delayed_ros2_control_node = TimerAction(
    #     period=5.0,
    #     actions=[ros2_control_node],
    # )

    # --- GZ nodes ---

    gz_spawn_entity = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-string",
            robot_description_content,
            "-name",
            "ur5e",
            "-allow_renaming",
            "true",
        ],
    )

    gz_launch_description = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [FindPackageShare("ros_gz_sim"), "/launch/gz_sim.launch.py"]
        ),
        launch_arguments={
            "gz_args": IfElseSubstitution(
                gazebo_gui,
                if_value=[" -r -v 4 ", world_file],
                else_value=[" -s -r -v 4 ", world_file],
            )
        }.items(),
    )

    # Make the /clock topic available in ROS
    gz_sim_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
        ],
        output="screen",
    )

     # NEU: Starte alle Controller-Spawner ERST, nachdem der Roboter in Gazebo gespawnt wurde
    delay_spawners_after_gz_spawn = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=gz_spawn_entity,
            on_exit=[
                joint_state_broadcaster_spawner,
                velocity_controllers_spawner,
                position_controllers_spawner,
                trajectory_controller_spawner,
                joint_trajectory_controller_spawner,
                rviz2_joint_state_publisher,
            ],
        )
    )

    nodes_to_start = [
        robot_state_publisher_node,
        gz_launch_description,
        gz_spawn_entity,
        delay_spawners_after_gz_spawn,
        initial_joint_controller_spawner_stopped,
        initial_joint_controller_spawner_started,
        rviz_node,
        gz_sim_bridge,
    ]

    return nodes_to_start


def generate_launch_description():
    declared_arguments = []
    # UR specific arguments
    declared_arguments.append(
        DeclareLaunchArgument(
            "ur_type",
            description="Type/series of used UR robot.",
            choices=[
                "ur3",
                "ur3e",
                "ur5",
                "ur5e",
                "ur7e",
                "ur10",
                "ur10e",
                "ur12e",
                "ur16e",
                "ur15",
                "ur20",
                "ur30",
            ],
            default_value="ur5e",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "safety_limits",
            default_value="true",
            description="Enables the safety limits controller if true.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "safety_pos_margin",
            default_value="0.15",
            description="The margin to lower and upper limits in the safety controller.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "safety_k_position",
            default_value="20",
            description="k-position factor in the safety controller.",
        )
    )
    # General arguments
    declared_arguments.append(
        DeclareLaunchArgument(
            "controllers_file",
            default_value=PathJoinSubstitution(
                [FindPackageShare("ur_simulation_gz"), "config", "ur_controllers.yaml"]
            ),
            description="Absolute path to YAML file with the controllers configuration.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "tf_prefix",
            default_value='""',
            description="Prefix of the joint names, useful for "
            "multi-robot setup. If changed than also joint names in the controllers' configuration "
            "have to be updated.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "activate_joint_controller",
            default_value="true",
            description="Enable headless mode for robot control",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "initial_joint_controller",
            default_value="scaled_joint_trajectory_controller",
            description="Robot controller to start.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "description_file",
            default_value=PathJoinSubstitution(
                [FindPackageShare("ur_simulation_gz"), "urdf", "ur_gz.urdf.xacro"]
            ),
            description="URDF/XACRO description file (absolute path) with the robot.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument("launch_rviz", default_value="true", description="Launch RViz?")
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "rviz_config_file",
            default_value=PathJoinSubstitution(
                [FindPackageShare("ur_description"), "rviz", "view_robot.rviz"]
            ),
            description="Rviz config file (absolute path) to use when launching rviz.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "gazebo_gui", default_value="true", description="Start gazebo with GUI?"
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "world_file",
            default_value="empty.sdf",
            description="Gazebo world file (absolute path or filename from the gazebosim worlds collection) containing a custom world.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'serial_port',
            default_value = '/dev/ttyUSB0',
            description = 'Serial port to which Mia Hand is connected.'
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'laterality',
            default_value = 'right',
            description = 'Parameter for loading a right or left hand in RViz2.'
                            'Ignored if rviz2_gui:=false.'
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'prefix',
            default_value = '',
            description = 'Prefix to be added before Mia Hand link and joint names.'
                            'Useful for multi-robot scenarios.'
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'robot_ns',
            default_value = 'mia_hand'
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'use_mock_hardware',
            default_value = 'true',
            description="Start robot with mock hardware mirroring command to its states.",
        )
    )

    return LaunchDescription(declared_arguments + [OpaqueFunction(function=launch_setup)])
