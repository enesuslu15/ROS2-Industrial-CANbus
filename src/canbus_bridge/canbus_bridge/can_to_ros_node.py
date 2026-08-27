import rclpy
from rclpy.node import Node
import can
import threading

from canbus_msgs.msg import MotorTelemetry, AnomalyAlert
from sensor_msgs.msg import JointState
import math
import time

from .can_protocol import (
    decode_frame,
    CAN_ID_RPM, CAN_ID_TEMP, CAN_ID_TORQUE,
    CAN_ID_VOLTAGE, CAN_ID_CURRENT, CAN_ID_ERROR,
    CAN_ID_ML_ANOMALY,
    ERROR_OVERHEAT, ERROR_OVERCURRENT, ERROR_UNDERVOLTAGE
)

class CanToRosNode(Node):
    def __init__(self):
        super().__init__('can_to_ros_node')
        
        # Publishers
        self.telemetry_pub = self.create_publisher(MotorTelemetry, '/motor/telemetry', 10)
        self.anomaly_pub = self.create_publisher(AnomalyAlert, '/motor/anomaly', 10)
        self.joint_pub = self.create_publisher(JointState, '/joint_states', 10)
        
        # Internal state
        self.telemetry = MotorTelemetry()
        self.motor_angle = 0.0
        self.last_time = time.time()
        
        self.get_logger().info('CAN to ROS2 Bridge Node started.')
        self.get_logger().info('Listening on UDP Multicast 239.0.0.1...')
        
        # CAN Bus connection
        try:
            self.bus = can.Bus(interface='udp_multicast', channel='239.0.0.1')
        except Exception as e:
            self.get_logger().error(f'Failed to connect to CAN Bus: {e}')
            return
            
        # Start listener thread
        self.running = True
        self.listener_thread = threading.Thread(target=self._can_listener, daemon=True)
        self.listener_thread.start()
        
        # Timer to publish telemetry periodically (e.g. 10Hz)
        self.timer = self.create_timer(0.1, self._publish_telemetry)
        
    def _can_listener(self):
        while self.running and rclpy.ok():
            try:
                msg = self.bus.recv(timeout=0.1)
                if msg is None:
                    continue
                    
                frame = decode_frame(msg.arbitration_id, bytes(msg.data))
                if frame is None:
                    continue
                    
                self._update_state(frame)
                
            except can.CanError:
                pass
                
    def _update_state(self, frame):
        # Update our internal telemetry state based on incoming CAN frames
        if frame.can_id == CAN_ID_RPM:
            self.telemetry.rpm = float(frame.value)
        elif frame.can_id == CAN_ID_TEMP:
            self.telemetry.temperature = float(frame.value)
        elif frame.can_id == CAN_ID_TORQUE:
            self.telemetry.torque = float(frame.value)
        elif frame.can_id == CAN_ID_VOLTAGE:
            self.telemetry.voltage = float(frame.value)
        elif frame.can_id == CAN_ID_CURRENT:
            self.telemetry.current = float(frame.value)
        elif frame.can_id == CAN_ID_ERROR:
            # frame.value holds the raw bitmask for error
            flags = int(frame.value)
            self.telemetry.is_overheat = bool(flags & ERROR_OVERHEAT)
            self.telemetry.is_overcurrent = bool(flags & ERROR_OVERCURRENT)
            self.telemetry.is_undervoltage = bool(flags & ERROR_UNDERVOLTAGE)
        elif frame.can_id == CAN_ID_ML_ANOMALY:
            # Publish anomaly alert if it's an anomaly (val == 1)
            is_anomaly = (int(frame.value) == 1)
            if is_anomaly:
                alert = AnomalyAlert()
                alert.is_anomaly = True
                alert.message = "ML Anomaly Detected!"
                alert.features = [
                    self.telemetry.rpm,
                    self.telemetry.temperature,
                    self.telemetry.torque,
                    self.telemetry.voltage,
                    self.telemetry.current
                ]
                self.anomaly_pub.publish(alert)
                self.get_logger().warn(f'ML Anomaly Alert Published! RPM: {self.telemetry.rpm}')
            
    def _publish_telemetry(self):
        # Publish the latest state
        self.telemetry_pub.publish(self.telemetry)
        
        # Calculate motor spin (integration)
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time
        
        # RPM to Radian per second: rad/s = RPM * 2 * pi / 60
        angular_vel = self.telemetry.rpm * 2.0 * math.pi / 60.0
        self.motor_angle += angular_vel * dt
        
        # Keep angle in [0, 2pi] roughly
        self.motor_angle %= (2 * math.pi)
        
        # Publish JointState so RViz2 shows rotation
        joint_msg = JointState()
        joint_msg.header.stamp = self.get_clock().now().to_msg()
        joint_msg.name = ['motor_joint']
        joint_msg.position = [self.motor_angle]
        joint_msg.velocity = [angular_vel]
        self.joint_pub.publish(joint_msg)
        
    def destroy_node(self):
        self.running = False
        if hasattr(self, 'bus'):
            self.bus.shutdown()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = CanToRosNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

