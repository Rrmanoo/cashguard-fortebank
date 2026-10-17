# CashGuard

Baseline cashier-video review service for the ForteBank Datathon 26 case. A local vision pipeline proposes observable events, applies a fixed rule catalog and returns timestamps, evidence frames and references for human review. The repository preserves the currently deployed event-first algorithm before detection-quality improvements.

**Current detection quality is inadequate.** The latest private development run completed all 42 clips but detected none of the 22 positive cases: TP 0, TN 20, FP 0, FN 22. Median end-to-end API latency was 36.30 seconds and maximum latency was 148.94 seconds. These are development-set measurements, not unseen-video validation. The private recordings, labels, predictions, descriptions, evidence images and weights are not included in this repository.

## Pipeline

1. PyAV decodes the recording and samples full-resolution frames at 2.5 fps.
2. RT-DETRv2-R50 and ByteTrack detect and track people.
3. Grounding DINO Tiny proposes desk, safe, doorway and object regions.
4. RTMPose provides hand cues using ONNX Runtime on the CPU.
5. Qwen3-VL-8B-Instruct BF16 annotates overlapping seven-frame windows through a local vLLM endpoint, with up to four simultaneous requests.
6. Event normalization and deterministic rules decide whether to emit a finding. YuNet blurs detected faces in returned evidence; it does not identify people.

No task-specific fine-tuning is present in this baseline. The source archive generalizes deployment paths and launch commands; the event prompts, sampling, thresholds and rule logic are retained.

## Requirements

Use a Linux NVIDIA CUDA environment. The original deployment uses physical GPU 1 and the perception code deliberately rejects another `CUDA_VISIBLE_DEVICES` setting. GPU 0 belongs to other workloads in that deployment. Review this isolation guard explicitly before adapting to a different machine.

`requirements.txt` contains the API dependencies. `requirements-inference.txt` records the observed inference package versions; it is not a clean-install lockfile. Select compatible CUDA, PyTorch and vLLM builds for the target host. FFmpeg and ffprobe are required for example previews and inspection.

Provision pretrained weights before enabling offline execution. Repository names and pinned revisions are recorded in `docs/models.json`; auxiliary ONNX download URLs and checksums are in `docs/aux-models.json`. Expected folders/files are:

```text
models/
  qwen3-vl-8b/
  rtdetr-v2/
  grounding-dino/
  rtmpose-m-wholebody.onnx
  yunet.onnx
```

The RTMPose model must be extracted from the listed archive and saved under the expected filename. Model licenses remain applicable independently of this repository; the ByteTrack MIT notice is in `licenses/`.

## Start

From the repository root, create a private key file without printing the key:

```sh
python -c 'import os,secrets; fd=os.open("api.key",os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); os.write(fd,secrets.token_urlsafe(32).encode()); os.close(fd)'
bash scripts/serve-model.sh
```

After the model health endpoint on port 9016 is ready, start the web app in a second terminal:

```sh
bash scripts/serve-app.sh
```

The app is at `http://127.0.0.1:9017`; the gallery is at `/examples`. `PYTHON_BIN`, `VLLM_BIN`, `MODEL_PATH`, `CASHGUARD_MODELS`, `CASHGUARD_DATA`, `CASHGUARD_EXAMPLES` and `CASHGUARD_API_KEY_FILE` can override deployment locations. The model URL must remain loopback. Inference must not send recordings, frames or scene descriptions to cloud AI services.

## API

All `/api/v1` endpoints require `X-API-Key` or the browser's signed twelve-hour session. Signing in does not store the API key in browser storage.

- `POST /api/v1/analyze`: multipart MOV in field `file`, returning `job_id`.
- `GET /api/v1/jobs/{job_id}`: processing status and completed result.
- `GET /api/v1/rules`: catalog and enabled/disabled rules.
- `GET /api/v1/examples`: saved example summaries.
- `GET /api/v1/examples/{id}`: saved result.
- `GET /api/v1/examples/{id}/video`: authenticated MP4 preview with range support.
- `POST /api/v1/session`: create a browser session after authentication.
- `GET /healthz`: model availability and current admission state.

The service accepts one video at a time. An occupied worker returns HTTP 429. Uploads are limited to 128 MB and 180 seconds; analysis has a 270-second subprocess deadline. Failures stay failed rather than becoming negative findings.

## Private examples and evaluation

Supply your own authorized data under `data/videos/` and a private `data/labels.json` list with `filename`, `violation` and `timestamp_sec` fields. The reference labels are used for comparison only and are not passed to inference.

```sh
python scripts/run-examples.py
python scripts/evaluate.py --labels data/labels.json --videos data/videos --key-file api.key --output evaluation/results.json
```

`CASHGUARD_BASE` overrides the example runner's root. Saved example results and silent H.264 previews live under `examples/`, independently of ordinary expiring jobs. The gallery offers inline players and reference/model comparisons. Recordings and outputs remain private and must follow the dataset's retention terms.

`tools/local-viewer.mjs` is an optional laptop-only viewer. It expects a private tunnel on local port 9019 to forward to the protected server application, and a temporary `tools/access.key` containing the existing server key. It binds only `127.0.0.1:9017`, injects authentication for local API requests, renders the examples into initial HTML and removes the temporary key after startup. It does not make the server API public. Stop any existing listener on local port 9017 before starting this viewer.

```sh
node tools/local-viewer.mjs
```

The earlier `scripts/diagnose.py` is retained as legacy source and references an older model-response schema; it is not the current diagnostic entry point.

## Checks

```sh
python -m unittest discover -s tests -v
```

All 41 existing tests pass on the deployment runtime. The public snapshot has no private fixture videos. A clean installation on a separate CUDA machine has not been validated.
