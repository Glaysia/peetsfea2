# Type1 TOML 스펙(현행 구현 반영)

이 문서는 `examples/type1.toml` 및 현재 구현(`src/peetsfea/domain/type1/parse.py`, `.../interpreter.py`)을 기준으로, **Type1 입력 스펙 구조**와 **파생/제약/코일 유전자(tx.coil)** 를 정리한다.

---

## 1) 값 표현/샘플링 규칙

대부분의 수치 필드는 아래 형태를 모두 허용한다:
- 스칼라: `foo = 12.3` → 고정값
- 범위: `foo = [min, max, step]`
  - `step=0` 또는 `min=max`면 고정값으로 취급

정수 범위도 동일하게 `[min, max, step]`를 사용한다.

---

## 2) 최상위 섹션 구조

- `units`
- `coordinate_system`
- `constraints`
- `layout`
- `materials.core`
- `tv`, `wall`, `floor`
- `tx.module`, `tx.position`, `tx.pcb`, `tx.coil`
- `rx.module`, `rx.position`, `rx.stack`

> 주의: TOML에 추가 키가 있어도 parser가 강제 에러를 내지 않으며, “현재 코드가 읽는 키”만 사용된다.

---

## 3) 위치/제약 파생 규칙(현재 interpreter 동작)

### 3.1 TV/Wall/Floor position 기본값
- `tv.position.center_x_mm` 미지정 시: `wall_plane_x + tv.thickness_mm/2` (TV back이 벽면에 flush)
- `wall.position.center_x_mm` 미지정 시: `wall_plane_x - wall.thickness_mm/2`
- `floor.position.center_z_mm` 미지정 시: `floor_plane_z - floor.thickness_mm/2`

### 3.2 TV가 present일 때 TX/RX 위치 강제 정렬
- `tx.position.center_y_mm`와 `rx.position.center_y_mm`는 TV의 `center_y_mm`로 강제
- TX Z:
  - `tx_center_z = tv_bottom_z - tx_gap_from_tv_bottom_mm - tx_core_h/2`
- RX Z:
  - `rx_center_z = tx_center_z + tx_core_h/2 + core_core_gap_mm + rx_core_h/2`

### 3.3 RX 크기 제약(현재 domain validation)
- TV가 present일 때:
  - `rx.module.outer_w_mm <= 0.9 * tv.width_mm`
  - `rx.module.outer_h_mm <= 0.9 * tv.height_mm`

---

## 4) `tx.pcb` (입력은 받지만, 현재 geometry에 부분 반영)

필드(현행):
- `layer_count`: 1 또는 2
- `total_thickness_mm`
- `dielectric_material`, `dielectric_epsilon_r`
- `[[tx.pcb.stackup]]` (dict list로 그대로 보존)

현재 구현에서는 coil 3D 생성이 “box-strip” 기반이며, stackup dict를 정밀하게 사용하지는 않는다(향후 확장 지점).

---

## 5) `tx.coil` (필수) — `schema="instances_v1"`

`tx.coil.schema`는 반드시 `"instances_v1"` 이어야 한다(레거시/하위호환 없음).

### 5.1 기본 필드
- `type`: 현재 `"pcb_trace"` 사용
- `pattern`: 현재 `"spiral"` 사용

### 5.2 제조/제약(유전자 범위)
- `min_trace_width_mm`: 예) `[0.2, 0.2, 0.0]`
- `min_trace_gap_mm`
- `edge_clearance_mm`
- `fill_scale`: (0,1] 범위 권장
- `pitch_duty`: >0 권장 (width = pitch_duty * pitch)

### 5.3 2-layer 분배(겹침 최소화)
- `trace_layer_count`: 1 또는 2
  - 실제 사용 레이어 수는 `min(tx.pcb.layer_count, trace_layer_count)`
  - 1이면 `layer_mode_idx`는 강제로 0(single-layer)로 처리
- `layer_mode_idx`: `[0,2,1]` 같은 정수 범위
  - 0 = single_layer_top
  - 1 = radial_split
  - 2 = alternate_turns
- `radial_split_top_turn_fraction`: [0,1]
- `radial_split_outer_is_top`: 0/1

### 5.4 Spiral / DD(dual-spiral)
- `max_spiral_count`: 현재 구현에서 2로 고정
- `spiral_count`: 1 또는 2
- `spiral_turns`: 길이 2의 int-range vector
- `spiral_direction_idx`: 길이 2의 int-range vector
  - 0 = CW, 1 = CCW
- `spiral_start_edge_idx`: 길이 2의 int-range vector
  - plane 기준 edge index:
    - 0 = +u, 1 = -u, 2 = +v, 3 = -v
- `dd_split_axis_idx`: 0(u split) / 1(v split)
- `dd_gap_mm`
- `dd_split_ratio`: (0,1)

### 5.5 구조(향후 확장용, 현재 geometry에는 미반영)
아래 필드들은 현재 **샘플링/저장까지는 되지만**, 3D coil 생성에는 아직 사용하지 않는다:
- `inner_plane_axis_idx` (0=yz, 1=zx, 2=xy)
- `inner_pcb_count`
- `inner_spacing_ratio_half` (좌우 대칭 벡터)
- `max_inner_pcb_count`

### 5.6 인스턴스(멀티 face)
`[[tx.coil.instances]]`는 “코일 인스턴스 목록”이며, 각 인스턴스가 어떤 face에 코일을 만들지 정의한다.
- 필드:
  - `name`: 식별자(문자/숫자/언더스코어). 미지정 시 자동 생성.
  - `face`: `"pos_x" | "neg_x" | "pos_y" | "neg_y" | "pos_z" | "neg_z"`
  - `present`: 0/1 int-range (예: `[1,1,0]`)
- 파이프라인은 `present=1`인 인스턴스 각각에 대해 3D coil을 생성한다.
- 참고: `outer_faces`는 더 이상 입력이 아니며, `instances`로부터 자동 파생된다.

---

## 6) 지금 기준으로 “안 되는 것/미구현”
- `tv.screen_diag_in`, `tv.aspect_ratio`로 width/height를 자동 계산하는 기능은 없다(필요하면 TOML에 `width_mm/height_mm`를 직접 넣어야 함).
- 코일은 polyline-sweep가 아니라 box-strip 근사이다.
- 인스턴스 간 series/parallel 연결(하나의 연속 도체로 연결)은 아직 없다(인스턴스별 독립 도체).
- L/R/손실/SRF는 이 repo에서 결정론적으로 계산하지 않는다(데이터셋 파이프라인은 genes/derived 저장까지).
