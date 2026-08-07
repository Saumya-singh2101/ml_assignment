
import cv2
import numpy as np


def preprocess_canvas(image_bytes: bytes) -> bytes:
    """
    Advanced OpenCV preprocessing pipeline for
    handwritten whiteboard/canvas images.

    Pipeline:

    1. Decode image
    2. Convert to grayscale
    3. Denoise
    4. Adaptive thresholding
    5. Morphological cleanup
    6. Connected-component filtering
    7. Detect handwriting region
    8. Add intelligent padding
    9. Crop unnecessary whitespace
    10. Upscale small handwriting
    11. Encode back to PNG

    The function intentionally keeps the same
    bytes -> bytes interface so the existing
    FastAPI pipeline does not need to change.
    """

    # =========================================================
    # 1. DECODE IMAGE
    # =========================================================

    image_array = np.frombuffer(
        image_bytes,
        dtype=np.uint8,
    )

    image = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR,
    )

    if image is None:
        raise ValueError(
            "Could not decode canvas image."
        )


    # =========================================================
    # 2. BASIC IMAGE VALIDATION
    # =========================================================

    original_height, original_width = image.shape[:2]

    if (
        original_height < 10
        or original_width < 10
    ):
        raise ValueError(
            "Canvas image is too small."
        )


    # =========================================================
    # 3. GRAYSCALE
    # =========================================================

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )


    # =========================================================
    # 4. DENOISING
    # =========================================================

    # Median filtering is useful for removing
    # isolated pixel noise while preserving
    # handwriting edges.

    denoised = cv2.medianBlur(
        gray,
        3,
    )


    # =========================================================
    # 5. ADAPTIVE THRESHOLD
    # =========================================================

    # Adaptive thresholding works better than a
    # fixed threshold when the canvas has:
    #
    # - shadows
    # - slightly grey background
    # - uneven brightness
    # - anti-aliased pen strokes

    binary = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        10,
    )


    # =========================================================
    # 6. MORPHOLOGICAL CLEANUP
    # =========================================================

    # Close small gaps in handwriting.

    close_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (3, 3),
    )

    binary = cv2.morphologyEx(
        binary,
        cv2.MORPH_CLOSE,
        close_kernel,
        iterations=1,
    )


    # Remove isolated noise.

    open_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (2, 2),
    )

    binary = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        open_kernel,
        iterations=1,
    )


    # =========================================================
    # 7. CONNECTED COMPONENT ANALYSIS
    # =========================================================

    # Instead of blindly taking every non-white
    # pixel, identify connected regions.

    num_labels, labels, stats, _ = (
        cv2.connectedComponentsWithStats(
            binary,
            connectivity=8,
        )
    )

    if num_labels <= 1:
        return image_bytes


    # =========================================================
    # 8. REMOVE TINY NOISE COMPONENTS
    # =========================================================

    cleaned = np.zeros_like(binary)

    image_area = (
        original_width
        * original_height
    )

    # Minimum component area.
    #
    # This is deliberately small because
    # handwriting can contain tiny dots,
    # decimal points, etc.

    min_area = max(
        8,
        int(image_area * 0.000002),
    )

    valid_components = 0

    for label in range(
        1,
        num_labels,
    ):

        area = stats[
            label,
            cv2.CC_STAT_AREA,
        ]

        if area < min_area:
            continue

        cleaned[
            labels == label
        ] = 255

        valid_components += 1


    # If filtering removed everything,
    # fall back to the threshold image.

    if valid_components == 0:
        cleaned = binary


    # =========================================================
    # 9. FIND HANDWRITING BOUNDING BOX
    # =========================================================

    coords = cv2.findNonZero(
        cleaned
    )

    if coords is None:
        return image_bytes


    x, y, width, height = (
        cv2.boundingRect(coords)
    )


    # =========================================================
    # 10. IGNORE UNREASONABLY LARGE DETECTION
    # =========================================================

    # If OpenCV thinks practically the entire
    # canvas is handwriting, cropping it provides
    # little benefit.

    detected_area = (
        width * height
    )

    canvas_area = (
        original_width
        * original_height
    )

    coverage = (
        detected_area
        / canvas_area
    )


    # If detection covers almost the entire
    # canvas, keep the original frame.

    if coverage > 0.95:
        cropped = image.copy()

    else:

        # =====================================================
        # 11. INTELLIGENT PADDING
        # =====================================================

        # Padding scales with handwriting size.

        padding_x = max(
            30,
            int(width * 0.08),
        )

        padding_y = max(
            30,
            int(height * 0.15),
        )

        x1 = max(
            0,
            x - padding_x,
        )

        y1 = max(
            0,
            y - padding_y,
        )

        x2 = min(
            original_width,
            x + width + padding_x,
        )

        y2 = min(
            original_height,
            y + height + padding_y,
        )

        cropped = image[
            y1:y2,
            x1:x2,
        ]


    # =========================================================
    # 12. UPSCALE SMALL HANDWRITING
    # =========================================================

    h, w = cropped.shape[:2]

    min_dimension = 512

    smallest_dimension = min(
        h,
        w,
    )

    if (
        smallest_dimension
        < min_dimension
    ):

        scale = (
            min_dimension
            / smallest_dimension
        )

        new_width = max(
            1,
            int(w * scale),
        )

        new_height = max(
            1,
            int(h * scale),
        )

        cropped = cv2.resize(
            cropped,
            (
                new_width,
                new_height,
            ),
            interpolation=cv2.INTER_CUBIC,
        )


    # =========================================================
    # 13. LIMIT EXTREME IMAGE SIZE
    # =========================================================

    # Avoid accidentally generating an enormous
    # image after upscaling.

    max_dimension = 2048

    h, w = cropped.shape[:2]

    largest_dimension = max(
        h,
        w,
    )

    if (
        largest_dimension
        > max_dimension
    ):

        scale = (
            max_dimension
            / largest_dimension
        )

        new_width = max(
            1,
            int(w * scale),
        )

        new_height = max(
            1,
            int(h * scale),
        )

        cropped = cv2.resize(
            cropped,
            (
                new_width,
                new_height,
            ),
            interpolation=cv2.INTER_AREA,
        )


    # =========================================================
    # 14. FINAL LIGHT SHARPENING
    # =========================================================

    # Slight sharpening helps preserve thin
    # handwritten strokes after resizing.

    blurred = cv2.GaussianBlur(
        cropped,
        (0, 0),
        1.0,
    )

    sharpened = cv2.addWeighted(
        cropped,
        1.15,
        blurred,
        -0.15,
        0,
    )


    # =========================================================
    # 15. ENCODE TO PNG
    # =========================================================

    success, encoded = cv2.imencode(
        ".png",
        sharpened,
        [
            cv2.IMWRITE_PNG_COMPRESSION,
            3,
        ],
    )

    if not success:
        raise ValueError(
            "Could not encode processed image."
        )


    return encoded.tobytes()
