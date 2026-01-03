# ---------------------------------------------------------
# 설정
# ---------------------------------------------------------
ROBOT_IP = "     " # 로봇 컨트롤러의 IP 주소
SERIAL_PORT = 'COM9' # 시리얼 데이터 수신 포트 (센서 연결 포트)
BAUD_RATE = 115200 # 시리얼 통신 속도

# [제어 모드 설정]
ENABLE_ROTATION = False # 회전(Rx, Ry, Rz) 제어 활성화 여부 (False: 위치(X, Y, Z)만 제어)

# [부드러운 움직임 설정] 
# 시리얼 입력 데이터(정수 값)를 로봇의 이동 거리(mm 또는 degree)로 변환하는 비율(민감도)
# 명령 주기를 늦추는 대신, 한 번에 움직이는 양(감도)을 키워야 속도가 유지.
SCALE_POS = 0.05 # 위치(X,Y,Z) 이동 민감도 (예: 입력 1000 -> 50mm 이동)
SCALE_ROT = 0.05 # 회전(Rx,Ry,Rz) 이동 민감도

# 최대 이동 제한 (한 번에 너무 많이 튀지 않게)
MAX_STEP_POS = 10.0 # 위치 이동의 최대 증분 (mm)
MAX_STEP_ROT = 2.0 # 회전 이동의 최대 증분 (degree)

# 입력 최소 임계값 (데드존: 이 값보다 작으면 움직이지 않음)
INPUT_THRESHOLD = 300

# ---------------------------------------------------------
# [핵심] 시리얼 데이터 수집 스레드
# ---------------------------------------------------------
class SerialReader(threading.Thread):
    def __init__(self, port, baud_rate):
        super().__init__()
        self.port = port
        self.baud_rate = baud_rate
        self.ser = None
        self.running = True
        self.latest_data = None 
        self.lock = threading.Lock() # 데이터 접근 시 동시성 문제 방지용 Lock
        # 시리얼 데이터 파싱을 위한 정규 표현식 (예: "X:123 Y:-45 Z:67 Rx:0 Ry:0 Rz:0")
        self.pattern = re.compile(r"X:(-?\d+)\s+Y:(-?\d+)\s+Z:(-?\d+)\s+Rx:(-?\d+)\s+Ry:(-?\d+)\s+Rz:(-?\d+)")

    def run(self):
        try:
            # 시리얼 포트 연결 시도
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=0.05)
            print(f"[Thread] Connected to Serial: {self.port}")
        except Exception as e:
            print(f"[Thread] Serial Error: {e}")
            return

        while self.running:
            if self.ser.in_waiting > 0: # 시리얼 버퍼에 데이터가 있는지 확인
                try:
                    # 한 줄 읽기 및 디코딩
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    match = self.pattern.search(line)
                    if match:
                        # 정규식으로 X, Y, Z, Rx, Ry, Rz 값 추출 및 정수형으로 저장
                        raw = {
                            'x': int(match.group(1)), 'y': int(match.group(2)), 'z': int(match.group(3)),
                            'rx': int(match.group(4)), 'ry': int(match.group(5)), 'rz': int(match.group(6))
                        }
                        with self.lock:
                            # 최신 데이터 업데이트 (다른 스레드 접근 보호)
                            self.latest_data = raw
                except:
                    # 데이터 파싱 실패 등 오류 무시하고 계속 진행
                    pass
            else:
                # 데이터가 없으면 잠시 대기
                time.sleep(0.001)

    def get_latest_data(self):
        # 외부에서 최신 데이터를 안전하게 가져오는 메서드
        with self.lock:
            return self.latest_data

    def stop(self):
        # 스레드 종료 및 시리얼 포트 닫기
        self.running = False
        if self.ser:
            self.ser.close()

            # ---------------------------------------------------------
# 헬퍼 함수
# ---------------------------------------------------------
FOUND_MOVE_FUNC = None # 탐색된 로봇 이동 함수를 저장할 전역 변수

def find_move_method(indy):
    # IndyDCP3 라이브러리의 버전이나 설정에 따라 사용 가능한 이동 함수(task_move, move_l 등)를 동적으로 찾음
    global FOUND_MOVE_FUNC
    candidates = ['task_move', 'move_task', 'move_l', 'movel', 'move_to_task', 'move_p', 'move']
    # ... (함수 탐색 로직) ...
    return False

def get_safe_task_pos(indy):
    # 로봇의 현재 Task Pose (X, Y, Z, Rx, Ry, Rz)를 안전하게 가져오는 함수
    # IndyDCP3 라이브러리의 여러 버전을 고려하여 다양한 메서드 이름 시도
    # ... (위치 가져오기 로직) ...
    return None

