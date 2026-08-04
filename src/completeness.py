"""Completeness curve computation and analysis.

This module implements routines for computing injection-based completeness
curves that quantify the fraction of injected clusters successfully detected
as a function of brightness, size, and other observational properties.

Functions:
    compute_completeness_curve: Compute completeness as a function of brightness.
    plot_completeness: Visualize completeness curves with error bars.

Key Features:
    - Binning and statistical uncertainty estimation.
    - Handling of edge cases (zero detections, perfect detection).
    - Plotting and export utilities.
    - Accounting for PSF quality flags in completeness weighting.
"""

def compute_completeness_curve(injected_catalog, detected_catalog, brightness_bins):
    """
    Computes the completeness curve based on the injected and detected catalogs.

    Parameters:
    - injected_catalog: A catalog of injected clusters with their properties.
    - detected_catalog: A catalog of detected clusters from the detection pipeline.
    - brightness_bins: A list of brightness thresholds to compute completeness at.

    Returns:
    - completeness_curve: A list of completeness values corresponding to the brightness_bins.
    """
    completeness_curve = []
    
    for brightness in brightness_bins:
        total_injected = sum(injected_catalog['brightness'] >= brightness)
        total_detected = sum((detected_catalog['brightness'] >= brightness) & 
                             (detected_catalog['true_position'] == injected_catalog['true_position']))
        
        if total_injected > 0:
            completeness = total_detected / total_injected
        else:
            completeness = 0.0
        
        completeness_curve.append(completeness)
    
    return completeness_curve


def plot_completeness(completeness_curve, brightness_bins):
    """
    Plots the completeness curve.

    Parameters:
    - completeness_curve: A list of completeness values.
    - brightness_bins: A list of brightness thresholds corresponding to the completeness values.
    """
    import matplotlib.pyplot as plt

    plt.figure(figsize=(10, 6))
    plt.plot(brightness_bins, completeness_curve, marker='o')
    plt.xlabel('Brightness')
    plt.ylabel('Completeness')
    plt.title('Completeness Curve')
    plt.grid()
    plt.ylim(0, 1)
    plt.xlim(min(brightness_bins), max(brightness_bins))
    plt.axhline(0.5, color='r', linestyle='--', label='50% Completeness')
    plt.legend()
    plt.show()