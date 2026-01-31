from __future__ import annotations

from collections import Counter
import random

from peetsfea.domain.type1.sampled_models import (
    FloorSampleMaybe,
    MaterialSample,
    ModuleSample,
    PcbSample,
    PositionSample,
    PositionSampleMaybe,
    TvSampleMaybe,
    TxCoilOuterFacesSample,
    TxCoilInstanceSample,
    TxCoilSample,
    Type1SampleInput,
    WallSampleMaybe,
)
from peetsfea.domain.type1.spec_models import RangeSpec, Type1Spec
from peetsfea.geometry.type1.layer_modes import Segment2D, layer_rect_spirals
from peetsfea.geometry.type1.self_contact import detect_self_contact
from peetsfea.geometry.type1.pcb_faces import IN_PLANE_SCALE
from peetsfea.geometry.type1.spiral_mask import DdSplit, build_planar_rect_spiral_masks
from peetsfea.geometry.type1.topology import topology_from_segments
from peetsfea.sampling.rng import sample_int_range, sample_range


def _sample_optional(rng: random.Random, spec: RangeSpec | None) -> float | None:
    if spec is None:
        return None
    return sample_range(rng, spec)


def _sample_position_optional(rng: random.Random, position) -> PositionSampleMaybe:
    return PositionSampleMaybe(
        center_x_mm=_sample_optional(rng, position.center_x_mm),
        center_y_mm=_sample_optional(rng, position.center_y_mm),
        center_z_mm=_sample_optional(rng, position.center_z_mm),
    )


def _sample_position(rng: random.Random, position) -> PositionSample:
    return PositionSample(
        center_x_mm=sample_range(rng, position.center_x_mm),
        center_y_mm=sample_range(rng, position.center_y_mm),
        center_z_mm=sample_range(rng, position.center_z_mm),
    )


def _sample_module(rng: random.Random, module) -> ModuleSample:
    return ModuleSample(
        present=module.present,
        model=module.model,
        outer_w_mm=sample_range(rng, module.outer_w_mm),
        outer_h_mm=sample_range(rng, module.outer_h_mm),
        thickness_mm=sample_range(rng, module.thickness_mm),
        offset_from_coil_mm=sample_range(rng, module.offset_from_coil_mm),
    )


