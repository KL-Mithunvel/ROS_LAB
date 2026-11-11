import dataclasses
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import coin_d6 as cd  # noqa: E402

P = cd.LD06


def make_frame(start_deg: float, end_deg: float, dists_mm: list[int], inten: int = 100) -> bytes:
    body = bytearray(P.header + b"\x00\x00")                       # header + speed
    body += int(start_deg * 100).to_bytes(2, "little")
    for d in dists_mm:
        body += d.to_bytes(2, "little") + bytes([inten])
    body += int(end_deg * 100).to_bytes(2, "little") + b"\x00\x00"  # end angle + timestamp
    return bytes(body) + bytes([cd.crc8(bytes(body))])


def decode_all(parser, data):
    return [pts for pts in parser.feed(data)]


def test_crc8_known_table_entries():
    assert cd.crc8(b"\x01") == 0x4D      # LD06 table[1]
    assert cd.crc8(b"\x02") == 0x9A      # LD06 table[2]
    assert cd.crc8(b"") == 0


def test_frame_length_matches_profile():
    assert len(make_frame(0, 11, [1000] * 12)) == P.frame_len


def test_decodes_angles_and_distances():
    frames = decode_all(cd.FrameParser(P), make_frame(10.0, 21.0, [1000 + i for i in range(12)]))
    assert len(frames) == 1
    pts = frames[0]
    assert len(pts) == 12
    assert pts[0].angle_deg == pytest.approx(10.0)
    assert pts[-1].angle_deg == pytest.approx(21.0)
    assert pts[3].dist_m == pytest.approx(1.003)
    assert pts[0].intensity == 100


def test_angle_wraps_through_zero():
    pts = decode_all(cd.FrameParser(P), make_frame(355.0, 6.0, [500] * 12))[0]
    assert pts[0].angle_deg == pytest.approx(355.0)
    assert pts[-1].angle_deg == pytest.approx(6.0)
    assert all(0 <= p.angle_deg < 360 for p in pts)


def test_bad_checksum_is_rejected_and_counted():
    frame = bytearray(make_frame(0, 11, [800] * 12))
    frame[-1] ^= 0xFF
    parser = cd.FrameParser(P)
    assert decode_all(parser, bytes(frame)) == []
    assert parser.frames_ok == 0 and parser.frames_bad >= 1


def test_resyncs_after_garbage_and_split_reads():
    stream = b"\xde\xad\x54" + make_frame(0, 11, [700] * 12) + make_frame(12, 23, [900] * 12)
    parser = cd.FrameParser(P)
    out = []
    for i in range(0, len(stream), 7):              # feed in awkward 7-byte chunks
        out += decode_all(parser, stream[i:i + 7])
    assert [round(f[0].dist_m, 1) for f in out] == [0.7, 0.9]
    assert parser.frames_ok == 2


def test_scan_assembler_releases_one_scan_per_revolution():
    asm = cd.ScanAssembler()
    scans = []
    for start in range(0, 360, 12):
        pts = [cd.Point(start + i, 1.0, 50) for i in range(12)]
        if (done := asm.add(pts)):
            scans.append(done)
    done = asm.add([cd.Point(2.0, 1.0, 50)])        # wrap into the next revolution
    assert done is not None and len(done) == 360
    assert scans == []


def test_analyze_finds_header_and_spacing():
    data = b"".join(b"\xaa\x55" + bytes(range(i, i + 18)) for i in range(0, 200, 1))
    pat, hits, gap = cd.analyze(data)[0]
    assert pat == b"\xaa\x55" and gap == 20 and hits > 100


def test_profile_validation_catches_overflowing_layout():
    bad = dataclasses.replace(P, n_points=40)
    with pytest.raises(ValueError):
        bad.validate()


def test_load_profile_from_yaml(tmp_path):
    f = tmp_path / "p.yaml"
    f.write_text(
        'name: t\nheader: "AA 55"\nframe_len: 20\nn_points: 4\npoints_offset: 4\n'
        "point_stride: 3\ndist_offset: 0\nintensity_offset: 2\nstart_angle_offset: 2\n"
        "end_angle_offset: 16\nchecksum: sum8\n", encoding="utf-8")
    prof = cd.load_profile(f)
    assert prof.header == b"\xaa\x55" and prof.checksum == "sum8"


def test_load_profile_rejects_garbage(tmp_path):
    f = tmp_path / "p.yaml"
    f.write_text("just: text\n", encoding="utf-8")
    with pytest.raises(ValueError):
        cd.load_profile(f)
