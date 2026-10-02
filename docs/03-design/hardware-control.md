# Hardware Control & Embedded Firmware Design

**Document ID:** `DOC-03-HARDWARE`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Pin Assignment Baseline

The proposed pin mapping represents a verified baseline for standard 30-pin and 38-pin ESP32 DevKit v1 boards, selected specifically to avoid bootloader strapping conflicts (`GPIO 0, 2, 12, 15`).

```text
                        ESP32 DevKit v1
                     +--------------------+
                 3V3 | [ ]            [ ] | GND
                 GND | [ ]            [ ] | GPIO 23 (SPI MOSI) ────> MFRC522 MOSI
   MFRC522 CS <── GPIO 5 | [ ]            [ ] | GPIO 22 (SPI RST)  ────> MFRC522 RST
   MFRC522 SCK <─ GPIO 18| [ ]            [ ] | GPIO 1  (TX0)      ────> Laptop RX
   MFRC522 MISO<─ GPIO 19| [ ]            [ ] | GPIO 3  (RX0)      <─── Laptop TX
   Servo PWM <─── GPIO 25| [ ]            [ ] | GPIO 21
   Green LED <─── GPIO 26| [ ]            [ ] | GPIO 19
   Red LED   <─── GPIO 27| [ ]            [ ] | GPIO 18
   Buzzer    <─── GPIO 32| [ ]            [ ] | GPIO 5
                     +--------------------+
```

### Complete Hardware Interconnect Table

| Peripheral | Signal | ESP32 Pin | Logic Level | Electrical Notes |
| :--- | :--- | :--- | :--- | :--- |
| **MFRC522 RFID** | `VCC` | `3V3` Pin | $3.3\text{ V}$ | **Do not connect to 5V.** Connect to ESP32 3.3V rail. |
| | `GND` | `GND` Pin | $0\text{ V}$ | Ground reference. |
| | `RST` | `GPIO 22` | $3.3\text{ V}$ | Active-low hardware reset. |
| | `SDA / SS`| `GPIO 5` | $3.3\text{ V}$ | SPI Chip Select (CS). |
| | `SCK` | `GPIO 18` | $3.3\text{ V}$ | SPI Bus Clock. |
| | `MISO` | `GPIO 19` | $3.3\text{ V}$ | SPI Master In / Slave Out. |
| | `MOSI` | `GPIO 23` | $3.3\text{ V}$ | SPI Master Out / Slave In. |
| **SG90 Servo** | `PWM` | `GPIO 25` | $3.3\text{ V}$ | $50\text{ Hz}$ PWM signal from ESP32 LEDC channel. |
| | `V+` (Red) | Ext $+5\text{ V}$| $5.0\text{ V}$ | **External 5V supply.** Never power from 3.3V LDO. |
| | `GND` | Ext GND | $0\text{ V}$ | Common ground tied directly to ESP32 GND pin. |
| **Green LED** | Anode | `GPIO 26` | $3.3\text{ V}$ | Via $330\,\Omega$ series resistor. Active HIGH. |
| **Red LED** | Anode | `GPIO 27` | $3.3\text{ V}$ | Via $330\,\Omega$ series resistor. Active HIGH. |
| **Buzzer** | Signal | `GPIO 32` | $3.3\text{ V}$ | Active buzzer or switching transistor base. |

---

## 2. Servo Actuation PWM Math & Configuration

The ESP32 drives the SG90 servo motor utilizing its hardware LED Control (LEDC) peripheral:

* **PWM Frequency:** $50\text{ Hz}$ (Period $T = 20\text{ ms} = 20,000\,\mu\text{s}$).
* **Timer Resolution:** 16 bits ($2^{16} - 1 = 65535$ counts).
* **Clock Calculation:**
  $$\text{Duty Cycle Count} = \left( \frac{\text{Pulse Width in }\mu\text{s}}{20,000\,\mu\text{s}} \right) \times 65535$$

| Physical State | Target Angle | Pulse Width | Computed 16-bit Duty |
| :--- | :--- | :--- | :--- |
| **LOCKED (Closed)** | $0^\circ$ | $500\,\mu\text{s}$ | $\frac{500}{20000} \times 65535 \approx \mathbf{1638}$ |
| **UNLOCKED (Open)** | $90^\circ$ | $1500\,\mu\text{s}$ | $\frac{1500}{20000} \times 65535 \approx \mathbf{4915}$ |
| **UNLOCKED (Max)** | $180^\circ$ | $2400\,\mu\text{s}$ | $\frac{2400}{20000} \times 65535 \approx \mathbf{7864}$ |

---

## 3. Non-Blocking FreeRTOS Firmware Loop

The ESP32 executes all state transitions without blocking delays (`delay()` is strictly prohibited):

```cpp
void loop() {
    uint32_t now = millis();

    // 1. Process UART NDJSON Commands from Host
    pollSerialCommands();

    // 2. Poll RFID Sensor (with 500ms debounce guard)
    pollRfidSensor(now);

    // 3. Update Actuator State Machine (Handle door hold timer)
    updateActuatorState(now);

    // 4. Emit Heartbeat every 1000ms
    if (now - last_heartbeat_ms >= 1000) {
        emitHeartbeat();
        last_heartbeat_ms = now;
    }
}
```

### Door Hold Logic
When `ACCESS_GRANTED` occurs:
1. Servo angle is set to $90^\circ$.
2. Green LED is set `HIGH`.
3. Buzzer emits two $100\text{ ms}$ pulses.
4. Firmware records `door_open_start_ms = millis()`.
5. When `millis() - door_open_start_ms >= door_hold_ms` (default 3000 ms), servo angle is restored to $0^\circ$, Green LED is set `LOW`, and state returns to `IDLE`.
