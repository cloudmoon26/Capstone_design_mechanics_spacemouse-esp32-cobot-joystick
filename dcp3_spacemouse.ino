/*
 * SpaceMouse to PC Serial Bridge
 * - SpaceMouse의 UART 데이터를 읽어서 PC(Python)로 전달합니다.
 * - Python 코드가 읽을 수 있도록 포맷을 "X:100 Y:200..." 형태로 통일했습니다.
 */

#include <HardwareSerial.h>

// SpaceMouse Module과 통신할 시리얼 포트 정의 (ESP32 RX:16, TX:17)
HardwareSerial SpaceMouseSerial(1);

// SpaceMouse 통신 프로토콜 상수
const byte REQUEST_DATA_COMMAND = 0xAC;
const byte START_BYTE = 0x96;
const byte END_BYTE = 0x8D;

// 6개 축의 데이터 저장을 위한 전역 변수
int16_t x_trans, y_trans, z_trans, x_rot, y_rot, z_rot;

// --- 함수 선언 ---
void parseData(byte* packet);
bool validateChecksum(byte* packet);

void setup() {
    // 1. PC와의 통신 (Python으로 데이터 전송용)
    Serial.begin(115200);
    while (!Serial);

    // 2. SpaceMouse와의 통신
    // Baud rate: 38400, 8N1 (SpaceMouse 모듈 표준)
    SpaceMouseSerial.begin(38400, SERIAL_8N1, 16, 17);

    // [중요] 파이썬 연결을 위해 초기화 문구는 출력하지 않거나 주석 처리합니다.
    // Serial.println("Ready..."); 
}

void loop() {
    // 1. 데이터 요청 명령 전송
    SpaceMouseSerial.write(REQUEST_DATA_COMMAND);
    
    // 2. 응답 대기 (타임아웃 10ms)
    unsigned long startTime = millis();
    while ((SpaceMouseSerial.available() < 16) && (millis() - startTime < 10)) {
        // 데이터가 16바이트 쌓일 때까지 기다림
        delay(1);
    }

    // 3. 데이터 읽기 및 파싱
    if (SpaceMouseSerial.available() >= 16) {
        byte packet[16];
        
        // 첫 바이트가 시작 바이트(0x96)인지 확인하며 읽기
        if (SpaceMouseSerial.peek() == START_BYTE) {
            SpaceMouseSerial.readBytes(packet, 16);

            // 종료 바이트 및 체크섬 검증
            if (packet[15] == END_BYTE && validateChecksum(packet)) {
                
                // 데이터 파싱 (바이트 -> 정수 변환)
                parseData(packet);

                // ★ [핵심] 파이썬 코드가 인식할 수 있는 포맷으로 출력 ★
                // 파이썬 Regex: r"X:(-?\d+)\s+Y:(-?\d+)..." 와 일치해야 함
                Serial.printf("X:%d Y:%d Z:%d Rx:%d Ry:%d Rz:%d\n", 
                              x_trans, y_trans, z_trans, x_rot, y_rot, z_rot);
                              
            } else {
                // 패킷이 깨졌으면 버퍼 비우기
                while(SpaceMouseSerial.available()) SpaceMouseSerial.read();
            }
        } else {
            // 쓰레기 값이면 한 바이트 버림
            SpaceMouseSerial.read();
        }
    }
    
    // 통신 주기 조절 (너무 빠르면 파이썬 쪽 버퍼 오버플로우 가능성)
    delay(10); 
}

// ---------------------------------------------------------
// 헬퍼 함수 구현
// ---------------------------------------------------------

// 체크섬 검증 함수
bool validateChecksum(byte* packet) {
    uint16_t calcChecksum = 0;
    // 처음 13바이트를 더함
    for (int i = 0; i < 13; i++) {
        calcChecksum += packet[i];
    }
    calcChecksum &= 0x3FFF; // 14비트로 마스킹

    // 패킷에 들어있는 체크섬 (13, 14번째 바이트)
    uint16_t rcvdChecksum = (packet[13] * 128) + packet[14];

    return (calcChecksum == rcvdChecksum);
}

// 데이터 파싱 함수 (14비트 데이터 처리)
void parseData(byte* packet) {
    // SpaceMouse 모듈은 2바이트를 사용하여 값을 표현 (Offset 8192)
    // 수식: (HighByte * 128 + LowByte) - 8192
    
    x_trans = (packet[1] * 128 + packet[2]) - 8192;
    y_trans = (packet[3] * 128 + packet[4]) - 8192;
    z_trans = (packet[5] * 128 + packet[6]) - 8192;
    
    x_rot   = (packet[7] * 128 + packet[8]) - 8192;
    y_rot   = (packet[9] * 128 + packet[10]) - 8192;
    z_rot   = (packet[11] * 128 + packet[12]) - 8192;
}