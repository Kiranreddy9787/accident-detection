"""Training and sequence-based inference for accident scene classification.

The classifier uses a MobileNetV3-Small CNN. It does not make predictions until
it receives a trained checkpoint produced by the ``train`` command below.
"""

import argparse
from pathlib import Path
from typing import Any

import cv2


MODEL_FILENAME = "accident_classifier.pt"
REQUIRED_CLASS_NAMES = {"accident", "no_accident"}


class AccidentModelError(RuntimeError):
    """Raised when accident-model training or inference cannot proceed."""


def _import_torch():
    try:
        import torch
        from torchvision import datasets, models, transforms
    except Exception as error:
        raise AccidentModelError("PyTorch and torchvision are required. Run 'pip install -r requirements.txt'.") from error
    return torch, datasets, models, transforms


def build_model(num_classes: int = 2, pretrained: bool = False):
    """Build a compact MobileNetV3-Small CNN classifier."""
    _torch, _datasets, models, _transforms = _import_torch()
    weights = models.MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
    model = models.mobilenet_v3_small(weights=weights)
    model.classifier[3] = __import__("torch").nn.Linear(model.classifier[3].in_features, num_classes)
    return model


def get_model_status(model_path: str | Path) -> dict[str, str]:
    """Return a UI-safe availability state without inventing a prediction."""
    path = Path(model_path)
    if not path.is_file():
        return {
            "status": "model_unavailable",
            "message": f"Model not trained/available. Place a trained '{MODEL_FILENAME}' file in models/.",
        }
    return {"status": "available", "message": "Trained accident classification model is available."}


def load_trained_model(model_path: str | Path):
    """Load a checkpoint saved by ``train_model`` for CPU inference."""
    status = get_model_status(model_path)
    if status["status"] != "available":
        return None, status

    torch, _datasets, _models, _transforms = _import_torch()
    try:
        try:
            checkpoint = torch.load(model_path, map_location="cpu", weights_only=True)
        except TypeError:  # Compatibility with older PyTorch versions.
            checkpoint = torch.load(model_path, map_location="cpu")
        class_names = checkpoint["class_names"]
        if set(class_names) != REQUIRED_CLASS_NAMES:
            raise KeyError("Checkpoint classes must be exactly 'accident' and 'no_accident'.")
        model = build_model(num_classes=len(class_names), pretrained=False)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        return (model, class_names), status
    except Exception as error:
        raise AccidentModelError(f"The trained accident model could not be loaded: {error}") from error


