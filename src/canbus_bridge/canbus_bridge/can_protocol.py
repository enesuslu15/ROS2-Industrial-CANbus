"""
can_protocol.py
───────────────
Endüstriyel CANbus protokol tanımları ve decode motoru.

CAN Frame Haritası
------------------
0x100  RPM           byte[0:2]  uint16        ×1        rpm
0x101  Sıcaklık      byte[0:2]  int16 / 10    °C
0x102  Tork          byte[0:2]  int16 / 100   N·m
0x103  Gerilim       byte[0:2]  uint16 / 10   V
0x104  Akım          byte[0:2]  int16 / 100   A
0x1FF  Hata Bayrağı  byte[0]    bitmask
"""

import struct
from dataclasses import dataclass, field
from typing import Optional

# ──────────────────────────────────────────────
#  CAN ID Sabitleri
# ──────────────────────────────────────────────
CAN_ID_RPM         = 0x100
CAN_ID_TEMP        = 0x101
CAN_ID_TORQUE      = 0x102
CAN_ID_VOLTAGE     = 0x103
CAN_ID_CURRENT     = 0x104
CAN_ID_ERROR       = 0x1FF
CAN_ID_ML_ANOMALY  = 0x200  # Added for Project 8: ML Anomaly Detection

# Hata bitmask'ları
ERROR_OVERHEAT     = 0b00000001   # bit 0
ERROR_OVERCURRENT  = 0b00000010   # bit 1
ERROR_UNDERVOLTAGE = 0b00000100   # bit 2
ERROR_COMM_LOSS    = 0b00001000   # bit 3
ERROR_ENCODER      = 0b00010000   # bit 4

# ──────────────────────────────────────────────
#  Veri Sınıfları
# ──────────────────────────────────────────────
@dataclass
class MotorTelemetry:
    """Anlık motor durumu."""
    rpm:        Optional[float] = None
    temp_c:     Optional[float] = None
    torque_nm:  Optional[float] = None
    voltage_v:  Optional[float] = None
    current_a:  Optional[float] = None
    error_flags: int = 0
    timestamp:  float = 0.0

    def active_errors(self) -> list[str]:
        errors = []
        if self.error_flags & ERROR_OVERHEAT:     errors.append("AŞIRI ISINMA")
        if self.error_flags & ERROR_OVERCURRENT:  errors.append("AŞIRI AKIM")
        if self.error_flags & ERROR_UNDERVOLTAGE: errors.append("DÜŞÜK GERİLİM")
        if self.error_flags & ERROR_COMM_LOSS:    errors.append("İLETİŞİM KAYBI")
        if self.error_flags & ERROR_ENCODER:      errors.append("ENCODER HATASI")
        return errors


@dataclass
class DecodedFrame:
    """Tek bir CAN frame'inin decode edilmiş hali."""
    can_id:    int
    raw_bytes: bytes
    signal:    str
    value:     float
    unit:      str
    is_error:  bool = False
    error_list: list = field(default_factory=list)

    @property
    def hex_str(self) -> str:
        return " ".join(f"{b:02X}" for b in self.raw_bytes)

    @property
    def formatted_value(self) -> str:
        if self.is_error:
            if self.error_list:
                return " | ".join(self.error_list)
            return "Sistem Normal"
        return f"{self.value:.2f} {self.unit}"


# ──────────────────────────────────────────────
#  Encode Fonksiyonları (Node A için)
# ──────────────────────────────────────────────
def encode_rpm(rpm: float) -> bytes:
    """RPM → 2 byte uint16."""
    val = max(0, min(65535, int(rpm)))
    return struct.pack(">H", val)

def encode_temp(temp_c: float) -> bytes:
    """Sıcaklık °C → 2 byte int16 (×10 scale)."""
    val = max(-3276, min(3276, int(temp_c * 10)))
    return struct.pack(">h", val)

def encode_torque(torque_nm: float) -> bytes:
    """Tork N·m → 2 byte int16 (×100 scale)."""
    val = max(-3276, min(3276, int(torque_nm * 100)))
    return struct.pack(">h", val)

