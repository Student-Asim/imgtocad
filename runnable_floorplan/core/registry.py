import logging

import torch
from ultralytics import YOLO

from api_endpoint import config as C
from api_endpoint.model import HorizonNet

log = logging.getLogger("pipeline")


class ModelRegistry:
    def __init__(self) -> None:
        self.horizonnet_model = None
        self.furniture_model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def load(self) -> None:
        model = HorizonNet(backbone="resnet50", use_rnn=True).to(self.device)
        ckpt = torch.load(C.HORIZONNET_WEIGHTS, map_location=self.device)
        model.load_state_dict(ckpt.get("state_dict", ckpt), strict=True)
        model.eval()
        self.horizonnet_model = model
        log.info("HorizonNet loaded on %s", self.device)
        self.furniture_model = YOLO(C.YOLO_MODEL)
        log.info("Furniture YOLO loaded: %s", C.YOLO_MODEL)