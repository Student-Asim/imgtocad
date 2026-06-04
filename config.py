import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
ENV_FILE = ROOT_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE)

def _get_path(name: str, default: str | Path) -> Path:
    raw = Path(os.getenv(name, str(default))).expanduser()
    if raw.is_absolute():
        return raw.resolve()
    return (ROOT_DIR / raw).resolve()
def _get_str(name: str, default: str) -> str:
    return os.getenv(name, default)


def _get_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _get_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# -----------------------------------------------------------------------------
# Paths and environment
# -----------------------------------------------------------------------------
PROJECT_DIR = ROOT_DIR
MODEL_DIR = ROOT_DIR
OUTPUT_DIR = Path(_get_str("OUTPUT_DIR", str(ROOT_DIR / "outputs"))).resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------------------------------------------------------
# Model configuration
# -----------------------------------------------------------------------------
YOLO_MODEL = _get_path(
    "YOLO_MODEL",
    ROOT_DIR / "runnable_floorplan" / "models" / "yolov8x.pt",
)
HORIZONNET_WEIGHTS = _get_path(
    "HORIZONNET_WEIGHTS",
    ROOT_DIR / "runnable_floorplan" / "models" / "model.pth",
)

PANORAMA_SIZE = (1024, 512)


# -----------------------------------------------------------------------------
# Furniture detection
# -----------------------------------------------------------------------------
FURNITURE_CONF = _get_float("FURNITURE_CONF", 0.12)
FURNITURE_IMGSZ = _get_int("FURNITURE_IMGSZ", 1024)

FURNITURE_CLASS_CONF = {
    "bed": _get_float("BED_CONF_THRESH", 0.35),
    "chair": _get_float("CHAIR_CONF_THRESH", 0.35),
    "sofa": _get_float("SOFA_CONF_THRESH", 0.35),
    "couch": _get_float("COUCH_CONF_THRESH", 0.14),
    "dining table": _get_float("DINING_TABLE_CONF_THRESH", 0.35),
    "bench": _get_float("BENCH_CONF_THRESH", 0.35),
    "tv": _get_float("TV_CONF_THRESH", 0.35),
}

FURNITURE_CLASSES = {
    "bed": "bed",
    "chair": "chair",
    "couch": "sofa",
    "sofa": "sofa",
    "dining table": "table",
    "bench": "sofa",
    "tv": "table",
}


# -----------------------------------------------------------------------------
# Roboflow / openings detection
# -----------------------------------------------------------------------------
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")
ROBOFLOW_URL = _get_str(
    "ROBOFLOW_URL",
    "https://detect.roboflow.com/door-window-detection-pipvh/1",
)
RF_CONNECT_TIMEOUT = _get_int("RF_CONNECT_TIMEOUT", 20)
RF_READ_TIMEOUT = _get_int("RF_READ_TIMEOUT", 60)
RF_RETRY_TOTAL = _get_int("RF_RETRY_TOTAL", 3)
RF_RETRY_CONNECT = _get_int("RF_RETRY_CONNECT", 3)
RF_RETRY_READ = _get_int("RF_RETRY_READ", 3)
RF_RETRY_BACKOFF = _get_float("RF_RETRY_BACKOFF", 1.0)
RF_FAIL_SOFT = _get_bool("RF_FAIL_SOFT", True)

RF_CLASS_MAP_ID = {
    0: "window",
    1: "door",
    2: "door",
}

DW_CLASS_CONF = {
    "door": _get_float("DOOR_CONF_THRESH", 0.40),
    "window": _get_float("WINDOW_CONF_THRESH", 0.30),
}


# -----------------------------------------------------------------------------
# Tiling / detection thresholds
# -----------------------------------------------------------------------------
TILE_W = _get_int("TILE_W", 512)
OVERLAP = _get_int("OVERLAP", 192)
CONF_THRESH = _get_float("CONF_THRESH", 0.50)
OVERLAP_THR = _get_int("OVERLAP_THR", 60)
NMS_IOU = _get_float("NMS_IOU", 0.25)


# -----------------------------------------------------------------------------
# Geometry / room layout
# -----------------------------------------------------------------------------
ROOM_SCALE = _get_float("ROOM_SCALE", 5.0)
WALL_THICKNESS = _get_float("WALL_THICKNESS", 0.18)
DOOR_WIDTH_M = _get_float("DOOR_WIDTH_M", 0.90)
WINDOW_WIDTH_M = _get_float("WINDOW_WIDTH_M", 1.20)
DXF_SCALE = _get_float("DXF_SCALE", 100.0)
MIN_EDGE_LEN = _get_float("MIN_EDGE_LEN", 0.20)
OPENING_MIN_WALL_MARGIN = _get_float("OPENING_MIN_WALL_MARGIN", 0.10)


# -----------------------------------------------------------------------------
# Corner extraction / polygon cleanup
# -----------------------------------------------------------------------------
PEAK_THRESH = _get_float("PEAK_THRESH", 0.38)
MIN_PEAK_DISTANCE = _get_int("MIN_PEAK_DISTANCE", 28)
CLUSTER_EPS = _get_int("CLUSTER_EPS", 14)


# -----------------------------------------------------------------------------
# Opening alignment heuristics
# -----------------------------------------------------------------------------
ALIGN_NEIGHBORHOOD_DEG = _get_float("ALIGN_NEIGHBORHOOD_DEG", 10.0)
ALIGN_VERTICAL_WEIGHT = _get_float("ALIGN_VERTICAL_WEIGHT", 0.18)
ALIGN_CENTER_PULL = _get_float("ALIGN_CENTER_PULL", 0.08)