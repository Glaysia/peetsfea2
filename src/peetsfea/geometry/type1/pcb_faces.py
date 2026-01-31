from __future__ import annotations

from peetsfea.domain.type1.sampled_models import Type1Sample
from peetsfea.geometry.plan import BoxPlan
from peetsfea.sampling.rng import half_size

PCB_THICKNESS_MM = 1.7
IN_PLANE_SCALE = 0.95
ASPECT_MIN_RATIO = 0.2
INWARD_OFFSET_FACTOR = 1.02
FR4_OUTER_THICKNESS_MM = 0.04
COPPER_THICKNESS_MM = 0.04
FR4_INNER_THICKNESS_MM = 0.04
AIR_GAP_MM = 0.15


def _aspect_ok(dim_a: float, dim_b: float) -> bool:
    if dim_a <= 0 or dim_b <= 0:
        return False
    small = min(dim_a, dim_b)
    large = max(dim_a, dim_b)
    return (small / large) >= ASPECT_MIN_RATIO


def _scaled_dims(dim_a: float, dim_b: float) -> tuple[float, float]:
    return dim_a * IN_PLANE_SCALE, dim_b * IN_PLANE_SCALE


def _make_box(
    name: str,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    *,
    material: str = "pcb",
    model: bool = True,
) -> BoxPlan | None:
    if size[0] <= 0 or size[1] <= 0 or size[2] <= 0:
        return None
    return BoxPlan(name=name, center_mm=center, size_mm=size, material=material, model=model)


def _module_center(sample: Type1Sample) -> tuple[float, float, float]:
    center_x = sample.wall_plane_x_mm + half_size(sample.tx_module.thickness_mm)
    return center_x, sample.tx_position.center_y_mm, sample.tx_position.center_z_mm


def _face_axis_and_sign(face_name: str) -> tuple[int, int] | None:
    if face_name.endswith("PosX"):
        return 0, 1
    if face_name.endswith("NegX"):
        return 0, -1
    if face_name.endswith("PosY"):
        return 1, 1
    if face_name.endswith("NegY"):
        return 1, -1
    if face_name.endswith("PosZ"):
        return 2, 1
    if face_name.endswith("NegZ"):
        return 2, -1
    return None


def _face_enabled(flag: bool, dim_a: float, dim_b: float) -> bool:
    return flag and dim_a > 0 and dim_b > 0


def _active_face_flags(sample: Type1Sample) -> dict[str, bool]:
    tx_thk = sample.tx_module.thickness_mm
    tx_w = sample.tx_module.outer_w_mm
    tx_h = sample.tx_module.outer_h_mm
    return {
        "pos_x": _face_enabled(sample.tx_coil.outer_faces.pos_x, tx_w, tx_h),
        "neg_x": _face_enabled(sample.tx_coil.outer_faces.neg_x, tx_w, tx_h),
        "pos_y": _face_enabled(sample.tx_coil.outer_faces.pos_y, tx_thk, tx_h),
        "neg_y": _face_enabled(sample.tx_coil.outer_faces.neg_y, tx_thk, tx_h),
        "pos_z": _face_enabled(sample.tx_coil.outer_faces.pos_z, tx_thk, tx_w),
        "neg_z": _face_enabled(sample.tx_coil.outer_faces.neg_z, tx_thk, tx_w),
    }


