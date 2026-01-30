# tv_wpt_coil 스펙/입력 형식 정리

이 문서는 `/home/harry/Projects/PythonProjects/tv_wpt_coil/type1/type1.toml` 및 `/home/harry/Projects/PythonProjects/tv_wpt_coil/lock/non_model.toml` 샘플을 기준으로 **입력 스펙 구조**, **필수값/기본값/파생값 후보**를 정리한 것입니다.

## 1) 입력 형식 요약 (샘플 TOML 기준)

- 최상위 섹션
  - `units`
  - `coordinate_system`
  - `constraints`
  - `layout`
  - `tv`, `wall`, `floor`
  - `materials.core`
  - `tx.module`, `tx.position`
  - `rx.module`, `rx.position`, `rx.stack`
- 값 타입
  - 단일 스칼라 (예: `units.length = "mm"`)
  - 범위형 샘플링 배열 `[min, max, step]` (예: `tx.module.outer_w_mm = [200, 400, 10]`)
  - 불리언 (예: `tv.present = true`)
  - 문자열 (예: `tv.aspect_ratio = "16:9"`)

## 2) 필수값 · 기본값 · 파생값 후보 표

아래 표는 **샘플 TOML/문서에서 나타난 값**을 기준으로 정리한 것이며,
실제 구현에서는 규칙 확정 필요(별도 표기).

### 2.1 공통/좌표계/제약

| 경로 | 타입 | 필수? | 기본값 후보 | 파생? | 비고 |
| --- | --- | --- | --- | --- | --- |
| units.length | str | 필수 | "mm" | - | 현재 샘플은 mm 고정 |
| coordinate_system.wall_plane_x_mm | float 또는 [min,max,step] | 필수 | 0.0 | - | type1.toml은 배열, non_model.toml은 스칼라 |
| coordinate_system.floor_plane_z_mm | float 또는 [min,max,step] | 필수 | 0.0 | - | 동일 |
| constraints.core_core_gap_mm | [min,max,step] | 필수 | 100.0 | - | TX-RX edge-to-edge 간격 |
| constraints.rx_total_thickness_mm_max | [min,max,step] | 필수 | 4.0 | - | RX 총 두께 상한 |
| constraints.tx_gap_from_tv_bottom_mm | [min,max,step] | 필수 | 100.0 | - | TX top이 TV bottom에서 떨어진 거리 |
| layout.right_edge_y_mm | [min,max,step] | 선택 | 0.0 | - | 현재 unused |

### 2.2 TV/Wall/Floor (비모델)

| 경로 | 타입 | 필수? | 기본값 후보 | 파생? | 비고 |
| --- | --- | --- | --- | --- | --- |
| tv.present | bool | 선택 | true | - | non_model에서도 동일 의미 |
| tv.screen_diag_in | float | 필수 | 83.0 | - | 샘플 고정 |
| tv.aspect_ratio | str | 필수 | "16:9" | - | 파생 시 width/height 계산 필요 |
| tv.width_mm | float | 선택 | 파생 | 예 | screen_diag_in + aspect_ratio로 계산 |
| tv.height_mm | float | 선택 | 파생 | 예 | 동일 |
| tv.thickness_mm | float | 필수 | 9.0 | - | 샘플 고정 |
| tv.model | bool | 선택 | false | - | 비모델 표시 |
| tv.position.center_x_mm | float | 선택 | tv.thickness_mm/2 | 예 | wall_plane_x 기준 (flush) |
| tv.position.center_y_mm | float | 선택 | 0.0 | - | 샘플 0.0 |
| tv.position.center_z_mm | float | 필수 | 1200.0 | - | 샘플 고정 |
| wall.present | bool | 선택 | true | - |  |
| wall.thickness_mm | float | 선택 | 100.0 | - |  |
| wall.size_y_mm | float | 선택 | 4000.0 | - |  |
| wall.size_z_mm | float | 선택 | 3000.0 | - |  |
| wall.model | bool | 선택 | false | - |  |
| wall.position.center_x_mm | float | 선택 | -wall.thickness_mm/2 | 예 | wall_plane_x 기준 |
| wall.position.center_y_mm | float | 선택 | 0.0 | - |  |
| wall.position.center_z_mm | float | 선택 | wall.size_z_mm/2 | 예 | floor_plane_z 기준 |
| floor.present | bool | 선택 | true | - |  |
| floor.thickness_mm | float | 선택 | 100.0 | - |  |
| floor.size_x_mm | float | 선택 | 3000.0 | - |  |
| floor.size_y_mm | float | 선택 | 4000.0 | - |  |
| floor.model | bool | 선택 | false | - |  |
| floor.position.center_x_mm | float | 선택 | floor.size_x_mm/2 | 예 | wall_plane_x 기준 |
| floor.position.center_y_mm | float | 선택 | 0.0 | - |  |
| floor.position.center_z_mm | float | 선택 | -floor.thickness_mm/2 | 예 | floor_plane_z 기준 |