def sample_type1(spec: Type1Spec, seed: int) -> Type1SampleInput:
    rng = random.Random(seed)

    wall_plane_x = sample_range(rng, spec.coordinate_system.wall_plane_x_mm)
    floor_plane_z = sample_range(rng, spec.coordinate_system.floor_plane_z_mm)
    core_core_gap = sample_range(rng, spec.constraints.core_core_gap_mm)
    rx_total_thickness_mm_max = sample_range(rng, spec.constraints.rx_total_thickness_mm_max)
    tx_gap_from_tv_bottom = sample_range(rng, spec.constraints.tx_gap_from_tv_bottom_mm)

    materials_core = MaterialSample(
        mu_r=sample_range(rng, spec.materials.core.mu_r),
        epsilon_r=sample_range(rng, spec.materials.core.epsilon_r),
        conductivity_s_per_m=sample_range(rng, spec.materials.core.conductivity_s_per_m),
    )

    tx_module = _sample_module(rng, spec.tx.module)
    rx_module = _sample_module(rng, spec.rx.module)

    tx_position = _sample_position(rng, spec.tx.position)
    rx_position = _sample_position(rng, spec.rx.position)

    tx_pcb = PcbSample(
        layer_count=spec.tx.pcb.layer_count,
        total_thickness_mm=spec.tx.pcb.total_thickness_mm,
        dielectric_material=spec.tx.pcb.dielectric_material,
        dielectric_epsilon_r=spec.tx.pcb.dielectric_epsilon_r,
        stackup=spec.tx.pcb.stackup,
    )

    axis_map = {0: "yz", 1: "zx", 2: "xy"}

    def sample_tx_coil() -> TxCoilSample:
        reject_stats: Counter[str] = Counter()

        if not tx_module.present:
            return TxCoilSample(
                schema=spec.tx.coil.schema,
                type=spec.tx.coil.type,
                pattern=spec.tx.coil.pattern,
                max_spiral_count=spec.tx.coil.max_spiral_count,
                max_inner_pcb_count=spec.tx.coil.max_inner_pcb_count,
                instances=(),
                outer_faces=TxCoilOuterFacesSample(
                    pos_x=False,
                    neg_x=False,
                    pos_y=False,
                    neg_y=False,
                    pos_z=False,
                    neg_z=False,
                ),
            )

        # Loop only around the parts that may be invalid due to sampling
        # (e.g., spiral masks failing). This keeps Type1 sampling deterministic.
        for _ in range(2000):
            tx_thk = tx_module.thickness_mm
            tx_w = tx_module.outer_w_mm
            tx_h = tx_module.outer_h_mm

            instances: list[TxCoilInstanceSample] = []
            valid = True

            for inst_idx, inst_spec in enumerate(spec.tx.coil.instances):
                present = bool(sample_int_range(rng, inst_spec.present))

                inner_plane_axis_idx = sample_int_range(rng, spec.tx.coil.inner_plane_axis_idx)
                if inner_plane_axis_idx not in axis_map:
                    raise ValueError(f"Invalid tx.coil.inner_plane_axis_idx: {inner_plane_axis_idx}")
                inner_plane_axis = axis_map[inner_plane_axis_idx]

                inner_pcb_count = sample_int_range(rng, spec.tx.coil.inner_pcb_count)
                if inner_pcb_count < 0 or inner_pcb_count > spec.tx.coil.max_inner_pcb_count:
                    reject_stats[f"{inst_spec.name}:inner_pcb_count_oob"] += 1
                    valid = False
                    break

                half = tuple(sample_range(rng, r) for r in spec.tx.coil.inner_spacing_ratio_half)
                gaps = inner_pcb_count + 1
                k = (gaps + 1) // 2
                head = half[:k]
                if gaps % 2 == 1:
                    weights = head + tuple(reversed(head[:-1]))
                else:
                    weights = head + tuple(reversed(head))
                if sum(weights) <= 0:
                    reject_stats[f"{inst_spec.name}:inner_spacing_sum_le_0"] += 1
                    valid = False
                    break
                full_weights = weights + tuple(0.0 for _ in range((spec.tx.coil.max_inner_pcb_count + 1) - gaps))

                inst = TxCoilInstanceSample(
                    name=inst_spec.name,
                    face=inst_spec.face,
                    present=present,
                    min_trace_width_mm=sample_range(rng, spec.tx.coil.min_trace_width_mm),
                    min_trace_gap_mm=sample_range(rng, spec.tx.coil.min_trace_gap_mm),
                    edge_clearance_mm=sample_range(rng, spec.tx.coil.edge_clearance_mm),
                    fill_scale=sample_range(rng, spec.tx.coil.fill_scale),
                    pitch_duty=sample_range(rng, spec.tx.coil.pitch_duty),
                    layer_mode_idx=sample_int_range(rng, spec.tx.coil.layer_mode_idx),
                    radial_split_top_turn_fraction=sample_range(rng, spec.tx.coil.radial_split_top_turn_fraction),
                    radial_split_outer_is_top=bool(sample_int_range(rng, spec.tx.coil.radial_split_outer_is_top)),
                    spiral_count=sample_int_range(rng, spec.tx.coil.spiral_count),
                    spiral_turns=tuple(sample_int_range(rng, r) for r in spec.tx.coil.spiral_turns),
                    spiral_direction_idx=tuple(sample_int_range(rng, r) for r in spec.tx.coil.spiral_direction_idx),
                    spiral_start_edge_idx=tuple(sample_int_range(rng, r) for r in spec.tx.coil.spiral_start_edge_idx),
                    dd_split_axis_idx=sample_int_range(rng, spec.tx.coil.dd_split_axis_idx),
                    dd_gap_mm=sample_range(rng, spec.tx.coil.dd_gap_mm),
                    dd_split_ratio=sample_range(rng, spec.tx.coil.dd_split_ratio),
                    trace_layer_count=sample_int_range(rng, spec.tx.coil.trace_layer_count),
                    inner_plane_axis_idx=inner_plane_axis_idx,
                    inner_plane_axis=inner_plane_axis,
                    inner_pcb_count=inner_pcb_count,
                    inner_spacing_ratio_half=half,
                    inner_spacing_ratio=full_weights,
                )

                instances.append(inst)
                if not inst.present:
                    continue

                if inst.face in ("pos_x", "neg_x"):
                    face_u_mm = tx_w * IN_PLANE_SCALE
                    face_v_mm = tx_h * IN_PLANE_SCALE
                elif inst.face in ("pos_y", "neg_y"):
                    face_u_mm = tx_thk * IN_PLANE_SCALE
                    face_v_mm = tx_h * IN_PLANE_SCALE
                else:
                    face_u_mm = tx_thk * IN_PLANE_SCALE
                    face_v_mm = tx_w * IN_PLANE_SCALE

                dd = None
                if inst.spiral_count == 2:
                    dd = DdSplit(axis_idx=inst.dd_split_axis_idx, gap_mm=inst.dd_gap_mm, ratio=inst.dd_split_ratio)

                # Step08-5: reject/resample if the 2D wiring becomes meaningless:
                # - self-contact (accidental short)
                # - topology not being a single open path (endpoints!=2, branches, multiple components)
                effective_trace_layers = min(tx_pcb.layer_count, inst.trace_layer_count)
                layer_mode_idx_effective = inst.layer_mode_idx if effective_trace_layers >= 2 else 0

                try:
                    masks = build_planar_rect_spiral_masks(
                        face_u_size_mm=face_u_mm,
                        face_v_size_mm=face_v_mm,
                        spiral_count=inst.spiral_count,
                        turns=inst.spiral_turns,
                        direction_idx=inst.spiral_direction_idx,
                        start_edge_idx=inst.spiral_start_edge_idx,
                        edge_clearance_mm=inst.edge_clearance_mm,
                        fill_scale=inst.fill_scale,
                        pitch_duty=inst.pitch_duty,
                        min_trace_width_mm=inst.min_trace_width_mm,
                        min_trace_gap_mm=inst.min_trace_gap_mm,
                        dd=dd,
                    )
                except ValueError:
                    reject_stats[f"{inst.name}:mask_value_error"] += 1
                    valid = False
                    break

                try:
                    layered = layer_rect_spirals(
                        masks,
                        layer_mode_idx=layer_mode_idx_effective,
                        radial_split_top_turn_fraction=inst.radial_split_top_turn_fraction,
                        radial_split_outer_is_top=inst.radial_split_outer_is_top,
                    )
                except ValueError:
                    reject_stats[f"{inst.name}:layer_split_value_error"] += 1
                    valid = False
                    break

                if any(detect_self_contact(tuple(l.top_segments)).detected for l in layered):
                    reject_stats[f"{inst.name}:self_contact_top"] += 1
                    valid = False
                    break
                if any(detect_self_contact(tuple(l.bottom_segments)).detected for l in layered):
                    reject_stats[f"{inst.name}:self_contact_bottom"] += 1
                    valid = False
                    break

                total_segments = [
                    Segment2D(a=s.a, b=s.b, width_mm=0.0)
                    for l in layered
                    for s in (l.top_segments + l.bottom_segments)
                ]
                if inst.spiral_count == 2 and len(layered) >= 2:
                    p0 = layered[0].terminal_b
                    p1 = layered[1].terminal_a
                    if p0[0] == p1[0] or p0[1] == p1[1]:
                        total_segments.append(Segment2D(a=p0, b=p1, width_mm=0.0))
                    else:
                        mid = (p1[0], p0[1])
                        total_segments.append(Segment2D(a=p0, b=mid, width_mm=0.0))
                        total_segments.append(Segment2D(a=mid, b=p1, width_mm=0.0))

                topology = topology_from_segments(tuple(total_segments))
                if topology.component_count != 1:
                    reject_stats[f"{inst.name}:topology_component_count"] += 1
                    valid = False
                    break
                if topology.endpoints_count != 2:
                    reject_stats[f"{inst.name}:topology_endpoints_count"] += 1
                    valid = False
                    break
                if topology.has_branch:
                    reject_stats[f"{inst.name}:topology_has_branch"] += 1
                    valid = False
                    break

            if not valid:
                continue

            if not any(inst.present for inst in instances):
                reject_stats["no_instance_present"] += 1
                continue

            outer_faces = TxCoilOuterFacesSample(
                pos_x=any(inst.present and inst.face == "pos_x" for inst in instances),
                neg_x=any(inst.present and inst.face == "neg_x" for inst in instances),
                pos_y=any(inst.present and inst.face == "pos_y" for inst in instances),
                neg_y=any(inst.present and inst.face == "neg_y" for inst in instances),
                pos_z=any(inst.present and inst.face == "pos_z" for inst in instances),
                neg_z=any(inst.present and inst.face == "neg_z" for inst in instances),
            )

            return TxCoilSample(
                schema=spec.tx.coil.schema,
                type=spec.tx.coil.type,
                pattern=spec.tx.coil.pattern,
                max_spiral_count=spec.tx.coil.max_spiral_count,
                max_inner_pcb_count=spec.tx.coil.max_inner_pcb_count,
                instances=tuple(instances),
                outer_faces=outer_faces,
            )

        raise ValueError(
            "Failed to sample a valid tx.coil configuration after many attempts. "
            f"reject_stats={dict(reject_stats)}"
        )

    tx_coil = sample_tx_coil()

    tv = TvSampleMaybe(
        present=spec.tv.present,
        model=spec.tv.model,
        width_mm=sample_range(rng, spec.tv.width_mm),
        height_mm=sample_range(rng, spec.tv.height_mm),
        thickness_mm=sample_range(rng, spec.tv.thickness_mm),
        position=_sample_position_optional(rng, spec.tv.position),
    )

    wall = WallSampleMaybe(
        present=spec.wall.present,
        model=spec.wall.model,
        thickness_mm=sample_range(rng, spec.wall.thickness_mm),
        size_y_mm=sample_range(rng, spec.wall.size_y_mm),
        size_z_mm=sample_range(rng, spec.wall.size_z_mm),
        position=_sample_position_optional(rng, spec.wall.position),
    )

    floor = FloorSampleMaybe(
        present=spec.floor.present,
        model=spec.floor.model,
        thickness_mm=sample_range(rng, spec.floor.thickness_mm),
        size_x_mm=sample_range(rng, spec.floor.size_x_mm),
        size_y_mm=sample_range(rng, spec.floor.size_y_mm),
        position=_sample_position_optional(rng, spec.floor.position),
    )

    return Type1SampleInput(
        units_length=spec.units.length,
        wall_plane_x_mm=wall_plane_x,
        floor_plane_z_mm=floor_plane_z,
        core_core_gap_mm=core_core_gap,
        rx_total_thickness_mm_max=rx_total_thickness_mm_max,
        tx_gap_from_tv_bottom_mm=tx_gap_from_tv_bottom,
        rx_stack_total_thickness_mm=sample_range(rng, spec.rx.stack.total_thickness_mm),
        materials_core=materials_core,
        tx_module=tx_module,
        tx_position=tx_position,
        tx_pcb=tx_pcb,
        tx_coil=tx_coil,
        rx_module=rx_module,
        rx_position=rx_position,
        tv=tv,
        wall=wall,
        floor=floor,
    )
