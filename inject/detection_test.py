def run_detection_pipeline(image, injected_clusters):
    # Placeholder for running the detection pipeline on the image
    # This function should implement the detection algorithm and return detected positions
    detected_positions = []  # Replace with actual detection logic
    return detected_positions

def compare_detections(detected_positions, ground_truth_positions, tolerance=0.5):
    # Compare detected positions with ground truth positions
    matches = []
    for detected in detected_positions:
        for truth in ground_truth_positions:
            if abs(detected - truth) < tolerance:
                matches.append((detected, truth))
                break
    return matches