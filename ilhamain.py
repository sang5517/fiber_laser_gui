import sys
import threading
import time
from datetime import datetime
from PyQt5 import QtWidgets, QtCore
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import pandas as pd

# =========================
# 전역 상태
# =========================
latest_s1, latest_s2, latest_ra = 0, 0, 0
powers1, powers2, ratio = [], [], []
count = 0
power_thread = None
power_running = False
timer = None
experiment_running = False
motor_moving = False
home_moving = False

win, canvas, ax = None, None, None
lbl_m0_pos, lbl_m1_pos = None, None

# =========================
# 모터/파워미터 가상 함수 (실제 하드웨어 함수로 대체)
# =========================
def Connect(a, b): pass
def SetServoOn(b): pass
def sync_hw_to_json(): pass
def MoveAbsPos(axis, pos): return True
def stop_motor(axis): print(f"[INFO] Motor {axis} stop")
def update_motor_label(axis): pass
def get_actual_pos_safe(axis): return 0
def home_motors_threaded(lbl_warning_gui=None): pass
def set_software_home(): pass
def load_position_json(): return {}
def get_minimum(times, p1, p2, r, name): return 50
def find_local_minima_sg(times, ratio, name): pass

# =========================
# 파워미터 측정
# =========================
def measure(nmeasurements, interval, filename=""):
    # 실제 PyVISA 측정 코드 대신 더미값 반환
    s1 = round(10 + 5 * time.time() % 1, 3)
    s2 = round(12 + 5 * time.time() % 1, 3)
    ra = s2 / s1 if s1 != 0 else 1e8
    return s1, s2, ra

def measure_thread_func():
    global latest_s1, latest_s2, latest_ra, power_running
    while power_running:
        try:
            latest_s1, latest_s2, latest_ra = measure(1, 1.0)
        except Exception as e:
            print("[ERROR] Measure failed:", e)
            power_running = False
        time.sleep(0.1)

# =========================
# GUI용 측정 시작/중지
# =========================
def start_power_meter():
    global power_thread, power_running, timer
    if power_thread and power_thread.is_alive(): return
    power_running = True
    power_thread = threading.Thread(target=measure_thread_func, daemon=True)
    power_thread.start()
    timer = QtCore.QTimer()
    timer.timeout.connect(update_plot)
    timer.start(1000)

def stop_power_meter():
    global power_running, timer
    power_running = False
    if timer:
        timer.stop()
        timer = None
    print("[INFO] Power meter stopped")

def save_data():
    if not powers1:
        print("[WARN] No data to save")
        return
    filename, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Save CSV", "", "CSV Files (*.csv)")
    if not filename: return
    df = pd.DataFrame({"Power_S1(W)": powers1, "Power_S2(W)": powers2, "Ratio": ratio})
    df.to_csv(filename, index=False)
    print(f"[INFO] Data saved to {filename}")

# =========================
# GUI plot 업데이트
# =========================
def update_plot():
    global powers1, powers2, ratio, count, ax, canvas, latest_s1, latest_s2, latest_ra
    s1, s2, ra = latest_s1, latest_s2, latest_ra
    if s1 == 0 and s2 == 0: return
    powers1.append(s1)
    powers2.append(s2)
    ratio.append(ra)
    count += 1
    x_data = list(range(1, count + 1))

    ax[0].cla()
    ax[0].plot(x_data, powers1, 'r-o', label='S1'); ax[0].set_title("Channel 1"); ax[0].legend(); ax[0].grid(True)
    ax[1].cla()
    ax[1].plot(x_data, powers2, 'b-o', label='S2'); ax[1].set_title("Channel 2"); ax[1].legend(); ax[1].grid(True)
    ax[2].cla()
    ax[2].plot(x_data, ratio, 'g-o', label='Ratio'); ax[2].set_title("Ratio"); ax[2].legend(); ax[2].grid(True)
    canvas.draw()

# =========================
# GUI 생성
# =========================
def show_control_gui():
    global win, canvas, ax, lbl_m0_pos, lbl_m1_pos

    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])

    win = QtWidgets.QWidget()
    win.setWindowTitle("Motor + Power Meter Control")
    win.closeEvent = on_close_event

    # matplotlib
    fig, ax = plt.subplots(3,1,figsize=(6,8))
    canvas = FigureCanvas(fig)

    # 모터 위치 라벨
    lbl_m0_pos = QtWidgets.QLabel(f"M0: {get_actual_pos_safe(0)}")
    lbl_m1_pos = QtWidgets.QLabel(f"M1: {get_actual_pos_safe(1)}")
    update_motor_label(0)
    update_motor_label(1)

    # 경고 라벨
    lbl_warning_gui = QtWidgets.QLabel("")

    # 버튼
    btn_start_power = QtWidgets.QPushButton("Start Power Meter")
    btn_start_power.clicked.connect(start_power_meter)
    btn_stop_power = QtWidgets.QPushButton("Stop Power Meter")
    btn_stop_power.clicked.connect(stop_power_meter)
    btn_save = QtWidgets.QPushButton("Save Data")
    btn_save.clicked.connect(save_data)

    layout = QtWidgets.QVBoxLayout()
    layout.addWidget(canvas)
    layout.addWidget(btn_start_power)
    layout.addWidget(btn_stop_power)
    layout.addWidget(btn_save)
    layout.addWidget(lbl_m0_pos)
    layout.addWidget(lbl_m1_pos)
    layout.addWidget(lbl_warning_gui)

    win.setLayout(layout)
    win.show()
    app.exec_()

def on_close_event(event):
    global power_running, powers1, powers2, ratio, count
    power_running = False
    powers1.clear(); powers2.clear(); ratio.clear(); count = 0
    stop_motor(0)
    stop_motor(1)
    event.accept()
    print("[INFO] GUI closed safely")

# =========================
# 메인
# =========================
if __name__ == "__main__":
    # 모터 연결 (더미)
    for nBdID in [0,1]:
        Connect(0, nBdID)
        SetServoOn(nBdID)
    sync_hw_to_json()
    show_control_gui()