def classify_video_window(
    video_path: str | Path,
    model_path: str | Path,
    sample_count: int = 12,
    minimum_frames: int = 8,
) -> dict[str, Any]:
    """Classify a short sequence, never a single arbitrary video frame.

    A scene is labelled ACCIDENT only if its average accident probability is at
    least 0.65 *and* at least 60% of sampled frames cross the same threshold.
    These thresholds are demonstration defaults, not validated accuracy claims.
    """
    if sample_count < minimum_frames or minimum_frames < 2:
        raise ValueError("sample_count must be at least minimum_frames, and minimum_frames must be at least 2.")

    model_data, status = load_trained_model(model_path)
    if model_data is None:
        return status

    source = Path(video_path)
    if not source.is_file():
        raise AccidentModelError("The source video for accident classification could not be found.")

    torch, _datasets, _models, transforms = _import_torch()
    capture = cv2.VideoCapture(str(source))
    try:
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames < minimum_frames:
            return {
                "status": "insufficient_frames",
                "message": f"At least {minimum_frames} readable frames are needed for accident classification.",
            }

        # Evenly sample a window across the uploaded scene rather than deciding
        # from a single frame. Duplicate indices are avoided on short videos.
        indices = sorted({round(index * (total_frames - 1) / (sample_count - 1)) for index in range(sample_count)})
        preprocess = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        tensors = []
        for frame_index in indices:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            readable, frame = capture.read()
            if readable:
                tensors.append(preprocess(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
    finally:
        capture.release()

    if len(tensors) < minimum_frames:
        return {
            "status": "insufficient_frames",
            "message": f"Only {len(tensors)} frames could be read; at least {minimum_frames} are required.",
        }

    model, class_names = model_data
    accident_index = class_names.index("accident")
    with torch.no_grad():
        probabilities = torch.softmax(model(torch.stack(tensors)), dim=1)[:, accident_index].tolist()
    mean_accident_probability = sum(probabilities) / len(probabilities)
    positive_frames = sum(probability >= 0.65 for probability in probabilities)
    is_accident = mean_accident_probability >= 0.65 and positive_frames / len(probabilities) >= 0.60
    return {
        "status": "classified",
        "label": "ACCIDENT" if is_accident else "NO ACCIDENT",
        "confidence": round(mean_accident_probability if is_accident else 1 - mean_accident_probability, 4),
        "accident_probability": round(mean_accident_probability, 4),
        "frames_evaluated": len(probabilities),
        "positive_frames": positive_frames,
        "peak_frame_index": indices[max(range(len(probabilities)), key=probabilities.__getitem__)],
        "peak_accident_probability": round(max(probabilities), 4),
    }


def extract_video_frames(source_directory: str | Path, destination_directory: str | Path, every_n_frames: int = 15) -> int:
    """Convert labelled videos in one directory into JPEG training frames."""
    source_directory, destination_directory = Path(source_directory), Path(destination_directory)
    if every_n_frames < 1:
        raise ValueError("every_n_frames must be at least 1.")
    destination_directory.mkdir(parents=True, exist_ok=True)
    saved = 0
    for video_path in source_directory.iterdir():
        if video_path.suffix.lower() not in {".mp4", ".avi", ".mov", ".mkv"}:
            continue
        capture = cv2.VideoCapture(str(video_path))
        frame_number = 0
        try:
            while True:
                readable, frame = capture.read()
                if not readable:
                    break
                if frame_number % every_n_frames == 0:
                    output = destination_directory / f"{video_path.stem}_{frame_number:06d}.jpg"
                    if cv2.imwrite(str(output), frame):
                        saved += 1
                frame_number += 1
        finally:
            capture.release()
    return saved


def train_model(data_directory: str | Path, output_path: str | Path, epochs: int = 10, batch_size: int = 16):
    """Train and evaluate the CNN using dataset/train and dataset/val images."""
    torch, datasets, _models, transforms = _import_torch()
    data_directory = Path(data_directory)
    train_path, validation_path = data_directory / "train", data_directory / "val"
    if not train_path.is_dir() or not validation_path.is_dir():
        raise AccidentModelError("Dataset must contain train/ and val/ folders.")

    transform = transforms.Compose([
        transforms.Resize((224, 224)), transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    train_dataset = datasets.ImageFolder(train_path, transform=transform)
    validation_dataset = datasets.ImageFolder(validation_path, transform=transform)
    if set(train_dataset.classes) != REQUIRED_CLASS_NAMES or validation_dataset.classes != train_dataset.classes:
        raise AccidentModelError("Both splits must contain accident/ and no_accident/ class folders.")
    if not train_dataset or not validation_dataset:
        raise AccidentModelError("Both train and validation folders need labelled images.")

    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    validation_loader = torch.utils.data.DataLoader(validation_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    model = build_model(num_classes=2, pretrained=True)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
    loss_function = torch.nn.CrossEntropyLoss()

    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        for images, labels in train_loader:
            optimizer.zero_grad()
            loss = loss_function(model(images), labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * images.size(0)
        print(f"Epoch {epoch + 1}/{epochs} - train loss: {running_loss / len(train_dataset):.4f}")

    model.eval()
    correct = total = 0
    with torch.no_grad():
        for images, labels in validation_loader:
            predictions = model(images).argmax(dim=1)
            correct += (predictions == labels).sum().item()
            total += labels.size(0)
    validation_accuracy = correct / total
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state_dict": model.state_dict(), "class_names": train_dataset.classes}, output_path)
    print(f"Validation accuracy: {validation_accuracy:.2%} ({correct}/{total})")
    print(f"Saved trained model to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Accident CNN training and inference utility")
    subparsers = parser.add_subparsers(dest="command", required=True)
    train_parser = subparsers.add_parser("train")
    train_parser.add_argument("--data-dir", default="dataset")
    train_parser.add_argument("--output", default=f"models/{MODEL_FILENAME}")
    train_parser.add_argument("--epochs", type=int, default=10)
    train_parser.add_argument("--batch-size", type=int, default=16)
    extract_parser = subparsers.add_parser("extract-frames")
    extract_parser.add_argument("source_directory")
    extract_parser.add_argument("destination_directory")
    extract_parser.add_argument("--every-n-frames", type=int, default=15)
    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--model", default=f"models/{MODEL_FILENAME}")
    args = parser.parse_args()
    if args.command == "train":
        train_model(args.data_dir, args.output, args.epochs, args.batch_size)
    elif args.command == "extract-frames":
        print(f"Saved {extract_video_frames(args.source_directory, args.destination_directory, args.every_n_frames)} frames.")
    else:
        print(get_model_status(args.model)["message"])


if __name__ == "__main__":
    main()