def trim_tx_module_for_pcb(
    sample: Type1Sample,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    if not sample.tx_module.present:
        return center, size

    if size[0] <= 0 or size[1] <= 0 or size[2] <= 0:
        return center, size

    flags = _active_face_flags(sample)
    if not any(flags.values()):
        return center, size

    pcb_thk = sample.tx_pcb.total_thickness_mm or PCB_THICKNESS_MM
    trim = pcb_thk + AIR_GAP_MM

    min_x = center[0] - half_size(size[0])
    max_x = center[0] + half_size(size[0])
    min_y = center[1] - half_size(size[1])
    max_y = center[1] + half_size(size[1])
    min_z = center[2] - half_size(size[2])
    max_z = center[2] + half_size(size[2])

    if flags["pos_x"]:
        max_x -= trim
    if flags["neg_x"]:
        min_x += trim
    if flags["pos_y"]:
        max_y -= trim
    if flags["neg_y"]:
        min_y += trim
    if flags["pos_z"]:
        max_z -= trim
    if flags["neg_z"]:
        min_z += trim

    new_sx = max_x - min_x
    new_sy = max_y - min_y
    new_sz = max_z - min_z
    if new_sx <= 0 or new_sy <= 0 or new_sz <= 0:
        raise ValueError("TX module trimmed size must remain positive")

    new_center = ((min_x + max_x) * 0.5, (min_y + max_y) * 0.5, (min_z + max_z) * 0.5)
    return new_center, (new_sx, new_sy, new_sz)


def _layer_sequence(layer_count: int) -> list[tuple[str, str, float]]:
    effective_layers = 1 if layer_count == 1 else 2
    if effective_layers == 1:
        middle_fr4 = PCB_THICKNESS_MM - (
            FR4_OUTER_THICKNESS_MM + COPPER_THICKNESS_MM + FR4_INNER_THICKNESS_MM
        )
        return [
            ("FR4_Outer", "fr4", FR4_OUTER_THICKNESS_MM),
            ("Cu_Outer", "copper", COPPER_THICKNESS_MM),
            ("FR4_Middle", "fr4", middle_fr4),
            ("FR4_Inner", "fr4", FR4_INNER_THICKNESS_MM),
        ]
    middle_fr4 = PCB_THICKNESS_MM - (
        FR4_OUTER_THICKNESS_MM + COPPER_THICKNESS_MM + COPPER_THICKNESS_MM + FR4_INNER_THICKNESS_MM
    )
    return [
        ("FR4_Outer", "fr4", FR4_OUTER_THICKNESS_MM),
        ("Cu_Outer", "copper", COPPER_THICKNESS_MM),
        ("FR4_Middle", "fr4", middle_fr4),
        ("Cu_Inner", "copper", COPPER_THICKNESS_MM),
        ("FR4_Inner", "fr4", FR4_INNER_THICKNESS_MM),
    ]


def split_face_layers(face: BoxPlan, layer_count: int) -> list[BoxPlan]:
    axis_info = _face_axis_and_sign(face.name)
    if axis_info is None:
        return []
    axis, sign = axis_info
    layers = _layer_sequence(layer_count)
    if not layers:
        return []

    face_center = list(face.center_mm)
    face_size = list(face.size_mm)
    outer_edge = face_center[axis] + sign * half_size(face_size[axis])

    boxes: list[BoxPlan] = []
    offset = 0.0
    for label, material, thickness in layers:
        if thickness <= 0:
            continue
        layer_center = outer_edge - sign * (offset + thickness / 2)
        center = list(face.center_mm)
        size = list(face.size_mm)
        center[axis] = layer_center
        size[axis] = thickness
        boxes.append(
            BoxPlan(
                name=f"{face.name}_{label}",
                center_mm=(center[0], center[1], center[2]),
                size_mm=(size[0], size[1], size[2]),
                material=material,
                model=face.model,
            )
        )
        offset += thickness

    return boxes


def build_tx_outer_face_layers(sample: Type1Sample) -> list[BoxPlan]:
    faces = build_tx_outer_faces(sample)
    boxes: list[BoxPlan] = []
    for face in faces:
        boxes.extend(split_face_layers(face, sample.tx_pcb.layer_count))
    return boxes


def build_tx_outer_faces(sample: Type1Sample) -> list[BoxPlan]:
    if not sample.tx_module.present:
        return []

    tx_thk = sample.tx_module.thickness_mm
    tx_w = sample.tx_module.outer_w_mm
    tx_h = sample.tx_module.outer_h_mm

    if tx_thk <= 0 or tx_w <= 0 or tx_h <= 0:
        return []

    pcb_thk = sample.tx_pcb.total_thickness_mm or PCB_THICKNESS_MM
    inward_offset = INWARD_OFFSET_FACTOR * half_size(pcb_thk)

    center_x, center_y, center_z = _module_center(sample)

    boxes: list[BoxPlan] = []

    def add_face(
        name: str,
        enabled: bool,
        face_dims: tuple[float, float],
        size: tuple[float, float, float],
        center: tuple[float, float, float],
    ) -> None:
        if not enabled:
            return
        box = _make_box(name, center=center, size=size)
        if box is not None:
            boxes.append(box)

    # +X / -X faces (Y-Z plane)
    yz_scaled = _scaled_dims(tx_w, tx_h)
    face_center_x_pos = center_x + half_size(tx_thk) - inward_offset
    face_center_x_neg = center_x - half_size(tx_thk) + inward_offset
    add_face(
        "TX_PCB_Face_PosX",
        sample.tx_coil.outer_faces.pos_x,
        (tx_w, tx_h),
        (pcb_thk, yz_scaled[0], yz_scaled[1]),
        (face_center_x_pos, center_y, center_z),
    )
    add_face(
        "TX_PCB_Face_NegX",
        sample.tx_coil.outer_faces.neg_x,
        (tx_w, tx_h),
        (pcb_thk, yz_scaled[0], yz_scaled[1]),
        (face_center_x_neg, center_y, center_z),
    )

    # +Y / -Y faces (X-Z plane)
    xz_scaled = _scaled_dims(tx_thk, tx_h)
    face_center_y_pos = center_y + half_size(tx_w) - inward_offset
    face_center_y_neg = center_y - half_size(tx_w) + inward_offset
    add_face(
        "TX_PCB_Face_PosY",
        sample.tx_coil.outer_faces.pos_y,
        (tx_thk, tx_h),
        (xz_scaled[0], pcb_thk, xz_scaled[1]),
        (center_x, face_center_y_pos, center_z),
    )
    add_face(
        "TX_PCB_Face_NegY",
        sample.tx_coil.outer_faces.neg_y,
        (tx_thk, tx_h),
        (xz_scaled[0], pcb_thk, xz_scaled[1]),
        (center_x, face_center_y_neg, center_z),
    )

    # +Z / -Z faces (X-Y plane)
    xy_scaled = _scaled_dims(tx_thk, tx_w)
    face_center_z_pos = center_z + half_size(tx_h) - inward_offset
    face_center_z_neg = center_z - half_size(tx_h) + inward_offset
    add_face(
        "TX_PCB_Face_PosZ",
        sample.tx_coil.outer_faces.pos_z,
        (tx_thk, tx_w),
        (xy_scaled[0], xy_scaled[1], pcb_thk),
        (center_x, center_y, face_center_z_pos),
    )
    add_face(
        "TX_PCB_Face_NegZ",
        sample.tx_coil.outer_faces.neg_z,
        (tx_thk, tx_w),
        (xy_scaled[0], xy_scaled[1], pcb_thk),
        (center_x, center_y, face_center_z_neg),
    )

    return boxes
