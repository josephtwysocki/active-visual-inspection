"""Utilities for visualizing perception results."""

from pathlib import Path
from typing import Union

import cv2
import numpy as np

from src.perception.smoke_detector import DetectionResult


def save_annotated_image(
    image: Union[str, Path, np.ndarray],
    result: DetectionResult,
    output_path: Union[str, Path],
) -> Path:
    """Draw detections on an image and save the annotated result.

    Args:
        image:
            Path to an RGB image or an image as a NumPy array.
        result:
            Normalized perception result containing smoke detections.
        output_path:
            Location where the annotated image should be saved.

    Returns:
        Path to the saved annotated image.

    Raises:
        FileNotFoundError:
            If an image path is supplied but cannot be loaded.
        ValueError:
            If the supplied NumPy image is invalid.
        OSError:
            If the annotated image cannot be written.
    """

    if isinstance(image, (str, Path)):
        image_path = Path(image)
        annotated = cv2.imread(str(image_path))

        if annotated is None:
            raise FileNotFoundError(
                f"Could not load image: {image_path}"
            )

    elif isinstance(image, np.ndarray):
        if image.size == 0:
            raise ValueError("Image array is empty.")

        # Work on a copy so annotation does not modify the
        # original image supplied by the caller.
        annotated = image.copy()

    else:
        raise TypeError(
            "image must be a file path or NumPy array."
        )

    for detection in result.detections:
        x1, y1, x2, y2 = detection.bbox

        # Draw bounding box.
        cv2.rectangle(
            annotated,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2,
        )

        label = (
            f"{detection.label} "
            f"{detection.confidence:.2f}"
        )

        # Keep the label inside the image when the detection
        # touches the top edge.
        text_y = max(y1 - 10, 20)

        cv2.putText(
            annotated,
            label,
            (x1, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    success = cv2.imwrite(
        str(output_path),
        annotated,
    )

    if not success:
        raise OSError(
            f"Could not save annotated image: {output_path}"
        )

    return output_path