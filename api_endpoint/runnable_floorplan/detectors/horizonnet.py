import numpy as np
import torch
import torchvision.transforms as T

from api_endpoint import config as C


def run_horizonnet(registry, img_pil):
    if registry.horizonnet_model is None:
        raise RuntimeError("HorizonNet not loaded.")
    device = next(registry.horizonnet_model.parameters()).device
    img_pil = img_pil.resize(C.PANORAMA_SIZE)
    img_np = np.array(img_pil)
    x = T.ToTensor()(img_pil).unsqueeze(0).to(device)
    with torch.no_grad():
        y_bon, y_cor = registry.horizonnet_model(x)
    cor = torch.sigmoid(y_cor)[0, 0].cpu().numpy()
    bon = y_bon.cpu().numpy()[0]
    return cor, bon, img_np, img_pil