def clamp(value, max_limit):
    # 값을 주어진 최대/최소 범위로 제한하는 함수 (MAX_STEP_POS/ROT 제한에 사용)
    if value > max_limit: return max_limit
    if value < -max_limit: return -max_limit
    return value

# ---------------------------------------------------------
# 메인 로직
# ---------------------------------------------------------
def main():
    global FOUND_MOVE_FUNC
    
    # 1. 로봇 연결
    try:
        indy = IndyDCP3(robot_ip=ROBOT_IP, index=0) # 로봇 객체 생성 및 연결
        print(f"Connected to Robot: {ROBOT_IP}")
        if not find_move_method(indy): return # 이동 함수를 찾지 못하면 종료
    except Exception as e:
        print(f"Robot Connection Failed: {e}")
        return

    # 2. 시리얼 리더 스레드 시작
    serial_thread = SerialReader(SERIAL_PORT, BAUD_RATE)
    serial_thread.start()
    time.sleep(1) 

    # 초기 위치 읽기
    initial_pose = get_safe_task_pos(indy)
    if initial_pose is None:
        print(" Failed! (Can't get position)")
        return
    
    # 로봇의 현재 위치를 기반으로 가상 위치(Virtual Pose) 초기화
    # 로봇의 실제 위치가 아니라, 시리얼 입력에 따라 계산된 '목표 위치'를 누적함
    virtual_pose = list(initial_pose)

    print("Starting SMOOTH Control Loop... Press Ctrl+C to stop.")
    
    try:
        while True:
            # 1. 최신 데이터 가져오기
            raw_data = serial_thread.get_latest_data()
            
            if raw_data is None:
                time.sleep(0.01)
                continue

            # 2. 단일 축 선택 + 데드존 필터링
            axes = ['x', 'y', 'z'] 
            if ENABLE_ROTATION:
                axes.extend(['rx', 'ry', 'rz']) 
            
            # 절대값이 가장 큰 축을 '주요 입력 축'으로 선택
            max_axis = max(axes, key=lambda k: abs(raw_data[k]))
            max_val = abs(raw_data[max_axis])

            if max_val < INPUT_THRESHOLD:
                # 데드존(최소 임계값)보다 작으면 움직이지 않고 대기
                time.sleep(0.01) 
                continue
            
            # 가장 큰 입력값 외에는 모두 0으로 필터링 (단일 축 제어 모드)
            filtered_data = {k: (raw_data[k] if k == max_axis else 0) for k in ['x','y','z','rx','ry','rz']}
            
            # 3. 델타 계산: (입력 값 * 민감도) 후 최대 이동 제한(Clamp) 적용
            delta_x = clamp(filtered_data['x'] * SCALE_POS, MAX_STEP_POS)
            delta_y = clamp(filtered_data['y'] * SCALE_POS, MAX_STEP_POS)
            delta_z = clamp(filtered_data['z'] * SCALE_POS, MAX_STEP_POS)
            
            delta_rx, delta_ry, delta_rz = 0, 0, 0
            if ENABLE_ROTATION:
                delta_rx = clamp(filtered_data['rx'] * SCALE_ROT, MAX_STEP_ROT)
                delta_ry = clamp(filtered_data['ry'] * SCALE_ROT, MAX_STEP_ROT)
                delta_rz = clamp(filtered_data['rz'] * SCALE_ROT, MAX_STEP_ROT)

            # 4. 가상 위치 누적: 계산된 증분(delta)을 목표 위치(virtual_pose)에 더함
            virtual_pose[0] += delta_x # X
            virtual_pose[1] += delta_y # Y
            virtual_pose[2] += delta_z # Z
            virtual_pose[3] += delta_rx # Rx
            virtual_pose[4] += delta_ry # Ry
            virtual_pose[5] += delta_rz # Rz

            # 5. 명령 전송: 누적된 목표 위치(virtual_pose)로 로봇 이동 명령 전송
            try:
                FOUND_MOVE_FUNC(virtual_pose)
            except Exception as e:
                # 이동 오류 발생 시 (예: 로봇 한계 도달), 현재 실제 위치로 목표 위치를 재동기화
                print(f"Move Error: {e}")
                print("Resyncing position...")
                current_real_pose = get_safe_task_pos(indy)
                if current_real_pose:
                    virtual_pose = list(current_real_pose)
                time.sleep(1)
                continue
            
            # 반응 속도 조절 (명령 전송 주기)
            # 너무 빠르면 로봇이 명령을 다 처리하지 못할 수 있음. 0.05초(20Hz) 권장.
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        # 프로그램 종료 시 시리얼 스레드 및 로봇 동작 정지
        serial_thread.stop()
        serial_thread.join()
        if hasattr(indy, 'stop_motion'):
            indy.stop_motion()

if __name__ == "__main__":
    main()