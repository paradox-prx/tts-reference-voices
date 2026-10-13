import csv
import io
import json
import zipfile

from studio import export
from studio.rows_io import parse_rows, parse_speakers_csv, speaker_tag


def test_speaker_tag():
    assert speaker_tag("Speaker_1.wav") == "speaker_1"
    assert speaker_tag("Ali Khan.WAV") == "ali_khan"


def test_parse_csv_rows():
    data = "id,text,speaker,tags,seed\n7,Hello.,Speaker_1,emotion:anger,42\n,Second row.,,,\n,,,,\n"
    rows = parse_rows(data.encode(), "rows.csv")
    assert [r.id for r in rows] == ["7", "0002"] and rows[0].speaker == "speaker_1" and rows[0].seed == 42
    assert rows[1].speaker is None and rows[1].seed is None


def test_parse_jsonl_and_json():
    rows = parse_rows(b'{"text": "a"}\n{"text": "b", "speaker": "X"}\n', "r.jsonl")
    assert [r.text for r in rows] == ["a", "b"] and rows[1].speaker == "x"
    rows = parse_rows(json.dumps([{"text": "a", "id": "q"}]).encode(), "r.json")
    assert rows[0].id == "q"


def test_speakers_csv():
    assert parse_speakers_csv("filename,transcript\nSpeaker_1.wav,hello there\n") == {"speaker_1": "hello there"}


def test_zip_layout(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF....WAVEfake")
    meta = [{"audio_path": "wavs/speaker_1/0001.wav", "text": "hi", "speaker": "speaker_1", "tags": "", "seed": 1,
             "duration_s": 1.0, "sample_rate": 24000, "qc_status": "pass", "wer": ""}]
    entries = [("wavs/speaker_1/0001.wav", wav), ("metadata.csv", export.metadata_csv(meta)),
               ("metadata.jsonl", export.metadata_jsonl(meta)), ("rejected.csv", export.rejected_csv([])),
               ("speakers/speaker_1.wav", wav),
               ("speakers.csv", export.speakers_csv([{"tag": "speaker_1", "transcript": "ref"}]))]
    data = b"".join(export.iter_zip(entries))
    z = zipfile.ZipFile(io.BytesIO(data))
    assert z.namelist() == [e[0] for e in entries]
    rows = list(csv.DictReader(io.StringIO(z.read("metadata.csv").decode())))
    assert list(rows[0].keys()) == export.META_FIELDS and rows[0]["audio_path"] in z.namelist()
    assert json.loads(z.read("metadata.jsonl").decode().splitlines()[0])["speaker"] == "speaker_1"
    name, pipe = export.convert(meta, "pipe_csv")
    assert pipe.decode().splitlines()[1] == "wavs/speaker_1/0001.wav|hi|speaker_1"