def encode_voltage(voltage_v: float) -> bytes:
    """Gerilim V → 2 byte uint16 (×10 scale)."""
    val = max(0, min(6553, int(voltage_v * 10)))
    return struct.pack(">H", val)

def encode_current(current_a: float) -> bytes:
    """Akım A → 2 byte int16 (×100 scale)."""
    val = max(-3276, min(3276, int(current_a * 100)))
    return struct.pack(">h", val)

def encode_error(flags: int) -> bytes:
    """Hata bayrakları → 1 byte."""
    return bytes([flags & 0xFF])


# ──────────────────────────────────────────────
#  Decode Fonksiyonları (Node B için)
# ──────────────────────────────────────────────
def decode_frame(can_id: int, data: bytes) -> Optional[DecodedFrame]:
    """
    Verilen CAN ID ve ham data byte'larını decode eder.
    Bilinmeyen ID için None döner.
    """
    try:
        if can_id == CAN_ID_RPM:
            val = struct.unpack(">H", data[:2])[0]
            return DecodedFrame(can_id, data, "Motor RPM", float(val), "RPM")

        elif can_id == CAN_ID_TEMP:
            val = struct.unpack(">h", data[:2])[0] / 10.0
            return DecodedFrame(can_id, data, "Motor Sıcaklığı", val, "°C")

        elif can_id == CAN_ID_TORQUE:
            val = struct.unpack(">h", data[:2])[0] / 100.0
            return DecodedFrame(can_id, data, "Tork", val, "N·m")

        elif can_id == CAN_ID_VOLTAGE:
            val = struct.unpack(">H", data[:2])[0] / 10.0
            return DecodedFrame(can_id, data, "DC Gerilim", val, "V")

        elif can_id == CAN_ID_CURRENT:
            val = struct.unpack(">h", data[:2])[0] / 100.0
            return DecodedFrame(can_id, data, "Faz Akımı", val, "A")

        elif can_id == CAN_ID_ERROR:
            flags = data[0] if data else 0
            dummy = DecodedFrame(can_id, data, "Hata Durumu", float(flags), "",
                                 is_error=True)
            dummy.error_list = _parse_error_flags(flags)
            return dummy

        elif can_id == CAN_ID_ML_ANOMALY:
            # 1 byte payload: 1 = Anomaly, 0 = Normal
            val = data[0] if data else 0
            is_anomaly = (val == 1)
            msg = "ML Anomali Tespit Edildi!" if is_anomaly else "ML Normal"
            return DecodedFrame(can_id, data, "ML Tahmini", float(val), "",
                                is_error=is_anomaly, error_list=[msg] if is_anomaly else [])

    except (struct.error, IndexError):
        return None

    return None

def encode_ml_anomaly(is_anomaly: bool) -> bytes:
    """ML anomali bayrağı -> 1 byte (1 veya 0)."""
    return bytes([1 if is_anomaly else 0])

def _parse_error_flags(flags: int) -> list[str]:
    errors = []
    if flags & ERROR_OVERHEAT:     errors.append("AŞIRI ISINMA")
    if flags & ERROR_OVERCURRENT:  errors.append("AŞIRI AKIM")
    if flags & ERROR_UNDERVOLTAGE: errors.append("DÜŞÜK GERİLİM")
    if flags & ERROR_COMM_LOSS:    errors.append("İLETİŞİM KAYBI")
    if flags & ERROR_ENCODER:      errors.append("ENCODER HATASI")
    return errors


# ──────────────────────────────────────────────
#  ID → İnsan Okunabilir Etiket
# ──────────────────────────────────────────────
CAN_ID_LABELS = {
    CAN_ID_RPM:     "RPM       ",
    CAN_ID_TEMP:    "SICAKLIK  ",
    CAN_ID_TORQUE:  "TORK      ",
    CAN_ID_VOLTAGE: "GERİLİM   ",
    CAN_ID_CURRENT: "AKIM      ",
    CAN_ID_ERROR:   "HATA      ",
    CAN_ID_ML_ANOMALY: "ML ANOMALİ",
}
