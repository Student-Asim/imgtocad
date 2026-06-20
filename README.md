# 4-Wall Floor Plan API

This project generates a 2D floor plan from four uploaded wall images: **front**, **right**, **back**, and **left**.

It is a simplified version of the earlier panorama-based pipeline. The current code keeps only the four-wall workflow so the project is easier to run, debug, and maintain.

## Features

- Upload 4 wall images instead of a panorama
- Detect doors and windows on each wall
- Detect furniture on each wall
- Build a room layout from four wall sections
- Render floor plan outputs as PNG and DXF
- Save debug images for layout, openings, and furniture detection

## Project Structure

```text
api_endpoint/
├── main.py
├── config.py
└── runnable_floorplan/
    ├── __init__.py
    ├── types.py
    ├── core/
    │   ├── __init__.py
    │   ├── pipeline.py
    │   ├── io_utils.py
    │   └── registry.py
    ├── detectors/
    │   ├── __init__.py
    │   ├── furniture.py
    │   └── openings.py
    ├── geometry/
    │   ├── __init__.py
    │   ├── room_builder.py
    │   ├── transforms.py
    │   └── angles.py
    └── renderers/
        ├── __init__.py
        ├── floorplan_renderer.py
        ├── debug_renderer.py
        └── dxf_export.py
```

## Workflow

1. Load the detection models.
2. Upload four wall images.
3. Detect doors, windows, and furniture from each wall.
4. Convert detections into wall sections.
5. Build the room layout from the four wall sections.
6. Render the final floor plan as PNG and DXF.
7. Save debug output images.

## API

### `POST /generate`

Uploads four wall images and returns result metadata with output file paths.

#### Form fields

- `front`: image file
- `right`: image file
- `back`: image file
- `left`: image file

#### Example response

```json
{
  "status": "done",
  "job_id": "abc123",
  "walls": 4,
  "room_size_m": {
    "width": 4.0,
    "depth": 4.0,
    "area": 16.0,
    "scale_source": "fallback"
  },
  "wall_lengths_m": {
    "front": 4.0,
    "right": 4.0,
    "back": 4.0,
    "left": 4.0
  },
  "openings": [],
  "furniture": [],
  "png_path": ".../outputs/abc123_final_cad_image.png",
  "dxf_path": ".../outputs/abc123_final_cad.dxf",
  "layout_debug_png_path": ".../outputs/abc123_debug/room_detection.png",
  "openings_debug_png_path": ".../outputs/abc123_debug/front_door_window_detection.png",
  "furniture_debug_png_path": ".../outputs/abc123_debug/front_furniture_detection.png"
}
```

### Download endpoints

- `GET /download/{job_id}/png`
- `GET /download/{job_id}/dxf`
- `GET /download/{job_id}/layout-debug`
- `GET /download/{job_id}/openings-debug`
- `GET /download/{job_id}/furniture-debug`

## Installation

Create and activate a virtual environment, then install dependencies.

```bash
python -m venv venv
```

### Windows PowerShell

```powershell
venv\Scripts\Activate.ps1
```

### Install packages

```bash
pip install -r requirements.txt
```

## Run the app

```bash
uvicorn api_endpoint.main:app --reload
```

Then open:

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Configuration

The project reads settings from `config.py` and optional `.env` values.

Important settings include:

- `OUTPUT_DIR`
- `YOLO_MODEL`
- `HORIZONNET_WEIGHTS`
- `ROBOFLOW_API_KEY`
- `ROBOFLOW_URL`
- `DOOR_WIDTH_M`
- `WINDOW_WIDTH_M`
- `WALL_THICKNESS`
- `DXF_SCALE`

## Notes

- GitHub is **not** affected by local file deletion until those changes are committed and pushed.
- If import errors appear after refactoring, check `__init__.py` files for stale imports.
- If Python still loads removed modules, clear `__pycache__` folders and restart Uvicorn.

## Troubleshooting

### ImportError: cannot import name ...

This usually means one of these:

- a function was renamed but the old import is still used
- a package `__init__.py` still exports removed code
- the file was changed but old cache files still exist

### Fix steps

1. Check the exact function name in the module.
2. Update all imports to match the current function name.
3. Clean `__pycache__` folders.
4. Restart the server.

### Remove Python cache on Windows PowerShell

```powershell
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Filter *.pyc | Remove-Item -Force
```

## Current Goal

This codebase is now intended to be a **four-wall-only** floor plan generator. Panorama upload logic should be removed from the API and pipeline if it is no longer needed.