### 2.3 재료

| 경로 | 타입 | 필수? | 기본값 후보 | 파생? | 비고 |
| --- | --- | --- | --- | --- | --- |
| materials.core.mu_r | [min,max,step] | 필수 | 800.0~2000.0 | - | 상대 투자율 범위 |
| materials.core.epsilon_r | [min,max,step] | 필수 | 10.0~15.0 | - | 상대 유전율 |
| materials.core.conductivity_s_per_m | [min,max,step] | 필수 | 0.001~0.02 | - | 전도도 |

### 2.4 TX

| 경로 | 타입 | 필수? | 기본값 후보 | 파생? | 비고 |
| --- | --- | --- | --- | --- | --- |
| tx.module.present | bool | 선택 | true | - |  |
| tx.module.outer_w_mm | [min,max,step] | 필수 | 200~400 | - |  |
| tx.module.outer_h_mm | [min,max,step] | 필수 | 200~400 | - |  |
| tx.module.thickness_mm | [min,max,step] | 필수 | 4~120 | - |  |
| tx.module.offset_from_coil_mm | [min,max,step] | 선택 | 0~3 | - |  |
| tx.module.model | bool | 선택 | false | - | 비모델 |
| tx.position.center_x_mm | [min,max,step] | 선택 | 0.0 | - |  |
| tx.position.center_y_mm | [min,max,step] | 선택 | 0.0 | - |  |
| tx.position.center_z_mm | [min,max,step] | 필수 | 120~560 | - |  |

### 2.5 RX

| 경로 | 타입 | 필수? | 기본값 후보 | 파생? | 비고 |
| --- | --- | --- | --- | --- | --- |
| rx.module.present | bool | 선택 | true | - |  |
| rx.module.outer_w_mm | [min,max,step] | 필수 | 140~1653.71 | - | TV 폭 90% 이하 제한 반영 |
| rx.module.outer_h_mm | [min,max,step] | 필수 | 140~930.21 | - | TV 높이 90% 이하 |
| rx.module.thickness_mm | [min,max,step] | 필수 | 2~4 | - | constraints.rx_total_thickness_mm_max와 연계 |
| rx.module.offset_from_coil_mm | [min,max,step] | 선택 | 0~1 | - |  |
| rx.module.model | bool | 선택 | false | - |  |
| rx.position.center_x_mm | [min,max,step] | 선택 | 0.0 | - |  |
| rx.position.center_y_mm | [min,max,step] | 선택 | 0.0 | - |  |
| rx.position.center_z_mm | [min,max,step] | 필수 | 600~700 | - |  |
| rx.stack.total_thickness_mm | [min,max,step] | 필수 | 2.5~4.0 | - | constraints.rx_total_thickness_mm_max 이하 |

## 3) 파생값 규칙(샘플에서 암시된 부분)

- TV 폭/높이 파생
  - `tv.width_mm`, `tv.height_mm`는 `tv.screen_diag_in`과 `tv.aspect_ratio`로 계산 가능
- TV 위치
  - `tv.position.center_x_mm`는 TV back이 벽면(`wall_plane_x`)에 flush일 때 `tv.thickness_mm/2`
- Wall 위치
  - `wall.position.center_x_mm = wall_plane_x - wall.thickness_mm/2`
  - `wall.position.center_z_mm = floor_plane_z + wall.size_z_mm/2`
- Floor 위치
  - `floor.position.center_z_mm = floor_plane_z - floor.thickness_mm/2`
  - `floor.position.center_x_mm = wall_plane_x + floor.size_x_mm/2`
- RX/TX 상대 위치(제약)
  - RX는 TX보다 +Z 방향으로 `constraints.core_core_gap_mm` 만큼 (edge-to-edge) 배치 필요
  - RX 총 스택 두께 `rx.stack.total_thickness_mm`는 `constraints.rx_total_thickness_mm_max` 이하
- RX 크기 제한
  - `rx.module.outer_w_mm <= 0.9 * tv.width_mm`
  - `rx.module.outer_h_mm <= 0.9 * tv.height_mm`

## 4) 스펙 경로(dot-notation) 후보

현재 샘플에서 일관성 있게 사용할 수 있는 경로 후보를 다음과 같이 제안합니다.

### 4.1 공통
- `units.length`
- `coordinate_system.wall_plane_x_mm`
- `coordinate_system.floor_plane_z_mm`
- `constraints.core_core_gap_mm`
- `constraints.rx_total_thickness_mm_max`
- `constraints.tx_gap_from_tv_bottom_mm`
- `layout.right_edge_y_mm`

### 4.2 비모델(공통 prefix 유지)

옵션 A: 현행 구조 유지 (type1.toml 기준)
- `tv.*`, `wall.*`, `floor.*`

옵션 B: non_model prefix 도입 (non_model.toml 기준)
- `non_model.tv.*`, `non_model.wall.*`, `non_model.floor.*`

권장: **Option B** (비모델 객체 묶음 명시)

### 4.3 TX/RX
- `tx.module.present`
- `tx.module.outer_w_mm`
- `tx.module.outer_h_mm`
- `tx.module.thickness_mm`
- `tx.module.offset_from_coil_mm`
- `tx.module.model`
- `tx.position.center_x_mm`
- `tx.position.center_y_mm`
- `tx.position.center_z_mm`

- `rx.module.present`
- `rx.module.outer_w_mm`
- `rx.module.outer_h_mm`
- `rx.module.thickness_mm`
- `rx.module.offset_from_coil_mm`
- `rx.module.model`
- `rx.position.center_x_mm`
- `rx.position.center_y_mm`
- `rx.position.center_z_mm`
- `rx.stack.total_thickness_mm`

## 5) 향후 검증 규칙 (문서화만, 코드 미구현)
아래는 **TOML을 읽을 때 non_model 범위 유효성을 검사해야 한다는 요구사항**을 기록한 항목이다.
추후 구현 시에는 `min/max` 샘플링 범위 기준으로 **최솟값/최댓값 모두 유효한지** 확인해야 한다.

- non_model 범위 유효성 (TV/Wall/Floor 기반)
  - RX가 TV 내부에 들어오는지 검사: RX 모듈(또는 stack)의 **외곽 상자**가 TV 외곽 상자 안에 들어오는지 확인.
  - TX가 TV와 바닥 사이에 있는지 검사: TX 모듈의 상단이 TV 하단보다 낮고, 하단이 바닥보다 높도록 확인.
  - 샘플링 범위의 **최댓값이 과도하게 크지 않은지** 검사: 예) RX 외곽 치수 ≤ TV 폭/높이, TX 외곽 치수 ≤ TV-바닥 사이 여유 공간, Z 범위가 non_model 범위를 벗어나지 않는지 등.
- 코일 범위 유효성 (향후)
  - 코일 파라미터의 **최댓값에서 만들어지는 코일 형상**이 해당 TX/RX 모듈 범위 안에 들어오는지 확인.
  - 코일 외곽이 non_model 범위(특히 TV 내부/바닥 위)를 벗어나지 않는지 확인.

## 6) 다음 단계 제안
- 샘플 TOML을 스키마로 확정하며 **필수/선택** 및 **파생 규칙**을 코드로 반영.
- `non_model` prefix 채택 여부 확정 후 경로 통일.
- constraints 기반 파생(예: TX-RX 간격, RX 크기 상한) 규칙을 공식화.
